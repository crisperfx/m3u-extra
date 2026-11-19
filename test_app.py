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

MERGING_LOG = (
    "23:05:15.665 INFO : Binary merging...\n"
    "Vid 1280x720 | 4003 Kbps | 25 Merging  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━       4.17% 47.57MB/1.11GB - 00:00:02             \n"
    "Vid 1280x720 | 4003 Kbps | 25 Merging  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      95.55% 1.06GB/1.11GB 783.29MBps 00:00:00\n"
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

    def test_merging_lines_are_ignored(self):
        self.assertIsNone(app_module.parse_progress_line(MERGING_LOG.splitlines()[1]))
        log_filter = app_module.LogFilter()
        output = log_filter.feed(MERGING_LOG + "INFO : Done\n")
        self.assertNotIn("Merging", output)
        self.assertNotIn("4.17%", output)
        self.assertNotIn("95.55%", output)
        self.assertIn("Done", output)

    def test_duplicate_progress_rows_are_merged(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("Vid 1920x1080 | en | h264 --- 108/1000 10.82% 1.23MB/s\n")
        job.observe("Vid 1920x1080 | en | h264 --- 109/1000 10.92% 1.23MB/s\n")
        info = job.info()
        self.assertEqual(len(info["progress_streams"]["video"]), 1)
        self.assertEqual(info["progress_streams"]["video"][0]["current"], 109)
        self.assertEqual(info["active_stream"]["kind"], "video")

    def test_near_complete_progress_is_normalized_to_100(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("Vid 1920x1080 | en | h264 --- 999/1000 99.90% 1.23MB/s\n")
        info = job.info()
        self.assertEqual(info["progress_streams"]["video"][0]["percent"], 100.0)
        self.assertIsNone(info["active_stream"])

    def test_selected_streams_block_resets_progress(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("INFO : Selected streams:\n")
        job.observe("Vid 1920x1080 | en | h264 --- 108/1000 10.82% 1.23MB/s\n")
        self.assertEqual(len(job.info()["progress_streams"]["video"]), 1)
        job.observe("INFO : Selected streams:\n")
        info = job.info()
        self.assertEqual(info["progress_streams"]["video"], [])
        self.assertIsNone(info["active_stream"])

    def test_finish_phase_marks_all_streams_complete(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("Vid 1920x1080 | en | h264 --- 108/1000 10.82% 1.23MB/s\n")
        job.status = "done"
        job.finish_phase()
        info = job.info()
        stream = info["progress_streams"]["video"][0]
        self.assertEqual(stream["current"], stream["total"])
        self.assertEqual(stream["percent"], 100.0)
        self.assertEqual(info["progress"], 100)
        self.assertIsNone(info["active_stream"])


class ArchiveTests(unittest.TestCase):
    def test_finished_job_log_can_be_reopened_and_cleared(self):
        job = app_module.Job("N_m3u8DL-RE example", ["N_m3u8DL-RE"])
        job.append_log("INFO : Example line\n")
        job.close_log()
        job.status = "done"
        job.finish_phase()
        app_module.write_archived_info(job)
        log_file = app_module.log_file_path(job.id)
        metadata_file = app_module.metadata_file_path(job.id)
        self.assertTrue(log_file.is_file())
        self.assertTrue(metadata_file.is_file())
        with app_module.app.test_client() as client:
            self.assertEqual(client.get(f"/log/{job.id}").status_code, 200)
            detail = client.get(f"/api/jobs/{job.id}").get_json()
            self.assertTrue(detail["archived"])
            jobs = client.get("/api/jobs").get_json()
            self.assertIn(job.id, [item["id"] for item in jobs])
            stream = client.get(f"/api/jobs/{job.id}/stream").get_data(as_text=True)
            self.assertIn("Example line", stream)
            self.assertIn("event: end", stream)
            self.assertEqual(client.delete("/api/jobs").status_code, 200)
            self.assertEqual(client.get(f"/log/{job.id}").status_code, 404)
        self.assertFalse(log_file.exists())
        self.assertFalse(metadata_file.exists())

    def test_clear_history_preserves_running_job_logs(self):
        job = app_module.Job("N_m3u8DL-RE running", ["N_m3u8DL-RE"])
        app_module._jobs[job.id] = job
        job.append_log("INFO : Still running\n")
        self.addCleanup(app_module._jobs.pop, job.id, None)
        self.addCleanup(lambda: app_module.log_file_path(job.id).unlink(missing_ok=True))
        self.addCleanup(job.close_log)
        with app_module.app.test_client() as client:
            self.assertEqual(client.delete("/api/jobs").status_code, 200)
        self.assertIn(job.id, app_module._jobs)
        self.assertTrue(app_module.log_file_path(job.id).is_file())


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
