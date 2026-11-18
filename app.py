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
    selector = f"period={DASH_AD_PERIOD_REGEX}:for=all"
    return result + [
        "-dv",
        selector,
        "-da",
        selector,
        "-ds",
        selector,
        "--ad-keyword",
        DASH_AD_URL_KEYWORD,
    ]


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
        self.status = "running"
        self.phase = "initialiseren"
        self.progress = None
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
            "returncode": self.returncode,
            "created": self.created,
            "started": self.started,
            "finished": self.finished,
        }

    def observe(self, line):
        changed = False
        for segment in split_output(line):
            phase = detect_phase(segment)
            if phase and self.phase != phase:
                if self.phase not in TERMINAL_PHASES or phase in TERMINAL_PHASES:
                    self.phase = phase
                    changed = True
            value = detect_progress(segment)
            if value is not None and value != self.progress:
                self.progress = value
                changed = True
            detail = segment[-200:]
            if detail and detail != self.detail:
                self.detail = detail
                changed = True
        if changed:
            self.output.put(("status", self.info()))

    def finish_phase(self):
        if self.status == "done":
            self.phase = "klaar"
            self.progress = 100
        elif self.status == "failed":
            self.phase = "gefaald"
        elif self.status == "cancelled":
            self.phase = "geannuleerd"
        self.output.put(("status", self.info()))

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
                    self.observe(combined)
                    self.output.put(("log", text))
                    carry = combined[-200:]
            elif self.proc.stdout is not None:
                for line in self.proc.stdout:
                    self.observe(line)
                    self.output.put(("log", line))
            self.returncode = self.proc.wait()
            with _jobs_lock:
                if self.status != "cancelled":
                    self.status = "done" if self.returncode == 0 else "failed"
                    self.finish_phase()
        except Exception as exc:
            self.output.put(("log", f"[webserver] {type(exc).__name__}: {exc}\n"))
            with _jobs_lock:
                if self.status != "cancelled":
                    self.status = "failed"
                    self.finish_phase()
        finally:
            self.finished = time.time()
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


def get_job(job_id):
    job = _jobs.get(job_id)
    if job is None:
        abort(404)
    return job


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
    items.sort(key=lambda item: item["created"], reverse=True)
    return jsonify(items)


@app.delete("/api/jobs")
def clear_jobs():
    global _jobs
    with _jobs_lock:
        _jobs = {
            job_id: job
            for job_id, job in _jobs.items()
            if job.status == "running"
        }
    return jsonify({"ok": True})


@app.get("/api/jobs/<job_id>")
def job_detail(job_id):
    return jsonify(get_job(job_id).info())


@app.get("/api/jobs/<job_id>/stream")
def job_stream(job_id):
    job = get_job(job_id)

    def generate():
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
    if not job.cancel():
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
