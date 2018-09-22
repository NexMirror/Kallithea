# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Global configuration file for TurboGears2 specific settings in Kallithea.

This file complements the .ini file.
"""

import platform
import os, sys, logging

import tg
from tg import hooks
from tg.configuration import AppConfig
from tg.support.converters import asbool
import alembic.config
from alembic.script.base import ScriptDirectory
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
import mercurial

from kallithea.lib.middleware.https_fixup import HttpsFixup
from kallithea.lib.middleware.simplegit import SimpleGit
from kallithea.lib.middleware.simplehg import SimpleHg
from kallithea.lib.auth import set_available_permissions
from kallithea.lib.utils import load_rcextensions, make_ui, set_app_settings, set_vcs_config, \
    set_indexer_config, check_git_version, repo2db_mapper
from kallithea.lib.utils2 import str2bool
import kallithea.model.base
from kallithea.model.scm import ScmModel

import formencode

log = logging.getLogger(__name__)


class KallitheaAppConfig(AppConfig):
    # Note: AppConfig has a misleading name, as it's not the application
    # configuration, but the application configurator. The AppConfig values are
    # used as a template to create the actual configuration, which might
    # overwrite or extend the one provided by the configurator template.

    # To make it clear, AppConfig creates the config and sets into it the same
    # values that AppConfig itself has. Then the values from the config file and
    # gearbox options are loaded and merged into the configuration. Then an
    # after_init_config(conf) method of AppConfig is called for any change that
    # might depend on options provided by configuration files.

    def __init__(self):
        super(KallitheaAppConfig, self).__init__()

        self['package'] = kallithea

        self['prefer_toscawidgets2'] = False
        self['use_toscawidgets'] = False

        self['renderers'] = []

        # Enable json in expose
        self['renderers'].append('json')

        # Configure template rendering
        self['renderers'].append('mako')
        self['default_renderer'] = 'mako'
        self['use_dotted_templatenames'] = False

        # Configure Sessions, store data as JSON to avoid pickle security issues
        self['session.enabled'] = True
        self['session.data_serializer'] = 'json'

        # Configure the base SQLALchemy Setup
        self['use_sqlalchemy'] = True
        self['model'] = kallithea.model.base
        self['DBSession'] = kallithea.model.meta.Session

        # Configure App without an authentication backend.
        self['auth_backend'] = None

        # Use custom error page for these errors. By default, Turbogears2 does not add
        # 400 in this list.
        # Explicitly listing all is considered more robust than appending to defaults,
        # in light of possible future framework changes.
        self['errorpage.status_codes'] = [400, 401, 403, 404]

        # Disable transaction manager -- currently Kallithea takes care of transactions itself
        self['tm.enabled'] = False


base_config = KallitheaAppConfig()

# TODO still needed as long as we use pylonslib
sys.modules['pylons'] = tg

# DebugBar, a debug toolbar for TurboGears2.
# (https://github.com/TurboGears/tgext.debugbar)
# To enable it, install 'tgext.debugbar' and 'kajiki', and run Kallithea with
# 'debug = true' (not in production!)
# See the Kallithea documentation for more information.
try:
    from tgext.debugbar import enable_debugbar
    import kajiki # only to check its existence
except ImportError:
    pass
else:
    base_config['renderers'].append('kajiki')
    enable_debugbar(base_config)


def setup_configuration(app):
    config = app.config

    # Verify that things work when Dulwich passes unicode paths to the file system layer.
    # Note: UTF-8 is preferred, but for example ISO-8859-1 or mbcs should also work under the right cirumstances.
    try:
        u'\xe9'.encode(sys.getfilesystemencoding()) # Test using é (&eacute;)
    except UnicodeEncodeError:
        log.error("Cannot encode Unicode paths to file system encoding %r", sys.getfilesystemencoding())
        for var in ['LC_CTYPE', 'LC_ALL', 'LANG']:
            if var in os.environ:
                val = os.environ[var]
                log.error("Note: Environment variable %s is %r - perhaps change it to some other value from 'locale -a', like 'C.UTF-8' or 'en_US.UTF-8'", var, val)
                break
        else:
            log.error("Note: No locale setting found in environment variables - perhaps set LC_CTYPE to some value from 'locale -a', like 'C.UTF-8' or 'en_US.UTF-8'")
        log.error("Terminating ...")
        sys.exit(1)

    # Mercurial sets encoding at module import time, so we have to monkey patch it
    hgencoding = config.get('hgencoding')
    if hgencoding:
        mercurial.encoding.encoding = hgencoding

    if config.get('ignore_alembic_revision', False):
        log.warn('database alembic revision checking is disabled')
    else:
        dbconf = config['sqlalchemy.url']
        alembic_cfg = alembic.config.Config()
        alembic_cfg.set_main_option('script_location', 'kallithea:alembic')
        alembic_cfg.set_main_option('sqlalchemy.url', dbconf)
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        available_heads = sorted(script_dir.get_heads())

        engine = create_engine(dbconf)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_heads = sorted(str(s) for s in context.get_current_heads())
        if current_heads != available_heads:
            log.error('Failed to run Kallithea:\n\n'
                      'The database version does not match the Kallithea version.\n'
                      'Please read the documentation on how to upgrade or downgrade the database.\n'
                      'Current database version id(s): %s\n'
                      'Expected database version id(s): %s\n'
                      'If you are a developer and you know what you are doing, you can add `ignore_alembic_revision = True` '
                      'to your .ini file to skip the check.\n' % (' '.join(current_heads), ' '.join(available_heads)))
            sys.exit(1)

    # store some globals into kallithea
    kallithea.CELERY_ON = str2bool(config['app_conf'].get('use_celery'))
    kallithea.CELERY_EAGER = str2bool(config['app_conf'].get('celery.always.eager'))
    kallithea.CONFIG = config

    load_rcextensions(root_path=config['here'])

    set_available_permissions(config)
    repos_path = make_ui('db').configitems('paths')[0][1]
    config['base_path'] = repos_path
    set_app_settings(config)

    instance_id = kallithea.CONFIG.get('instance_id', '*')
    if instance_id == '*':
        instance_id = '%s-%s' % (platform.uname()[1], os.getpid())
        kallithea.CONFIG['instance_id'] = instance_id

    # update kallithea.CONFIG with the meanwhile changed 'config'
    kallithea.CONFIG.update(config)

    # configure vcs and indexer libraries (they are supposed to be independent
    # as much as possible and thus avoid importing tg.config or
    # kallithea.CONFIG).
    set_vcs_config(kallithea.CONFIG)
    set_indexer_config(kallithea.CONFIG)

    check_git_version()


hooks.register('configure_new_app', setup_configuration)


def setup_application(app):
    config = app.config

    # we want our low level middleware to get to the request ASAP. We don't
    # need any stack middleware in them - especially no StatusCodeRedirect buffering
    app = SimpleHg(app, config)
    app = SimpleGit(app, config)

    # Enable https redirects based on HTTP_X_URL_SCHEME set by proxy
    if any(asbool(config.get(x)) for x in ['https_fixup', 'force_https', 'use_htsts']):
        app = HttpsFixup(app, config)
    return app


hooks.register('before_config', setup_application)
