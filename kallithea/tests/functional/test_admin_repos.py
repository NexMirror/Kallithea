# -*- coding: utf-8 -*-

import os
import urllib

import mock
import pytest

from kallithea.lib import vcs
from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.model.db import Permission, RepoGroup, Repository, Ui, User, UserRepoToPerm
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.user import UserModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture, error_function


fixture = Fixture()


def _get_permission_for_user(user, repo):
    perm = UserRepoToPerm.query() \
                .filter(UserRepoToPerm.repository ==
                        Repository.get_by_repo_name(repo)) \
                .filter(UserRepoToPerm.user == User.get_by_username(user)) \
                .all()
    return perm


class _BaseTestCase(TestController):
    """
    Write all tests here
    """
    REPO = None
    REPO_TYPE = None
    NEW_REPO = None
    OTHER_TYPE_REPO = None
    OTHER_TYPE = None

    def test_index(self):
        self.log_user()
        response = self.app.get(url('repos'))

    def test_create(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        assert response.json == {u'result': True}
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name, repo_name))

        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name).one()

        assert new_repo.repo_name == repo_name
        assert new_repo.description == description

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name)))
        except vcs.exceptions.VCSError:
            pytest.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name)
        Session().commit()

    def test_case_insensitivity(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                                 fixture._get_repo_create_params(repo_private=False,
                                                                 repo_name=repo_name,
                                                                 repo_type=self.REPO_TYPE,
                                                                 repo_description=description,
                                                                 _session_csrf_secret_token=self.session_csrf_secret_token()))
        # try to create repo with swapped case
        swapped_repo_name = repo_name.swapcase()
        response = self.app.post(url('repos'),
                                 fixture._get_repo_create_params(repo_private=False,
                                                                 repo_name=swapped_repo_name,
                                                                 repo_type=self.REPO_TYPE,
                                                                 repo_description=description,
                                                                 _session_csrf_secret_token=self.session_csrf_secret_token()))
        response.mustcontain('already exists')

        RepoModel().delete(repo_name)
        Session().commit()

    def test_create_in_group(self):
        self.log_user()

        ## create GROUP
        group_name = u'sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description=u'test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        Session().commit()

        repo_name = u'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        assert response.json == {u'result': True}
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        assert new_repo.repo_name == repo_name_full
        assert new_repo.description == description

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        inherited_perms = UserRepoToPerm.query() \
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        assert len(inherited_perms) == 1

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name_full)))
        except vcs.exceptions.VCSError:
            RepoGroupModel().delete(group_name)
            Session().commit()
            pytest.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        Session().commit()

    def test_create_in_group_without_needed_permissions(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        # avoid spurious RepoGroup DetachedInstanceError ...
        session_csrf_secret_token = self.session_csrf_secret_token()
        # revoke
        user_model = UserModel()
        # disable fork and create on default user
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.create.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.create.none')
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.fork.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.fork.none')

        # disable on regular user
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.none')
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.none')
        Session().commit()

        ## create GROUP
        group_name = u'reg_sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description=u'test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        Session().commit()

        group_name_allowed = u'reg_sometest_allowed_%s' % self.REPO_TYPE
        gr_allowed = RepoGroupModel().create(group_name=group_name_allowed,
                                     group_description=u'test',
                                     owner=TEST_USER_REGULAR_LOGIN)
        Session().commit()

        repo_name = u'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,
                                                _session_csrf_secret_token=session_csrf_secret_token))

        response.mustcontain('Invalid value')

        # user is allowed to create in this group
        repo_name = u'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name_allowed, repo_name])
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr_allowed.group_id,
                                                _session_csrf_secret_token=session_csrf_secret_token))

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        assert response.json == {u'result': True}
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        assert new_repo.repo_name == repo_name_full
        assert new_repo.description == description

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        inherited_perms = UserRepoToPerm.query() \
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        assert len(inherited_perms) == 1

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name_full)))
        except vcs.exceptions.VCSError:
            RepoGroupModel().delete(group_name)
            Session().commit()
            pytest.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        RepoGroupModel().delete(group_name_allowed)
        Session().commit()

    def test_create_in_group_inherit_permissions(self):
        self.log_user()

        ## create GROUP
        group_name = u'sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description=u'test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        perm = Permission.get_by_key('repository.write')
        RepoGroupModel().grant_user_permission(gr, TEST_USER_REGULAR_LOGIN, perm)

        ## add repo permissions
        Session().commit()

        repo_name = u'ingroup_inherited_%s' % self.REPO_TYPE
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,
                                                repo_copy_permissions=True,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        assert new_repo.repo_name == repo_name_full
        assert new_repo.description == description

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name_full)))
        except vcs.exceptions.VCSError:
            RepoGroupModel().delete(group_name)
            Session().commit()
            pytest.fail('no repo %s in filesystem' % repo_name)

        # check if inherited permissiona are applied
        inherited_perms = UserRepoToPerm.query() \
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        assert len(inherited_perms) == 2

        assert TEST_USER_REGULAR_LOGIN in [x.user.username
                                                    for x in inherited_perms]
        assert 'repository.write' in [x.permission.permission_name
                                               for x in inherited_perms]

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        Session().commit()

    def test_create_remote_repo_wrong_clone_uri(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                clone_uri='http://127.0.0.1/repo',
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        response.mustcontain('Invalid repository URL')

    def test_create_remote_repo_wrong_clone_uri_hg_svn(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                clone_uri='svn+http://127.0.0.1/repo',
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        response.mustcontain('Invalid repository URL')

    def test_delete(self):
        self.log_user()
        repo_name = u'vcs_test_new_to_delete_%s' % self.REPO_TYPE
        description = u'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_type=self.REPO_TYPE,
                                                repo_name=repo_name,
                                                repo_description=description,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name, repo_name))
        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name).one()

        assert new_repo.repo_name == repo_name
        assert new_repo.description == description

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name)))
        except vcs.exceptions.VCSError:
            pytest.fail('no repo %s in filesystem' % repo_name)

        response = self.app.post(url('delete_repo', repo_name=repo_name),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

        self.checkSessionFlash(response, 'Deleted repository %s' % (repo_name))

        response.follow()

        # check if repo was deleted from db
        deleted_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name).scalar()

        assert deleted_repo is None

        assert os.path.isdir(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name)) == False

    def test_delete_non_ascii(self):
        self.log_user()
        non_ascii = "ąęł"
        repo_name = "%s%s" % (safe_str(self.NEW_REPO), non_ascii)
        repo_name_unicode = safe_unicode(repo_name)
        description = 'description for newly created repo' + non_ascii
        description_unicode = safe_unicode(description)
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        assert response.json == {u'result': True}
        self.checkSessionFlash(response,
                               u'Created repository <a href="/%s">%s</a>'
                               % (urllib.quote(repo_name), repo_name_unicode))
        # test if the repo was created in the database
        new_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name_unicode).one()

        assert new_repo.repo_name == repo_name_unicode
        assert new_repo.description == description_unicode

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(safe_str(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name_unicode)))
        except vcs.exceptions.VCSError:
            pytest.fail('no repo %s in filesystem' % repo_name)

        response = self.app.post(url('delete_repo', repo_name=repo_name),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Deleted repository %s' % (repo_name_unicode))
        response.follow()

        # check if repo was deleted from db
        deleted_repo = Session().query(Repository) \
            .filter(Repository.repo_name == repo_name_unicode).scalar()

        assert deleted_repo is None

        assert os.path.isdir(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name_unicode)) == False

    def test_delete_repo_with_group(self):
        # TODO:
        pass

    def test_delete_browser_fakeout(self):
        response = self.app.post(url('delete_repo', repo_name=self.REPO),
                                 params=dict(_session_csrf_secret_token=self.session_csrf_secret_token()))

    def test_show(self):
        self.log_user()
        response = self.app.get(url('summary_home', repo_name=self.REPO))

    def test_edit(self):
        response = self.app.get(url('edit_repo', repo_name=self.REPO))

    def test_set_private_flag_sets_default_to_none(self):
        self.log_user()
        # initially repository perm should be read
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        assert len(perm), 1
        assert perm[0].permission.permission_name == 'repository.read'
        assert Repository.get_by_repo_name(self.REPO).private == False

        response = self.app.post(url('update_repo', repo_name=self.REPO),
                        fixture._get_repo_create_params(repo_private=1,
                                                repo_name=self.REPO,
                                                repo_type=self.REPO_TYPE,
                                                owner=TEST_USER_ADMIN_LOGIN,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        self.checkSessionFlash(response,
                               msg='Repository %s updated successfully' % (self.REPO))
        assert Repository.get_by_repo_name(self.REPO).private == True

        # now the repo default permission should be None
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        assert len(perm), 1
        assert perm[0].permission.permission_name == 'repository.none'

        response = self.app.post(url('update_repo', repo_name=self.REPO),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=self.REPO,
                                                repo_type=self.REPO_TYPE,
                                                owner=TEST_USER_ADMIN_LOGIN,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))
        self.checkSessionFlash(response,
                               msg='Repository %s updated successfully' % (self.REPO))
        assert Repository.get_by_repo_name(self.REPO).private == False

        # we turn off private now the repo default permission should stay None
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        assert len(perm), 1
        assert perm[0].permission.permission_name == 'repository.none'

        # update this permission back
        perm[0].permission = Permission.get_by_key('repository.read')
        Session().commit()

    def test_set_repo_fork_has_no_self_id(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        response = self.app.get(url('edit_repo_advanced', repo_name=self.REPO))
        opt = """<option value="%s">%s</option>""" % (repo.repo_id, self.REPO)
        response.mustcontain(no=[opt])

    def test_set_fork_of_other_repo(self):
        self.log_user()
        other_repo = u'other_%s' % self.REPO_TYPE
        fixture.create_repo(other_repo, repo_type=self.REPO_TYPE)
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(other_repo)
        response = self.app.post(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo2.repo_id, _session_csrf_secret_token=self.session_csrf_secret_token()))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(other_repo)
        self.checkSessionFlash(response,
            'Marked repository %s as fork of %s' % (repo.repo_name, repo2.repo_name))

        assert repo.fork == repo2
        response = response.follow()
        # check if given repo is selected

        opt = """<option value="%s" selected="selected">%s</option>""" % (
                    repo2.repo_id, repo2.repo_name)
        response.mustcontain(opt)

        fixture.destroy_repo(other_repo, forks='detach')

    def test_set_fork_of_other_type_repo(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        response = self.app.post(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo2.repo_id, _session_csrf_secret_token=self.session_csrf_secret_token()))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        self.checkSessionFlash(response,
            'Cannot set repository as fork of repository with other type')

    def test_set_fork_of_none(self):
        self.log_user()
        ## mark it as None
        response = self.app.post(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=None, _session_csrf_secret_token=self.session_csrf_secret_token()))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        self.checkSessionFlash(response,
                               'Marked repository %s as fork of %s'
                               % (repo.repo_name, "Nothing"))
        assert repo.fork is None

    def test_set_fork_of_same_repo(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        response = self.app.post(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo.repo_id, _session_csrf_secret_token=self.session_csrf_secret_token()))
        self.checkSessionFlash(response,
                               'An error occurred during this operation')

    def test_create_on_top_level_without_permissions(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        # revoke
        user_model = UserModel()
        # disable fork and create on default user
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.create.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.create.none')
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.fork.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.fork.none')

        # disable on regular user
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.none')
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.none')
        Session().commit()


        user = User.get(usr['user_id'])

        repo_name = self.NEW_REPO + u'no_perms'
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))

        response.mustcontain('<span class="error-message">Invalid value</span>')

        RepoModel().delete(repo_name)
        Session().commit()

    @mock.patch.object(RepoModel, '_create_filesystem_repo', error_function)
    def test_create_repo_when_filesystem_op_fails(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = 'description for newly created repo'

        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                _session_csrf_secret_token=self.session_csrf_secret_token()))

        self.checkSessionFlash(response,
                               'Error creating repository %s' % repo_name)
        # repo must not be in db
        repo = Repository.get_by_repo_name(repo_name)
        assert repo is None

        # repo must not be in filesystem !
        assert not os.path.isdir(os.path.join(Ui.get_by_key('paths', '/').ui_value, repo_name))


class TestAdminReposControllerGIT(_BaseTestCase):
    REPO = GIT_REPO
    REPO_TYPE = 'git'
    NEW_REPO = NEW_GIT_REPO
    OTHER_TYPE_REPO = HG_REPO
    OTHER_TYPE = 'hg'


class TestAdminReposControllerHG(_BaseTestCase):
    REPO = HG_REPO
    REPO_TYPE = 'hg'
    NEW_REPO = NEW_HG_REPO
    OTHER_TYPE_REPO = GIT_REPO
    OTHER_TYPE = 'git'

    def test_permanent_url_protocol_access(self):
        repo = Repository.get_by_repo_name(self.REPO)
        permanent_name = '_%d' % repo.repo_id

        # 400 Bad Request - Unable to detect pull/push action
        self.app.get(url('summary_home', repo_name=permanent_name),
            extra_environ={'HTTP_ACCEPT': 'application/mercurial'},
            status=400,
        )
