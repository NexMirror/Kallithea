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

import kallithea


class CeleryConfig(object):
    imports = ['kallithea.lib.celerylib.tasks']
    task_always_eager = False

# map from Kallithea .ini Celery 3 config names to Celery 4 config names
celery3_compat = {
    'broker.url': 'broker_url',
    'celery.accept.content': 'accept_content',
    'celery.always.eager': 'task_always_eager',
    'celery.amqp.task.result.expires': 'result_expires',
    'celeryd.concurrency': 'worker_concurrency',
    'celeryd.max.tasks.per.child': 'worker_max_tasks_per_child',
    #'celery.imports' ends up unchanged
    'celery.result.backend': 'result_backend',
    'celery.result.serializer': 'result_serializer',
    'celery.task.serializer': 'task_serializer',
}

list_config_names = """imports accept_content""".split()


desupported = set([
    'celery.result.dburi',
    'celery.result.serialier',
    'celery.send.task.error.emails',
])


log = logging.getLogger(__name__)


def make_celery_config(config):
    """Return Celery config object populated from relevant settings in a config dict, such as tg.config"""

    celery_config = CeleryConfig()

    for config_key, config_value in sorted(config.items()):
        if config_key in desupported and config_value:
            log.error('Celery configuration setting %r is no longer supported', config_key)
        celery_key = celery3_compat.get(config_key)
        parts = config_key.split('.', 1)
        if celery_key:  # explicit Celery 3 backwards compatibility
            pass
        elif parts[0] == 'celery' and len(parts) == 2:  # Celery 4 config key
            celery_key = parts[1]
        else:
            continue
        if not isinstance(config_value, str):
            continue
        if celery_key in list_config_names:
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
    celery_config = make_celery_config(tg.config)
    kallithea.CELERY_EAGER = celery_config.task_always_eager
    app.config_from_object(celery_config)
    return app
