import requests
import urllib.parse
import yt_dlp
import os
import sys
import re
from utils import upperescape, checkconfig, offsethandler, YoutubeDLLogger, ytdl_hooks, ytdl_hooks_debug, setup_logging  # NOQA
from datetime import datetime
import schedule
import time
import logging
import argparse

# allow debug arg for verbose logging
parser = argparse.ArgumentParser(description='Loads Configuration.')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args = parser.parse_args()

# setup logger
logger = setup_logging(True, True, args.debug)

date_format = "%Y-%m-%dT%H:%M:%SZ"
now = datetime.now()

CONFIGFILE = os.environ['CONFIGPATH']
CONFIGPATH = CONFIGFILE.replace('config.yml', '')
SCANINTERVAL = 60


class SonarrYTDL(object):

    def __init__(self):
        cfg = checkconfig()
        self.cfg_sonarrytdl(cfg)
        self.cfg_sonarr(cfg)
        self.cfg_series(cfg)
        self.cfg_ytdl(cfg)

    def cfg_sonarrytdl(self, cfg):
        """Loads main configuration

        Args:
            cfg (dict): Configuration File

        """
 
        try:
            self.set_scan_interval(cfg['sonarrytdl']['scan_interval'])
            try:
                self.debug = cfg['sonarrytdl']['debug'] in ['true', 'True']
                if self.debug:
                    logger.setLevel(logging.DEBUG)
                    for logs in logger.handlers:
                        if logs.name == 'FileHandler':
                            logs.setLevel(logging.DEBUG)
                        if logs.name == 'StreamHandler':
                            logs.setLevel(logging.DEBUG)
                    logger.debug('DEBUGGING ENABLED')
            except AttributeError:
                self.debug = False
        except Exception:
            sys.exit("Error with sonarrytdl config.yml values.")

    def cfg_sonarr(self, cfg):
        """Loads Sonarr configuration

        Args:
            cfg (dict): Configuration File

        """

        try:
            scheme = "http"
            if cfg['sonarr']['ssl'] in ['true', 'True']:
                scheme = "https"
            self.base_url = "{0}://{1}:{2}".format(
                scheme,
                cfg['sonarr']['host'],
                str(cfg['sonarr']['port'])
            )
            self.api_key = cfg['sonarr']['apikey']
        except Exception:
            sys.exit("Error with sonarr config.yml values.")

    def cfg_ytdl(self, cfg):
        """Loads YTDL configuration

        Args:
            cfg (dict): Configuration File

        """

        try:
            self.ytdl_format = cfg['ytdl']['default_format']
        except Exception:
            sys.exit("Error with ytdl config.yml values.")

    def cfg_series(self, cfg):
        """Loads Series configuration

        Args:
            cfg (dict): Configuration File

        """

        try:
            self.series = cfg["series"]
        except Exception:
            sys.exit("Error with series config.yml values.")

    def sonarr_response_handler(self, response):
        if response.status_code != 200:
            sys.exit('Issue communicating with sonarr!')
        elif response.status_code == 200:
            if isinstance(response.json(), list):
                return response.json()
            # If sonarr is available but doesn't return a list (can do this when errors like disk space happen)
            else:
                sys.exit('Sonarr available but not returning correct information.')

    def get_episodes_by_series_id(self, series_id):
        """Returns all episodes for the given series

        Args:
            series_id (int): Sonarr series id

        Returns:
            list: all episodes in the given series
        """

        logger.debug('Begin call Sonarr for all episodes for series_id: {}'.format(series_id))
        args = {'seriesId': series_id}
        res = self.request_get("{}/api/episode".format(
            self.base_url),
            args
        )
        return self.sonarr_response_handler(res)

    def get_series(self):
        """Return all series in your collection
        
        Returns:
            list: shows available in sonarr 
        """
        logger.debug('Begin call Sonarr for all available series')
        res = self.request_get("{}/api/series".format(
            self.base_url
        ))
        return self.sonarr_response_handler(res)


    def request_get(self, url, params=None):
        """Wrapper on the requests.get"""
        logger.debug('Begin GET with url: {}'.format(url))
        args = {
            "apikey": self.api_key
        }
        if params is not None:
            logger.debug('Begin GET with params: {}'.format(params))
            args.update(params)
        url = "{}?{}".format(
            url,
            urllib.parse.urlencode(args)
        )
        res = requests.get(url)
        return res

    def request_put(self, url, params=None, jsondata=None):
        """Wrapper on the requests.put

        Args:
            url (str): api that accepts put requests
            params (str, optional): additional url parameters. Defaults to None.
            jsondata (dict, optional): data to put to url. Defaults to None.

        Returns:
            Response: api response
        """        
        logger.debug('Begin PUT with url: {}'.format(url))
        headers = {
            'Content-Type': 'application/json',
        }
        args = (
            ('apikey', self.api_key),
        )
        if params is not None:
            args.update(params)
            logger.debug('Begin PUT with params: {}'.format(params))
        res = requests.post(
            url,
            headers=headers,
            params=args,
            json=jsondata
        )
        return res

    def rescanseries(self, series_id):
        """Refresh series information from trakt and rescan disk

        Args:
            series_id (int): Sonarr series id

        Returns:
            _type_: _description_
        """

        logger.debug('Begin call Sonarr to rescan for series_id: {}'.format(series_id))
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
        """Return all series in Sonarr that are to be downloaded by youtube-dl
        
        Returns:
            dict: containing configuration values
        """
        
        series = self.get_series()
        matched = []
        for ser in series[:]:
            for wnt in self.series:
                if wnt['title'] == ser['title']:
                    # Set default values
                    ser['subtitles'] = False
                    ser['playlistreverse'] = True
                    ser['subtitles_languages'] = ['en']
                    ser['subtitles_autogenerated'] = False
                    # Update values
                    if 'regex' in wnt:
                        regex = wnt['regex']
                        if 'sonarr' in regex:
                            ser['sonarr_regex'] = regex['sonarr']
                        if 'site' in regex:
                            ser['site_regex_match'] = regex['site']['match']
                            ser['site_regex_replace'] = regex['site']['replace']
                    if 'offset' in wnt:
                        ser['offset'] = wnt['offset']
                    if 'cookies_file' in wnt:
                        ser['cookies_file'] = wnt['cookies_file']
                    if 'format' in wnt:
                        ser['format'] = wnt['format']
                    if 'playlistreverse' in wnt:
                        if wnt['playlistreverse'] == 'False':
                            ser['playlistreverse'] = False
                    if 'subtitles' in wnt:
                        ser['subtitles'] = True
                        if 'languages' in wnt['subtitles']:
                            ser['subtitles_languages'] = wnt['subtitles']['languages']
                        if 'autogenerated' in wnt['subtitles']:
                            ser['subtitles_autogenerated'] = wnt['subtitles']['autogenerated']
                    ser['url'] = wnt['url']
                    matched.append(ser)
        for check in matched:
            if not check['monitored']:
                logger.warning('{0} is not currently monitored'.format(ser['title']))
        del series[:]
        return matched

    def getseriesepisodes(self, series):
        """ Gets episodes for a series where they are in the configuration file and exists in sonarr. 
            It only will get episodes that are monitored and dont have a file already.    

        Args:
            series (list): list of series to get episodes for

        Returns:
            list: missing monitored episodes episodes
        """

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
                    if 'sonarr_regex' in ser:
                        try:
                            for regex in ser['sonarr_regex']:
                                match = regex['match']
                                replace = regex['replace']
                                logger.debug('Updating episode title "{0}" with regex "{1}" and replacement "{2}"'.format(eps['title'], match, replace))
                                eps['title'] = re.sub(match, replace, eps['title'])
                                logger.debug('New title "{0}"'.format(eps['title']))
                        except TypeError:
                            logger.error('{0} has invalid settings for sonarr regex'.format(ser['title']))
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
                    'cookiefile': cookie_path
                })
                # if self.debug is True:
                logger.debug('  Cookies file used: {}'.format(cookie_path))
            if cookie_exists is False:
                logger.warning('  cookie files specified but doesn''t exist.')
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

    def ytdl_eps_search_opts(self, regextitle, playlistreverse, cookies=None):
        """Generates the Youtube DL options for searching a specific episode in a playlist

        Args:
            regextitle (str): Regex to use to match the episode name in youtube
            playlistreverse (bool): Search playlist videos in reverse order
            cookies (str, optional): cookie file location. Defaults to None.
        
        Returns:
            dict: Youtube DL options
        """

        ytdlopts = {
            'ignoreerrors': True,
            'playlistreverse': playlistreverse,
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
        """Search a playlist, channel or direct link using youtube dl match title regex.

        Args:
            ydl_opts (dict): contains basic youtube dl options to search with
            playlist (str): a youtube url to search

        Returns:
            (bool): True if found, False if not.
            (str):  direct video url if found, empty string if not.
        """

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(
                    playlist,
                    download=False
                )
                # Handle no results returned (possible deleted channel or issue with cookies) 
                if result == None:
                    logger.error('url {0} returned no videos, please check config.'.format(playlist))
                    return False, ''
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
                        ydleps = self.ytdl_eps_search_opts(upperescape(eps['title']), ser['playlistreverse'], cookies)
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
                            if 'subtitles' in ser:
                                if ser['subtitles']:
                                    postprocessors = []
                                    postprocessors.append({
                                        'key': 'FFmpegSubtitlesConvertor',
                                        'format': 'srt',
                                    })
                                    postprocessors.append({
                                        'key': 'FFmpegEmbedSubtitle',
                                    })
                                    autosubs = str(ser['subtitles_autogenerated']).lower() in ['true','t', 'y', 'yes']
                                    ytdl_format_options.update({
                                        'writesubtitles': True,                                        
                                        'writeautomaticsub': autosubs,
                                        'subtitleslangs': ser['subtitles_languages'],
                                        'postprocessors': postprocessors,
                                    })


                            if self.debug is True:
                                ytdl_format_options.update({
                                    'quiet': False,
                                    'logger': YoutubeDLLogger(),
                                    'progress_hooks': [ytdl_hooks_debug],
                                })
                                logger.debug('Youtube-DL opts used for downloading')
                                logger.debug(ytdl_format_options)
                            try:
                                with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
                                    ydl.download([dlurl])
                                self.rescanseries(ser['id'])
                                logger.info("      Downloaded - {}".format(eps['title']))
                            except Exception as e:
                                logger.error("      Failed - {} - {}".format(eps['title'], e))
                        else:
                            logger.info("    {}: Missing - {}:".format(e + 1, eps['title']))
        else:
            logger.info("Nothing to process")

    def set_scan_interval(self, interval):
        """ Changes the SCANINTERVAL if it is different that the default 60 Minutes
        Args:
            interval (int): Minutes to set SCANINTERVAL to.
        """

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


if __name__ == "__main__":
    logger.info('Initial run')
    main()
    schedule.every(int(SCANINTERVAL)).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
