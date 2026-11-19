import atexit
import os
import shutil
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
