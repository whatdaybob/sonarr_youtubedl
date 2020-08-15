# sonarr_youtubedl by [@whatdaybob](https://github.com/whatdaybob)

## What is it

Use this docker image to hook [Youtube-DL](https://ytdl-org.github.io/youtube-dl/index.html) into [Sonarr](https://sonarr.tv/) and download your webseries from the list of [supported sites](https://ytdl-org.github.io/youtube-dl/supportedsites.html).

## How do I use it

Firstly you need a series that is available online in the supported sites that YouTube-DL can grab from.
Secondly you need to add this to Sonarr and monitor the episodes that you want.
Thirdly edit your config.yml accordingly so that this knows where your Sonarr is, which series you are after and where to grab it from.
Lastly be aware that this requires the TVDB to match exactly what the episodes titles are in the scan, generally this is ok but as its an openly editable site sometime there can be differences.

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
sonarr:
    host: 192.168.1.123
    port: 1234
    apikey: 12341234
    ssl: false
series:
  - title: Shenanigans
    url: https://www.youtube.com/playlist?list=PLTur7oukosPFqFQkSpsJC8t2o9mRaxfVk
  - title: Ready Set Show
    url: https://www.youtube.com/playlist?list=PLTur7oukosPEwFTPJ1WeDvitauWzRiIhp
```

copy the `config.yml.template` to a new file called `config.yml` and edit accordingly.

If i helped in anyway and you would like to help me, consider donating a lovely beverage with the below.

<!-- markdownlint-disable MD033 -->
<a href="https://www.buymeacoffee.com/whatdaybob" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/lato-black.png" alt="Buy Me A Coffee" style="height: 51px !important;width: 217px !important;" ></a>
<!-- markdownlint-enable MD033 -->