# -*- coding: utf-8 -*-

"""
Kallithea wrapper of Celery

The Celery configuration is in the normal Pylons ini file. We thus have to set
the `CELERY_LOADER` environment variable to point at a custom "loader" that can
read it. That environment variable must be set *before* importing celery. To
ensure that, we wrap celery in this module.

We read the configuration from tg.config, thus it must be initialized before
loading this module. To make sure that really is the case and give an early
warning, we check one of the mandatory settings.

This module must thus not be imported in global scope but must be imported on
demand in function scope after tg.config has been initialized.
"""

import os
import warnings

import celery.app

# Verify Pylons configuration has been loaded
from tg import config
assert config['celery.imports'] == 'kallithea.lib.celerylib.tasks', 'Kallithea Celery configuration has not been loaded'

# Prepare environment to point at Kallithea Pylons loader
CELERYPYLONS_LOADER = 'kallithea.lib.celerypylons.loader.PylonsLoader'
if os.environ.get('CELERY_LOADER', CELERYPYLONS_LOADER) != CELERYPYLONS_LOADER:
    warnings.warn("'CELERY_LOADER' environment variable will be overridden by celery-pylons.")
os.environ['CELERY_LOADER'] = CELERYPYLONS_LOADER

# Create celery app, thus immediately triggering use of the custom Pylons loader
app = celery.app.app_or_default()

import celery.result as result
from celery.task import task
from celery.bin import worker
