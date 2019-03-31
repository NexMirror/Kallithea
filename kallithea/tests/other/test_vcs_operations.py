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
Test suite for vcs push/pull operations.

The tests need Git > 1.8.1.

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 30, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

import os
import re
import tempfile
import time
import urllib2
import json
from tempfile import _RandomNameSequence
from subprocess import Popen, PIPE

import pytest

from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture
from kallithea.model.db import User, Repository, UserIpMap, CacheInvalidation, Ui, UserLog
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.user import UserModel

DEBUG = True
HOST = '127.0.0.1:4999'  # test host

fixture = Fixture()


class Command(object):

    def __init__(self, cwd):
        self.cwd = cwd

    def execute(self, cmd, *args, **environ):
        """
        Runs command on the system with given ``args``.
        """

        command = cmd + ' ' + ' '.join(args)
        ignoreReturnCode = environ.pop('ignoreReturnCode', False)
        if DEBUG:
            print '*** CMD %s ***' % command
        testenv = dict(os.environ)
        testenv['LANG'] = 'en_US.UTF-8'
        testenv['LANGUAGE'] = 'en_US:en'
        testenv['HGPLAIN'] = ''
        testenv['HGRCPATH'] = ''
        testenv.update(environ)
        p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, cwd=self.cwd, env=testenv)
        stdout, stderr = p.communicate()
        if DEBUG:
            if stdout:
                print 'stdout:', repr(stdout)
            if stderr:
                print 'stderr:', repr(stderr)
        if not ignoreReturnCode:
            assert p.returncode == 0
        return stdout, stderr


def _get_tmp_dir(prefix='vcs_operations-', suffix=''):
    return tempfile.mkdtemp(dir=TESTS_TMP_PATH, prefix=prefix, suffix=suffix)


def _add_files(vcs, dest_dir, files_no=3):
    """
    Generate some files, add it to dest_dir repo and push back
    vcs is git or hg and defines what VCS we want to make those files for

    :param vcs:
    :param dest_dir:
    """
    added_file = '%ssetup.py' % _RandomNameSequence().next()
    open(os.path.join(dest_dir, added_file), 'a').close()
    Command(dest_dir).execute('%s add %s' % (vcs, added_file))

    email = 'me@example.com'
    if os.name == 'nt':
        author_str = 'User <%s>' % email
    else:
        author_str = 'User ǝɯɐᴎ <%s>' % email
    for i in xrange(files_no):
        cmd = """echo "added_line%s" >> %s""" % (i, added_file)
        Command(dest_dir).execute(cmd)
        if vcs == 'hg':
            cmd = """hg commit -m "committed new %s" -u "%s" "%s" """ % (
                i, author_str, added_file
            )
        elif vcs == 'git':
            cmd = """git commit -m "committed new %s" --author "%s" "%s" """ % (
                i, author_str, added_file
            )
        # git commit needs EMAIL on some machines
        Command(dest_dir).execute(cmd, EMAIL=email)

def _add_files_and_push(webserver, vcs, dest_dir, ignoreReturnCode=False, files_no=3,
                            clone_url=None, username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS):
    _add_files(vcs, dest_dir, files_no=files_no)
    # PUSH it back
    _REPO = None
    if vcs == 'hg':
        _REPO = HG_REPO
    elif vcs == 'git':
        _REPO = GIT_REPO

    if clone_url is None:
        clone_url = webserver.repo_url(_REPO, username=username, password=password)

    stdout = stderr = None
    if vcs == 'hg':
        stdout, stderr = Command(dest_dir).execute('hg push --verbose', clone_url, ignoreReturnCode=ignoreReturnCode)
    elif vcs == 'git':
        stdout, stderr = Command(dest_dir).execute('git push --verbose', clone_url, "master", ignoreReturnCode=ignoreReturnCode)

    return stdout, stderr


def _check_outgoing(vcs, cwd, clone_url=''):
    if vcs == 'hg':
        # hg removes the password from default URLs, so we have to provide it here via the clone_url
        return Command(cwd).execute('hg -q outgoing', clone_url, ignoreReturnCode=True)
    elif vcs == 'git':
        Command(cwd).execute('git remote update')
        return Command(cwd).execute('git log origin/master..master')


def set_anonymous_access(enable=True):
    user = User.get_default_user()
    user.active = enable
    Session().commit()
    if enable != User.get_default_user().active:
        raise Exception('Cannot set anonymous access')


#==============================================================================
# TESTS
#==============================================================================


def _check_proper_git_push(stdout, stderr):
    # WTF Git stderr is output ?!
    assert 'fatal' not in stderr
    assert 'rejected' not in stderr
    assert 'Pushing to' in stderr
    assert 'master -> master' in stderr


@pytest.mark.usefixtures("test_context_fixture")
class TestVCSOperations(TestController):

    @classmethod
    def setup_class(cls):
        # DISABLE ANONYMOUS ACCESS
        set_anonymous_access(False)

    def setup_method(self, method):
        r = Repository.get_by_repo_name(GIT_REPO)
        Repository.unlock(r)
        r.enable_locking = False
        Session().commit()

        r = Repository.get_by_repo_name(HG_REPO)
        Repository.unlock(r)
        r.enable_locking = False
        Session().commit()

    @pytest.fixture()
    def testhook_cleanup(self):
        yield
        # remove hook
        for hook in ['prechangegroup', 'pretxnchangegroup', 'preoutgoing', 'changegroup', 'outgoing', 'incoming']:
            entry = Ui.get_by_key('hooks', '%s.testhook' % hook)
            if entry:
                Session().delete(entry)
        Session().commit()

    @pytest.fixture(scope="module")
    def testfork(self):
        # create fork so the repo stays untouched
        git_fork_name = u'%s_fork%s' % (GIT_REPO, _RandomNameSequence().next())
        fixture.create_fork(GIT_REPO, git_fork_name)
        hg_fork_name = u'%s_fork%s' % (HG_REPO, _RandomNameSequence().next())
        fixture.create_fork(HG_REPO, hg_fork_name)
        return {'git': git_fork_name, 'hg': hg_fork_name}

    def test_clone_hg_repo_by_admin(self, webserver):
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir())

        assert 'requesting all changes' in stdout
        assert 'adding changesets' in stdout
        assert 'adding manifests' in stdout
        assert 'adding file changes' in stdout

        assert stderr == ''

    def test_clone_git_repo_by_admin(self, webserver):
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir())

        assert 'Cloning into' in stdout + stderr
        assert stderr == '' or stdout == ''

    def test_clone_wrong_credentials_hg(self, webserver):
        clone_url = webserver.repo_url(HG_REPO, password='bad!')
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'abort: authorization failed' in stderr

    def test_clone_wrong_credentials_git(self, webserver):
        clone_url = webserver.repo_url(GIT_REPO, password='bad!')
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'fatal: Authentication failed' in stderr

    def test_clone_git_dir_as_hg(self, webserver):
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'HTTP Error 404: Not Found' in stderr

    def test_clone_hg_repo_as_git(self, webserver):
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'not found' in stderr

    def test_clone_non_existing_path_hg(self, webserver):
        clone_url = webserver.repo_url('trololo')
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'HTTP Error 404: Not Found' in stderr

    def test_clone_non_existing_path_git(self, webserver):
        clone_url = webserver.repo_url('trololo')
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'not found' in stderr

    def test_push_new_repo_git(self, webserver):
        # Clear the log so we know what is added
        UserLog.query().delete()
        Session().commit()

        # Create an empty server repo using the API
        repo_name = u'new_git_%s' % _RandomNameSequence().next()
        usr = User.get_by_username(TEST_USER_ADMIN_LOGIN)
        params = {
            "id": 7,
            "api_key": usr.api_key,
            "method": 'create_repo',
            "args": dict(repo_name=repo_name,
                         owner=TEST_USER_ADMIN_LOGIN,
                         repo_type='git'),
        }
        req = urllib2.Request(
            'http://%s:%s/_admin/api' % webserver.server_address,
            data=json.dumps(params),
            headers={'content-type': 'application/json'})
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        # Expect something like:
        # {u'result': {u'msg': u'Created new repository `new_git_XXX`', u'task': None, u'success': True}, u'id': 7, u'error': None}
        assert result[u'result'][u'success']

        # Create local clone of the empty server repo
        local_clone_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, local_clone_dir, ignoreReturnCode=True)

        # Make 3 commits and push to the empty server repo.
        # The server repo doesn't have any other heads than the
        # refs/heads/master we are pushing, but the `git log` in the push hook
        # should still list the 3 commits.
        stdout, stderr = _add_files_and_push(webserver, 'git', local_clone_dir, clone_url=clone_url)
        _check_proper_git_push(stdout, stderr)

        # Verify that we got the right events in UserLog. Expect something like:
        # <UserLog('id:new_git_XXX:started_following_repo')>
        # <UserLog('id:new_git_XXX:user_created_repo')>
        # <UserLog('id:new_git_XXX:pull')>
        # <UserLog('id:new_git_XXX:push:aed9d4c1732a1927da3be42c47eb9afdc200d427,d38b083a07af10a9f44193486959a96a23db78da,4841ff9a2b385bec995f4679ef649adb3f437622')>
        uls = list(UserLog.query().order_by(UserLog.user_log_id))
        assert len(uls) == 4
        assert uls[0].action == 'started_following_repo'
        assert uls[1].action == 'user_created_repo'
        assert uls[2].action == 'pull'
        assert uls[3].action.startswith(u'push:')
        assert uls[3].action.count(',') == 2 # expect 3 commits

    def test_push_new_file_hg(self, webserver, testfork):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        clone_url = webserver.repo_url(testfork['hg'])
        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir, clone_url=clone_url)

        assert 'pushing to' in stdout
        assert 'Repository size' in stdout
        assert 'Last revision is now' in stdout

    def test_push_new_file_git(self, webserver, testfork):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        # commit some stuff into this repo
        clone_url = webserver.repo_url(testfork['git'])
        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir, clone_url=clone_url)
        print [(x.repo_full_path,x.repo_path) for x in Repository.query()] # TODO: what is this for
        _check_proper_git_push(stdout, stderr)

    def test_push_invalidates_cache_hg(self, webserver, testfork):
        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == HG_REPO).scalar()
        if not key:
            key = CacheInvalidation(HG_REPO, HG_REPO)
            Session().add(key)

        key.cache_active = True
        Session().commit()

        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(testfork['hg'])
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir, files_no=1, clone_url=clone_url)

        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == testfork['hg']).all()
        assert key == []

    def test_push_invalidates_cache_git(self, webserver, testfork):
        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == GIT_REPO).scalar()
        if not key:
            key = CacheInvalidation(GIT_REPO, GIT_REPO)
            Session().add(key)

        key.cache_active = True
        Session().commit()

        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(testfork['git'])
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        # commit some stuff into this repo
        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir, files_no=1, clone_url=clone_url)
        _check_proper_git_push(stdout, stderr)

        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == testfork['git']).all()
        assert key == []

    def test_push_wrong_credentials_hg(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir, username='bad',
                                             password='name', ignoreReturnCode=True)

        assert 'abort: authorization failed' in stderr

    def test_push_wrong_credentials_git(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir, username='bad',
                                             password='name', ignoreReturnCode=True)

        assert 'fatal: Authentication failed' in stderr

    def test_push_with_readonly_credentials_hg(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(HG_REPO, username=TEST_USER_REGULAR_LOGIN, password=TEST_USER_REGULAR_PASS)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir, username=TEST_USER_REGULAR_LOGIN,
                                             password=TEST_USER_REGULAR_PASS, ignoreReturnCode=True)

        assert 'abort: HTTP Error 403: Forbidden' in stderr

    def test_push_with_readonly_credentials_git(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO, username=TEST_USER_REGULAR_LOGIN, password=TEST_USER_REGULAR_PASS)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir, username=TEST_USER_REGULAR_LOGIN,
                                             password=TEST_USER_REGULAR_PASS, ignoreReturnCode=True)

        assert 'The requested URL returned error: 403' in stderr

    def test_push_back_to_wrong_url_hg(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(
            webserver, 'hg', dest_dir, clone_url='http://%s:%s/tmp' % (
                webserver.server_address[0], webserver.server_address[1]),
            ignoreReturnCode=True)

        assert 'HTTP Error 404: Not Found' in stderr

    def test_push_back_to_wrong_url_git(self, webserver):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(
            webserver, 'git', dest_dir, clone_url='http://%s:%s/tmp' % (
                webserver.server_address[0], webserver.server_address[1]),
            ignoreReturnCode=True)

        assert 'not found' in stderr

    def test_clone_and_create_lock_hg(self, webserver):
        # enable locking
        r = Repository.get_by_repo_name(HG_REPO)
        r.enable_locking = True
        Session().commit()
        # clone
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir())

        # check if lock was made
        r = Repository.get_by_repo_name(HG_REPO)
        assert r.locked[0] == User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id

    def test_clone_and_create_lock_git(self, webserver):
        # enable locking
        r = Repository.get_by_repo_name(GIT_REPO)
        r.enable_locking = True
        Session().commit()
        # clone
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir())

        # check if lock was made
        r = Repository.get_by_repo_name(GIT_REPO)
        assert r.locked[0] == User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id

    def test_clone_after_repo_was_locked_hg(self, webserver):
        # lock repo
        r = Repository.get_by_repo_name(HG_REPO)
        Repository.lock(r, User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id)
        # pull fails since repo is locked
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        msg = ("""abort: HTTP Error 423: Repository `%s` locked by user `%s`"""
                % (HG_REPO, TEST_USER_ADMIN_LOGIN))
        assert msg in stderr

    def test_clone_after_repo_was_locked_git(self, webserver):
        # lock repo
        r = Repository.get_by_repo_name(GIT_REPO)
        Repository.lock(r, User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id)
        # pull fails since repo is locked
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        msg = ("""The requested URL returned error: 423""")
        assert msg in stderr

    def test_push_on_locked_repo_by_other_user_hg(self, webserver):
        # clone some temp
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        # lock repo
        r = Repository.get_by_repo_name(HG_REPO)
        # let this user actually push !
        RepoModel().grant_user_permission(repo=r, user=TEST_USER_REGULAR_LOGIN,
                                          perm='repository.write')
        Session().commit()
        Repository.lock(r, User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id)

        # push fails repo is locked by other user !
        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir,
                                             username=TEST_USER_REGULAR_LOGIN,
                                             password=TEST_USER_REGULAR_PASS,
                                             ignoreReturnCode=True)
        msg = ("""abort: HTTP Error 423: Repository `%s` locked by user `%s`"""
                % (HG_REPO, TEST_USER_ADMIN_LOGIN))
        assert msg in stderr

    def test_push_on_locked_repo_by_other_user_git(self, webserver):
        # Note: Git hooks must be executable on unix. This test will thus fail
        # for example on Linux if /tmp is mounted noexec.

        # clone some temp
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        # lock repo
        r = Repository.get_by_repo_name(GIT_REPO)
        # let this user actually push !
        RepoModel().grant_user_permission(repo=r, user=TEST_USER_REGULAR_LOGIN,
                                          perm='repository.write')
        Session().commit()
        Repository.lock(r, User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id)

        # push fails repo is locked by other user !
        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir,
                                             username=TEST_USER_REGULAR_LOGIN,
                                             password=TEST_USER_REGULAR_PASS,
                                             ignoreReturnCode=True)
        err = 'Repository `%s` locked by user `%s`' % (GIT_REPO, TEST_USER_ADMIN_LOGIN)
        assert err in stderr

        # TODO: fix this somehow later on Git, Git is stupid and even if we throw
        # back 423 to it, it makes ANOTHER request and we fail there with 405 :/

        msg = ("""abort: HTTP Error 423: Repository `%s` locked by user `%s`"""
                % (GIT_REPO, TEST_USER_ADMIN_LOGIN))
        #msg = "405 Method Not Allowed"
        #assert msg in stderr

    def test_push_unlocks_repository_hg(self, webserver, testfork):
        # enable locking
        r = Repository.get_by_repo_name(testfork['hg'])
        r.enable_locking = True
        Session().commit()
        # clone some temp
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(testfork['hg'])
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, dest_dir)

        # check for lock repo after clone
        r = Repository.get_by_repo_name(testfork['hg'])
        uid = User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id
        assert r.locked[0] == uid

        # push is ok and repo is now unlocked
        stdout, stderr = _add_files_and_push(webserver, 'hg', dest_dir, clone_url=clone_url)
        assert str('remote: Released lock on repo `%s`' % testfork['hg']) in stdout
        # we need to cleanup the Session Here !
        Session.remove()
        r = Repository.get_by_repo_name(testfork['hg'])
        assert r.locked == [None, None]

    # TODO: fix me ! somehow during tests hooks don't get called on Git
    def test_push_unlocks_repository_git(self, webserver, testfork):
        # enable locking
        r = Repository.get_by_repo_name(testfork['git'])
        r.enable_locking = True
        Session().commit()
        # clone some temp
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(testfork['git'])
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, dest_dir)

        # check for lock repo after clone
        r = Repository.get_by_repo_name(testfork['git'])
        assert r.locked[0] == User.get_by_username(TEST_USER_ADMIN_LOGIN).user_id

        # push is ok and repo is now unlocked
        stdout, stderr = _add_files_and_push(webserver, 'git', dest_dir, clone_url=clone_url)
        _check_proper_git_push(stdout, stderr)

        assert ('remote: Released lock on repo `%s`' % testfork['git']) in stderr
        # we need to cleanup the Session Here !
        Session.remove()
        r = Repository.get_by_repo_name(testfork['git'])
        assert r.locked == [None, None]

    def test_ip_restriction_hg(self, webserver):
        user_model = UserModel()
        try:
            user_model.add_extra_ip(TEST_USER_ADMIN_LOGIN, '10.10.10.10/32')
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)
            clone_url = webserver.repo_url(HG_REPO)
            stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
            assert 'abort: HTTP Error 403: Forbidden' in stderr
        finally:
            # release IP restrictions
            for ip in UserIpMap.query():
                UserIpMap.delete(ip.ip_id)
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)

        clone_url = webserver.repo_url(HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir())

        assert 'requesting all changes' in stdout
        assert 'adding changesets' in stdout
        assert 'adding manifests' in stdout
        assert 'adding file changes' in stdout

        assert stderr == ''

    def test_ip_restriction_git(self, webserver):
        user_model = UserModel()
        try:
            user_model.add_extra_ip(TEST_USER_ADMIN_LOGIN, '10.10.10.10/32')
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)
            clone_url = webserver.repo_url(GIT_REPO)
            stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
            # The message apparently changed in Git 1.8.3, so match it loosely.
            assert re.search(r'\b403\b', stderr)
        finally:
            # release IP restrictions
            for ip in UserIpMap.query():
                UserIpMap.delete(ip.ip_id)
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)

        clone_url = webserver.repo_url(GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir())

        assert 'Cloning into' in stdout + stderr
        assert stderr == '' or stdout == ''

    @parametrize('repo_type, repo_name', [
                #('git',      GIT_REPO), # git hooks doesn't work like hg hooks
                ('hg',       HG_REPO),
    ])
    def test_custom_hooks_preoutgoing(self, testhook_cleanup, webserver, testfork, repo_type, repo_name):
        # set prechangegroup to failing hook (returns True)
        Ui.create_or_update_hook('preoutgoing.testhook', 'python:kallithea.tests.fixture.failing_test_hook')
        Session().commit()
        # clone repo
        clone_url = webserver.repo_url(testfork[repo_type], username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS)
        dest_dir = _get_tmp_dir()
        stdout, stderr = Command(TESTS_TMP_PATH) \
            .execute('%s clone' % repo_type, clone_url, dest_dir, ignoreReturnCode=True)
        if repo_type == 'hg':
            assert 'preoutgoing.testhook hook failed' in stdout
        elif repo_type == 'git':
            assert 'error: 406' in stderr

    @parametrize('repo_type, repo_name', [
                #('git',      GIT_REPO), # git hooks doesn't work like hg hooks
                ('hg',       HG_REPO),
    ])
    def test_custom_hooks_prechangegroup(self, testhook_cleanup, webserver, testfork, repo_type, repo_name):

        # set prechangegroup to failing hook (returns True)
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.failing_test_hook')
        Session().commit()
        # clone repo
        clone_url = webserver.repo_url(testfork[repo_type], username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS)
        dest_dir = _get_tmp_dir()
        stdout, stderr = Command(TESTS_TMP_PATH).execute('%s clone' % repo_type, clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, repo_type, dest_dir,
                                             username=TEST_USER_ADMIN_LOGIN,
                                             password=TEST_USER_ADMIN_PASS,
                                             ignoreReturnCode=True)
        assert 'failing_test_hook failed' in stdout + stderr
        assert 'Traceback' not in stdout + stderr
        assert 'prechangegroup.testhook hook failed' in stdout + stderr
        # there are still outgoing changesets
        stdout, stderr = _check_outgoing(repo_type, dest_dir, clone_url)
        assert stdout != ''

        # set prechangegroup hook to exception throwing method
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.exception_test_hook')
        Session().commit()
        # re-try to push
        stdout, stderr = Command(dest_dir).execute('%s push' % repo_type, clone_url, ignoreReturnCode=True)
        if repo_type == 'hg':
            # like with 'hg serve...' 'HTTP Error 500: INTERNAL SERVER ERROR' should be returned
            assert 'HTTP Error 500: INTERNAL SERVER ERROR' in stderr
        elif repo_type == 'git':
            assert 'exception_test_hook threw an exception' in stderr
        # there are still outgoing changesets
        stdout, stderr = _check_outgoing(repo_type, dest_dir, clone_url)
        assert stdout != ''

        # set prechangegroup hook to method that returns False
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.passing_test_hook')
        Session().commit()
        # re-try to push
        stdout, stderr = Command(dest_dir).execute('%s push' % repo_type, clone_url, ignoreReturnCode=True)
        assert 'passing_test_hook succeeded' in stdout + stderr
        assert 'Traceback' not in stdout + stderr
        assert 'prechangegroup.testhook hook failed' not in stdout + stderr
        # no more outgoing changesets
        stdout, stderr = _check_outgoing(repo_type, dest_dir, clone_url)
        assert stdout == ''
        assert stderr == ''

    def test_add_submodule(self, webserver, testfork):
        dest_dir = _get_tmp_dir()
        clone_url = webserver.repo_url(GIT_REPO)

        fork_url = webserver.repo_url(testfork['git'])

        # add submodule
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', fork_url, dest_dir)
        stdout, stderr = Command(dest_dir).execute('git submodule add', clone_url, 'testsubmodule')
        stdout, stderr = Command(dest_dir).execute('git commit -am "added testsubmodule pointing to', clone_url, '"', EMAIL=TEST_USER_ADMIN_EMAIL)
        stdout, stderr = Command(dest_dir).execute('git push', fork_url, 'master')

        # check for testsubmodule link in files page
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=testfork['git'],
                                    revision='tip',
                                    f_path='/'))
        response.mustcontain('<a class="submodule-dir" href="%s" target="_blank"><i class="icon-file-submodule"></i><span>testsubmodule @ ' % clone_url)

        # check that following a submodule link actually works - and redirects
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=testfork['git'],
                                    revision='tip',
                                    f_path='/testsubmodule'),
                                status=302)
        assert response.location == clone_url
