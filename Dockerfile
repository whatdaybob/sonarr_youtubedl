# # Preparation Build for ffmpeg
# FROM alpine:latest as prep
# LABEL maintainer="Martin Jones <whatdaybob@outlook.com>"
# ENV FFMPEG_VERSION=5.0.1
# WORKDIR /tmp/ffmpeg
# RUN \
#     apk add --update build-base curl nasm tar bzip2 \
#     zlib-dev openssl-dev yasm-dev lame-dev libogg-dev x264-dev libvpx-dev libvorbis-dev x265-dev freetype-dev libass-dev libwebp-dev rtmpdump-dev libtheora-dev opus-dev && \
#     DIR=$(mktemp -d) && cd ${DIR} && \
#     curl -s http://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz | tar zxvf - -C . && \
#     cd ffmpeg-${FFMPEG_VERSION} && \
#     ./configure \
#     --enable-version3 --enable-gpl --enable-nonfree --enable-small --enable-libmp3lame --enable-libx264 --enable-libx265 --enable-libvpx --enable-libtheora --enable-libvorbis --enable-libopus --enable-libass --enable-libwebp --enable-librtmp --enable-postproc --enable-libfreetype --enable-openssl --disable-debug && \
#     make && \
#     make install && \
#     make distclean && \
#     rm -rf ${DIR} && \
#     apk del build-base curl tar bzip2 x264 openssl nasm && rm -rf /var/cache/apk/*

FROM lsiobase/ffmpeg:bin as ffmpeg

# Base Image to build from
FROM python:3.9-alpine as base

# Preparation Build for python packages
FROM base as builder
LABEL maintainer="Martin Jones <whatdaybob@outlook.com>"
RUN apk add --no-cache alpine-sdk
RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install --prefix='/install' -r /requirements.txt

# Final build
FROM base
LABEL maintainer="Martin Jones <whatdaybob@outlook.com>"
RUN apk add --no-cache alpine-sdk
# Copy ffmpeg from prep environment
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin
# Copy python requirements from prep environment
COPY --from=builder /install /usr/local
# add local files
COPY app/ /app
# create abc user so root isn't used
RUN adduser -S abc -G users
# create some files / folders
RUN mkdir -p /config /app /sonarr_root /logs && \
	touch /var/lock/sonarr_youtube.lock && \
# update file permissions
    chmod a+x \
    /app/sonarr_youtubedl.py \ 
    /app/utils.py \
    /app/config.yml.template

# add volumes
VOLUME /config
VOLUME /sonarr_root
VOLUME /logs

# ENV setup
ENV CONFIGPATH /config/config.yml

CMD [ "python", "-u", "/app/sonarr_youtubedl.py" ]
