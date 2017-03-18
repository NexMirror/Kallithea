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
import os, sys

import tg
from tg import hooks
from tg.configuration import AppConfig
from tg.support.converters import asbool

from kallithea.lib.middleware.https_fixup import HttpsFixup
from kallithea.lib.middleware.simplegit import SimpleGit
from kallithea.lib.middleware.simplehg import SimpleHg
from kallithea.lib.auth import set_available_permissions
from kallithea.lib.db_manage import DbManage
from kallithea.lib.utils import load_rcextensions, make_ui, set_app_settings, set_vcs_config, \
    set_indexer_config, check_git_version, repo2db_mapper
from kallithea.lib.utils2 import str2bool
from kallithea.model.scm import ScmModel

import formencode
import kallithea


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

    # store some globals into kallithea
    kallithea.CELERY_ON = str2bool(config['app_conf'].get('use_celery'))
    kallithea.CELERY_EAGER = str2bool(config['app_conf'].get('celery.always.eager'))
    kallithea.CONFIG = config

    load_rcextensions(root_path=config['here'])

    # FIXME move test setup code out of here
    test = os.path.split(config['__file__'])[-1] == 'test.ini'
    if test:
        test_env = not int(os.environ.get('KALLITHEA_NO_TMP_PATH', 0))
        test_index = not int(os.environ.get('KALLITHEA_WHOOSH_TEST_DISABLE', 0))
        if os.environ.get('TEST_DB'):
            # swap config if we pass environment variable
            config['sqlalchemy.url'] = os.environ.get('TEST_DB')

        from kallithea.tests.fixture import create_test_env, create_test_index
        from kallithea.tests.base import TESTS_TMP_PATH
        #set KALLITHEA_NO_TMP_PATH=1 to disable re-creating the database and
        #test repos
        if test_env:
            create_test_env(TESTS_TMP_PATH, config)
        #set KALLITHEA_WHOOSH_TEST_DISABLE=1 to disable whoosh index during tests
        if test_index:
            create_test_index(TESTS_TMP_PATH, config, True)

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

    if str2bool(config.get('initial_repo_scan', True)):
        repo2db_mapper(ScmModel().repo_scan(repos_path),
                       remove_obsolete=False, install_git_hooks=False)

    formencode.api.set_stdtranslation(languages=[config.get('lang')])

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
