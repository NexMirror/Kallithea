# -*- coding: utf-8 -*-

from tg import config

# TODO: drop this mangling and just use a separate celery config section
to_pylons = lambda x: x.replace('_', '.').lower()
to_celery = lambda x: x.replace('.', '_').upper()

LIST_PARAMS = """CELERY_IMPORTS ADMINS ROUTES CELERY_ACCEPT_CONTENT""".split()


class PylonsSettingsProxy(object):
    """Pylons Settings Proxy

    Make settings from pylons.config appear the way Celery expects them.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        pylons_key = to_pylons(key)
        value = config[pylons_key]
        if key in LIST_PARAMS:
            return value.split()
        return self.type_converter(value)

    def __contains__(self, key):
        pylons_key = to_pylons(key)
        try:
            config[pylons_key]
        except KeyError:
            return False
        return True

    def __setattr__(self, key, value):
        pylons_key = to_pylons(key)
        config[pylons_key] = value

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def type_converter(self, value):
        #cast to int
        if value.isdigit():
            return int(value)

        #cast to bool
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        return value
