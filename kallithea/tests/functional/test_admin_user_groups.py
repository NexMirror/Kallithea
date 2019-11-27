# -*- coding: utf-8 -*-
from kallithea.model.db import Permission, UserGroup, UserGroupToPerm
from kallithea.model.meta import Session
from kallithea.tests.base import *


TEST_USER_GROUP = u'admins_test'


class TestAdminUsersGroupsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('users_groups'))
        # Test response...

    def test_create(self):
        self.log_user()
        users_group_name = TEST_USER_GROUP
        response = self.app.post(url('users_groups'),
                                 {'users_group_name': users_group_name,
                                  'user_group_description': u'DESC',
                                  'active': True,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.follow()

        self.checkSessionFlash(response,
                               'Created user group <a href="/_admin/user_groups/')
        self.checkSessionFlash(response,
                               '/edit">%s</a>' % TEST_USER_GROUP)

    def test_new(self):
        response = self.app.get(url('new_users_group'))

    def test_update(self):
        response = self.app.post(url('update_users_group', id=1), status=403)

    def test_update_browser_fakeout(self):
        response = self.app.post(url('update_users_group', id=1),
                                 params=dict(_session_csrf_secret_token=self.session_csrf_secret_token()))

    def test_delete(self):
        self.log_user()
        users_group_name = TEST_USER_GROUP + 'another'
        response = self.app.post(url('users_groups'),
                                 {'users_group_name': users_group_name,
                                  'user_group_description': u'DESC',
                                  'active': True,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.follow()

        self.checkSessionFlash(response,
                               'Created user group ')

        gr = Session().query(UserGroup) \
            .filter(UserGroup.users_group_name == users_group_name).one()

        response = self.app.post(url('delete_users_group', id=gr.users_group_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

        gr = Session().query(UserGroup) \
            .filter(UserGroup.users_group_name == users_group_name).scalar()

        assert gr is None

    def test_default_perms_enable_repository_read_on_group(self):
        self.log_user()
        users_group_name = TEST_USER_GROUP + 'another2'
        response = self.app.post(url('users_groups'),
                                 {'users_group_name': users_group_name,
                                  'user_group_description': u'DESC',
                                  'active': True,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.follow()

        ug = UserGroup.get_by_group_name(users_group_name)
        self.checkSessionFlash(response,
                               'Created user group ')
        ## ENABLE REPO CREATE ON A GROUP
        response = self.app.post(url('edit_user_group_default_perms_update',
                                     id=ug.users_group_id),
                                 {'create_repo_perm': True,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.follow()
        ug = UserGroup.get_by_group_name(users_group_name)
        p = Permission.get_by_key('hg.create.repository')
        p2 = Permission.get_by_key('hg.usergroup.create.false')
        p3 = Permission.get_by_key('hg.fork.none')
        # check if user has this perms, they should be here since
        # defaults are on
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group == ug).all()

        assert sorted([[x.users_group_id, x.permission_id, ] for x in perms]) == sorted([[ug.users_group_id, p.permission_id],
                    [ug.users_group_id, p2.permission_id],
                    [ug.users_group_id, p3.permission_id]])

        ## DISABLE REPO CREATE ON A GROUP
        response = self.app.post(
            url('edit_user_group_default_perms_update', id=ug.users_group_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

        response.follow()
        ug = UserGroup.get_by_group_name(users_group_name)
        p = Permission.get_by_key('hg.create.none')
        p2 = Permission.get_by_key('hg.usergroup.create.false')
        p3 = Permission.get_by_key('hg.fork.none')

        # check if user has this perms, they should be here since
        # defaults are on
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group == ug).all()

        assert sorted([[x.users_group_id, x.permission_id, ] for x in perms]) == sorted([[ug.users_group_id, p.permission_id],
                    [ug.users_group_id, p2.permission_id],
                    [ug.users_group_id, p3.permission_id]])

        # DELETE !
        ug = UserGroup.get_by_group_name(users_group_name)
        ugid = ug.users_group_id
        response = self.app.post(url('delete_users_group', id=ug.users_group_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        response = response.follow()
        gr = Session().query(UserGroup) \
            .filter(UserGroup.users_group_name == users_group_name).scalar()

        assert gr is None
        p = Permission.get_by_key('hg.create.repository')
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group_id == ugid).all()
        perms = [[x.users_group_id,
                  x.permission_id, ] for x in perms]
        assert perms == []

    def test_default_perms_enable_repository_fork_on_group(self):
        self.log_user()
        users_group_name = TEST_USER_GROUP + 'another2'
        response = self.app.post(url('users_groups'),
                                 {'users_group_name': users_group_name,
                                  'user_group_description': u'DESC',
                                  'active': True,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.follow()

        ug = UserGroup.get_by_group_name(users_group_name)
        self.checkSessionFlash(response,
                               'Created user group ')
        ## ENABLE REPO CREATE ON A GROUP
        response = self.app.post(url('edit_user_group_default_perms_update',
                                     id=ug.users_group_id),
                                 {'fork_repo_perm': True, '_session_csrf_secret_token': self.session_csrf_secret_token()})

        response.follow()
        ug = UserGroup.get_by_group_name(users_group_name)
        p = Permission.get_by_key('hg.create.none')
        p2 = Permission.get_by_key('hg.usergroup.create.false')
        p3 = Permission.get_by_key('hg.fork.repository')
        # check if user has this perms, they should be here since
        # defaults are on
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group == ug).all()

        assert sorted([[x.users_group_id, x.permission_id, ] for x in perms]) == sorted([[ug.users_group_id, p.permission_id],
                    [ug.users_group_id, p2.permission_id],
                    [ug.users_group_id, p3.permission_id]])

        ## DISABLE REPO CREATE ON A GROUP
        response = self.app.post(url('edit_user_group_default_perms_update', id=ug.users_group_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

        response.follow()
        ug = UserGroup.get_by_group_name(users_group_name)
        p = Permission.get_by_key('hg.create.none')
        p2 = Permission.get_by_key('hg.usergroup.create.false')
        p3 = Permission.get_by_key('hg.fork.none')
        # check if user has this perms, they should be here since
        # defaults are on
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group == ug).all()

        assert sorted([[x.users_group_id, x.permission_id, ] for x in perms]) == sorted([[ug.users_group_id, p.permission_id],
                    [ug.users_group_id, p2.permission_id],
                    [ug.users_group_id, p3.permission_id]])

        # DELETE !
        ug = UserGroup.get_by_group_name(users_group_name)
        ugid = ug.users_group_id
        response = self.app.post(url('delete_users_group', id=ug.users_group_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        response = response.follow()
        gr = Session().query(UserGroup) \
                           .filter(UserGroup.users_group_name ==
                                   users_group_name).scalar()

        assert gr is None
        p = Permission.get_by_key('hg.fork.repository')
        perms = UserGroupToPerm.query() \
            .filter(UserGroupToPerm.users_group_id == ugid).all()
        perms = [[x.users_group_id,
                  x.permission_id, ] for x in perms]
        assert perms == []

    def test_delete_browser_fakeout(self):
        response = self.app.post(url('delete_users_group', id=1),
                                 params=dict(_session_csrf_secret_token=self.session_csrf_secret_token()))
