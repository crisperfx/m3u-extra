import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

APP_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/downloads")).resolve()
NDL_BINARY = os.environ.get("NDL_BINARY", "/usr/local/bin/N_m3u8DL-RE")
FFMPEG_BINARY = os.environ.get("FFMPEG_BINARY") or shutil.which("ffmpeg") or "ffmpeg"
MP4DECRYPT_BINARY = os.environ.get("MP4DECRYPT_BINARY", "/usr/local/bin/mp4decrypt")
PORT = int(os.environ.get("PORT", "8000"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "3"))
WEB_USER = os.environ.get("WEB_USER")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD")
EXT_TOKEN = os.environ.get("EXT_TOKEN", "")

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path(os.environ.get("LOG_DIR", str(DOWNLOAD_DIR / ".logs"))).resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")


def log_file_path(job_id):
    return LOG_DIR / f"{job_id}.log"


def metadata_file_path(job_id):
    return LOG_DIR / f"{job_id}.json"


def valid_job_id(job_id):
    return bool(JOB_ID_PATTERN.match(job_id or ""))


def read_archived_info(job_id):
    if not valid_job_id(job_id):
        return None
    try:
        return json.loads(metadata_file_path(job_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_archived_info(job):
    info = job.info()
    info["archived"] = True
    try:
        metadata_file_path(job.id).write_text(
            json.dumps(info, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024

_jobs = {}
_jobs_lock = threading.Lock()

BINARY_NAMES = {"N_m3u8DL-RE", "N_m3u8DL-RE.exe"}
PHASE_PATTERNS = (
    ("parsing", re.compile(r"parsing streams|loading url|content matched|selected streams|extracted,? there are", re.I)),
    ("downloading", re.compile(r"start downloading|reading media info|binary merging|extracting[^\r\n]*subtitle|pssh\(wv\)|kid:", re.I)),
    ("decrypting", re.compile(r"decrypting using", re.I)),
    ("muxing", re.compile(r"muxing to|cleaning files|rename to", re.I)),
)
TERMINAL_PHASES = {"muxing", "klaar", "gefaald", "geannuleerd"}
PROGRESS_PATTERN = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*%")
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
TIMESTAMP_PATTERN = re.compile(r"(?=\d{2}:\d{2}:\d{2}\.\d{3}\s)")
HIDDEN_DIRS = {"@eaDir", "#recycle", "#snapshot", "@tmp", "$RECYCLE.BIN"}
LANGUAGE_LABELS = {
    "nederlands": "Nederlands",
    "nld": "Nederlands",
    "dut": "Nederlands",
    "nl": "Nederlands",
    "english": "Engels",
    "eng": "Engels",
    "en": "Engels",
    "frans": "Frans",
    "fra": "Frans",
    "fre": "Frans",
    "fr": "Frans",
    "duits": "Duits",
    "deu": "Duits",
    "ger": "Duits",
    "de": "Duits",
    "spaans": "Spaans",
    "spa": "Spaans",
    "es": "Spaans",
    "italiaans": "Italiaans",
    "ita": "Italiaans",
    "it": "Italiaans",
    "portugees": "Portugees",
    "por": "Portugees",
    "pt": "Portugees",
    "japans": "Japans",
    "jpn": "Japans",
    "ja": "Japans",
    "koreaans": "Koreaans",
    "kor": "Koreaans",
    "ko": "Koreaans",
    "chinees": "Chinees",
    "zho": "Chinees",
    "chi": "Chinees",
    "zh": "Chinees",
    "russisch": "Russisch",
    "rus": "Russisch",
    "ru": "Russisch",
    "arabisch": "Arabisch",
    "ara": "Arabisch",
    "ar": "Arabisch",
    "hindi": "Hindi",
    "hin": "Hindi",
    "hi": "Hindi",
}
def build_language_pattern(mapping):
    alternatives = "|".join(sorted((re.escape(code) for code in mapping), key=len, reverse=True))
    return re.compile(r"(?<!\w)(" + alternatives + r")(?!\w)", re.I)


LANGUAGE_CODE_LABELS = {code: label for code, label in LANGUAGE_LABELS.items() if len(code) <= 3}
LANGUAGE_NAME_LABELS = {code: label for code, label in LANGUAGE_LABELS.items() if len(code) > 3}
LANGUAGE_CODE_PATTERN = build_language_pattern(LANGUAGE_CODE_LABELS)
LANGUAGE_NAME_PATTERN = build_language_pattern(LANGUAGE_NAME_LABELS)
RESOLUTION_PATTERN = re.compile(r"(?<!\w)(\d{3,4}[xX]\d{3,4})(?!\w)")
STREAM_LINE_PATTERN = re.compile(r"^(Vid|Aud|Sub|Text)\b", re.I)
SELECTED_STREAMS_PATTERN = re.compile(r"selected streams\s*:", re.I)
LOG_LEVEL_PATTERN = re.compile(r"^\s*(?:INFO|WARN|WARNING|ERROR|DEBUG|TRACE)\s*:\s*", re.I)
TIMESTAMP_LINE_PATTERN = re.compile(r"^\s*\d{2}:\d{2}:\d{2}\.\d{3}\s+")
STREAM_KIND_MAP = {"vid": "video", "aud": "audio", "sub": "subtitle", "text": "subtitle"}
STREAM_LABELS = {"video": "Video", "audio": "Audio", "subtitle": "Ondertiteling"}
STREAM_IGNORE_PATTERN = re.compile(r"segments|~\s*\d|\d+\s*%", re.I)
PROGRESS_LINE_PATTERN = re.compile(
    r"^(Vid|Aud|Sub|Text)\s+(.+?)\s*(?:-{3,}\s*)?(\d+)\s*/\s*(\d+)\s+(\d+(?:\.\d+)?)\s*%\s*(.*)$",
    re.I,
)
STREAM_STATUS_BAR_PATTERN = re.compile(
    r"^(?:\d{2}:\d{2}:\d{2}\.\d{3}\s+\w+\s*:\s*)?"
    r"(Vid|Aud|Sub|Text)\b.*"
    r"\b(?:Downloading|Decrypting|Merging|Extracting|Muxing|Finalizing|Processing completed)\b",
    re.I,
)
DASH_AD_PERIOD_REGEX = (
    r"(mid-roll|mid_roll|midroll|pre-roll|pre_roll|preroll|"
    r"post-roll|post_roll|postroll|ad-pod|ad_pod|adpod|ad-break|ad_break|adbreak|"
    r"bump|bumper|promo|break)"
)
DASH_AD_URL_KEYWORD = r"dai\.google\.com/segments/redirect"
AD_PERIOD_PATTERN = re.compile(DASH_AD_PERIOD_REGEX, re.I)


@app.before_request
def require_auth():
    if request.path == "/api/extension/submit":
        return None
    if not WEB_USER or not WEB_PASSWORD:
        return None
    auth = request.authorization
    if auth and auth.username == WEB_USER and auth.password == WEB_PASSWORD:
        return None
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="N_m3u8DL-RE"'},
    )


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Ext-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


def strip_option(tokens, name, has_value=True):
    kept = []
    value = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == name:
            if has_value and i + 1 < len(tokens):
                value = tokens[i + 1]
                i += 2
            else:
                i += 1
            continue
        if token.startswith(name + "="):
            value = token[len(name) + 1 :]
            i += 1
            continue
        kept.append(token)
        i += 1
    return kept, value


def safe_dir(value):
    if not value:
        return DOWNLOAD_DIR
    candidate = Path(value.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = DOWNLOAD_DIR / candidate
    candidate = candidate.resolve()
    if candidate != DOWNLOAD_DIR and DOWNLOAD_DIR not in candidate.parents:
        raise ValueError("--save-dir moet binnen /downloads blijven")
    return candidate


def safe_name(value, limit=120):
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    name = name.replace("\x00", "").strip()
    name = name[:limit].rstrip(" ._")
    return name or "download"


def extract_title(argv):
    for index, token in enumerate(argv):
        if token == "--save-name" and index + 1 < len(argv):
            return argv[index + 1]
    for token in argv[1:]:
        if token.startswith("-"):
            continue
        try:
            path = urlparse(token).path
        except ValueError:
            path = token
        name = Path(path.rstrip("/")).name
        if name:
            return name
    return "Taak"


def detect_phase(text):
    matches = []
    for phase, pattern in PHASE_PATTERNS:
        for match in pattern.finditer(text):
            matches.append((match.start(), phase))
    if not matches:
        return None
    return max(matches, key=lambda item: item[0])[1]


def detect_progress(text):
    matches = PROGRESS_PATTERN.findall(text)
    if not matches:
        return None
    return min(100, max(0, int(float(matches[-1]))))


def split_output(text):
    clean = ANSI_PATTERN.sub("", text)
    segments = []
    for part in re.split(r"[\r\n]+", clean):
        for segment in TIMESTAMP_PATTERN.split(part):
            if segment.strip():
                segments.append(segment.strip())
    return segments


def last_log_detail(text):
    segments = split_output(text)
    return segments[-1][-200:] if segments else ""


def clean_log_line(raw):
    text = ANSI_PATTERN.sub("", raw)
    text = TIMESTAMP_LINE_PATTERN.sub("", text)
    text = LOG_LEVEL_PATTERN.sub("", text)
    return text.strip()


def stream_language(text):
    match = LANGUAGE_CODE_PATTERN.search(text) or LANGUAGE_NAME_PATTERN.search(text)
    if not match:
        return None, None
    code = match.group(1).lower()
    return code, LANGUAGE_LABELS[code]


def parse_stream_line(raw):
    line = clean_log_line(raw)
    match = STREAM_LINE_PATTERN.match(line)
    if not match:
        return None
    kind = STREAM_KIND_MAP[match.group(1).lower()]
    parts = [part.strip() for part in line.split("|") if part.strip()]
    main = parts[0]
    rest = main[match.end() :].strip()
    code, language = stream_language(line)
    resolution_match = RESOLUTION_PATTERN.search(line)
    resolution = resolution_match.group(1) if resolution_match else None
    track_match = re.search(r"\b(\d+)\b", rest)
    details = []
    for part in parts[1:]:
        if STREAM_IGNORE_PATTERN.search(part):
            continue
        if code and part.lower() == code:
            continue
        if language and part.lower() == language.lower():
            continue
        details.append(part)
    name = resolution or language or rest or STREAM_LABELS[kind]
    return {
        "kind": kind,
        "label": STREAM_LABELS[kind],
        "name": name,
        "resolution": resolution,
        "language": language,
        "language_code": code,
        "track": track_match.group(1) if track_match else None,
        "details": " · ".join(details),
        "raw": line,
    }


def parse_progress_line(raw):
    line = clean_log_line(raw)
    match = PROGRESS_LINE_PATTERN.match(line)
    if not match:
        return None
    kind = STREAM_KIND_MAP[match.group(1).lower()]
    return {
        "kind": kind,
        "label": match.group(2).strip(),
        "current": int(match.group(3)),
        "total": int(match.group(4)),
        "percent": float(match.group(5)),
        "tail": match.group(6).strip(),
        "text": line,
    }


def normalize_progress_item(item):
    total = item.get("total")
    if total and (item.get("percent", 0) >= 99.5 or item.get("current", 0) >= total - 1):
        item["current"] = total
        item["percent"] = 100.0
    return item


def progress_key(item):
    label = re.sub(r"[\s━─—-]+$", "", item.get("label", "")).strip()
    return (item.get("kind"), re.sub(r"\s+", " ", label).lower())


def stream_progress_percent(item):
    if not item or not item.get("total"):
        return 0.0
    return min(100.0, max(0.0, item.get("current", 0) * 100 / item["total"]))


def aggregate_stream_progress(progress_streams, selected_streams=None):
    if selected_streams:
        slots = []
        for kind in ("video", "audio", "subtitle"):
            selected = selected_streams.get(kind) or []
            entries = progress_streams.get(kind) or []
            for index in range(len(selected)):
                slots.append(
                    stream_progress_percent(entries[index] if index < len(entries) else None)
                )
        if slots:
            return int(sum(slots) / len(slots))
    entries = []
    for items in progress_streams.values():
        entries.extend(item for item in items if item.get("total"))
    total = sum(item["total"] for item in entries)
    if not total:
        return None
    current = sum(min(item["current"], item["total"]) for item in entries)
    return min(100, max(0, int(current * 100 / total)))


class LogFilter:
    def __init__(self):
        self.residue = ""

    def feed(self, text):
        if not text:
            return ""
        data = self.residue + ANSI_PATTERN.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
        self.residue = ""
        if not data.endswith("\n"):
            head, _, self.residue = data.rpartition("\n")
            lines = head.split("\n") if head else []
        else:
            lines = data.split("\n")[:-1]
        kept = []
        for line in lines:
            if not line.strip() or parse_progress_line(line) or STREAM_STATUS_BAR_PATTERN.match(line):
                continue
            kept.append(line)
        return "".join(line + "\n" for line in kept)


class StreamCollector:
    def __init__(self):
        self.video = []
        self.audio = []
        self.subtitle = []
        self.collecting = False
        self.residue = ""

    def buckets(self):
        return {"video": self.video, "audio": self.audio, "subtitle": self.subtitle}

    def feed(self, text):
        if not text:
            return False
        data = self.residue + ANSI_PATTERN.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
        self.residue = ""
        if not data.endswith("\n"):
            head, _, self.residue = data.rpartition("\n")
            lines = head.split("\n") if head else []
        else:
            lines = data.split("\n")[:-1]
        changed = False
        for raw in lines:
            changed = self.consume(raw) or changed
        return changed

    def consume(self, raw):
        line = clean_log_line(raw)
        if not line:
            return False
        if SELECTED_STREAMS_PATTERN.search(line):
            self.video = []
            self.audio = []
            self.subtitle = []
            self.collecting = True
            return True
        if not self.collecting:
            return False
        parsed = parse_stream_line(line)
        if parsed:
            bucket = self.buckets()[parsed["kind"]]
            if parsed not in bucket:
                bucket.append(parsed)
            return True
        self.collecting = False
        return False

    def info(self):
        return {
            "video": list(self.video),
            "audio": list(self.audio),
            "subtitle": list(self.subtitle),
        }


def has_option(tokens, names):
    for token in tokens:
        if token in names:
            return True
        if any(name.startswith("--") and token.startswith(name + "=") for name in names):
            return True
    return False


def is_dash_input(tokens):
    for token in tokens:
        if token.startswith("-"):
            continue
        candidate = urlparse(token).path or token
        if candidate.lower().endswith(".mpd"):
            return True
    return False


def find_manifest_input(tokens):
    for token in tokens:
        if token.startswith("-"):
            continue
        candidate = urlparse(token).path if "://" in token else token
        if candidate.lower().endswith(".mpd"):
            return token
    return None


def extract_headers(tokens):
    headers = {}
    for index, token in enumerate(tokens):
        if token in ("-H", "--header") and index + 1 < len(tokens):
            value = tokens[index + 1]
            if ":" in value:
                name, header_value = value.split(":", 1)
                headers[name.strip()] = header_value.strip()
            continue
        for name in ("--header=", "-H="):
            if token.startswith(name):
                value = token[len(name) :]
                if ":" in value:
                    key, header_value = value.split(":", 1)
                    headers[key.strip()] = header_value.strip()
                break
    return headers


def fetch_manifest_text(url, headers):
    if not url.lower().startswith(("http://", "https://")):
        return None
    request_headers = {"User-Agent": "Mozilla/5.0"}
    request_headers.update(headers)
    try:
        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read(2_000_000).decode("utf-8", "replace")
    except Exception:
        return None


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def format_indices(indices):
    values = sorted(set(indices))
    if not values:
        return ""
    groups = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    groups.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(groups)


def detect_vod_drop_parts(tokens):
    if has_option(tokens, {"--vod-list-parts", "--vod-drop-parts", "--vod-select-parts"}):
        return None
    source = find_manifest_input(tokens)
    if not source:
        return None
    text = fetch_manifest_text(source, extract_headers(tokens))
    if not text:
        return None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    periods = [element for element in root.iter() if local_name(element.tag) == "Period"]
    if len(periods) < 2:
        return None
    ad_indices = []
    for index, period in enumerate(periods):
        parts = [period.get("id", "")]
        for element in period.iter():
            if local_name(element.tag) == "BaseURL" and element.text:
                parts.append(element.text)
            for key in ("media", "initialization", "index"):
                value = element.get(key)
                if value:
                    parts.append(value)
        blob = " ".join(parts)
        if AD_PERIOD_PATTERN.search(period.get("id", "")) or re.search(
            r"dai\.google\.com|googlevideo\.com|dclk_video_ads", blob, re.I
        ):
            ad_indices.append(index)
    if not ad_indices or len(ad_indices) == len(periods):
        return None
    return format_indices(ad_indices)


def inject_dash_ad_filters(tokens):
    if not is_dash_input(tokens):
        return tokens
    if has_option(
        tokens,
        {
            "--ad-keyword",
            "--vod-list-parts",
            "--vod-drop-parts",
            "--vod-select-parts",
        },
    ):
        return tokens
    if any("period=" in token for token in tokens):
        return tokens
    result = list(tokens)
    drop_parts = detect_vod_drop_parts(result)
    if drop_parts:
        result += ["--vod-drop-parts", drop_parts]
    result += ["--ad-keyword", DASH_AD_URL_KEYWORD]
    selector = f"period={DASH_AD_PERIOD_REGEX}:for=all"
    if not has_option(result, {"-sv", "--select-video"}):
        result += ["-dv", selector]
    if not has_option(result, {"-sa", "--select-audio"}):
        result += ["-da", selector]
    if not has_option(result, {"-ss", "--select-subtitle"}):
        result += ["-ds", selector]
    return result


def parse_command(raw):
    raw = raw.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
    if not raw:
        raise ValueError("Plak eerst een commando")
    if len(raw) > 20000:
        raise ValueError("Commando is te lang")

    tokens = shlex.split(raw, posix=True)
    if not tokens:
        raise ValueError("Ongeldig commando")
    if any("\x00" in token for token in tokens):
        raise ValueError("Ongeldig teken in commando")
    if Path(tokens[0]).name not in BINARY_NAMES:
        raise ValueError("Commando moet beginnen met N_m3u8DL-RE of N_m3u8DL-RE.exe")

    args = tokens[1:]

    for option in (
        "--log-file-path",
        "--ffmpeg-binary-path",
        "--decryption-binary-path",
    ):
        args, _ = strip_option(args, option)

    for option in ("--no-log", "--no-ansi-color", "--disable-update-check"):
        args, _ = strip_option(args, option, has_value=False)

    args, save_dir_raw = strip_option(args, "--save-dir")
    args, save_name_raw = strip_option(args, "--save-name")
    args = inject_dash_ad_filters(args)

    base_dir = safe_dir(save_dir_raw)
    save_name = safe_name(save_name_raw) if save_name_raw is not None else None
    save_dir = base_dir / safe_name(save_name, limit=80) if save_name else base_dir
    save_dir.mkdir(parents=True, exist_ok=True)

    argv = [NDL_BINARY] + args + [
        "--save-dir",
        str(save_dir),
        "--no-log",
        "--no-ansi-color",
        "--disable-update-check",
        "--ui-language",
        "en-US",
        "--ffmpeg-binary-path",
        FFMPEG_BINARY,
        "--decryption-binary-path",
        MP4DECRYPT_BINARY,
    ]
    if save_name is not None:
        argv += ["--save-name", save_name]

    return argv


class Job:
    def __init__(self, command, argv):
        self.id = uuid.uuid4().hex[:12]
        self.command = command
        self.title = extract_title(argv)
        self.argv = argv
        self.output = queue.Queue()
        self.streams = StreamCollector()
        self.progress_streams = {"video": [], "audio": [], "subtitle": []}
        self.active_stream = None
        self.log_filter = LogFilter()
        self.log_file = None
        self.status = "running"
        self.phase = "initialiseren"
        self.progress = None
        self.aggregate_ready = False
        self.detail = ""
        self.returncode = None
        self.proc = None
        self.created = time.time()
        self.started = None
        self.finished = None

    def info(self):
        return {
            "id": self.id,
            "command": self.command,
            "title": self.title,
            "status": self.status,
            "phase": self.phase,
            "progress": self.progress,
            "detail": self.detail,
            "streams": self.streams.info(),
            "progress_streams": {
                kind: [dict(item) for item in items]
                for kind, items in self.progress_streams.items()
            },
            "active_stream": dict(self.active_stream) if self.active_stream else None,
            "returncode": self.returncode,
            "created": self.created,
            "started": self.started,
            "finished": self.finished,
        }

    def observe_progress(self, raw):
        parsed = parse_progress_line(raw)
        if not parsed:
            return None
        normalize_progress_item(parsed)
        key = progress_key(parsed)
        items = self.progress_streams[parsed["kind"]]
        existing = next((item for item in items if progress_key(item) == key), None)
        previous = existing.get("current", 0) if existing else 0
        if existing:
            existing.update(parsed)
            current = existing
        else:
            items.append(parsed)
            current = parsed
        return current, current.get("current", 0) - previous

    def observe(self, line, stream_chunk=None):
        changed = False
        raw_stream = stream_chunk if stream_chunk is not None else line
        raw_lines = re.split(r"[\r\n]+", ANSI_PATTERN.sub("", raw_stream))
        selected_seen = any(
            SELECTED_STREAMS_PATTERN.search(clean_log_line(part)) for part in raw_lines
        )
        streams_before = self.streams.info()
        streams_changed = self.streams.feed(raw_stream)
        if streams_changed:
            changed = True
        if selected_seen and self.streams.info() != streams_before:
            self.progress_streams = {"video": [], "audio": [], "subtitle": []}
            self.active_stream = None
            self.aggregate_ready = False
            changed = True
        progress_updates = []
        for segment in raw_lines:
            update = self.observe_progress(segment)
            if update:
                changed = True
                progress_updates.append(update)
        detected_progress = None
        for segment in split_output(line):
            if parse_progress_line(segment) or STREAM_STATUS_BAR_PATTERN.match(segment):
                continue
            phase = detect_phase(segment)
            if phase and self.phase != phase:
                if self.phase not in TERMINAL_PHASES or phase in TERMINAL_PHASES:
                    self.phase = phase
                    changed = True
            value = detect_progress(segment)
            if value is not None:
                detected_progress = value
            detail = segment[-200:]
            if detail and detail != self.detail:
                self.detail = detail
                changed = True
        aggregate = aggregate_stream_progress(
            self.progress_streams, self.streams.info()
        )
        had_aggregate = self.aggregate_ready
        self.aggregate_ready = aggregate is not None
        if aggregate is not None:
            if had_aggregate and self.progress is not None:
                next_progress = max(self.progress, aggregate)
            else:
                next_progress = aggregate
        elif detected_progress is not None and not had_aggregate:
            next_progress = detected_progress
        else:
            next_progress = None
        if next_progress is not None and next_progress != self.progress:
            self.progress = next_progress
            changed = True
        advancing = [
            (item, delta)
            for item, delta in progress_updates
            if delta > 0 and item.get("percent", 100) < 100
        ]
        if advancing:
            self.active_stream = max(advancing, key=lambda pair: pair[1])[0]
        elif self.active_stream is None:
            self.active_stream = next(
                (item for items in self.progress_streams.values() for item in items),
                None,
            )
        if changed:
            self.output.put(("status", self.info()))

    def finish_phase(self):
        if self.status == "done":
            self.phase = "klaar"
            self.progress = 100
            for items in self.progress_streams.values():
                for item in items:
                    item["current"] = item.get("total", item.get("current", 0))
                    item["percent"] = 100.0
        elif self.status == "failed":
            self.phase = "gefaald"
        elif self.status == "cancelled":
            self.phase = "geannuleerd"
        self.output.put(("status", self.info()))

    def append_log(self, text):
        if not text:
            return
        try:
            if self.log_file is None:
                self.log_file = log_file_path(self.id).open("w", encoding="utf-8")
            self.log_file.write(text)
            self.log_file.flush()
        except OSError:
            pass

    def close_log(self):
        if self.log_file is not None:
            try:
                self.log_file.close()
            except OSError:
                pass
            self.log_file = None

    def start(self):
        threading.Thread(target=self._run, daemon=True, name=f"job-{self.id}").start()

    def _run(self):
        self.started = time.time()
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["TERM"] = "xterm"
        try:
            self.proc = subprocess.Popen(
                self.argv,
                cwd=str(DOWNLOAD_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                env=env,
            )
            if self.proc.stdout is not None and hasattr(self.proc.stdout, "fileno"):
                carry = ""
                while True:
                    data = os.read(self.proc.stdout.fileno(), 8192)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    combined = carry + text
                    self.observe(combined, text)
                    filtered = self.log_filter.feed(text)
                    if filtered:
                        self.append_log(filtered)
                        self.output.put(("log", filtered))
                    carry = combined[-200:]
            elif self.proc.stdout is not None:
                for line in self.proc.stdout:
                    self.observe(line, line)
                    filtered = self.log_filter.feed(line)
                    if filtered:
                        self.append_log(filtered)
                        self.output.put(("log", filtered))
            self.returncode = self.proc.wait()
            with _jobs_lock:
                if self.status != "cancelled":
                    self.status = "done" if self.returncode == 0 else "failed"
                    self.finish_phase()
        except Exception as exc:
            message = f"[webserver] {type(exc).__name__}: {exc}\n"
            self.append_log(message)
            self.output.put(("log", message))
            with _jobs_lock:
                if self.status != "cancelled":
                    self.status = "failed"
                    self.finish_phase()
        finally:
            self.finished = time.time()
            self.close_log()
            write_archived_info(self)
            self.output.put(("end", None))

    def cancel(self):
        with _jobs_lock:
            if self.status not in ("running", "queued"):
                return False
            self.status = "cancelled"
            self.finish_phase()
        self.finished = time.time()
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except OSError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.output.put(("end", None))
        return True


class ArchivedJob:
    def __init__(self, info):
        self.info_data = info
        self.id = info.get("id")

    def info(self):
        return dict(self.info_data)


def get_job(job_id):
    if not valid_job_id(job_id):
        abort(404)
    info = read_archived_info(job_id)
    if info is not None:
        return ArchivedJob(info)
    job = _jobs.get(job_id)
    if job is not None:
        return job
    abort(404)


def resolve_file(name):
    parts = Path(name).parts
    if any(part in HIDDEN_DIRS or part.startswith(".") for part in parts):
        return None
    try:
        target = (DOWNLOAD_DIR / name).resolve()
    except (OSError, ValueError):
        return None
    if target == DOWNLOAD_DIR or DOWNLOAD_DIR not in target.parents:
        return None
    return target if target.is_file() else None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/log/<job_id>")
def log_page(job_id):
    get_job(job_id)
    return render_template("log.html", job_id=job_id)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "binary": NDL_BINARY,
            "download_dir": str(DOWNLOAD_DIR),
            "max_concurrent": MAX_CONCURRENT,
        }
    )


def enqueue_job(command, argv):
    with _jobs_lock:
        active = sum(1 for item in _jobs.values() if item.status == "running")
        if active >= MAX_CONCURRENT:
            return None
        job = Job(command, argv)
        _jobs[job.id] = job
    job.start()
    return job


@app.post("/api/jobs")
def create_job():
    data = request.get_json(silent=True) or {}
    command = str(data.get("command", ""))
    try:
        argv = parse_command(command)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    job = enqueue_job(command, argv)
    if job is None:
        return jsonify({"error": f"Maximaal {MAX_CONCURRENT} gelijktijdige taken"}), 429
    return jsonify(job.info()), 201


@app.post("/api/extension/submit")
def extension_submit():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", ""))
    if not EXT_TOKEN or token != EXT_TOKEN:
        return jsonify({"error": "Ongeldige token"}), 401

    command = str(data.get("command", ""))
    try:
        argv = parse_command(command)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    job = enqueue_job(command, argv)
    if job is None:
        return jsonify({"error": f"Maximaal {MAX_CONCURRENT} gelijktijdige taken"}), 429
    return jsonify({"ok": True, "id": job.id}), 201


@app.get("/api/jobs")
def list_jobs():
    with _jobs_lock:
        items = [job.info() for job in _jobs.values()]
    seen = {item.get("id") for item in items}
    for path in LOG_DIR.glob("*.json"):
        info = read_archived_info(path.stem)
        if info and info.get("id") not in seen:
            items.append(info)
            seen.add(info.get("id"))
    items.sort(key=lambda item: item.get("created", 0), reverse=True)
    return jsonify(items)


@app.delete("/api/jobs")
def clear_jobs():
    global _jobs
    with _jobs_lock:
        running_ids = {
            job_id for job_id, job in _jobs.items() if job.status == "running"
        }
        _jobs = {
            job_id: job
            for job_id, job in _jobs.items()
            if job.status == "running"
        }
        stale_paths = [
            path
            for pattern in ("*.log", "*.json")
            for path in LOG_DIR.glob(pattern)
            if path.stem not in running_ids
        ]
    for path in stale_paths:
        try:
            path.unlink()
        except OSError:
            pass
    return jsonify({"ok": True})


@app.get("/api/jobs/<job_id>")
def job_detail(job_id):
    return jsonify(get_job(job_id).info())


@app.get("/api/jobs/<job_id>/stream")
def job_stream(job_id):
    job = get_job(job_id)

    def generate():
        if isinstance(job, ArchivedJob):
            path = log_file_path(job_id)
            if path.is_file():
                try:
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        for line in handle:
                            yield "data: " + json.dumps({"line": line}, ensure_ascii=False) + "\n\n"
                except OSError:
                    pass
            yield "event: status\ndata: " + json.dumps(job.info(), ensure_ascii=False) + "\n\n"
            yield "event: end\ndata: " + json.dumps(job.info(), ensure_ascii=False) + "\n\n"
            return
        while True:
            try:
                kind, payload = job.output.get(timeout=10)
            except queue.Empty:
                if job.status != "running":
                    break
                yield ": ping\n\n"
                continue
            if kind == "end":
                break
            if kind == "status":
                yield "event: status\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
                continue
            yield "data: " + json.dumps({"line": payload}, ensure_ascii=False) + "\n\n"
        yield "event: end\ndata: " + json.dumps(job.info(), ensure_ascii=False) + "\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/jobs/<job_id>/cancel")
def cancel_job(job_id):
    job = get_job(job_id)
    if isinstance(job, ArchivedJob) or not job.cancel():
        return jsonify({"error": "Taak is al klaar"}), 409
    return jsonify(job.info())


@app.get("/api/files")
def list_files():
    files = []
    for root, dirs, filenames in os.walk(DOWNLOAD_DIR):
        dirs[:] = [d for d in dirs if d not in HIDDEN_DIRS and not d.startswith(".")]
        for filename in filenames:
            if filename.startswith(".") or Path(filename).suffix.lower() != ".mkv":
                continue
            path = Path(root) / filename
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append(
                {
                    "name": path.relative_to(DOWNLOAD_DIR).as_posix(),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    files.sort(key=lambda item: item["modified"], reverse=True)
    return jsonify(files)


@app.get("/api/files/<path:name>")
def download_file(name):
    target = resolve_file(name)
    if target is None:
        abort(404)
    return send_file(target, as_attachment=True, download_name=target.name)


@app.delete("/api/files/<path:name>")
def delete_file(name):
    target = resolve_file(name)
    if target is None:
        abort(404)
    target.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=PORT, threads=16)
