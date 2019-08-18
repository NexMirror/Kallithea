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

from __future__ import print_function

import json
import os
import re
import tempfile
import time
import urllib2
from subprocess import PIPE, Popen
from tempfile import _RandomNameSequence

import pytest

from kallithea import CONFIG
from kallithea.model.db import CacheInvalidation, Repository, Ui, User, UserIpMap, UserLog
from kallithea.model.meta import Session
from kallithea.model.ssh_key import SshKeyModel
from kallithea.model.user import UserModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


DEBUG = True
HOST = '127.0.0.1:4999'  # test host

fixture = Fixture()


# Parameterize different kinds of VCS testing - both the kind of VCS and the
# access method (HTTP/SSH)

# Mixin for using HTTP and SSH URLs
class HttpVcsTest(object):
    @staticmethod
    def repo_url_param(webserver, repo_name, **kwargs):
        return webserver.repo_url(repo_name, **kwargs)

class SshVcsTest(object):
    public_keys = {
        TEST_USER_REGULAR_LOGIN: u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== kallithea@localhost',
        TEST_USER_ADMIN_LOGIN: u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUq== kallithea@localhost',
    }

    @classmethod
    def repo_url_param(cls, webserver, repo_name, username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS, client_ip=IP_ADDR):
        user = User.get_by_username(username)
        if user.ssh_keys:
            ssh_key = user.ssh_keys[0]
        else:
            sshkeymodel = SshKeyModel()
            ssh_key = sshkeymodel.create(user, u'test key', cls.public_keys[user.username])
            Session().commit()

        return cls._ssh_param(repo_name, user, ssh_key, client_ip)

# Mixins for using Mercurial and Git
class HgVcsTest(object):
    repo_type = 'hg'
    repo_name = HG_REPO

class GitVcsTest(object):
    repo_type = 'git'
    repo_name = GIT_REPO

# Combine mixins to give the combinations we want to parameterize tests with
class HgHttpVcsTest(HgVcsTest, HttpVcsTest):
    pass

class GitHttpVcsTest(GitVcsTest, HttpVcsTest):
    pass

class HgSshVcsTest(HgVcsTest, SshVcsTest):
    @staticmethod
    def _ssh_param(repo_name, user, ssh_key, client_ip):
        # Specify a custom ssh command on the command line
        return r"""--config ui.ssh="bash -c 'SSH_ORIGINAL_COMMAND=\"\$2\" SSH_CONNECTION=\"%s 1024 127.0.0.1 22\" kallithea-cli ssh-serve -c %s %s %s' --" ssh://someuser@somehost/%s""" % (
            client_ip,
            CONFIG['__file__'],
            user.user_id,
            ssh_key.user_ssh_key_id,
            repo_name)

class GitSshVcsTest(GitVcsTest, SshVcsTest):
    @staticmethod
    def _ssh_param(repo_name, user, ssh_key, client_ip):
        # Set a custom ssh command in the global environment
        os.environ['GIT_SSH_COMMAND'] = r"""bash -c 'SSH_ORIGINAL_COMMAND="$2" SSH_CONNECTION="%s 1024 127.0.0.1 22" kallithea-cli ssh-serve -c %s %s %s' --""" % (
            client_ip,
            CONFIG['__file__'],
            user.user_id,
            ssh_key.user_ssh_key_id)
        return "ssh://someuser@somehost/%s""" % repo_name

parametrize_vcs_test = parametrize('vt', [
    HgHttpVcsTest,
    GitHttpVcsTest,
    HgSshVcsTest,
    GitSshVcsTest,
])
parametrize_vcs_test_hg = parametrize('vt', [
    HgHttpVcsTest,
    HgSshVcsTest,
])
parametrize_vcs_test_http = parametrize('vt', [
    HgHttpVcsTest,
    GitHttpVcsTest,
])

class Command(object):

    def __init__(self, cwd):
        self.cwd = cwd

    def execute(self, *args, **environ):
        """
        Runs command on the system with given ``args`` using simple space
        join without safe quoting.
        """
        command = ' '.join(args)
        ignoreReturnCode = environ.pop('ignoreReturnCode', False)
        if DEBUG:
            print('*** CMD %s ***' % command)
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
                print('stdout:', stdout)
            if stderr:
                print('stderr:', stderr)
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
    Command(dest_dir).execute(vcs, 'add', added_file)

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

def _add_files_and_push(webserver, vt, dest_dir, clone_url, ignoreReturnCode=False, files_no=3):
    _add_files(vt.repo_type, dest_dir, files_no=files_no)
    # PUSH it back
    stdout = stderr = None
    if vt.repo_type == 'hg':
        stdout, stderr = Command(dest_dir).execute('hg push -f --verbose', clone_url, ignoreReturnCode=ignoreReturnCode)
    elif vt.repo_type == 'git':
        stdout, stderr = Command(dest_dir).execute('git push -f --verbose', clone_url, "master", ignoreReturnCode=ignoreReturnCode)

    return stdout, stderr


def _check_outgoing(vcs, cwd, clone_url):
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

    @parametrize_vcs_test
    def test_clone_repo_by_admin(self, webserver, vt):
        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, _get_tmp_dir())

        if vt.repo_type == 'git':
            assert 'Cloning into' in stdout + stderr
            assert stderr == '' or stdout == ''
        elif vt.repo_type == 'hg':
            assert 'requesting all changes' in stdout
            assert 'adding changesets' in stdout
            assert 'adding manifests' in stdout
            assert 'adding file changes' in stdout
            assert stderr == ''

    @parametrize_vcs_test_http
    def test_clone_wrong_credentials(self, webserver, vt):
        clone_url = vt.repo_url_param(webserver, vt.repo_name, password='bad!')
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        if vt.repo_type == 'git':
            assert 'fatal: Authentication failed' in stderr
        elif vt.repo_type == 'hg':
            assert 'abort: authorization failed' in stderr

    def test_clone_git_dir_as_hg(self, webserver):
        clone_url = HgHttpVcsTest.repo_url_param(webserver, GIT_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('hg clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'HTTP Error 404: Not Found' in stderr or "not a valid repository" in stdout and 'abort:' in stderr

    def test_clone_hg_repo_as_git(self, webserver):
        clone_url = GitHttpVcsTest.repo_url_param(webserver, HG_REPO)
        stdout, stderr = Command(TESTS_TMP_PATH).execute('git clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        assert 'not found' in stderr

    @parametrize_vcs_test
    def test_clone_non_existing_path(self, webserver, vt):
        clone_url = vt.repo_url_param(webserver, 'trololo')
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
        if vt.repo_type == 'git':
            assert 'not found' in stderr or 'abort: Access to %r denied' % 'trololo' in stderr
        elif vt.repo_type == 'hg':
            assert 'HTTP Error 404: Not Found' in stderr or 'abort: no suitable response from remote hg' in stderr and 'remote: abort: Access to %r denied' % 'trololo' in stdout

    @parametrize_vcs_test
    def test_push_new_repo(self, webserver, vt):
        # Clear the log so we know what is added
        UserLog.query().delete()
        Session().commit()

        # Create an empty server repo using the API
        repo_name = u'new_%s_%s' % (vt.repo_type, _RandomNameSequence().next())
        usr = User.get_by_username(TEST_USER_ADMIN_LOGIN)
        params = {
            "id": 7,
            "api_key": usr.api_key,
            "method": 'create_repo',
            "args": dict(repo_name=repo_name,
                         owner=TEST_USER_ADMIN_LOGIN,
                         repo_type=vt.repo_type),
        }
        req = urllib2.Request(
            'http://%s:%s/_admin/api' % webserver.server_address,
            data=json.dumps(params),
            headers={'content-type': 'application/json'})
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        # Expect something like:
        # {u'result': {u'msg': u'Created new repository `new_XXX`', u'task': None, u'success': True}, u'id': 7, u'error': None}
        assert result[u'result'][u'success']

        # Create local clone of the empty server repo
        local_clone_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, local_clone_dir)

        # Make 3 commits and push to the empty server repo.
        # The server repo doesn't have any other heads than the
        # refs/heads/master we are pushing, but the `git log` in the push hook
        # should still list the 3 commits.
        stdout, stderr = _add_files_and_push(webserver, vt, local_clone_dir, clone_url=clone_url)
        if vt.repo_type == 'git':
            _check_proper_git_push(stdout, stderr)
        elif vt.repo_type == 'hg':
            assert 'pushing to ' in stdout
            assert 'remote: added ' in stdout

        # Verify that we got the right events in UserLog. Expect something like:
        # <UserLog('id:new_git_XXX:started_following_repo')>
        # <UserLog('id:new_git_XXX:user_created_repo')>
        # <UserLog('id:new_git_XXX:pull')>
        # <UserLog('id:new_git_XXX:push:aed9d4c1732a1927da3be42c47eb9afdc200d427,d38b083a07af10a9f44193486959a96a23db78da,4841ff9a2b385bec995f4679ef649adb3f437622')>
        action_parts = [ul.action.split(':', 1) for ul in UserLog.query().order_by(UserLog.user_log_id)]
        assert [(t[0], (t[1].count(',') + 1) if len(t) == 2 else 0) for t in action_parts] == ([
            (u'started_following_repo', 0),
            (u'user_created_repo', 0),
            (u'pull', 0),
            (u'push', 3)]
            if vt.repo_type == 'git' else [
            (u'started_following_repo', 0),
            (u'user_created_repo', 0),
            # (u'pull', 0), # Mercurial outgoing hook is not called for empty clones
            (u'push', 3)])

    @parametrize_vcs_test
    def test_push_new_file(self, webserver, testfork, vt):
        UserLog.query().delete()
        Session().commit()

        dest_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        clone_url = vt.repo_url_param(webserver, testfork[vt.repo_type])
        stdout, stderr = _add_files_and_push(webserver, vt, dest_dir, clone_url=clone_url)

        if vt.repo_type == 'git':
            _check_proper_git_push(stdout, stderr)
        elif vt.repo_type == 'hg':
            assert 'pushing to' in stdout
            assert 'Repository size' in stdout
            assert 'Last revision is now' in stdout

        action_parts = [ul.action.split(':', 1) for ul in UserLog.query().order_by(UserLog.user_log_id)]
        assert [(t[0], (t[1].count(',') + 1) if len(t) == 2 else 0) for t in action_parts] == \
            [(u'pull', 0), (u'push', 3)]

    @parametrize_vcs_test
    def test_pull(self, webserver, testfork, vt):
        UserLog.query().delete()
        Session().commit()

        dest_dir = _get_tmp_dir()
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'init', dest_dir)

        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(dest_dir).execute(vt.repo_type, 'pull', clone_url)

        if vt.repo_type == 'git':
            assert 'FETCH_HEAD' in stderr
        elif vt.repo_type == 'hg':
            assert 'new changesets' in stdout

        action_parts = [ul.action for ul in UserLog.query().order_by(UserLog.user_log_id)]
        assert action_parts == [u'pull']

    @parametrize_vcs_test
    def test_push_invalidates_cache(self, webserver, testfork, vt):
        pre_cached_tip = [repo.get_api_data()['last_changeset']['short_id'] for repo in Repository.query().filter(Repository.repo_name == testfork[vt.repo_type])]

        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == testfork[vt.repo_type]).scalar()
        if not key:
            key = CacheInvalidation(testfork[vt.repo_type], testfork[vt.repo_type])
            Session().add(key)

        key.cache_active = True
        Session().commit()

        dest_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, testfork[vt.repo_type])
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, vt, dest_dir, files_no=1, clone_url=clone_url)

        if vt.repo_type == 'git':
            _check_proper_git_push(stdout, stderr)

        post_cached_tip = [repo.get_api_data()['last_changeset']['short_id'] for repo in Repository.query().filter(Repository.repo_name == testfork[vt.repo_type])]
        assert pre_cached_tip != post_cached_tip

        key = CacheInvalidation.query().filter(CacheInvalidation.cache_key
                                               == testfork[vt.repo_type]).all()
        assert key == []

    @parametrize_vcs_test_http
    def test_push_wrong_credentials(self, webserver, vt):
        dest_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        clone_url = webserver.repo_url(vt.repo_name, username='bad', password='name')
        stdout, stderr = _add_files_and_push(webserver, vt, dest_dir,
                                             clone_url=clone_url, ignoreReturnCode=True)

        if vt.repo_type == 'git':
            assert 'fatal: Authentication failed' in stderr
        elif vt.repo_type == 'hg':
            assert 'abort: authorization failed' in stderr

    @parametrize_vcs_test
    def test_push_with_readonly_credentials(self, webserver, vt):
        UserLog.query().delete()
        Session().commit()

        dest_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, vt.repo_name, username=TEST_USER_REGULAR_LOGIN, password=TEST_USER_REGULAR_PASS)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, vt, dest_dir, ignoreReturnCode=True, clone_url=clone_url)

        if vt.repo_type == 'git':
            assert 'The requested URL returned error: 403' in stderr or 'abort: Push access to %r denied' % str(vt.repo_name) in stderr
        elif vt.repo_type == 'hg':
            assert 'abort: HTTP Error 403: Forbidden' in stderr or 'abort: push failed on remote' in stderr and 'remote: Push access to %r denied' % str(vt.repo_name) in stdout

        action_parts = [ul.action.split(':', 1) for ul in UserLog.query().order_by(UserLog.user_log_id)]
        assert [(t[0], (t[1].count(',') + 1) if len(t) == 2 else 0) for t in action_parts] == \
            [(u'pull', 0)]

    @parametrize_vcs_test
    def test_push_back_to_wrong_url(self, webserver, vt):
        dest_dir = _get_tmp_dir()
        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(
            webserver, vt, dest_dir, clone_url='http://%s:%s/tmp' % (
                webserver.server_address[0], webserver.server_address[1]),
            ignoreReturnCode=True)

        if vt.repo_type == 'git':
            assert 'not found' in stderr
        elif vt.repo_type == 'hg':
            assert 'HTTP Error 404: Not Found' in stderr

    @parametrize_vcs_test
    def test_ip_restriction(self, webserver, vt):
        user_model = UserModel()
        try:
            # Add IP constraint that excludes the test context:
            user_model.add_extra_ip(TEST_USER_ADMIN_LOGIN, '10.10.10.10/32')
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)
            clone_url = vt.repo_url_param(webserver, vt.repo_name)
            stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, _get_tmp_dir(), ignoreReturnCode=True)
            if vt.repo_type == 'git':
                # The message apparently changed in Git 1.8.3, so match it loosely.
                assert re.search(r'\b403\b', stderr) or 'abort: User test_admin from 127.0.0.127 cannot be authorized' in stderr
            elif vt.repo_type == 'hg':
                assert 'abort: HTTP Error 403: Forbidden' in stderr or 'remote: abort: User test_admin from 127.0.0.127 cannot be authorized' in stdout
        finally:
            # release IP restrictions
            for ip in UserIpMap.query():
                UserIpMap.delete(ip.ip_id)
            Session().commit()
            # IP permissions are cached, need to wait for the cache in the server process to expire
            time.sleep(1.5)

        clone_url = vt.repo_url_param(webserver, vt.repo_name)
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, _get_tmp_dir())

        if vt.repo_type == 'git':
            assert 'Cloning into' in stdout + stderr
            assert stderr == '' or stdout == ''
        elif vt.repo_type == 'hg':
            assert 'requesting all changes' in stdout
            assert 'adding changesets' in stdout
            assert 'adding manifests' in stdout
            assert 'adding file changes' in stdout

            assert stderr == ''

    @parametrize_vcs_test_hg # git hooks doesn't work like hg hooks
    def test_custom_hooks_preoutgoing(self, testhook_cleanup, webserver, testfork, vt):
        # set prechangegroup to failing hook (returns True)
        Ui.create_or_update_hook('preoutgoing.testhook', 'python:kallithea.tests.fixture.failing_test_hook')
        Session().commit()
        # clone repo
        clone_url = vt.repo_url_param(webserver, testfork[vt.repo_type], username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS)
        dest_dir = _get_tmp_dir()
        stdout, stderr = Command(TESTS_TMP_PATH) \
            .execute(vt.repo_type, 'clone', clone_url, dest_dir, ignoreReturnCode=True)
        if vt.repo_type == 'hg':
            assert 'preoutgoing.testhook hook failed' in stdout
        elif vt.repo_type == 'git':
            assert 'error: 406' in stderr

    @parametrize_vcs_test_hg # git hooks doesn't work like hg hooks
    def test_custom_hooks_prechangegroup(self, testhook_cleanup, webserver, testfork, vt):
        # set prechangegroup to failing hook (returns exit code 1)
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.failing_test_hook')
        Session().commit()
        # clone repo
        clone_url = vt.repo_url_param(webserver, testfork[vt.repo_type], username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS)
        dest_dir = _get_tmp_dir()
        stdout, stderr = Command(TESTS_TMP_PATH).execute(vt.repo_type, 'clone', clone_url, dest_dir)

        stdout, stderr = _add_files_and_push(webserver, vt, dest_dir, clone_url,
                                             ignoreReturnCode=True)
        assert 'failing_test_hook failed' in stdout + stderr
        assert 'Traceback' not in stdout + stderr
        assert 'prechangegroup.testhook hook failed' in stdout + stderr
        # there are still outgoing changesets
        stdout, stderr = _check_outgoing(vt.repo_type, dest_dir, clone_url)
        assert stdout != ''

        # set prechangegroup hook to exception throwing method
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.exception_test_hook')
        Session().commit()
        # re-try to push
        stdout, stderr = Command(dest_dir).execute('%s push' % vt.repo_type, clone_url, ignoreReturnCode=True)
        if vt is HgHttpVcsTest:
            # like with 'hg serve...' 'HTTP Error 500: INTERNAL SERVER ERROR' should be returned
            assert 'HTTP Error 500: INTERNAL SERVER ERROR' in stderr
        elif vt is HgSshVcsTest:
            assert 'remote: Exception: exception_test_hook threw an exception' in stdout
        else: assert False
        # there are still outgoing changesets
        stdout, stderr = _check_outgoing(vt.repo_type, dest_dir, clone_url)
        assert stdout != ''

        # set prechangegroup hook to method that returns False
        Ui.create_or_update_hook('prechangegroup.testhook', 'python:kallithea.tests.fixture.passing_test_hook')
        Session().commit()
        # re-try to push
        stdout, stderr = Command(dest_dir).execute('%s push' % vt.repo_type, clone_url, ignoreReturnCode=True)
        assert 'passing_test_hook succeeded' in stdout + stderr
        assert 'Traceback' not in stdout + stderr
        assert 'prechangegroup.testhook hook failed' not in stdout + stderr
        # no more outgoing changesets
        stdout, stderr = _check_outgoing(vt.repo_type, dest_dir, clone_url)
        assert stdout == ''
        assert stderr == ''

    def test_add_submodule_git(self, webserver, testfork):
        dest_dir = _get_tmp_dir()
        clone_url = GitHttpVcsTest.repo_url_param(webserver, GIT_REPO)

        fork_url = GitHttpVcsTest.repo_url_param(webserver, testfork['git'])

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
        # check _repo_files_url that will be used to reload as AJAX
        response.mustcontain('var _repo_files_url = ("/%s/files/");' % testfork['git'])

        response.mustcontain('<a class="submodule-dir" href="%s" target="_blank"><i class="icon-file-submodule"></i><span>testsubmodule @ ' % clone_url)

        # check that following a submodule link actually works - and redirects
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=testfork['git'],
                                    revision='tip',
                                    f_path='/testsubmodule'),
                                status=302)
        assert response.location == clone_url
