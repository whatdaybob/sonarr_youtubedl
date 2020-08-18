# sonarr_youtubedl by [@whatdaybob](https://github.com/whatdaybob)

![Docker Build](https://img.shields.io/docker/cloud/automated/whatdaybob/sonarr_youtubedl?style=flat-square)
![Docker Pulls](https://img.shields.io/docker/pulls/whatdaybob/sonarr_youtubedl?style=flat-square)
![Docker Stars](https://img.shields.io/docker/stars/whatdaybob/sonarr_youtubedl?style=flat-square)
[![Docker Hub](https://img.shields.io/badge/Open%20On-DockerHub-blue)](https://hub.docker.com/r/whatdaybob/sonarr_youtubedl)

[whatdaybob/sonarr_youtubedl](https://github.com/whatdaybob/Custom_Docker_Images/tree/master/sonarr_youtubedl) is a [Sonarr](https://sonarr.tv/) companion script to allow the automatic downloading of web series normally not available for Sonarr to search for. Using [Youtube-DL](https://ytdl-org.github.io/youtube-dl/index.html) it allows you to download your webseries from the list of [supported sites](https://ytdl-org.github.io/youtube-dl/supportedsites.html).

## Features

* Downloading **Web Series** using online sources normally unavailable to Sonarr
* Ability to specify the downloaded video format globally or per series
* Downloads new episodes automatically once available
* Imports directly to Sonarr and it can then update your plex as and example
* Allows setting time offsets to handle prerelease series
* Can pass cookies.txt to handle site logins

## How do I use it

Firstly you need a series that is available online in the supported sites that YouTube-DL can grab from.
Secondly you need to add this to Sonarr and monitor the episodes that you want.
Thirdly edit your config.yml accordingly so that this knows where your Sonarr is, which series you are after and where to grab it from.
Lastly be aware that this requires the TVDB to match exactly what the episodes titles are in the scan, generally this is ok but as its an openly editable site sometime there can be differences.

## Supported Architectures

The architectures supported by this image are:

| Architecture | Tag |
| :----: | --- |
| x86-64 | latest |
| x86-64 | dev |

## Version Tags

| Tag | Description |
| :----: | --- |
| latest | Current release code |
| dev | Pre-release code for testing issues |

## Great how do I get started

Obviously its a docker image so you need docker, if you don't know what that is you need to look into that first.

### docker

```bash
docker create \
  --name=sonarr_youtubedl \
  -v /path/to/data:/config \
  -v /path/to/sonarrmedia:/sonarr_root \
  --restart unless-stopped \
  whatdaybob/sonarr_youtubedl
```

### docker-compose

```yaml
---
version: '3.4'
services:
  sonarr_youtubedl:
    image: whatdaybob/sonarr_youtubedl
    container_name: sonarr_youtubedl
    volumes:
      - /path/to/data:/config
      - /path/to/sonarrmedia:/sonarr_root
```

### Docker volumes

| Parameter | Function |
| :----: | --- |
| `-v /config` | sonarr_youtubedl configs |
| `-v /sonarr_root` | Library location from Sonarr container |

## Configuration file

On first run the docker will create a template file in the config folder.

```yaml
sonarrytdl:
    scan_interval: 1 # Minutes between scan
sonarr:
    host: 192.168.1.123
    port: 1234
    apikey: 12341234
    ssl: false
ytdl:
  # For information on format refer to https://github.com/ytdl-org/youtube-dl#format-selection
    default_format: bestvideo[width<=1920]+bestaudio/best[width<=1920]
series:
  # Standard channel to check
  - title: Smarter Every Day
    url: https://www.youtube.com/channel/UC6107grRI4m0o2-emgoDnAA
  # Example using cookies file and custom format
  # For information on cookies refer to https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl
  # For information on format refer to https://github.com/ytdl-org/youtube-dl#format-selection
  - title: The Slow Mo Guys
    url: https://www.youtube.com/channel/UCUK0HBIBWgM2c4vsPhkYY4w
    cookies_file: youtube_cookies.txt # located in the same config folder
    format: bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best
  # Youtube playlist of latest season with time offset, useful for member videos having early release
  - title: CHUMP
    url: https://www.youtube.com/playlist?list=PLUBVPK8x-XMiVzV098TtYq55awkA2XmXm
    offset:
      days: 2
      hours: 3
```

copy the `config.yml.template` to a new file called `config.yml` and edit accordingly.

If I helped in anyway and you would like to help me, consider donating a lovely beverage with the below.

<!-- markdownlint-disable MD033 -->
<a href="https://www.buymeacoffee.com/whatdaybob" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/lato-black.png" alt="Buy Me A Coffee" style="height: 51px !important;width: 217px !important;" ></a>
<!-- markdownlint-enable MD033 -->