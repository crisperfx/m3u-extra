# m3u-extra

[![Docker Hub build](https://github.com/crisperfx/m3u-extra/actions/workflows/docker-hub.yml/badge.svg)](https://github.com/crisperfx/m3u-extra/actions/workflows/docker-hub.yml)

| Manual command | Per-stream detail | Single-page log |
| --- | --- | --- |
| <img width="260" alt="Manual command entry" src="https://github.com/user-attachments/assets/48848608-4af6-465e-b2a6-09f3a81cbbc3" /><br><sub>Paste and run a full <code>N_m3u8DL-RE</code> command directly from the interface.</sub> | <img width="260" alt="Detailed progress per stream" src="https://github.com/user-attachments/assets/0f6164ab-7466-4814-a904-b1c7e218453c" /><br><sub>See the selected streams and progress for each job at a glance.</sub> | <img width="260" alt="Log and job details on one page" src="https://github.com/user-attachments/assets/74c969ed-b97f-4304-b444-9c66729ca292" /><br><sub>Follow the live log and job details together on one page.</sub> |

A small web interface for `N_m3u8DL-RE`. Paste a copied download command, start the job and follow the progress and live log in your browser. The Docker image already includes `N_m3u8DL-RE`, `ffmpeg` and `mp4decrypt`, so nothing needs to be installed locally.

## Quick start

With Docker:

```bash
docker run -d \
  --name ndl-web \
  -p 8000:8000 \
  -v /path/to/downloads:/downloads \
  -e TZ=Europe/Brussels \
  crisperfx/m3u-extra:latest
```

Then open `http://<server-or-nas-ip>:8000`.

With Docker Compose, use the included `docker-compose.yml`:

```bash
docker compose up -d
```

Files are stored in the folder you mount at `/downloads`.

## How to use

1. Paste the full `N_m3u8DL-RE` command into the text field.
2. Click **Start download**.
3. Use the compact `NL` / `EN` / `FR` button in the top-right corner to cycle between Dutch, English and French. The choice is remembered in your browser.
4. The homepage keeps the selected streams listed under each task and shows progress for the active stream only. A completed stream stays at 100% until the next stream starts. Overall progress is averaged over all selected streams and never moves backwards. Use **Log ↗** on a task to open the detailed live log when you want it.
5. The log page shows the selected streams and compact progress per stream. Per-segment and stream status lines (merging, decrypting, processing completed, finalizing) are filtered out to keep memory use low.
6. Under **Files** you can find, download or delete finished `.mkv` files.
7. Use **Options** to set an uploader tag and to enable or disable automatic resolution tags. Extension titles become `Title (year) 1080p Uploader` or `Series S01E03 1080p Uploader`. The resolution is measured from the downloaded file with `ffprobe` after completion, so the final name always matches the effective downloaded resolution.
8. Use **Queue** to add a job without starting it. Queued jobs appear in both the queue list and the task list; **Start queue** fills the available slots up to `MAX_CONCURRENT` and keeps starting the next queued job whenever a slot frees, until the queue is empty.
9. In **Options**, turn off **Start downloads immediately** to pause new submissions globally. They are queued instead of starting; **Start queue** remains the manual override.

Active jobs live in the container memory. Finished jobs and their filtered logs are saved under `/downloads/.logs`, so a log can be reopened after the download finishes and even after a container restart. Settings live in `/settings/settings.json`, outside the downloads mount. **Clear history** deletes the saved logs but never the settings. Files remain on disk as long as the `/downloads` mount is correct.

## Settings

Copy `.env.example` to `.env` when using Docker Compose. Fill in only what you need.

| Setting | What it does | Default |
| --- | --- | --- |
| `TZ` | Container time zone | `Europe/Brussels` in the example |
| `MAX_CONCURRENT` | Number of downloads that can run at the same time | `3` |
| `LOG_DIR` | Folder for saved logs and job history | `/downloads/.logs` |
| `SETTINGS_DIR` | Folder for `settings.json` with the uploader tag, resolution and auto-start settings | `/settings` |
| `WEB_USER` and `WEB_PASSWORD` | Basic login. Leave both empty to disable login protection. | empty |
| `EXT_TOKEN` | Secret token for the browser extension. Only needed if you want to start downloads from the extension. | empty |

`SETTINGS_FILE` is still accepted if you need to override the exact settings-file path.

For the browser extension, set the server URL to the address you use to open the web UI, for example `http://<server-or-nas-ip>:8000` (or `:7890` with the included Dockhand stack). Use the same value as `EXT_TOKEN` for the API token; leave it empty only if `EXT_TOKEN` is empty.

## Browser extension

The modified extension is included in `extension/`:

- `WidevineProxy2-1.2.37.crx` — drag this file onto `chrome://extensions` with Developer mode enabled.
- `WidevineProxy2-1.2.37.zip` — unpack it, then use **Load unpacked** and select the extracted folder (the one containing `manifest.json`).

The source files are in `extension/src`. The server URL and token are not hardcoded; open the extension options and enter them yourself. The manifest contains a fixed public key, so unpacked installs keep the same extension ID and keep these settings on later updates.

The popup **Update** button fetches the latest `extension/src` scripts from this GitHub repository, reloads the active page and shows the active live version, so no extension reinstall is needed. If GitHub is unreachable, the bundled scripts are used.

### What to fill in

Open the popup and click **Opties** (or right-click the extension and choose **Options**):

| Field | What to enter |
| --- | --- |
| **Server URL** | The URL you use for the web UI, for example `http://192.168.1.10:7890`. Only the scheme, host and port are stored; any path is removed. |
| **API-token** | The same value as `EXT_TOKEN` in `.env`. Leave empty when `EXT_TOKEN` is empty. |
| **Test server** | Checks `/api/health`; use this to confirm the URL and the Chrome host permission. |
| **Knopactie** | `copy_only`, `send_only` or `copy_send` (default). Sending posts to `/api/extension/submit` with the token in the request body. |

Click **Opslaan** after changing anything. Chrome asks for host permission for the server URL; accept it, otherwise sending will fail.

### Stream selection options

These settings build the `--select-video`, `--select-audio` and `--select-subtitle` parts of the command:

- **Video**: a preset dropdown with `none`, `best`, 1080p, 720p, 576p, 432p, 4K and a custom value. The **for** dropdown appends `:for=best`, `:for=best2`, `:for=worst`, etc.
- **Audio** and **Ondertiteling**: choose `none`, `for=all`, **Talen** (languages) or **Aangepast** (custom).
- In **Talen**, check Dutch (`nl|nld`), Flemish (`nl-BE`) and/or English (`en|eng`) and add extra codes such as `fr|fre` in the extra field. Multiple languages are combined into exact matches like `lang=^nl$|^nld$|^nl-BE$|^en$|^eng$`.
- The **for** dropdown appends `:for=best`, `:for=best2`, `:for=best3`, `:for=worst` or `:for=worst2` to language or custom selections. It is disabled for `none` and `for=all`.
- Select Flemish audio with the **Vlaams** checkbox plus **Beste 1**, or use custom `lang=^nl-BE$:for=best`. For two best tracks across Flemish and English use `lang=^nl-BE$|^en$:for=best2`. A bare `"nl|en":for=best2` is normalized to `lang=^nl$|^en$:for=best2`.
- Defaults: video `res=^1280x:for=best`, audio `for=all`, subtitles `for=all`.

### Extra compared with the stock extension

- Server URL and token are configurable and are never hardcoded.
- The key button can copy, send or do both; its label changes to `copy`, `send` or `copy+send`.
- Stream selectors and `for=best` are exposed in the options page instead of being fixed in the generated command.
- The popup shows `Now: <installed version>` with `Version Available: <live version>` underneath, plus **Reload** and **Update** buttons.
- Manifest headers stay intact, including the full `index.mpd?...` URL and the original `Origin`, `Referer` and `User-Agent` headers.
- Manifests without keys produce an empty `keys: []` entry, so no-key streams still generate a usable command.

## Updates

Every push to `main` that changes files other than `README.md` builds a new image and publishes it to Docker Hub. The latest build is available as `crisperfx/m3u-extra:latest`; each commit also gets a `sha-<commit>` tag. Tags such as `v1.0.0` are published with the same tag on Docker Hub.

To update:

```bash
docker compose pull
docker compose up -d
```

Or for a standalone container:

```bash
docker pull crisperfx/m3u-extra:latest
docker stop ndl-web
docker rm ndl-web
docker run -d --name ndl-web -p 8000:8000 -v /path/to/downloads:/downloads crisperfx/m3u-extra:latest
```

## Building locally

If you want to build the image yourself:

```bash
docker build -t crisperfx/m3u-extra:latest .
```

## Disclaimer

This project is not associated with or endorsed by any other project, service, or website. It is designed for educational purposes only.
