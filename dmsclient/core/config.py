import os

from configparser import ConfigParser
from enum import Enum

__all__ = ['ReadStatus', 'Sec', 'DmsConfig']


class ReadStatus(Enum):
    """Result enum for DmsConfig.read()"""
    NOT_FOUND = 0
    OUTDATED = 1
    LATEST = 2


class Sec(Enum):
    """Available config sections"""
    ALIASES = 'ALIASES'
    GENERAL = 'GENERAL'


class DmsConfig():

    def __init__(self):
        """Create a config with default values"""
        self._p = ConfigParser()

        self._add_section(Sec.GENERAL)
        self._set(Sec.GENERAL, 'api', 'https://dms.fachschaft.tf/api')
        self._set(Sec.GENERAL, 'token', '')
        self._set(Sec.GENERAL, 'version', '1')

        self._add_section(Sec.ALIASES)
        self._set(Sec.ALIASES, 'wasser', 'Prinzen Perle')

    def read(self, path):
        """Read given config. If config is an older config version it is migrated
        and can later be updated with write()
        """
        found = self._p.read(path)
        if not found:
            return ReadStatus.NOT_FOUND

        res = ReadStatus.LATEST

        # Update config to new version
        if 'token' in self._p.defaults():
            res = ReadStatus.OUTDATED
            self._set(Sec.GENERAL, 'version', '1')
            self._set(Sec.GENERAL, 'token', self._p.defaults()['token'])
            del self._p.defaults()['token']

        # Future breaking config change can use:
        # if self._p.getint(Sec.GENERAL, 'version') == 1:
        #     res = ReadStatus.OUTDATED
        #     self._p.set(Sec.GENERAL, 'version', 2)

        return res

    def write(self, path):
        """Write the current state of the config into a file"""
        with open(path, 'w') as f:
            self._p.write(f)

    @property
    def api(self):
        """Api endpoint of the drink management system"""
        return self._get(Sec.GENERAL, 'api')

    @property
    def token(self):
        """Access token for the drink management system"""
        return self._get(Sec.GENERAL, 'token')

    @property
    def aliases(self):
        """List of aliases. Alias = (lowercase alias, mapped drink)"""
        return [(x.lower(), y) for (x, y) in self._items(Sec.ALIASES)]

    def _add_section(self, sec):
        """Wrapper for Configparser.add_section allowing Enum Sec as "sec"."""
        return self._p.add_section(sec.name)

    def _items(self, sec):
        """Wrapper for Configparser.items allowing Enum Sec as "sec"."""
        return self._p.items(sec.name)

    def _get(self, sec, key):
        """Wrapper for Configparser.get allowing Enum Sec as "sec"."""
        return self._p.get(sec.name, key)

    def _set(self, sec, key, value):
        """Wrapper for Configparser.set allowing Enum Sec as "sec"."""
        return self._p.set(sec.name, key, value)
