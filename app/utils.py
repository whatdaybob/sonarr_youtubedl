import re
import os

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
    configexists = os.path.exists('/config/config.yml')
    configtemplateexists = os.path.exists('/config/config.yml.template')
    if not configexists:
        print('Configuration file not found.')
        if not configtemplateexists:
            os.system('cp /app/config.yml.template /config/config.yml.template')
        print('Create a config.yml using config.yml.template as an example.')
        print('Exiting.')
        exit()
    else:
        print('Configuration Found. Loading file.')