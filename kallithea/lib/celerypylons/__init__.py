# -*- coding: utf-8 -*-

"""
Kallithea wrapper of Celery

The Celery configuration is in the ini file. To read the settings and translate
to a Celery format we use PylonsSettingsProxy.

We read the configuration from tg.config, thus it must be initialized before
loading this module. To make sure that really is the case and give an early
warning, we check one of the mandatory settings.

This module must thus not be imported in global scope but must be imported on
demand in function scope after tg.config has been initialized.
"""

import os
import warnings

import celery

from kallithea.lib.celerypylons.loader import PylonsSettingsProxy

# Verify Pylons configuration has been loaded
from tg import config
assert config['celery.imports'] == 'kallithea.lib.celerylib.tasks', 'Kallithea Celery configuration has not been loaded'

# Create celery app from the TurboGears configuration file
app = celery.Celery()
app.config_from_object(PylonsSettingsProxy())

import celery.result as result
from celery.task import task
from celery.bin import worker
