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
Helpers for fixture generation
"""

import logging
import os
import shutil
import tarfile
from os.path import dirname

import mock
from tg import request
from tg.util.webtest import test_context

from kallithea.lib import helpers
from kallithea.lib.auth import AuthUser
from kallithea.lib.db_manage import DbManage
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.comment import ChangesetCommentsModel
from kallithea.model.db import ChangesetStatus, Gist, RepoGroup, Repository, User, UserGroup
from kallithea.model.gist import GistModel
from kallithea.model.meta import Session
from kallithea.model.pull_request import CreatePullRequestAction  # , CreatePullRequestIterationAction, PullRequestModel
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.scm import ScmModel
from kallithea.model.user import UserModel
from kallithea.model.user_group import UserGroupModel
from kallithea.tests.base import (
    GIT_REPO, HG_REPO, IP_ADDR, TEST_USER_ADMIN_EMAIL, TEST_USER_ADMIN_LOGIN, TEST_USER_REGULAR_LOGIN, TESTS_TMP_PATH, invalidate_all_caches)


log = logging.getLogger(__name__)

FIXTURES = os.path.join(dirname(dirname(os.path.abspath(__file__))), 'tests', 'fixtures')


def error_function(*args, **kwargs):
    raise Exception('Total Crash !')


class Fixture(object):

    def __init__(self):
        pass

    def anon_access(self, status):
        """
        Context manager for controlling anonymous access.
        Anon access will be set and committed, but restored again when exiting the block.

        Usage:

        fixture = Fixture()
        with fixture.anon_access(False):
            stuff
        """

        class context(object):
            def __enter__(self):
                anon = User.get_default_user()
                self._before = anon.active
                anon.active = status
                Session().commit()
                invalidate_all_caches()

            def __exit__(self, exc_type, exc_val, exc_tb):
                anon = User.get_default_user()
                anon.active = self._before
                Session().commit()

        return context()

    def _get_repo_create_params(self, **custom):
        """Return form values to be validated through RepoForm"""
        defs = dict(
            repo_name=None,
            repo_type='hg',
            clone_uri='',
            repo_group=u'-1',
            repo_description=u'DESC',
            repo_private=False,
            repo_landing_rev='rev:tip',
            repo_copy_permissions=False,
            repo_state=Repository.STATE_CREATED,
        )
        defs.update(custom)
        if 'repo_name_full' not in custom:
            defs.update({'repo_name_full': defs['repo_name']})

        # fix the repo name if passed as repo_name_full
        if defs['repo_name']:
            defs['repo_name'] = defs['repo_name'].split('/')[-1]

        return defs

    def _get_repo_group_create_params(self, **custom):
        """Return form values to be validated through RepoGroupForm"""
        defs = dict(
            group_name=None,
            group_description=u'DESC',
            parent_group_id=u'-1',
            perms_updates=[],
            perms_new=[],
            recursive=False
        )
        defs.update(custom)

        return defs

    def _get_user_create_params(self, name, **custom):
        defs = dict(
            username=name,
            password='qweqwe',
            email='%s+test@example.com' % name,
            firstname=u'TestUser',
            lastname=u'Test',
            active=True,
            admin=False,
            extern_type='internal',
            extern_name=None
        )
        defs.update(custom)

        return defs

    def _get_user_group_create_params(self, name, **custom):
        defs = dict(
            users_group_name=name,
            user_group_description=u'DESC',
            users_group_active=True,
            user_group_data={},
        )
        defs.update(custom)

        return defs

    def create_repo(self, name, repo_group=None, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            r = Repository.get_by_repo_name(name)
            if r:
                return r

        if isinstance(repo_group, RepoGroup):
            repo_group = repo_group.group_id

        form_data = self._get_repo_create_params(repo_name=name, **kwargs)
        form_data['repo_group'] = repo_group # patch form dict so it can be used directly by model
        cur_user = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        RepoModel().create(form_data, cur_user)
        Session().commit()
        ScmModel().mark_for_invalidation(name)
        return Repository.get_by_repo_name(name)

    def create_fork(self, repo_to_fork, fork_name, **kwargs):
        repo_to_fork = Repository.get_by_repo_name(repo_to_fork)

        form_data = self._get_repo_create_params(repo_name=fork_name,
                                            fork_parent_id=repo_to_fork,
                                            repo_type=repo_to_fork.repo_type,
                                            **kwargs)
        # patch form dict so it can be used directly by model
        form_data['description'] = form_data['repo_description']
        form_data['private'] = form_data['repo_private']
        form_data['landing_rev'] = form_data['repo_landing_rev']

        owner = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        RepoModel().create_fork(form_data, cur_user=owner)
        Session().commit()
        ScmModel().mark_for_invalidation(fork_name)
        r = Repository.get_by_repo_name(fork_name)
        assert r
        return r

    def destroy_repo(self, repo_name, **kwargs):
        RepoModel().delete(repo_name, **kwargs)
        Session().commit()

    def create_repo_group(self, name, parent_group_id=None, **kwargs):
        assert '/' not in name, (name, kwargs) # use group_parent_id to make nested groups
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            gr = RepoGroup.get_by_group_name(group_name=name)
            if gr:
                return gr
        form_data = self._get_repo_group_create_params(group_name=name, **kwargs)
        gr = RepoGroupModel().create(
            group_name=form_data['group_name'],
            group_description=form_data['group_name'],
            parent=parent_group_id,
            owner=kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN),
            )
        Session().commit()
        gr = RepoGroup.get_by_group_name(gr.group_name)
        return gr

    def destroy_repo_group(self, repogroupid):
        RepoGroupModel().delete(repogroupid)
        Session().commit()

    def create_user(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            user = User.get_by_username(name)
            if user:
                return user
        form_data = self._get_user_create_params(name, **kwargs)
        user = UserModel().create(form_data)
        Session().commit()
        user = User.get_by_username(user.username)
        return user

    def destroy_user(self, userid):
        UserModel().delete(userid)
        Session().commit()

    def create_user_group(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            gr = UserGroup.get_by_group_name(group_name=name)
            if gr:
                return gr
        form_data = self._get_user_group_create_params(name, **kwargs)
        owner = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        user_group = UserGroupModel().create(
            name=form_data['users_group_name'],
            description=form_data['user_group_description'],
            owner=owner, active=form_data['users_group_active'],
            group_data=form_data['user_group_data'])
        Session().commit()
        user_group = UserGroup.get_by_group_name(user_group.users_group_name)
        return user_group

    def destroy_user_group(self, usergroupid):
        UserGroupModel().delete(user_group=usergroupid, force=True)
        Session().commit()

    def create_gist(self, **kwargs):
        form_data = {
            'description': u'new-gist',
            'owner': TEST_USER_ADMIN_LOGIN,
            'gist_type': Gist.GIST_PUBLIC,
            'lifetime': -1,
            'gist_mapping': {'filename1.txt': {'content': 'hello world'}}
        }
        form_data.update(kwargs)
        gist = GistModel().create(
            description=form_data['description'], owner=form_data['owner'], ip_addr=IP_ADDR,
            gist_mapping=form_data['gist_mapping'], gist_type=form_data['gist_type'],
            lifetime=form_data['lifetime']
        )
        Session().commit()

        return gist

    def destroy_gists(self, gistid=None):
        for g in Gist.query():
            if gistid:
                if gistid == g.gist_access_id:
                    GistModel().delete(g)
            else:
                GistModel().delete(g)
        Session().commit()

    def load_resource(self, resource_name, strip=True):
        with open(os.path.join(FIXTURES, resource_name), 'rb') as f:
            source = f.read()
            if strip:
                source = source.strip()

        return source

    def commit_change(self, repo, filename, content, message, vcs_type,
                      parent=None, newfile=False, author=None):
        repo = Repository.get_by_repo_name(repo)
        _cs = parent
        if parent is None:
            _cs = EmptyChangeset(alias=vcs_type)
        if author is None:
            author = '%s <%s>' % (TEST_USER_ADMIN_LOGIN, TEST_USER_ADMIN_EMAIL)

        if newfile:
            nodes = {
                filename: {
                    'content': content
                }
            }
            cs = ScmModel().create_nodes(
                user=TEST_USER_ADMIN_LOGIN,
                ip_addr=IP_ADDR,
                repo=repo,
                message=message,
                nodes=nodes,
                parent_cs=_cs,
                author=author,
            )
        else:
            cs = ScmModel().commit_change(
                repo=repo.scm_instance, repo_name=repo.repo_name,
                cs=parent,
                user=TEST_USER_ADMIN_LOGIN,
                ip_addr=IP_ADDR,
                author=author,
                message=message,
                content=content,
                f_path=filename
            )
        return cs

    def review_changeset(self, repo, revision, status, author=TEST_USER_ADMIN_LOGIN):
        comment = ChangesetCommentsModel().create(u"review comment", repo, author, revision=revision, send_email=False)
        csm = ChangesetStatusModel().set_status(repo, ChangesetStatus.STATUS_APPROVED, author, comment, revision=revision)
        Session().commit()
        return csm

    def create_pullrequest(self, testcontroller, repo_name, pr_src_rev, pr_dst_rev, title=u'title'):
        org_ref = 'branch:stable:%s' % pr_src_rev
        other_ref = 'branch:default:%s' % pr_dst_rev
        with test_context(testcontroller.app): # needed to be able to mock request user
            org_repo = other_repo = Repository.get_by_repo_name(repo_name)
            owner_user = User.get_by_username(TEST_USER_ADMIN_LOGIN)
            reviewers = [User.get_by_username(TEST_USER_REGULAR_LOGIN)]
            request.authuser = AuthUser(dbuser=owner_user)
            # creating a PR sends a message with an absolute URL - without routing that requires mocking
            with mock.patch.object(helpers, 'url', (lambda arg, qualified=False, **kwargs: ('https://localhost' if qualified else '') + '/fake/' + arg)):
                cmd = CreatePullRequestAction(org_repo, other_repo, org_ref, other_ref, title, u'No description', owner_user, reviewers)
                pull_request = cmd.execute()
            Session().commit()
        return pull_request.pull_request_id


#==============================================================================
# Global test environment setup
#==============================================================================

def create_test_env(repos_test_path, config):
    """
    Makes a fresh database and
    install test repository into tmp dir
    """

    # PART ONE create db
    dbconf = config['sqlalchemy.url']
    log.debug('making test db %s', dbconf)

    # create test dir if it doesn't exist
    if not os.path.isdir(repos_test_path):
        log.debug('Creating testdir %s', repos_test_path)
        os.makedirs(repos_test_path)

    dbmanage = DbManage(dbconf=dbconf, root=config['here'],
                        tests=True)
    dbmanage.create_tables(override=True)
    # for tests dynamically set new root paths based on generated content
    dbmanage.create_settings(dbmanage.prompt_repo_root_path(repos_test_path))
    dbmanage.create_default_user()
    dbmanage.admin_prompt()
    dbmanage.create_permissions()
    dbmanage.populate_default_permissions()
    Session().commit()
    # PART TWO make test repo
    log.debug('making test vcs repositories')

    idx_path = config['index_dir']
    data_path = config['cache_dir']

    # clean index and data
    if idx_path and os.path.exists(idx_path):
        log.debug('remove %s', idx_path)
        shutil.rmtree(idx_path)

    if data_path and os.path.exists(data_path):
        log.debug('remove %s', data_path)
        shutil.rmtree(data_path)

    # CREATE DEFAULT TEST REPOS
    tar = tarfile.open(os.path.join(FIXTURES, 'vcs_test_hg.tar.gz'))
    tar.extractall(os.path.join(TESTS_TMP_PATH, HG_REPO))
    tar.close()

    tar = tarfile.open(os.path.join(FIXTURES, 'vcs_test_git.tar.gz'))
    tar.extractall(os.path.join(TESTS_TMP_PATH, GIT_REPO))
    tar.close()

    # LOAD VCS test stuff
    from kallithea.tests.vcs import setup_package
    setup_package()


def create_test_index(repo_location, config, full_index):
    """
    Makes default test index
    """

    from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
    from kallithea.lib.pidlock import DaemonLock

    index_location = os.path.join(config['index_dir'])
    if not os.path.exists(index_location):
        os.makedirs(index_location)

    l = DaemonLock(os.path.join(index_location, 'make_index.lock'))
    WhooshIndexingDaemon(index_location=index_location,
                         repo_location=repo_location) \
        .run(full_index=full_index)
    l.release()


def failing_test_hook(ui, repo, **kwargs):
    ui.write("failing_test_hook failed\n")
    return 1


def exception_test_hook(ui, repo, **kwargs):
    raise Exception("exception_test_hook threw an exception")


def passing_test_hook(ui, repo, **kwargs):
    ui.write("passing_test_hook succeeded\n")
    return 0
