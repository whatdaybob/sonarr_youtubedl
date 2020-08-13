import re
import os
import sys
import datetime

CONFIGPATH = os.environ['CONFIGPATH']


def upperescape(s):
    """Uppercase and Escape string.

    Used to help with YT-DL regex match.
    """
    string = s.upper()
    string = re.escape(string)
    return string


def checkconfig():
    """Check configuration exists.

    Guide users to create their own configuration.
    """
    configexists = os.path.exists(os.path.abspath(CONFIGPATH))
    configtemplateexists = os.path.exists(CONFIGPATH + '.template')
    if not configexists:
        print('Configuration file not found.')
        if not configtemplateexists:
            os.system('cp /app/config.yml.template ' + CONFIGPATH + '.template')
        sys.exit("Create a config.yml using config.yml.template as an example.")
    else:
        print('Configuration Found. Loading file.')


def offsethandler(airdate, offset):
    """ Takes the offset given and adjusts check

    Useful for priority shows
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
