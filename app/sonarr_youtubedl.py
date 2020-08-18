import yaml
import requests
import urllib.parse
import youtube_dl
import os
from utils import upperescape, checkconfig, offsethandler
from datetime import datetime
import schedule
import time

date_format = "%Y-%m-%dT%H:%M:%SZ"
now = datetime.now()
CONFIGFILE = os.environ['CONFIGPATH']
CONFIGPATH = CONFIGFILE.replace('config.yml', '')
SCANINTERVAL = 60


class SonarrYTDL(object):

    def __init__(self):
        """Set up app with config"""
        checkconfig()
        with open(
            CONFIGFILE,
            "r"
        ) as ymlfile:
            cfg = yaml.load(
                ymlfile,
                Loader=yaml.BaseLoader
            )
        self.ipaddr = cfg['sonarr']['host']
        self.port = str(cfg['sonarr']['port'])
        scheme = "http"
        if cfg['sonarr']['ssl']:
            scheme == "https"
        self.base_url = "{0}://{1}:{2}".format(
            scheme,
            self.ipaddr,
            self.port
        )
        self.api_key = cfg['sonarr']['apikey']
        self.series = cfg["series"]
        self.ytdl_format = cfg['ytdl']['default_format']
        self.set_scan_interval(cfg['sonarrytdl']['scan_interval'])

    def get_episodes_by_series_id(self, series_id):
        """Returns all episodes for the given series"""
        args = {'seriesId': series_id}
        res = self.request_get("{}/api/episode".format(
            self.base_url),
            args
        )
        return res.json()

    def get_episode_files_by_series_id(self, series_id):
        """Returns all episode files for the given series"""
        res = self.request_get("{}/api/episodefile?seriesId={}".format(
            self.base_url,
            series_id
        ))
        return res.json()

    def get_series(self):
        """Return all series in your collection"""
        res = self.request_get("{}/api/series".format(
            self.base_url
        ))
        return res.json()

    def get_series_by_series_id(self, series_id):
        """Return the series with the matching ID or 404 if no matching series is found"""
        res = self.request_get("{}/api/series/{}".format(
            self.base_url,
            series_id
        ))
        return res.json()

    def request_get(self, url, params=None):
        """Wrapper on the requests.get"""
        args = {
            "apikey": self.api_key
        }
        if params is not None:
            args.update(params)
        url = "{}?{}".format(
            url,
            urllib.parse.urlencode(args)
        )
        res = requests.get(url)
        return res

    def request_put(self, url, params=None, jsondata=None):
        """Wrapper on the requests.put"""
        headers = {
            'Content-Type': 'application/json',
        }
        args = (
            ('apikey', self.api_key),
        )
        if params is not None:
            args.update(params)
        res = requests.post(
            url,
            headers=headers,
            params=args,
            json=jsondata
        )
        return res

    def rescanseries(self, series_id):
        """Refresh series information from trakt and rescan disk"""
        data = {
            "name": "RescanSeries",
            "seriesId": str(series_id)
        }
        res = self.request_put(
            "{}/api/command".format(self.base_url),
            None,
            data
        )
        return res.json()

    def filterseries(self):
        """Return all series in Sonarr that are to be downloaded by youtube-dl"""
        series = self.get_series()
        matched = []
        for ser in series[:]:
            for wnt in self.series:
                if wnt['title'] == ser['title']:
                    if 'offset' in wnt:
                        ser['offset'] = wnt['offset']
                    if 'cookies_file' in wnt:
                        ser['cookies_file'] = wnt['cookies_file']
                    if 'format' in wnt:
                        ser['format'] = wnt['format']
                    ser['url'] = wnt['url']
                    matched.append(ser)
        for check in matched:
            if not check['monitored']:
                print('WARNING: {0} is not currently monitored'.format(ser['title']))
        del series[:]
        return matched

    def getseriesepisodes(self, series):
        needed = []
        for ser in series[:]:
            episodes = self.get_episodes_by_series_id(ser['id'])
            for eps in episodes[:]:
                eps_date = now
                if "airDateUtc" in eps:
                    eps_date = datetime.strptime(eps['airDateUtc'], date_format)
                    if 'offset' in ser:
                        eps_date = offsethandler(eps_date, ser['offset'])
                if not eps['monitored']:
                    episodes.remove(eps)
                elif eps['hasFile']:
                    episodes.remove(eps)
                elif eps_date > now:
                    episodes.remove(eps)
                else:
                    needed.append(eps)
                    continue
            if len(episodes) == 0:
                print('{0} no episodes needed'.format(ser['title']))
                series.remove(ser)
            else:
                print('{0} missing {1} episodes'.format(
                    ser['title'],
                    len(episodes)
                ))
                for i, e in enumerate(episodes):
                    print('  {0}: {1} - {2}'.format(
                        i + 1,
                        ser['title'],
                        e['title']
                    ))
        return needed

    def appendcookie(self, ytdlopts, cookies=None):
        if cookies is not None:
            ytdlopts.update({
                'cookie': CONFIGPATH + cookies
            })
            return ytdlopts
        else:
            return ytdlopts

    def customformat(self, ytdlopts, customformat=None):
        if customformat is not None:
            ytdlopts.update({
                'format': customformat
            })
            return ytdlopts
        else:
            return ytdlopts

    def ytdl_eps_search_opts(self, regextitle, cookies=None):
        ytdlopts = {
            'ignoreerrors': True,
            'playlistreverse': True,
            'matchtitle': regextitle,
            'quiet': True,
        }
        ytdlopts = self.appendcookie(ytdlopts, cookies)
        return ytdlopts

    def ytsearch(self, ydl_opts, playlist):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(
                    playlist,
                    download=False
                )
        except Exception as e:
            print(e)
        else:
            video_url = None
            if 'entries' in result and len(result['entries']) > 0:
                try:
                    video_url = result['entries'][0].get('webpage_url')
                except Exception as e:
                    print(e)
            else:
                video_url = result.get('webpage_url')
            if playlist == video_url:
                return False, ''
            if video_url is None:
                print('')
                return False, ''
            else:
                return True, video_url

    def download(self, series, episodes):
        print("", "Processing Wanted Downloads", sep="\n")
        for s, ser in enumerate(series):
            print("{}:".format(ser['title']))
            for e, eps in enumerate(episodes):
                if ser['id'] == eps['seriesId']:
                    cookies = None
                    url = ser['url']
                    if 'cookies_file' in ser:
                        cookies = ser['cookies_file']
                    ydleps = self.ytdl_eps_search_opts(upperescape(eps['title']), cookies)
                    found, dlurl = self.ytsearch(ydleps, url)
                    if found:
                        print("", "{}: Found - {}:".format(e + 1, eps['title']), sep="  ")
                        ytdl_format_options = {
                            'format': self.ytdl_format,
                            'merge-output-format': 'mp4',
                            'outtmpl': '/sonarr_root{0}/Season {1}/{2} - S{1}E{3} - {4} WEBDL.%(ext)s'.format(
                                ser['path'],
                                eps['seasonNumber'],
                                ser['title'],
                                eps['episodeNumber'],
                                eps['title']
                            )
                        }
                        ytdl_format_options = self.appendcookie(ytdl_format_options, cookies)
                        if 'format' in ser:
                            ytdl_format_options = self.customformat(ytdl_format_options, ser['format'])
                        youtube_dl.YoutubeDL(ytdl_format_options).download([dlurl])
                        self.rescanseries(ser['id'])
                    else:
                        print("", "{}: Missing - {}:".format(e + 1, eps['title']), sep="  ")

    def set_scan_interval(self, interval):
        global SCANINTERVAL
        if interval != SCANINTERVAL:
            SCANINTERVAL = interval
            print('Scan interval set to every {} minutes by config.yml'.format(interval))
        else:
            print('Default scan interval of every {} minutes in use'.format(interval))
        return


def main():
    client = SonarrYTDL()
    series = client.filterseries()
    episodes = client.getseriesepisodes(series)
    client.download(series, episodes)
    print('Waiting...')


print('Initial run')
main()
schedule.every(int(SCANINTERVAL)).minutes.do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
