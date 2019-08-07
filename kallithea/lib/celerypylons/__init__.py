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

import celery
import celery.result as result
import tg
from celery.bin import worker
from celery.task import task


def celery_config(config):
    """Return Celery config object populated from relevant settings in a config dict, such as tg.config"""

    # Verify .ini file configuration has been loaded
    assert config['celery.imports'] == 'kallithea.lib.celerylib.tasks', 'Kallithea Celery configuration has not been loaded'

    class CeleryConfig(object):
        pass

    celery_config = CeleryConfig()

    PREFIXES = """ADMINS BROKER CASSANDRA CELERYBEAT CELERYD CELERYMON CELERY EMAIL SERVER""".split()
    LIST_PARAMS = """CELERY_IMPORTS ADMINS ROUTES CELERY_ACCEPT_CONTENT""".split()

    for config_key, config_value in sorted(config.items()):
        celery_key = config_key.replace('.', '_').upper()
        if celery_key.split('_', 1)[0] not in PREFIXES:
            continue
        if not isinstance(config_value, basestring):
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


# Create celery app from the TurboGears configuration file
app = celery.Celery()
app.config_from_object(celery_config(tg.config))
