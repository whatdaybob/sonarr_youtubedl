import requests
import urllib.parse
import youtube_dl
import os
import sys
import re
from utils import upperescape, checkconfig, offsethandler, YoutubeDLLogger, ytdl_hooks, ytdl_hooks_debug
from datetime import datetime
import schedule
import time
import logging

# setup logger
logger = logging.getLogger('sonarr_youtubedl')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# setup logfile
loggerfile = logging.FileHandler('sonarr_youtubedl.log')
loggerfile.setLevel(logging.INFO)
loggerfile.setFormatter(formatter)
logger.addHandler(loggerfile)

# setup console log
loggerconsole = logging.StreamHandler()
loggerconsole.setLevel(logging.INFO)
loggerconsole.setFormatter(formatter)
logger.addHandler(loggerconsole)

date_format = "%Y-%m-%dT%H:%M:%SZ"
now = datetime.now()

CONFIGFILE = os.environ['CONFIGPATH']
CONFIGPATH = CONFIGFILE.replace('config.yml', '')
SCANINTERVAL = 60


class SonarrYTDL(object):

    def __init__(self):
        """Set up app with config file settings"""
        cfg = checkconfig()

        # Sonarr_YTDL Setup

        try:
            self.set_scan_interval(cfg['sonarrytdl']['scan_interval'])
            try:
                self.debug = cfg['sonarrytdl']['debug'] in ['true', 'True']
                if self.debug:
                    logger.setLevel(logging.DEBUG)
                    loggerconsole.setLevel(logging.DEBUG)
                    loggerfile.setLevel(logging.DEBUG)
                    logger.debug('DEBUGGING ENABLED')
            except AttributeError:
                self.debug = False
        except Exception:
            sys.exit("Error with sonarrytdl config.yml values.")

        # Sonarr Setup
        try:
            scheme = "http"
            if cfg['sonarr']['ssl']:
                scheme == "https"
            self.base_url = "{0}://{1}:{2}".format(
                scheme,
                cfg['sonarr']['host'],
                str(cfg['sonarr']['port'])
            )
            self.api_key = cfg['sonarr']['apikey']
        except Exception:
            sys.exit("Error with sonarr config.yml values.")

        # YTDL Setup
        try:
            self.ytdl_format = cfg['ytdl']['default_format']
        except Exception:
            sys.exit("Error with ytdl config.yml values.")

        # YTDL Setup
        try:
            self.series = cfg["series"]
        except Exception:
            sys.exit("Error with series config.yml values.")

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
                    if 'regex' in wnt:
                        regex = wnt['regex']
                        if 'sonarr' in regex:
                            ser['sonarr_regex_match'] = regex['sonarr']['match']
                            ser['sonarr_regex_replace'] = regex['sonarr']['replace']
                        if 'site' in regex:
                            ser['site_regex_match'] = regex['site']['match']
                            ser['site_regex_replace'] = regex['site']['replace']
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
                logger.warn('{0} is not currently monitored'.format(ser['title']))
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
                    if 'sonarr_regex_match' in ser:
                        match = ser['sonarr_regex_match']
                        replace = ser['sonarr_regex_replace']
                        eps['title'] = re.sub(match, replace, eps['title'])
                    needed.append(eps)
                    continue
            if len(episodes) == 0:
                logger.info('{0} no episodes needed'.format(ser['title']))
                series.remove(ser)
            else:
                logger.info('{0} missing {1} episodes'.format(
                    ser['title'],
                    len(episodes)
                ))
                for i, e in enumerate(episodes):
                    logger.info('  {0}: {1} - {2}'.format(
                        i + 1,
                        ser['title'],
                        e['title']
                    ))
        return needed

    def appendcookie(self, ytdlopts, cookies=None):
        """Checks if specified cookie file exists in config
        - ``ytdlopts``: Youtube-dl options to append cookie to
        - ``cookies``: filename of cookie file to append to Youtube-dl opts
        returns:
            ytdlopts
                original if problem with cookies file
                updated with cookies value if cookies file exists
        """
        if cookies is not None:
            cookie_path = os.path.abspath(CONFIGPATH + cookies)
            cookie_exists = os.path.exists(cookie_path)
            if cookie_exists is True:
                ytdlopts.update({
                    'cookie': cookie_path
                })
                # if self.debug is True:
                logger.debug('  Cookies file used: {}'.format(cookie_path))
            if cookie_exists is False:
                logger.warn('  cookie files specified but doesn''t exist.')
            return ytdlopts
        else:
            return ytdlopts

    def customformat(self, ytdlopts, customformat=None):
        """Checks if specified cookie file exists in config
        - ``ytdlopts``: Youtube-dl options to change the ytdl format for
        - ``customformat``: format to download
        returns:
            ytdlopts
                original: if no custom format
                updated: with new format value if customformat exists
        """
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
        if self.debug is True:
            ytdlopts.update({
                'quiet': False,
                'logger': YoutubeDLLogger(),
                'progress_hooks': [ytdl_hooks],
            })
        ytdlopts = self.appendcookie(ytdlopts, cookies)
        if self.debug is True:
            logger.debug('Youtube-DL opts used for episode matching')
            logger.debug(ytdlopts)
        return ytdlopts

    def ytsearch(self, ydl_opts, playlist):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(
                    playlist,
                    download=False
                )
        except Exception as e:
            logger.error(e)
        else:
            video_url = None
            if 'entries' in result and len(result['entries']) > 0:
                try:
                    video_url = result['entries'][0].get('webpage_url')
                except Exception as e:
                    logger.error(e)
            else:
                video_url = result.get('webpage_url')
            if playlist == video_url:
                return False, ''
            if video_url is None:
                logger.error('No video_url')
                return False, ''
            else:
                return True, video_url

    def download(self, series, episodes):
        if len(series) != 0:
            logger.info("Processing Wanted Downloads")
            for s, ser in enumerate(series):
                logger.info("  {}:".format(ser['title']))
                for e, eps in enumerate(episodes):
                    if ser['id'] == eps['seriesId']:
                        cookies = None
                        url = ser['url']
                        if 'cookies_file' in ser:
                            cookies = ser['cookies_file']
                        ydleps = self.ytdl_eps_search_opts(upperescape(eps['title']), cookies)
                        found, dlurl = self.ytsearch(ydleps, url)
                        if found:
                            logger.info("    {}: Found - {}:".format(e + 1, eps['title']))
                            ytdl_format_options = {
                                'format': self.ytdl_format,
                                'quiet': True,
                                'merge-output-format': 'mp4',
                                'outtmpl': '/sonarr_root{0}/Season {1}/{2} - S{1}E{3} - {4} WEBDL.%(ext)s'.format(
                                    ser['path'],
                                    eps['seasonNumber'],
                                    ser['title'],
                                    eps['episodeNumber'],
                                    eps['title']
                                ),
                                'progress_hooks': [ytdl_hooks],
                                'noplaylist': True,
                            }
                            ytdl_format_options = self.appendcookie(ytdl_format_options, cookies)
                            if 'format' in ser:
                                ytdl_format_options = self.customformat(ytdl_format_options, ser['format'])
                            if self.debug is True:
                                ytdl_format_options.update({
                                    'quiet': False,
                                    'logger': YoutubeDLLogger(),
                                    'progress_hooks': [ytdl_hooks_debug],
                                })
                                logger.debug('Youtube-DL opts used for downloading')
                                logger.debug(ytdl_format_options)
                            try:
                                youtube_dl.YoutubeDL(ytdl_format_options).download([dlurl])
                                self.rescanseries(ser['id'])
                                logger.info("      Downloaded - {}".format(eps['title']))
                            except Exception as e:
                                logger.error("      Failed - {} - {}".format(eps['title'], e))
                        else:
                            logger.info("    {}: Missing - {}:".format(e + 1, eps['title']))
        else:
            logger.info("Nothing to process")

    def set_scan_interval(self, interval):
        global SCANINTERVAL
        if interval != SCANINTERVAL:
            SCANINTERVAL = interval
            logger.info('Scan interval set to every {} minutes by config.yml'.format(interval))
        else:
            logger.info('Default scan interval of every {} minutes in use'.format(interval))
        return


def main():
    client = SonarrYTDL()
    series = client.filterseries()
    episodes = client.getseriesepisodes(series)
    client.download(series, episodes)
    logger.info('Waiting...')


logger.info('Initial run')
main()
schedule.every(int(SCANINTERVAL)).minutes.do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
