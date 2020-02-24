# -*- coding: utf-8 -*-

"""
Kallithea wrapper of Celery

The Celery configuration is in the Kallithea ini file but must be converted to an
entirely different format before Celery can use it.

We read the configuration from tg.config at module import time. This module can
thus not be imported in global scope but must be imported on demand in function
scope after tg.config has been initialized.

To make sure that the config really has been initialized, we check one of the
mandatory settings.
"""

import logging

import celery
import tg


class CeleryConfig(object):
    CELERY_IMPORTS = ['kallithea.lib.celerylib.tasks']
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TASK_SERIALIZER = 'json'


desupported = set([
    'celery.result.dburi',
    'celery.result.serialier',
    'celery.send.task.error.emails',
])


log = logging.getLogger(__name__)


def celery_config(config):
    """Return Celery config object populated from relevant settings in a config dict, such as tg.config"""

    celery_config = CeleryConfig()

    PREFIXES = """ADMINS BROKER CASSANDRA CELERYBEAT CELERYD CELERYMON CELERY EMAIL SERVER""".split()
    LIST_PARAMS = """CELERY_IMPORTS CELERY_ACCEPT_CONTENT""".split()

    for config_key, config_value in sorted(config.items()):
        if config_key in desupported and config_value:
            log.error('Celery configuration setting %r is no longer supported', config_key)
        celery_key = config_key.replace('.', '_').upper()
        if celery_key.split('_', 1)[0] not in PREFIXES:
            continue
        if not isinstance(config_value, str):
            continue
        if celery_key in LIST_PARAMS:
            celery_value = config_value.split()
        elif config_value.isdigit():
            celery_value = int(config_value)
        elif config_value.lower() in ['true', 'false']:
            celery_value = config_value.lower() == 'true'
        else:
            celery_value = config_value
        setattr(celery_config, celery_key, celery_value)
    return celery_config


def make_app():
    """Create celery app from the TurboGears configuration file"""
    app = celery.Celery()
    app.config_from_object(celery_config(tg.config))
    return app
