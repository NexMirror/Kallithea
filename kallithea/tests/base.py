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

import datetime
import logging
import os
import re
import tempfile
import time

import pytest
from webtest import TestApp

from kallithea.lib.utils2 import safe_str
from kallithea.model.db import User


log = logging.getLogger(__name__)

skipif = pytest.mark.skipif
parametrize = pytest.mark.parametrize

# Hack: These module global values MUST be set to actual values before running any tests. This is currently done by conftest.py.
url = None
testapp = None

__all__ = [
    'skipif', 'parametrize', 'url', 'TestController',
    'ldap_lib_installed', 'pam_lib_installed', 'invalidate_all_caches',
    'TESTS_TMP_PATH', 'HG_REPO', 'GIT_REPO', 'NEW_HG_REPO', 'NEW_GIT_REPO',
    'HG_FORK', 'GIT_FORK', 'TEST_USER_ADMIN_LOGIN', 'TEST_USER_ADMIN_PASS',
    'TEST_USER_ADMIN_EMAIL', 'TEST_USER_REGULAR_LOGIN', 'TEST_USER_REGULAR_PASS',
    'TEST_USER_REGULAR_EMAIL', 'TEST_USER_REGULAR2_LOGIN',
    'TEST_USER_REGULAR2_PASS', 'TEST_USER_REGULAR2_EMAIL', 'IP_ADDR',
    'TEST_HG_REPO', 'TEST_HG_REPO_CLONE', 'TEST_HG_REPO_PULL', 'TEST_GIT_REPO',
    'TEST_GIT_REPO_CLONE', 'TEST_GIT_REPO_PULL', 'HG_REMOTE_REPO',
    'GIT_REMOTE_REPO', 'HG_TEST_REVISION', 'GIT_TEST_REVISION',
]

## SOME GLOBALS FOR TESTS

TESTS_TMP_PATH = os.environ.get('KALLITHEA_TESTS_TMP_PATH', tempfile.mkdtemp(prefix='kallithea-test-'))

TEST_USER_ADMIN_LOGIN = 'test_admin'
TEST_USER_ADMIN_PASS = 'test12'
TEST_USER_ADMIN_EMAIL = 'test_admin@example.com'

TEST_USER_REGULAR_LOGIN = 'test_regular'
TEST_USER_REGULAR_PASS = 'test12'
TEST_USER_REGULAR_EMAIL = 'test_regular@example.com'

TEST_USER_REGULAR2_LOGIN = 'test_regular2'
TEST_USER_REGULAR2_PASS = 'test12'
TEST_USER_REGULAR2_EMAIL = 'test_regular2@example.com'

IP_ADDR = '127.0.0.127'

HG_REPO = u'vcs_test_hg'
GIT_REPO = u'vcs_test_git'

NEW_HG_REPO = u'vcs_test_hg_new'
NEW_GIT_REPO = u'vcs_test_git_new'

HG_FORK = u'vcs_test_hg_fork'
GIT_FORK = u'vcs_test_git_fork'

HG_TEST_REVISION = u"a53d9201d4bc278910d416d94941b7ea007ecd52"
GIT_TEST_REVISION = u"7ab37bc680b4aa72c34d07b230c866c28e9fc204"


## VCS
uniq_suffix = str(int(time.mktime(datetime.datetime.now().timetuple())))

GIT_REMOTE_REPO = os.path.join(TESTS_TMP_PATH, GIT_REPO)

TEST_GIT_REPO = os.path.join(TESTS_TMP_PATH, GIT_REPO)
TEST_GIT_REPO_CLONE = os.path.join(TESTS_TMP_PATH, 'vcs-git-clone-%s' % uniq_suffix)
TEST_GIT_REPO_PULL = os.path.join(TESTS_TMP_PATH, 'vcs-git-pull-%s' % uniq_suffix)

HG_REMOTE_REPO = os.path.join(TESTS_TMP_PATH, HG_REPO)

TEST_HG_REPO = os.path.join(TESTS_TMP_PATH, HG_REPO)
TEST_HG_REPO_CLONE = os.path.join(TESTS_TMP_PATH, 'vcs-hg-clone-%s' % uniq_suffix)
TEST_HG_REPO_PULL = os.path.join(TESTS_TMP_PATH, 'vcs-hg-pull-%s' % uniq_suffix)

# By default, some of the tests will utilise locally available
# repositories stored within tar.gz archives as source for
# cloning. Should you wish to use some other, remote archive, simply
# uncomment these entries and/or update the URLs to use.
#
# GIT_REMOTE_REPO = 'git://github.com/codeinn/vcs.git'
# HG_REMOTE_REPO = 'http://bitbucket.org/marcinkuzminski/vcs'

# skip ldap tests if LDAP lib is not installed
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


def invalidate_all_caches():
    """Invalidate all beaker caches currently configured.
    Useful when manipulating IP permissions in a test and changes need to take
    effect immediately.
    Note: Any use of this function is probably a workaround - it should be
    replaced with a more specific cache invalidation in code or test."""
    from beaker.cache import cache_managers
    for cache in cache_managers.values():
        cache.clear()


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class TestController(object):
    """Pytest-style test controller"""

    # Note: pytest base classes cannot have an __init__ method

    @pytest.fixture(autouse=True)
    def app_fixture(self):
        h = NullHandler()
        logging.getLogger("kallithea").addHandler(h)
        self.app = TestApp(testapp)
        return self.app

    def log_user(self, username=TEST_USER_ADMIN_LOGIN,
                 password=TEST_USER_ADMIN_PASS):
        self._logged_username = username
        response = self.app.post(url(controller='login', action='index'),
                                 {'username': username,
                                  'password': password,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})

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

    def session_csrf_secret_token(self):
        return self.app.get(url('session_csrf_secret_token')).body

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
