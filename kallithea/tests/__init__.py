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
Pylons application test package

This package assumes the Pylons environment is already loaded.

This module initializes the application via ``websetup`` (`paster
setup-app`) and provides the base testing objects.

Refer to docs/contributing.rst for details on running the test suite.
"""
import os
import re
import time
import logging
import datetime
import hashlib
import tempfile
from os.path import join as jn

from tempfile import _RandomNameSequence

import pylons
import pylons.test
from pylons import config, url
from pylons.i18n.translation import _get_translator
from pylons.util import ContextObj

from routes.util import URLGenerator
from webtest import TestApp
import pytest

from kallithea.lib.compat import unittest
from kallithea import is_windows
from kallithea.model.db import Notification, User, UserNotification
from kallithea.model.meta import Session
from kallithea.lib.utils2 import safe_str


os.environ['TZ'] = 'UTC'
if not is_windows:
    time.tzset()

log = logging.getLogger(__name__)

skipif = pytest.mark.skipif
parametrize = pytest.mark.parametrize

__all__ = [
    'skipif', 'parametrize', 'environ', 'url', 'TestController',
    'ldap_lib_installed', 'pam_lib_installed',
    'TESTS_TMP_PATH', 'HG_REPO', 'GIT_REPO', 'NEW_HG_REPO', 'NEW_GIT_REPO',
    'HG_FORK', 'GIT_FORK', 'TEST_USER_ADMIN_LOGIN', 'TEST_USER_ADMIN_PASS',
    'TEST_USER_ADMIN_EMAIL', 'TEST_USER_REGULAR_LOGIN', 'TEST_USER_REGULAR_PASS',
    'TEST_USER_REGULAR_EMAIL', 'TEST_USER_REGULAR2_LOGIN',
    'TEST_USER_REGULAR2_PASS', 'TEST_USER_REGULAR2_EMAIL', 'TEST_HG_REPO',
    'TEST_HG_REPO_CLONE', 'TEST_HG_REPO_PULL', 'TEST_GIT_REPO',
    'TEST_GIT_REPO_CLONE', 'TEST_GIT_REPO_PULL', 'HG_REMOTE_REPO',
    'GIT_REMOTE_REPO', 'SCM_TESTS',
]

# Invoke websetup with the current config file
# SetupCommand('setup-app').run([config_file])

environ = {}

#SOME GLOBALS FOR TESTS

TESTS_TMP_PATH = jn(tempfile.gettempdir(), 'rc_test_%s' % _RandomNameSequence().next())
TEST_USER_ADMIN_LOGIN = 'test_admin'
TEST_USER_ADMIN_PASS = 'test12'
TEST_USER_ADMIN_EMAIL = 'test_admin@example.com'

TEST_USER_REGULAR_LOGIN = 'test_regular'
TEST_USER_REGULAR_PASS = 'test12'
TEST_USER_REGULAR_EMAIL = 'test_regular@example.com'

TEST_USER_REGULAR2_LOGIN = 'test_regular2'
TEST_USER_REGULAR2_PASS = 'test12'
TEST_USER_REGULAR2_EMAIL = 'test_regular2@example.com'

HG_REPO = u'vcs_test_hg'
GIT_REPO = u'vcs_test_git'

NEW_HG_REPO = u'vcs_test_hg_new'
NEW_GIT_REPO = u'vcs_test_git_new'

HG_FORK = u'vcs_test_hg_fork'
GIT_FORK = u'vcs_test_git_fork'

## VCS
SCM_TESTS = ['hg', 'git']
uniq_suffix = str(int(time.mktime(datetime.datetime.now().timetuple())))

GIT_REMOTE_REPO = 'git://github.com/codeinn/vcs.git'

TEST_GIT_REPO = jn(TESTS_TMP_PATH, GIT_REPO)
TEST_GIT_REPO_CLONE = jn(TESTS_TMP_PATH, 'vcsgitclone%s' % uniq_suffix)
TEST_GIT_REPO_PULL = jn(TESTS_TMP_PATH, 'vcsgitpull%s' % uniq_suffix)


HG_REMOTE_REPO = 'http://bitbucket.org/marcinkuzminski/vcs'

TEST_HG_REPO = jn(TESTS_TMP_PATH, HG_REPO)
TEST_HG_REPO_CLONE = jn(TESTS_TMP_PATH, 'vcshgclone%s' % uniq_suffix)
TEST_HG_REPO_PULL = jn(TESTS_TMP_PATH, 'vcshgpull%s' % uniq_suffix)

TEST_DIR = tempfile.gettempdir()
TEST_REPO_PREFIX = 'vcs-test'

# cached repos if any !
# comment out to get some other repos from bb or github
GIT_REMOTE_REPO = jn(TESTS_TMP_PATH, GIT_REPO)
HG_REMOTE_REPO = jn(TESTS_TMP_PATH, HG_REPO)

#skip ldap tests if LDAP lib is not installed
ldap_lib_installed = False
try:
    import ldap
    ldap.API_VERSION
    ldap_lib_installed = True
except ImportError:
    # means that python-ldap is not installed
    pass

try:
    import pam
    pam.PAM_TEXT_INFO
    pam_lib_installed = True
except ImportError:
    pam_lib_installed = False

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class TestController(object):
    """Pytest-style test controller"""

    # Note: pytest base classes cannot have an __init__ method

    @pytest.fixture(autouse=True)
    def app_fixture(self):
        self.wsgiapp = pylons.test.pylonsapp
        self.init_stack(self.wsgiapp.config)
        self.app = TestApp(self.wsgiapp)
        self.maxDiff = None
        self.index_location = config['app_conf']['index_dir']
        return self.app

    def init_stack(self, config=None):
        if not config:
            config = pylons.test.pylonsapp.config
        url._push_object(URLGenerator(config['routes.map'], environ))
        pylons.app_globals._push_object(config['pylons.app_globals'])
        pylons.config._push_object(config)
        pylons.tmpl_context._push_object(ContextObj())
        # Initialize a translator for tests that utilize i18n
        translator = _get_translator(pylons.config.get('lang'))
        pylons.translator._push_object(translator)
        h = NullHandler()
        logging.getLogger("kallithea").addHandler(h)

    def remove_all_notifications(self):
        Notification.query().delete()

        # Because query().delete() does not (by default) trigger cascades.
        # http://docs.sqlalchemy.org/en/rel_0_7/orm/collections.html#passive-deletes
        UserNotification.query().delete()
        Session().commit()

    def log_user(self, username=TEST_USER_ADMIN_LOGIN,
                 password=TEST_USER_ADMIN_PASS):
        self._logged_username = username
        response = self.app.post(url(controller='login', action='index'),
                                 {'username': username,
                                  'password': password})

        if 'Invalid username or password' in response.body:
            pytest.fail('could not login using %s %s' % (username, password))

        assert response.status == '302 Found'
        self.assert_authenticated_user(response, username)

        response = response.follow()
        return response.session['authuser']

    def _get_logged_user(self):
        return User.get_by_username(self._logged_username)

    def assert_authenticated_user(self, response, expected_username):
        cookie = response.session.get('authuser')
        user = cookie and cookie.get('user_id')
        user = user and User.get(user)
        user = user and user.username
        assert user == expected_username

    def authentication_token(self):
        return self.app.get(url('authentication_token')).body

    def checkSessionFlash(self, response, msg=None, skip=0, _matcher=lambda msg, m: msg in m):
        if 'flash' not in response.session:
            pytest.fail(safe_str(u'msg `%s` not found - session has no flash:\n%s' % (msg, response)))
        try:
            level, m = response.session['flash'][-1 - skip]
            if _matcher(msg, m):
                return
        except IndexError:
            pass
        pytest.fail(safe_str(u'msg `%s` not found in session flash (skipping %s): %s' %
                           (msg, skip,
                            ', '.join('`%s`' % m for level, m in response.session['flash']))))

    def checkSessionFlashRegex(self, response, regex, skip=0):
        self.checkSessionFlash(response, regex, skip=skip, _matcher=re.search)

