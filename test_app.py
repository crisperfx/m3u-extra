import atexit
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
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

DECRYPTING_LOG = (
    "23:24:24.484 INFO : Decrypting using MP4DECRYPT...\n"
    "Vid 1280x720 | 4003 Kbps | 25 Decrypting ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━           - - - 00:00:00\n"
    "Vid 1280x720 | 4003 Kbps | 25 Decrypting ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━           - - - 00:00:00\n"
    "Vid 1280x720 | 4003 Kbps | 25 Decrypting ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━           - - - 00:00:00\n"
)

PROCESSING_LOG = (
    "Vid 1280x720 | 4003 Kbps | 25 Processing completed ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     100.00% 1.11GB - 00:00:00\n"
    "Vid 1280x720 | 4003 Kbps | 25 Processing completed          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        100.00%          1.11GB    -    00:00:00\n"
    "Aud 640 Kbps | Surround | eng | F801CH Finalizing  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━           -      - - 00:00:00\n"
    "23:28:47.289 INFO : Aud 640 Kbps | Surround | eng | F801CH Processing completed\n"
    "23:28:47.331 WARN : Type: cenc\n"
)


class StreamParsingTests(unittest.TestCase):
    def test_parse_video_line(self):
        parsed = app_module.parse_stream_line(SAMPLE_LOG.splitlines()[1])
        self.assertEqual(parsed["kind"], "video")
        self.assertEqual(parsed["resolution"], "1920x1080")
        self.assertEqual(parsed["track"], "2")
        self.assertIn("avc1.640028", parsed["details"])

    def test_parse_video_line_with_name_before_resolution(self):
        parsed = app_module.parse_stream_line(
            "Vid Original | 1280x720 | 4528 Kbps | 1 | dvh1.05.02 | 358 Segments | Main | ~22m52s"
        )
        self.assertEqual(parsed["resolution"], "1280x720")
        self.assertEqual(parsed["track"], "1")

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

    def test_parse_flemish_audio_line(self):
        parsed = app_module.parse_stream_line("Aud eac-3 | Flemish | nl-BE | 6CH")
        self.assertEqual(parsed["language"], "Vlaams")
        self.assertEqual(parsed["language_code"], "nl-be")
        self.assertNotIn("Flemish", parsed["details"])
        self.assertNotIn("nl-BE", parsed["details"])

    def test_parse_region_audio_line(self):
        parsed = app_module.parse_stream_line("Aud eac-3 | English (UK) | en-GB | 6CH")
        self.assertEqual(parsed["language"], "Engels (UK)")
        self.assertEqual(parsed["language_code"], "en-gb")

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

    def test_job_progress_is_based_on_all_selected_streams(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe(SAMPLE_LOG)
        job.observe(PROGRESS_LOG)
        info = job.info()
        self.assertEqual(info["progress"], 2)
        self.assertEqual(len(info["progress_streams"]["video"]), 1)
        self.assertEqual(len(info["progress_streams"]["audio"]), 2)
        self.assertEqual(len(info["progress_streams"]["subtitle"]), 1)
        self.assertIn("10.82%", info["progress_streams"]["video"][0]["text"])

    def test_repeated_selected_streams_block_does_not_reset_progress(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe(SAMPLE_LOG)
        job.observe(PROGRESS_LOG)
        self.assertEqual(job.info()["progress"], 2)
        job.observe(SAMPLE_LOG)
        self.assertEqual(job.info()["progress"], 2)

    def test_overall_progress_does_not_drop_when_next_stream_starts(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe(SAMPLE_LOG)
        job.observe("Vid 1920x1080 | 5644 Kbps | 2 | 25 --- 100/100 100.00% done\n")
        self.assertEqual(job.info()["progress"], 25)
        job.observe("Aud 640 Kbps | Surround | eng | F801CH --- 0/100 0.00%\n")
        self.assertEqual(job.info()["progress"], 25)
        job.observe("Aud 640 Kbps | Surround | eng | F801CH --- 50/100 50.00%\n")
        self.assertEqual(job.info()["progress"], 37)

    def test_merging_lines_are_ignored(self):
        self.assertIsNone(app_module.parse_progress_line(MERGING_LOG.splitlines()[1]))
        log_filter = app_module.LogFilter()
        output = log_filter.feed(MERGING_LOG + "INFO : Done\n")
        self.assertNotIn("Merging", output)
        self.assertNotIn("4.17%", output)
        self.assertNotIn("95.55%", output)
        self.assertIn("Done", output)

    def test_decrypting_status_lines_are_ignored(self):
        self.assertIsNone(app_module.parse_progress_line(DECRYPTING_LOG.splitlines()[1]))
        log_filter = app_module.LogFilter()
        output = log_filter.feed(DECRYPTING_LOG)
        self.assertIn("Decrypting using MP4DECRYPT", output)
        self.assertNotIn("Decrypting ━", output)

    def test_processing_completed_status_lines_are_ignored(self):
        log_filter = app_module.LogFilter()
        output = log_filter.feed(PROCESSING_LOG)
        self.assertNotIn("Processing completed", output)
        self.assertNotIn("Finalizing", output)
        self.assertIn("Type: cenc", output)

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
        self.assertEqual(info["active_stream"]["percent"], 100.0)

    def test_selected_streams_block_resets_progress(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("INFO : Selected streams:\n")
        job.observe("Vid 1920x1080 | en | h264 --- 108/1000 10.82% 1.23MB/s\n")
        self.assertEqual(len(job.info()["progress_streams"]["video"]), 1)
        job.observe("INFO : Selected streams:\n")
        info = job.info()
        self.assertEqual(info["progress_streams"]["video"], [])
        self.assertIsNone(info["active_stream"])

    def test_active_stream_is_the_one_that_advances(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe(
            "Vid 1920x1080 | en | h264 --- 0/100 0.00%\n"
            "Aud 192 Kbps | Stereo | eng --- 0/100 0.00%\n"
            "Sub nld | Nederlands --- 0/100 0.00%\n"
        )
        job.observe(
            "Vid 1920x1080 | en | h264 --- 5/100 5.00%\n"
            "Aud 192 Kbps | Stereo | eng --- 0/100 0.00%\n"
            "Sub nld | Nederlands --- 0/100 0.00%\n"
        )
        active = job.info()["active_stream"]
        self.assertEqual(active["kind"], "video")
        self.assertEqual(active["current"], 5)

    def test_completed_stream_stays_visible_until_next_stream_advances(self):
        job = app_module.Job("x", ["N_m3u8DL-RE"])
        job.observe("Vid 1920x1080 | en | h264 --- 10/10 100.00%\n")
        active = job.info()["active_stream"]
        self.assertEqual(active["kind"], "video")
        self.assertEqual(active["percent"], 100.0)
        job.observe("Aud 192 Kbps | Stereo | eng --- 0/100 0.00%\n")
        active = job.info()["active_stream"]
        self.assertEqual(active["kind"], "video")
        job.observe("Aud 192 Kbps | Stereo | eng --- 5/100 5.00%\n")
        active = job.info()["active_stream"]
        self.assertEqual(active["kind"], "audio")
        self.assertEqual(active["current"], 5)

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
        self.assertEqual(info["active_stream"]["percent"], 100.0)


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

    def test_finished_live_job_uses_saved_log(self):
        job = app_module.Job("N_m3u8DL-RE live", ["N_m3u8DL-RE"])
        job.append_log("INFO : Saved live line\n")
        job.close_log()
        job.status = "done"
        job.finish_phase()
        app_module.write_archived_info(job)
        app_module._jobs[job.id] = job
        self.addCleanup(app_module._jobs.pop, job.id, None)
        self.addCleanup(lambda: app_module.metadata_file_path(job.id).unlink(missing_ok=True))
        self.addCleanup(lambda: app_module.log_file_path(job.id).unlink(missing_ok=True))
        with app_module.app.test_client() as client:
            stream = client.get(f"/api/jobs/{job.id}/stream").get_data(as_text=True)
        self.assertIn("Saved live line", stream)

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

    def test_subtitle_language_zzz_filter_is_removed(self):
        command = (
            'N_m3u8DL-RE.exe "https://example.com/index.mpd?'
            'aws.manifestfilter=subtitle_language%3Azzz%3Btrickplay_type%3Anone%3Baudio_codec%3AAACL" '
            '--save-name test'
        )
        with mock.patch.object(app_module, "fetch_manifest_text", return_value=None):
            argv = app_module.parse_command(command)
        source = argv[1]
        self.assertNotIn("subtitle_language", source)
        self.assertIn("trickplay_type%3Anone", source)
        self.assertIn("audio_codec%3AAACL", source)

    def test_other_subtitle_language_filter_is_preserved(self):
        command = (
            'N_m3u8DL-RE.exe "https://example.com/index.mpd?'
            'aws.manifestfilter=subtitle_language%3Anld%3Btrickplay_type%3Anone"'
        )
        with mock.patch.object(app_module, "fetch_manifest_text", return_value=None):
            argv = app_module.parse_command(command)
        self.assertIn("subtitle_language%3Anld", argv[1])

    def test_empty_manifestfilter_is_removed(self):
        command = (
            'N_m3u8DL-RE.exe "https://example.com/index.mpd?'
            'aws.manifestfilter=subtitle_language%3Azzz&foo=bar"'
        )
        with mock.patch.object(app_module, "fetch_manifest_text", return_value=None):
            argv = app_module.parse_command(command)
        self.assertNotIn("aws.manifestfilter", argv[1])
        self.assertIn("foo=bar", argv[1])


class TitleMetadataTests(unittest.TestCase):
    def test_series_title_from_meta(self):
        self.assertEqual(
            app_module.title_from_meta(
                {"title": "Omerta", "season": "1", "episode": 3}
            ),
            "Omerta S01E03",
        )

    def test_movie_title_from_meta(self):
        self.assertEqual(
            app_module.title_from_meta({"title": "The Loner", "year": "2026"}),
            "The Loner (2026)",
        )

    def test_resolution_from_meta_is_ignored(self):
        self.assertEqual(
            app_module.title_from_meta(
                {
                    "title": "The Odyssey",
                    "year": "2026",
                    "resolution": "1080p",
                }
            ),
            "The Odyssey (2026)",
        )

    def test_parse_command_uses_title_override(self):
        command = (
            'N_m3u8DL-RE.exe "https://example.com/index.mpd" '
            '--save-name "Omerta S1 A3 Hiep hiep hoera - Online kijken - Streamz"'
        )
        with mock.patch.object(app_module, "fetch_manifest_text", return_value=None):
            argv = app_module.parse_command(command, title_override="Omerta S01E03")
        self.assertEqual(argv[argv.index("--save-name") + 1], "Omerta S01E03")

    def test_extension_submit_applies_meta(self):
        with (
            mock.patch.object(app_module, "EXT_TOKEN", "token"),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
            mock.patch.object(app_module, "enqueue_job") as enqueue,
        ):
            enqueue.return_value.id = "abc"
            response = app_module.app.test_client().post(
                "/api/extension/submit",
                json={
                    "token": "token",
                    "command": 'N_m3u8DL-RE.exe "https://example.com/index.mpd"',
                    "meta": {"title": "The Loner", "year": "2026"},
                },
            )
        self.assertEqual(response.status_code, 201)
        argv = enqueue.call_args.args[1]
        self.assertEqual(argv[argv.index("--save-name") + 1], "The Loner (2026)")


class SettingsAndQueueTests(unittest.TestCase):
    def test_settings_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".settings.json"
            with mock.patch.object(app_module, "SETTINGS_FILE", path):
                client = app_module.app.test_client()
                saved = client.post(
                    "/api/settings",
                    json={"uploader_tag": "YTS", "resolution_tag": False},
                )
                self.assertEqual(saved.status_code, 200)
                loaded = client.get("/api/settings").get_json()
                self.assertEqual(
                    loaded,
                    {
                        "uploader_tag": "YTS",
                        "resolution_tag": False,
                        "auto_start": True,
                    },
                )

    def test_legacy_settings_are_migrated(self):
        with (
            tempfile.TemporaryDirectory() as settings_dir,
            tempfile.TemporaryDirectory() as download_dir,
        ):
            target = Path(settings_dir) / "settings.json"
            legacy = Path(download_dir) / ".settings.json"
            legacy.write_text(
                json.dumps({"uploader_tag": "YTS", "auto_start": False}),
                encoding="utf-8",
            )
            with (
                mock.patch.object(app_module, "SETTINGS_FILE", target),
                mock.patch.object(app_module, "LEGACY_SETTINGS_FILE", legacy),
            ):
                loaded = app_module.load_settings()
            self.assertEqual(loaded["uploader_tag"], "YTS")
            self.assertFalse(loaded["auto_start"])
            self.assertTrue(target.exists())
            self.assertFalse(legacy.exists())

    def test_auto_start_false_queues_new_jobs(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd"'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {"uploader_tag": "", "resolution_tag": True, "auto_start": False}
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(app_module, "SETTINGS_FILE", path),
                mock.patch.object(app_module, "_jobs", {}),
                mock.patch.object(app_module.Job, "launch") as launch,
                mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
            ):
                response = app_module.app.test_client().post(
                    "/api/jobs", json={"command": command}
                )
                self.assertEqual(response.status_code, 201)
                job = app_module._jobs[response.get_json()["id"]]
                self.assertEqual(job.status, "queued")
                launch.assert_not_called()

    def test_explicit_start_overrides_auto_start_false(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd"'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {"uploader_tag": "", "resolution_tag": True, "auto_start": False}
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(app_module, "SETTINGS_FILE", path),
                mock.patch.object(app_module, "_jobs", {}),
                mock.patch.object(app_module.Job, "launch") as launch,
                mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
            ):
                response = app_module.app.test_client().post(
                    "/api/jobs", json={"command": command, "queue": False}
                )
                self.assertEqual(response.status_code, 201)
                job = app_module._jobs[response.get_json()["id"]]
                self.assertEqual(job.status, "running")
                launch.assert_called_once()

    def test_uploader_tag_is_appended_to_save_name(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd"'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".settings.json"
            path.write_text(
                json.dumps({"uploader_tag": "YTS", "resolution_tag": True}),
                encoding="utf-8",
            )
            with (
                mock.patch.object(app_module, "SETTINGS_FILE", path),
                mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
                mock.patch.object(app_module, "detect_vod_drop_parts", return_value=None),
            ):
                argv = app_module.parse_command(
                    command, title_override="The Odyssey (2026)"
                )
        self.assertEqual(
            argv[argv.index("--save-name") + 1], "The Odyssey (2026) YTS"
        )

    def test_queue_job_is_not_started(self):
        with (
            mock.patch.object(app_module, "_jobs", {}),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
        ):
            response = app_module.app.test_client().post(
                "/api/jobs",
                json={
                    "command": 'N_m3u8DL-RE.exe "https://example.com/index.mpd"',
                    "queue": True,
                },
            )
            self.assertEqual(response.status_code, 201)
            job = app_module._jobs[response.get_json()["id"]]
            self.assertEqual(job.status, "queued")

    def test_start_queue_launches_queued_jobs(self):
        with (
            mock.patch.object(app_module, "_jobs", {}),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
            mock.patch.object(app_module.Job, "launch") as launch,
        ):
            client = app_module.app.test_client()
            client.post(
                "/api/jobs",
                json={
                    "command": 'N_m3u8DL-RE.exe "https://example.com/index.mpd"',
                    "queue": True,
                },
            )
            response = client.post("/api/jobs/queue/start")
            self.assertEqual(response.get_json()["started"], 1)
            launch.assert_called_once()

    def test_clear_history_preserves_queued_jobs(self):
        with (
            mock.patch.object(app_module, "_jobs", {}),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
        ):
            client = app_module.app.test_client()
            response = client.post(
                "/api/jobs",
                json={
                    "command": 'N_m3u8DL-RE.exe "https://example.com/index.mpd"',
                    "queue": True,
                },
            )
            client.delete("/api/jobs")
            self.assertIn(response.get_json()["id"], app_module._jobs)


class QueueDrainingTests(unittest.TestCase):
    class FakeJob:
        def __init__(self, status):
            self.status = status
            self.phase = status
            self.launch = mock.Mock()

    def test_queue_keeps_filling_free_slots(self):
        running = self.FakeJob("running")
        first = self.FakeJob("queued")
        second = self.FakeJob("queued")
        third = self.FakeJob("queued")
        with (
            mock.patch.object(
                app_module,
                "_jobs",
                {"running": running, "first": first, "second": second, "third": third},
            ),
            mock.patch.object(app_module, "_queue_pump_active", True),
            mock.patch.object(app_module, "MAX_CONCURRENT", 2),
        ):
            started, remaining = app_module.pump_queue_once()
            self.assertEqual(started, 1)
            self.assertEqual(remaining, 2)
            first.launch.assert_called_once()
            running.status = "done"

            started, remaining = app_module.pump_queue_once()
            self.assertEqual(started, 1)
            self.assertEqual(remaining, 1)
            second.launch.assert_called_once()
            first.status = "done"

            started, remaining = app_module.pump_queue_once()
            self.assertEqual(started, 1)
            self.assertEqual(remaining, 0)
            third.launch.assert_called_once()
            self.assertFalse(app_module._queue_pump_active)

    def test_queue_pump_is_inactive_without_start(self):
        first = self.FakeJob("queued")
        with (
            mock.patch.object(app_module, "_jobs", {"first": first}),
            mock.patch.object(app_module, "_queue_pump_active", False),
            mock.patch.object(app_module, "MAX_CONCURRENT", 3),
        ):
            started, remaining = app_module.pump_queue_once()
        self.assertEqual(started, 0)
        self.assertEqual(remaining, 1)
        first.launch.assert_not_called()


class JobStreamEditTests(unittest.TestCase):
    def test_stream_selectors_reads_long_and_short_options(self):
        argv = [
            "N_m3u8DL-RE",
            "-sv",
            "lang=eng",
            "--select-audio=lang=nld",
        ]
        self.assertEqual(
            app_module.stream_selectors(argv),
            {"video": "lang=eng", "audio": "lang=nld"},
        )

    def test_rewrite_stream_selectors_replaces_values(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd" -sv lang=eng -sa 7'
        result = app_module.rewrite_stream_selectors(
            command, {"video": "lang=nld", "audio": "lang=eng", "subtitle": ""}
        )
        self.assertIn("--select-video lang=nld", result)
        self.assertIn("--select-audio lang=eng", result)
        self.assertNotIn("lang=eng -sa", result)
        self.assertNotIn("--select-subtitle", result)

    def test_selector_for_tracks_builds_id_regex(self):
        self.assertEqual(
            app_module.selector_for_tracks(["10", "2", "10"]),
            "id=^(2|10)$:for=all",
        )
        self.assertEqual(app_module.selector_for_tracks([]), "for=all")

    def test_edit_streams_endpoint_accepts_tracks(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd"'
        job = app_module.Job(command, ["N_m3u8DL-RE", "https://example.com/index.mpd"])
        with (
            mock.patch.object(app_module, "_jobs", {job.id: job}),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
        ):
            response = app_module.app.test_client().post(
                f"/api/jobs/{job.id}/streams",
                json={"tracks": {"audio": ["15", "16"], "subtitle": []}},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["selectors"],
            {"audio": "id=^(15|16)$:for=all", "subtitle": "for=all"},
        )

    def test_edit_streams_endpoint_updates_queued_job(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd" -sv lang=eng'
        job = app_module.Job(command, ["N_m3u8DL-RE", "-sv", "lang=eng"])
        with (
            mock.patch.object(app_module, "_jobs", {job.id: job}),
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
        ):
            client = app_module.app.test_client()
            response = client.post(
                f"/api/jobs/{job.id}/streams",
                json={"video": "lang=nld", "audio": "", "subtitle": ""},
            )
        self.assertEqual(response.status_code, 200)
        info = response.get_json()
        self.assertEqual(info["selectors"], {"video": "lang=nld"})
        self.assertEqual(job.status, "queued")

    def test_edit_streams_endpoint_rejects_running_job(self):
        job = app_module.Job("N_m3u8DL-RE", ["N_m3u8DL-RE"])
        job.status = "running"
        with mock.patch.object(app_module, "_jobs", {job.id: job}):
            response = app_module.app.test_client().post(
                f"/api/jobs/{job.id}/streams", json={"video": "lang=nld"}
            )
        self.assertEqual(response.status_code, 409)

    def test_retry_endpoint_restarts_failed_job(self):
        command = 'N_m3u8DL-RE.exe "https://example.com/index.mpd"'
        job = app_module.Job(command, ["N_m3u8DL-RE", "https://example.com/index.mpd"])
        job.status = "failed"
        with (
            mock.patch.object(app_module, "_jobs", {job.id: job}),
            mock.patch.object(app_module.Job, "launch") as launch,
            mock.patch.object(app_module, "fetch_manifest_text", return_value=None),
        ):
            response = app_module.app.test_client().post(
                f"/api/jobs/{job.id}/retry"
            )
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.get_json()["id"], job.id)
        launch.assert_called_once()

    def test_retry_endpoint_rejects_running_job(self):
        job = app_module.Job("N_m3u8DL-RE", ["N_m3u8DL-RE"])
        job.status = "running"
        with mock.patch.object(app_module, "_jobs", {job.id: job}):
            response = app_module.app.test_client().post(
                f"/api/jobs/{job.id}/retry"
            )
        self.assertEqual(response.status_code, 409)


class EffectiveResolutionTests(unittest.TestCase):
    def test_strip_name_tags(self):
        self.assertEqual(
            app_module.strip_name_tags("The Odyssey (2026) YTS", ["YTS"]),
            "The Odyssey (2026)",
        )

    def test_apply_effective_resolution_renames_output(self):
        directory = Path(tempfile.mkdtemp(dir=app_module.DOWNLOAD_DIR))
        settings_dir = Path(tempfile.mkdtemp(dir=app_module.DOWNLOAD_DIR))
        self.addCleanup(shutil.rmtree, directory, True)
        self.addCleanup(shutil.rmtree, settings_dir, True)
        settings_path = settings_dir / ".settings.json"
        settings_path.write_text(
            json.dumps({"uploader_tag": "YTS", "resolution_tag": True}),
            encoding="utf-8",
        )
        old_name = "The Odyssey (2026) YTS"
        output_dir = directory / old_name
        output_dir.mkdir()
        (output_dir / f"{old_name}.mkv").write_bytes(b"fake")
        argv = ["N_m3u8DL-RE", "--save-dir", str(output_dir), "--save-name", old_name]
        with (
            mock.patch.object(app_module, "SETTINGS_FILE", settings_path),
            mock.patch.object(app_module, "probe_video_resolution", return_value="720p"),
        ):
            job = app_module.Job("command", argv)
            self.addCleanup(job.close_log)
            job.started = app_module.time.time()
            result = app_module.apply_effective_resolution(job)
        new_name = "The Odyssey (2026) 720p YTS"
        self.assertEqual(result, new_name)
        self.assertEqual(job.title, new_name)
        self.assertTrue((directory / new_name / f"{new_name}.mkv").exists())

    def test_apply_effective_resolution_skips_when_disabled(self):
        directory = Path(tempfile.mkdtemp(dir=app_module.DOWNLOAD_DIR))
        settings_dir = Path(tempfile.mkdtemp(dir=app_module.DOWNLOAD_DIR))
        self.addCleanup(shutil.rmtree, directory, True)
        self.addCleanup(shutil.rmtree, settings_dir, True)
        settings_path = settings_dir / ".settings.json"
        settings_path.write_text(
            json.dumps({"uploader_tag": "YTS", "resolution_tag": False}),
            encoding="utf-8",
        )
        old_name = "The Odyssey (2026) YTS"
        (directory / f"{old_name}.mkv").write_bytes(b"fake")
        argv = ["N_m3u8DL-RE", "--save-dir", str(directory), "--save-name", old_name]
        with mock.patch.object(app_module, "SETTINGS_FILE", settings_path):
            job = app_module.Job("command", argv)
            result = app_module.apply_effective_resolution(job)
        self.assertIsNone(result)
        self.assertTrue((directory / f"{old_name}.mkv").exists())


class StaticAssetTests(unittest.TestCase):
    def test_index_static_links_are_versioned(self):
        html = app_module.app.test_client().get("/").get_data(as_text=True)
        self.assertRegex(html, r"/static/style\.css\?v=1\.2\.36-\d+")
        self.assertRegex(html, r"/static/app\.js\?v=1\.2\.36-\d+")

    def test_mobile_bottom_nav_css_present(self):
        css = app_module.STATIC_DIR.joinpath("style.css").read_text(encoding="utf-8")
        self.assertIn("position: fixed", css)
        self.assertIn("bottom: calc(84px", css)
        self.assertIn("backdrop-filter: none", css)
        self.assertIn("z-index: 60", css)

    def test_queue_track_editor_present(self):
        js = app_module.STATIC_DIR.joinpath("app.js").read_text(encoding="utf-8")
        css = app_module.STATIC_DIR.joinpath("style.css").read_text(encoding="utf-8")
        self.assertIn("mode: 'tracks'", js)
        self.assertIn("box.type = 'checkbox'", js)
        self.assertIn("draft.tracks[kind]", js)
        self.assertIn(".track-row", css)

    def test_jobs_are_collapsible(self):
        js = app_module.STATIC_DIR.joinpath("app.js").read_text(encoding="utf-8")
        css = app_module.STATIC_DIR.joinpath("style.css").read_text(encoding="utf-8")
        self.assertIn("collapsedJobs", js)
        self.assertIn("job-toggle", js)
        self.assertIn("job-details", js)
        self.assertIn(".job-details[hidden]", css)


if __name__ == "__main__":
    unittest.main()
