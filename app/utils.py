import re
import os
import sys
import datetime
import yaml
import logging
from logging.handlers import RotatingFileHandler


CONFIGFILE = os.environ['CONFIGPATH']

def upperescape(string):
    """ Uppercase and Escape string. 
        Used to help with YT-DL regex match
        Standardises character and makes guesses at punctuation

    Args:
        string (str): the string to manipulate

    Returns:
        str: regex escaped string
    """    
    # YTDL is case insensitive for ease.
    string = string.upper() 
    # Standardise quote characters as YTDL converts these.
    string = string.replace('’',"'") 
    string = string.replace('“','"')
    string = string.replace('”','"')
    # Escape the characters
    string = re.escape(string)
    # Make it look for and as whole or ampersands
    string = string.replace('\\ AND\\ ','\\ (AND|&)\\ ')
    # Handle some numerals being incorrect
    string = string.replace("1","(1|I)")
    string = string.replace("2","(2|II)")
    string = string.replace("3","(3|III)")
    string = string.replace("4","(4|IV)")
    string = string.replace("5","(5|V)")
    string = string.replace("6","(6|VI)")
    string = string.replace("7","(7|VII)")
    string = string.replace("8","(8|VIII)")
    string = string.replace("9","(9|IX)")
    string = string.replace("10","(10|X)")
    # Make punctuation optional for human error
    string = string.replace("'","([']?)") # optional apostrophe
    string = string.replace(",","([,]?)") # optional comma
    string = string.replace("!","([!]?)") # optional question mark
    string = string.replace("\\.","([\\.]?)") # optional period
    string = string.replace("\\?","([\\?]?)") # optional question mark
    string = string.replace(":","([:]?)") # optional colon
    string = string.replace("–","([–-]?)") # optional hyphen U+002d
    string = re.sub("S\\\\", "([']?)"+"S\\\\", string) # optional belonging apostrophe (has to be last due to question mark)
    return string


def checkconfig():
    """ Checks if config files exist in config path
        If no config available, will copy template to config folder and exit script

    Returns:
        dict: configuration values
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

    Args:
        airdate (datetime): Airdate from sonarr
        offset (dict): Offsets from series config.yml 

    Returns:
        datetime: adjusted airdate
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
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)


def ytdl_hooks_debug(d):
    """ Debug logging hooks for Youtube DL download process.
        Updates the logger with download progress percent and ETA

    Args:
        d (dict): current youtube dl download status
    """
    logger = logging.getLogger('sonarr_youtubedl')
    if d['status'] == 'finished':
        file_tuple = os.path.split(os.path.abspath(d['filename']))
        logger.info("      Done downloading {}".format(file_tuple[1]))  # print("Done downloading {}".format(file_tuple[1]))
    if d['status'] == 'downloading':
        progress = "      {} - {} - {}".format(d['filename'], d['_percent_str'], d['_eta_str'])
        logger.debug(progress)


def ytdl_hooks(d):
    """ Standard logging hooks for Youtube DL download process.
        Updates the logger only when completed.

    Args:
        d (dict): Youtube DL complete message
    """
    logger = logging.getLogger('sonarr_youtubedl')
    if d['status'] == 'finished':
        file_tuple = os.path.split(os.path.abspath(d['filename']))
        logger.info("      Downloaded - {}".format(file_tuple[1]))

def setup_logging(lf_enabled=True, lc_enabled=True, debugging=False):
    """ Function to setup logging

    Args:
        lf_enabled (bool, optional): is log file enabled. Defaults to True.
        lc_enabled (bool, optional): is console logging enabled. Defaults to True.
        debugging (bool, optional): is debugging enabled. Defaults to False.

    Returns:
        Logger: used to pass logging information to
    """    
    log_level = logging.INFO
    log_level = logging.DEBUG if debugging == True else log_level
    logger = logging.getLogger('sonarr_youtubedl')
    logger.setLevel(log_level)
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if lf_enabled:
        # setup logfile
        log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
        if not os.path.exists(log_file):
            os.makedirs(log_file)
        log_file = os.path.abspath(log_file + '/sonarr_youtubedl.log')
        loggerfile = RotatingFileHandler(
            log_file,
            maxBytes=5000000,
            backupCount=5
        )
        loggerfile.setLevel(log_level)
        loggerfile.set_name('FileHandler')
        loggerfile.setFormatter(log_format)
        logger.addHandler(loggerfile)

    if lc_enabled:
        # setup console log
        loggerconsole = logging.StreamHandler()
        loggerconsole.setLevel(log_level)
        loggerconsole.set_name('StreamHandler')
        loggerconsole.setFormatter(log_format)
        logger.addHandler(loggerconsole)

    return logger
