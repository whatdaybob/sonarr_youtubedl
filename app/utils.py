import re
import os
import sys
import datetime
import yaml
import logging

CONFIGFILE = os.environ['CONFIGPATH']
# CONFIGPATH = CONFIGFILE.replace('config.yml', '')


def upperescape(string):
    """Uppercase and Escape string. Used to help with YT-DL regex match.
    - ``string``: string to manipulate

    returns:
        ``string``: str new string
    """
    string = string.upper()
    string = re.escape(string)
    return string


def checkconfig():
    """Checks if config files exist in config path
    If no config available, will copy template to config folder and exit script

    returns:

        `cfg`: dict containing configuration values
    """
    logger = logging.getLogger('sonarr_youtubedl')
    config_template = os.path.abspath(CONFIGFILE + '.template')
    config_template_exists = os.path.exists(os.path.abspath(config_template))
    config_file = os.path.abspath(CONFIGFILE)
    config_file_exists = os.path.exists(os.path.abspath(config_file))
    if not config_file_exists:
        logger.critical('Configuration file not found.')  # print('Configuration file not found.')
        if not config_template_exists:
            os.system('cp /app/config.yml.template ' + config_template)
        logger.critical("Create a config.yml using config.yml.template as an example.")  # sys.exit("Create a config.yml using config.yml.template as an example.")
        sys.exit()
    else:
        logger.info('Configuration Found. Loading file.')  # print('Configuration Found. Loading file.')
        with open(
            config_file,
            "r"
        ) as ymlfile:
            cfg = yaml.load(
                ymlfile,
                Loader=yaml.BaseLoader
            )
        return cfg


def offsethandler(airdate, offset):
    """Adjusts an episodes airdate
    - ``airdate``: Airdate from sonarr # (datetime)
    - ``offset``: Offset from series config.yml # (dict)

    returns:
        ``airdate``: datetime updated original airdate
    """
    weeks = 0
    days = 0
    hours = 0
    minutes = 0
    if 'weeks' in offset:
        weeks = int(offset['weeks'])
    if 'days' in offset:
        days = int(offset['days'])
    if 'hours' in offset:
        hours = int(offset['hours'])
    if 'minutes' in offset:
        minutes = int(offset['minutes'])
    airdate = airdate + datetime.timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes)
    return airdate


class YoutubeDLLogger(object):

    def __init__(self):
        self.logger = logging.getLogger('sonarr_youtubedl')

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def warning(self, msg: str) -> None:
        self.logger.info(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)


def ytdl_hooks_debug(d):
    logger = logging.getLogger('sonarr_youtubedl')
    if d['status'] == 'finished':
        file_tuple = os.path.split(os.path.abspath(d['filename']))
        logger.info("      Done downloading {}".format(file_tuple[1]))  # print("Done downloading {}".format(file_tuple[1]))
    if d['status'] == 'downloading':
        progress = "      {} - {} - {}".format(d['filename'], d['_percent_str'], d['_eta_str'])
        logger.debug(progress)


def ytdl_hooks(d):
    logger = logging.getLogger('sonarr_youtubedl')
    if d['status'] == 'finished':
        file_tuple = os.path.split(os.path.abspath(d['filename']))
        logger.info("      Downloaded - {}".format(file_tuple[1]))


def setup_logging(lf_enabled=True, lc_enabled=True):

    logger = logging.getLogger('sonarr_youtubedl')
    logger.setLevel(logging.INFO)
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if lf_enabled:
        # setup logfile
        log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
        log_file = os.path.abspath(log_file + '/sonarr_youtubedl.log')
        loggerfile = logging.FileHandler(log_file)
        loggerfile.setLevel(logging.INFO)
        loggerfile.set_name('FileHandler')
        loggerfile.setFormatter(log_format)
        logger.addHandler(loggerfile)

    if lc_enabled:
        # setup console log
        loggerconsole = logging.StreamHandler()
        loggerconsole.setLevel(logging.INFO)
        loggerconsole.set_name('StreamHandler')
        loggerconsole.setFormatter(log_format)
        logger.addHandler(loggerconsole)

    return logger
