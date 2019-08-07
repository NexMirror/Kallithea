# -*- coding: utf-8 -*-

import urllib

from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.model.db import Repository, User
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.user import UserModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class _BaseTestCase(TestController):
    """
    Write all tests here
    """
    REPO = None
    REPO_TYPE = None
    NEW_REPO = None
    REPO_FORK = None

    def setup_method(self, method):
        self.username = u'forkuser'
        self.password = u'qweqwe'
        u1 = fixture.create_user(self.username, password=self.password, email=u'fork_king@example.com')
        self.u1_id = u1.user_id
        Session().commit()

    def teardown_method(self, method):
        fixture.destroy_user(self.u1_id)
        Session().commit()

    def test_index(self):
        self.log_user()
        repo_name = self.REPO
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain("""There are no forks yet""")

    def test_no_permissions_to_fork(self):
        self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)['user_id']
        try:
            user_model = UserModel()
            usr = User.get_default_user()
            user_model.revoke_perm(usr, 'hg.fork.repository')
            user_model.grant_perm(usr, 'hg.fork.none')
            Session().commit()
            # try create a fork
            repo_name = self.REPO
            self.app.post(url(controller='forks', action='fork_create',
                              repo_name=repo_name), {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=403)
        finally:
            usr = User.get_default_user()
            user_model.revoke_perm(usr, 'hg.fork.none')
            user_model.grant_perm(usr, 'hg.fork.repository')
            Session().commit()

    def test_index_with_fork(self):
        self.log_user()

        # create a fork
        fork_name = self.REPO_FORK
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': u'-1',
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip',
            '_session_csrf_secret_token': self.session_csrf_secret_token()}

        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain(
            """<a href="/%s">%s</a>""" % (fork_name, fork_name)
        )

        # remove this fork
        response = self.app.post(url('delete_repo', repo_name=fork_name),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

    def test_fork_create_into_group(self):
        self.log_user()
        group = fixture.create_repo_group(u'vc')
        group_id = group.group_id
        fork_name = self.REPO_FORK
        fork_name_full = 'vc/%s' % fork_name
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': group_id,
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip',
            '_session_csrf_secret_token': self.session_csrf_secret_token()}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)
        repo = Repository.get_by_repo_name(fork_name_full)
        assert repo.fork.repo_name == self.REPO

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=fork_name_full))
        # test if we have a message that fork is ok
        self.checkSessionFlash(response,
                'Forked repository %s as <a href="/%s">%s</a>'
                % (repo_name, fork_name_full, fork_name_full))

        # test if the fork was created in the database
        fork_repo = Session().query(Repository) \
            .filter(Repository.repo_name == fork_name_full).one()

        assert fork_repo.repo_name == fork_name_full
        assert fork_repo.fork.repo_name == repo_name

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=fork_name_full))
        response.mustcontain(fork_name_full)
        response.mustcontain(self.REPO_TYPE)
        response.mustcontain('Fork of "<a href="/%s">%s</a>"' % (repo_name, repo_name))

        fixture.destroy_repo(fork_name_full)
        fixture.destroy_repo_group(group_id)

    def test_fork_unicode(self):
        self.log_user()

        # create a fork
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        fork_name = safe_str(self.REPO_FORK + u'-rødgrød')
        creation_args = {
            'repo_name': fork_name,
            'repo_group': u'-1',
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': 'unicode repo 1',
            'private': 'False',
            'landing_rev': 'rev:tip',
            '_session_csrf_secret_token': self.session_csrf_secret_token()}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))
        response.mustcontain(
            """<a href="/%s">%s</a>""" % (urllib.quote(fork_name), fork_name)
        )
        fork_repo = Repository.get_by_repo_name(safe_unicode(fork_name))
        assert fork_repo

        # fork the fork
        fork_name_2 = safe_str(self.REPO_FORK + u'-blåbærgrød')
        creation_args = {
            'repo_name': fork_name_2,
            'repo_group': u'-1',
            'fork_parent_id': fork_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': 'unicode repo 2',
            'private': 'False',
            'landing_rev': 'rev:tip',
            '_session_csrf_secret_token': self.session_csrf_secret_token()}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=fork_name), creation_args)
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=fork_name))
        response.mustcontain(
            """<a href="/%s">%s</a>""" % (urllib.quote(fork_name_2), fork_name_2)
        )

        # remove these forks
        response = self.app.post(url('delete_repo', repo_name=fork_name_2),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        response = self.app.post(url('delete_repo', repo_name=fork_name),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

    def test_fork_create_and_permissions(self):
        self.log_user()
        fork_name = self.REPO_FORK
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': u'-1',
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip',
            '_session_csrf_secret_token': self.session_csrf_secret_token()}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)
        repo = Repository.get_by_repo_name(self.REPO_FORK)
        assert repo.fork.repo_name == self.REPO

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=fork_name))
        # test if we have a message that fork is ok
        self.checkSessionFlash(response,
                'Forked repository %s as <a href="/%s">%s</a>'
                % (repo_name, fork_name, fork_name))

        # test if the fork was created in the database
        fork_repo = Session().query(Repository) \
            .filter(Repository.repo_name == fork_name).one()

        assert fork_repo.repo_name == fork_name
        assert fork_repo.fork.repo_name == repo_name

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=fork_name))
        response.mustcontain(fork_name)
        response.mustcontain(self.REPO_TYPE)
        response.mustcontain('Fork of "<a href="/%s">%s</a>"' % (repo_name, repo_name))

        usr = self.log_user(self.username, self.password)['user_id']

        forks = Repository.query() \
            .filter(Repository.repo_type == self.REPO_TYPE) \
            .filter(Repository.fork_id != None).all()
        assert 1 == len(forks)

        # set read permissions for this
        RepoModel().grant_user_permission(repo=forks[0],
                                          user=usr,
                                          perm='repository.read')
        Session().commit()

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain('<div>fork of vcs test</div>')

        # remove permissions
        default_user = User.get_default_user()
        try:
            RepoModel().grant_user_permission(repo=forks[0],
                                              user=usr, perm='repository.none')
            RepoModel().grant_user_permission(repo=forks[0],
                                              user=default_user, perm='repository.none')
            Session().commit()

            # fork shouldn't be visible
            response = self.app.get(url(controller='forks', action='forks',
                                        repo_name=repo_name))
            response.mustcontain('There are no forks yet')

        finally:
            RepoModel().grant_user_permission(repo=forks[0],
                                              user=usr, perm='repository.read')
            RepoModel().grant_user_permission(repo=forks[0],
                                              user=default_user, perm='repository.read')
            RepoModel().delete(repo=forks[0])


class TestGIT(_BaseTestCase):
    REPO = GIT_REPO
    NEW_REPO = NEW_GIT_REPO
    REPO_TYPE = 'git'
    REPO_FORK = GIT_FORK


class TestHG(_BaseTestCase):
    REPO = HG_REPO
    NEW_REPO = NEW_HG_REPO
    REPO_TYPE = 'hg'
    REPO_FORK = HG_FORK
