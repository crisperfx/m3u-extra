# m3u-extra

[![Docker Hub build](https://github.com/crisperfx/m3u-extra/actions/workflows/docker-hub.yml/badge.svg)](https://github.com/crisperfx/m3u-extra/actions/workflows/docker-hub.yml)

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
3. The live log opens in a separate tab, with the current phase and progress percentage.
4. Under **Files** you can find, download or delete finished `.mkv` files.

Active jobs live in the container memory. Files remain on disk as long as the `/downloads` mount is correct.

## Settings

Copy `.env.example` to `.env` when using Docker Compose. Fill in only what you need.

| Setting | What it does | Default |
| --- | --- | --- |
| `TZ` | Container time zone | `Europe/Brussels` in the example |
| `MAX_CONCURRENT` | Number of downloads that can run at the same time | `3` |
| `WEB_USER` and `WEB_PASSWORD` | Basic login. Leave both empty to disable login protection. | empty |
| `EXT_TOKEN` | Secret token for the browser extension. Only needed if you want to start downloads from the extension. | empty |

For the browser extension, set the server URL to `http://<server-or-nas-ip>:8000` and use the same value as `EXT_TOKEN` for the token.

## Browser extension

The modified extension is included in `extension/`:

- `WidevineProxy2-1.2.7.crx` — drag this file onto `chrome://extensions` with Developer mode enabled.
- `WidevineProxy2-1.2.7.zip` — unpack it, then use **Load unpacked** and select the `src` folder.

The source files are in `extension/src`. The server URL and token are not hardcoded; open the extension options and enter them yourself.

## Updates

Every push to `main` builds a new image and publishes it to Docker Hub. The latest build is available as `crisperfx/m3u-extra:latest`; each commit also gets a `sha-<commit>` tag. Tags such as `v1.0.0` are published with the same tag on Docker Hub.

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

## Automatic publishing

The workflow is in `.github/workflows/docker-hub.yml`. Publishing needs two repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (a Docker Hub access token, not your account password)

Without these secrets the code still works, but no image is published. Set the Docker Hub repository to **Public** if everyone should be able to pull the image without logging in.
