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

import os
import kallithea
import platform

import pylons
import mako.lookup
import formencode

import kallithea.lib.app_globals as app_globals

from kallithea.config.routing import make_map

from kallithea.lib import helpers
from kallithea.lib.auth import set_available_permissions
from kallithea.lib.utils import repo2db_mapper, make_ui, set_app_settings, \
    load_rcextensions, check_git_version, set_vcs_config, set_indexer_config
from kallithea.lib.utils2 import engine_from_config, str2bool
from kallithea.model.base import init_model
from kallithea.model.scm import ScmModel

from routes.middleware import RoutesMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool

from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp

from kallithea.lib.middleware.simplehg import SimpleHg
from kallithea.lib.middleware.simplegit import SimpleGit
from kallithea.lib.middleware.https_fixup import HttpsFixup
from kallithea.lib.middleware.sessionmiddleware import SecureSessionMiddleware
from kallithea.lib.middleware.wrapper import RequestWrapper

def setup_configuration(config, paths, app_conf, test_env, test_index):

    # store some globals into kallithea
    kallithea.CELERY_ON = str2bool(config['app_conf'].get('use_celery'))
    kallithea.CELERY_EAGER = str2bool(config['app_conf'].get('celery.always.eager'))

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.h'] = helpers
    kallithea.CONFIG = config

    load_rcextensions(root_path=config['here'])

    # Setup cache object as early as possible
    pylons.cache._push_object(config['pylons.app_globals'].cache)

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = mako.lookup.TemplateLookup(
        directories=paths['templates'],
        strict_undefined=True,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # sets the c attribute access when don't existing attribute are accessed
    config['pylons.strict_tmpl_context'] = True
    test = os.path.split(config['__file__'])[-1] == 'test.ini'
    if test:
        if test_env is None:
            test_env = not int(os.environ.get('KALLITHEA_NO_TMP_PATH', 0))
        if test_index is None:
            test_index = not int(os.environ.get('KALLITHEA_WHOOSH_TEST_DISABLE', 0))
        if os.environ.get('TEST_DB'):
            # swap config if we pass enviroment variable
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

    # MULTIPLE DB configs
    # Setup the SQLAlchemy database engine
    sa_engine = engine_from_config(config, 'sqlalchemy.')
    init_model(sa_engine)

    set_available_permissions(config)
    repos_path = make_ui('db').configitems('paths')[0][1]
    config['base_path'] = repos_path
    set_app_settings(config)

    instance_id = kallithea.CONFIG.get('instance_id', '*')
    if instance_id == '*':
        instance_id = '%s-%s' % (platform.uname()[1], os.getpid())
        kallithea.CONFIG['instance_id'] = instance_id

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # store config reference into our module to skip import magic of
    # pylons
    kallithea.CONFIG.update(config)
    set_vcs_config(kallithea.CONFIG)
    set_indexer_config(kallithea.CONFIG)

    #check git version
    check_git_version()

    if str2bool(config.get('initial_repo_scan', True)):
        repo2db_mapper(ScmModel().repo_scan(repos_path),
                       remove_obsolete=False, install_git_hooks=False)
    formencode.api.set_stdtranslation(languages=[config.get('lang')])

    return config

def setup_application(config, global_conf, full_stack, static_files):

    # The Pylons WSGI app
    app = PylonsApp(config=config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'], use_method_override=False)
    app = SecureSessionMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    if asbool(config['pdebug']):
        from kallithea.lib.profiler import ProfilingMiddleware
        app = ProfilingMiddleware(app)

    if asbool(full_stack):

        from kallithea.lib.middleware.sentry import Sentry
        from kallithea.lib.middleware.appenlight import AppEnlight
        if AppEnlight and asbool(config['app_conf'].get('appenlight')):
            app = AppEnlight(app, config)
        elif Sentry:
            app = Sentry(app, config)

        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        # Note: will buffer the output in memory!
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

        # we want our low level middleware to get to the request ASAP. We don't
        # need any pylons stack middleware in them - especially no StatusCodeRedirect buffering
        app = SimpleHg(app, config)
        app = SimpleGit(app, config)

        # Enable https redirects based on HTTP_X_URL_SCHEME set by proxy
        if any(asbool(config.get(x)) for x in ['https_fixup', 'force_https', 'use_htsts']):
            app = HttpsFixup(app, config)

        app = RequestWrapper(app, config) # logging

    # Establish the Registry for this application
    app = RegistryManager(app) # thread / request-local module globals / variables

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])

    app.config = config

    return app
