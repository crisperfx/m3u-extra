import atexit
import os
import shutil
import tempfile
import unittest
from unittest import mock

_TEST_DOWNLOAD_DIR = tempfile.mkdtemp(prefix="m3u-extra-test-")
os.environ["DOWNLOAD_DIR"] = _TEST_DOWNLOAD_DIR
atexit.register(shutil.rmtree, _TEST_DOWNLOAD_DIR, True)

import app as app_module

SAMPLE_LOG = """22:50:31.885 INFO : Selected streams:
22:50:31.886 INFO : Vid *CENC 1920x1080 | 5644 Kbps | 2 | 25 | avc1.640028 | 775 Segments | ~49m30s
22:50:31.887 INFO : Aud *CENC 7 | 640 Kbps | Surround | ac-3 | eng | F801CH | 775 Segments | ~49m30s
22:50:31.887 INFO : Aud *CENC 6 | 192 Kbps | Stereo | mp4a.40.2 | eng | 2CH | 775 Segments | ~49m30s
22:50:31.888 INFO : Sub 8 | nld | Nederlands | stpp | 775 Segments | ~49m30s
22:50:31.888 WARN : Writing meta json
"""

PROGRESS_LOG = (
    "Vid 1920x1080 | 5644 Kbps | 25         ------------------------------ 84/776 10.82% 249.80MB/2.25GB 27.45MBps 00:01:11 /\r"
    "Aud 640 Kbps | Surround | eng | F801CH ------------------------------   0/100 0.00%               -     -     --:--:--\r"
    "Aud 192 Kbps | Stereo | eng | 2CH      ------------------------------   0/100 0.00%               -     -     --:--:--\r"
    "Sub nld | Nederlands | stpp            ------------------------------   0/100 0.00%               -     -     --:--:--\r"
)


class StreamParsingTests(unittest.TestCase):
    def test_parse_video_line(self):
        parsed = app_module.parse_stream_line(SAMPLE_LOG.splitlines()[1])
        self.assertEqual(parsed["kind"], "video")
        self.assertEqual(parsed["resolution"], "1920x1080")
        self.assertIn("avc1.640028", parsed["details"])

    def test_parse_audio_line(self):
        parsed = app_module.parse_stream_line(SAMPLE_LOG.splitlines()[2])
        self.assertEqual(parsed["kind"], "audio")
        self.assertEqual(parsed["language"], "Engels")
        self.assertEqual(parsed["language_code"], "eng")
        self.assertEqual(parsed["track"], "7")
        self.assertNotIn("eng", parsed["details"])

    def test_parse_subtitle_line(self):
        parsed = app_module.parse_stream_line(SAMPLE_LOG.splitlines()[4])
        self.assertEqual(parsed["kind"], "subtitle")
        self.assertEqual(parsed["language"], "Nederlands")
        self.assertEqual(parsed["language_code"], "nld")
        self.assertIn("stpp", parsed["details"])

    def test_collector_parses_sample(self):
        collector = app_module.StreamCollector()
        collector.feed(SAMPLE_LOG)
        info = collector.info()
        self.assertEqual(len(info["video"]), 1)
        self.assertEqual(len(info["audio"]), 2)
        self.assertEqual(len(info["subtitle"]), 1)
        self.assertEqual(info["video"][0]["resolution"], "1920x1080")
        self.assertEqual(info["audio"][0]["language_code"], "eng")
        self.assertEqual(info["subtitle"][0]["language_code"], "nld")

    def test_collector_handles_small_chunks(self):
        collector = app_module.StreamCollector()
        for start in range(0, len(SAMPLE_LOG), 13):
            collector.feed(SAMPLE_LOG[start:start + 13])
        info = collector.info()
        self.assertEqual(len(info["video"]), 1)
        self.assertEqual(len(info["audio"]), 2)
        self.assertEqual(len(info["subtitle"]), 1)

    def test_job_info_contains_streams(self):
        job = app_module.Job("N_m3u8DL-RE", ["N_m3u8DL-RE"])
        job.observe(SAMPLE_LOG)
        info = job.info()
        self.assertEqual(info["streams"]["video"][0]["resolution"], "1920x1080")
        self.assertEqual(info["streams"]["subtitle"][0]["language_code"], "nld")


class ProgressTests(unittest.TestCase):
    def test_parse_progress_line(self):
        parsed = app_module.parse_progress_line(PROGRESS_LOG.split("\r")[0])
        self.assertEqual(parsed["kind"], "video")
        self.assertEqual(parsed["current"], 84)
        self.assertEqual(parsed["total"], 776)
        self.assertEqual(parsed["percent"], 10.82)
        self.assertIn("10.82%", parsed["text"])

    def test_log_filter_drops_progress_lines(self):
        log_filter = app_module.LogFilter()
        output = log_filter.feed("INFO : Selected streams:\r" + PROGRESS_LOG + "INFO : Done\n")
        self.assertIn("Selected streams", output)
        self.assertIn("Done", output)
        self.assertNotIn("10.82%", output)
        self.assertNotIn("F801CH", output)

    def test_log_filter_handles_chunks(self):
        log_filter = app_module.LogFilter()
        output = "".join(
            log_filter.feed(PROGRESS_LOG[start:start + 19])
            for start in range(0, len(PROGRESS_LOG), 19)
        )
        self.assertEqual(output, "")

    def test_job_progress_is_weighted_across_streams(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe(SAMPLE_LOG)
        job.observe(PROGRESS_LOG)
        info = job.info()
        self.assertEqual(info["progress"], 7)
        self.assertEqual(len(info["progress_streams"]["video"]), 1)
        self.assertEqual(len(info["progress_streams"]["audio"]), 2)
        self.assertEqual(len(info["progress_streams"]["subtitle"]), 1)
        self.assertIn("10.82%", info["progress_streams"]["video"][0]["text"])


class AdFilterTests(unittest.TestCase):
    def test_explicit_subtitle_selector_is_preserved(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd" -sv best -sa for=all -ss lang=nld'
        with mock.patch.object(app_module, "fetch_manifest_text", return_value=None):
            argv = app_module.parse_command(command)
        self.assertEqual(argv[argv.index("-ss") + 1], "lang=nld")
        self.assertNotIn("-ds", argv)
        self.assertNotIn("-da", argv)
        self.assertNotIn("-dv", argv)
        self.assertIn("--ad-keyword", argv)


if __name__ == "__main__":
    unittest.main()
