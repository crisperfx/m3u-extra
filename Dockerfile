FROM alpine:3.21 AS ndl-build

ARG NDL_COMMIT=7849be8437148b33324d5ba298804d49d3add3d8
ARG DOTNET_SDK_VERSION=10.0.300

RUN apk add --no-cache \
      bash \
      wget \
      tar \
      clang \
      build-base \
      cmake \
      icu-dev \
      icu-data-full \
      zlib-static \
      openssl-dev \
      openssl-libs-static

RUN wget -nv "https://builds.dotnet.microsoft.com/dotnet/Sdk/${DOTNET_SDK_VERSION}/dotnet-sdk-${DOTNET_SDK_VERSION}-linux-musl-x64.tar.gz" -O /tmp/dotnet-sdk.tar.gz \
 && mkdir -p /opt/dotnet \
 && tar -xzf /tmp/dotnet-sdk.tar.gz -C /opt/dotnet \
 && rm -f /tmp/dotnet-sdk.tar.gz

ENV PATH="/opt/dotnet:${PATH}" \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1

WORKDIR /src

RUN wget -nv "https://codeload.github.com/nilaoda/N_m3u8DL-RE/tar.gz/${NDL_COMMIT}" -O /tmp/ndl-src.tar.gz \
 && tar -xzf /tmp/ndl-src.tar.gz -C /src --strip-components=1 \
 && rm -f /tmp/ndl-src.tar.gz \
 && dotnet publish src/N_m3u8DL-RE -r linux-musl-x64 -c Release -o /out

FROM python:3.12-slim

ARG BENTO4_VERSION=1-6-0-641

LABEL org.opencontainers.image.source="https://github.com/crisperfx/m3u-extra" \
      org.opencontainers.image.description="Webinterface voor N_m3u8DL-RE downloads"

ENV PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/downloads \
    SETTINGS_DIR=/settings \
    NDL_BINARY=/usr/local/bin/N_m3u8DL-RE \
    FFMPEG_BINARY=/usr/bin/ffmpeg \
    MP4DECRYPT_BINARY=/usr/local/bin/mp4decrypt

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip ffmpeg libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ndl-build /out/N_m3u8DL-RE /usr/local/bin/N_m3u8DL-RE

RUN chmod 0755 /usr/local/bin/N_m3u8DL-RE

RUN curl -fsSL "https://www.bok.net/Bento4/binaries/Bento4-SDK-${BENTO4_VERSION}.x86_64-unknown-linux.zip" -o /tmp/bento4.zip \
 && unzip -j /tmp/bento4.zip '*/bin/mp4decrypt' -d /usr/local/bin \
 && chmod 0755 /usr/local/bin/mp4decrypt \
 && rm -f /tmp/bento4.zip

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/

RUN mkdir -p /downloads /settings

EXPOSE 8000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=16", "app:app"]
