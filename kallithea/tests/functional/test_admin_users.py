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

import pytest
from sqlalchemy.orm.exc import NoResultFound
from tg.util.webtest import test_context
from webob.exc import HTTPNotFound

from kallithea.controllers.admin.users import UsersController
from kallithea.lib import helpers as h
from kallithea.lib.auth import check_password
from kallithea.model import validators
from kallithea.model.db import Permission, RepoGroup, User, UserApiKeys, UserSshKeys
from kallithea.model.meta import Session
from kallithea.model.user import UserModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


@pytest.fixture
def user_and_repo_group_fail():
    username = 'repogrouperr'
    groupname = u'repogroup_fail'
    user = fixture.create_user(name=username)
    repo_group = fixture.create_repo_group(name=groupname, cur_user=username)
    yield user, repo_group
    # cleanup
    if RepoGroup.get_by_group_name(groupname):
        fixture.destroy_repo_group(repo_group)


class TestAdminUsersController(TestController):
    test_user_1 = 'testme'

    @classmethod
    def teardown_class(cls):
        if User.get_by_username(cls.test_user_1):
            UserModel().delete(cls.test_user_1)
            Session().commit()

    def test_index(self):
        self.log_user()
        response = self.app.get(url('users'))
        # TODO: Test response...

    def test_create(self):
        self.log_user()
        username = 'newtestuser'
        password = 'test12'
        password_confirmation = password
        name = u'name'
        lastname = u'lastname'
        email = 'mail@example.com'

        response = self.app.post(url('new_user'),
            {'username': username,
             'password': password,
             'password_confirmation': password_confirmation,
             'firstname': name,
             'active': True,
             'lastname': lastname,
             'extern_name': 'internal',
             'extern_type': 'internal',
             'email': email,
             '_session_csrf_secret_token': self.session_csrf_secret_token()})
        # 302 Found
        # The resource was found at http://localhost/_admin/users/5/edit; you should be redirected automatically.

        self.checkSessionFlash(response, '''Created user %s''' % username)

        response = response.follow()
        response.mustcontain("""%s user settings""" % username) # in <title>

        new_user = Session().query(User). \
            filter(User.username == username).one()

        assert new_user.username == username
        assert check_password(password, new_user.password) == True
        assert new_user.name == name
        assert new_user.lastname == lastname
        assert new_user.email == email

    def test_create_err(self):
        self.log_user()
        username = 'new_user'
        password = ''
        name = u'name'
        lastname = u'lastname'
        email = 'errmail.example.com'

        response = self.app.post(url('new_user'),
            {'username': username,
             'password': password,
             'name': name,
             'active': False,
             'lastname': lastname,
             'email': email,
             '_session_csrf_secret_token': self.session_csrf_secret_token()})

        with test_context(self.app):
            msg = validators.ValidUsername(False, {})._messages['system_invalid_username']
        msg = h.html_escape(msg % {'username': 'new_user'})
        response.mustcontain("""<span class="error-message">%s</span>""" % msg)
        response.mustcontain("""<span class="error-message">Please enter a value</span>""")
        response.mustcontain("""<span class="error-message">An email address must contain a single @</span>""")

        def get_user():
            Session().query(User).filter(User.username == username).one()

        with pytest.raises(NoResultFound):
            get_user(), 'found user in database'

    def test_new(self):
        self.log_user()
        response = self.app.get(url('new_user'))

    @parametrize('name,attrs',
        [('firstname', {'firstname': 'new_username'}),
         ('lastname', {'lastname': 'new_username'}),
         ('admin', {'admin': True}),
         ('admin', {'admin': False}),
         ('extern_type', {'extern_type': 'ldap'}),
         ('extern_type', {'extern_type': None}),
         ('extern_name', {'extern_name': 'test'}),
         ('extern_name', {'extern_name': None}),
         ('active', {'active': False}),
         ('active', {'active': True}),
         ('email', {'email': 'someemail@example.com'}),
        # ('new_password', {'new_password': 'foobar123',
        #                   'password_confirmation': 'foobar123'})
        ])
    def test_update(self, name, attrs):
        self.log_user()
        usr = fixture.create_user(self.test_user_1, password='qweqwe',
                                  email='testme@example.com',
                                  extern_type='internal',
                                  extern_name=self.test_user_1,
                                  skip_if_exists=True)
        Session().commit()
        params = usr.get_api_data(True)
        params.update({'password_confirmation': ''})
        params.update({'new_password': ''})
        params.update(attrs)
        if name == 'email':
            params['emails'] = [attrs['email']]
        if name == 'extern_type':
            # cannot update this via form, expected value is original one
            params['extern_type'] = "internal"
        if name == 'extern_name':
            # cannot update this via form, expected value is original one
            params['extern_name'] = self.test_user_1
            # special case since this user is not logged in yet his data is
            # not filled so we use creation data

        params.update({'_session_csrf_secret_token': self.session_csrf_secret_token()})
        response = self.app.post(url('update_user', id=usr.user_id), params)
        self.checkSessionFlash(response, 'User updated successfully')
        params.pop('_session_csrf_secret_token')

        updated_user = User.get_by_username(self.test_user_1)
        updated_params = updated_user.get_api_data(True)
        updated_params.update({'password_confirmation': ''})
        updated_params.update({'new_password': ''})

        assert params == updated_params

    def test_delete(self):
        self.log_user()
        username = 'newtestuserdeleteme'

        fixture.create_user(name=username)

        new_user = Session().query(User) \
            .filter(User.username == username).one()
        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})

        self.checkSessionFlash(response, 'Successfully deleted user')

    def test_delete_repo_err(self):
        self.log_user()
        username = 'repoerr'
        reponame = u'repoerr_fail'

        fixture.create_user(name=username)
        fixture.create_repo(name=reponame, cur_user=username)

        new_user = Session().query(User) \
            .filter(User.username == username).one()
        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'User "%s" still '
                               'owns 1 repositories and cannot be removed. '
                               'Switch owners or remove those repositories: '
                               '%s' % (username, reponame))

        response = self.app.post(url('delete_repo', repo_name=reponame),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Deleted repository %s' % reponame)

        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Successfully deleted user')

    def test_delete_repo_group_err(self, user_and_repo_group_fail):
        new_user, repo_group = user_and_repo_group_fail
        username = new_user.username
        groupname = repo_group.group_name

        self.log_user()

        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'User "%s" still '
                               'owns 1 repository groups and cannot be removed. '
                               'Switch owners or remove those repository groups: '
                               '%s' % (username, groupname))

        # Relevant _if_ the user deletion succeeded to make sure we can render groups without owner
        # rg = RepoGroup.get_by_group_name(group_name=groupname)
        # response = self.app.get(url('repos_groups', id=rg.group_id))

        response = self.app.post(url('delete_repo_group', group_name=groupname),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Removed repository group %s' % groupname)

        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Successfully deleted user')

    def test_delete_user_group_err(self):
        self.log_user()
        username = 'usergrouperr'
        groupname = u'usergroup_fail'

        fixture.create_user(name=username)
        ug = fixture.create_user_group(name=groupname, cur_user=username)

        new_user = Session().query(User) \
            .filter(User.username == username).one()
        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'User "%s" still '
                               'owns 1 user groups and cannot be removed. '
                               'Switch owners or remove those user groups: '
                               '%s' % (username, groupname))

        # TODO: why do this fail?
        #response = self.app.delete(url('delete_users_group', id=groupname))
        #self.checkSessionFlash(response, 'Removed user group %s' % groupname)

        fixture.destroy_user_group(ug.users_group_id)

        response = self.app.post(url('delete_user', id=new_user.user_id),
            params={'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Successfully deleted user')

    def test_edit(self):
        self.log_user()
        user = User.get_by_username(TEST_USER_ADMIN_LOGIN)
        response = self.app.get(url('edit_user', id=user.user_id))

    def test_add_perm_create_repo(self):
        self.log_user()
        perm_none = Permission.get_by_key('hg.create.none')
        perm_create = Permission.get_by_key('hg.create.repository')

        user = UserModel().create_or_update(username='dummy', password='qwe',
                                            email='dummy', firstname=u'a',
                                            lastname=u'b')
        Session().commit()
        uid = user.user_id

        try:
            # User should have None permission on creation repository
            assert UserModel().has_perm(user, perm_none) == False
            assert UserModel().has_perm(user, perm_create) == False

            response = self.app.post(url('edit_user_perms_update', id=uid),
                                     params=dict(create_repo_perm=True,
                                                 _session_csrf_secret_token=self.session_csrf_secret_token()))

            perm_none = Permission.get_by_key('hg.create.none')
            perm_create = Permission.get_by_key('hg.create.repository')

            # User should have None permission on creation repository
            assert UserModel().has_perm(uid, perm_none) == False
            assert UserModel().has_perm(uid, perm_create) == True
        finally:
            UserModel().delete(uid)
            Session().commit()

    def test_revoke_perm_create_repo(self):
        self.log_user()
        perm_none = Permission.get_by_key('hg.create.none')
        perm_create = Permission.get_by_key('hg.create.repository')

        user = UserModel().create_or_update(username='dummy', password='qwe',
                                            email='dummy', firstname=u'a',
                                            lastname=u'b')
        Session().commit()
        uid = user.user_id

        try:
            # User should have None permission on creation repository
            assert UserModel().has_perm(user, perm_none) == False
            assert UserModel().has_perm(user, perm_create) == False

            response = self.app.post(url('edit_user_perms_update', id=uid),
                                     params=dict(_session_csrf_secret_token=self.session_csrf_secret_token()))

            perm_none = Permission.get_by_key('hg.create.none')
            perm_create = Permission.get_by_key('hg.create.repository')

            # User should have None permission on creation repository
            assert UserModel().has_perm(uid, perm_none) == True
            assert UserModel().has_perm(uid, perm_create) == False
        finally:
            UserModel().delete(uid)
            Session().commit()

    def test_add_perm_fork_repo(self):
        self.log_user()
        perm_none = Permission.get_by_key('hg.fork.none')
        perm_fork = Permission.get_by_key('hg.fork.repository')

        user = UserModel().create_or_update(username='dummy', password='qwe',
                                            email='dummy', firstname=u'a',
                                            lastname=u'b')
        Session().commit()
        uid = user.user_id

        try:
            # User should have None permission on creation repository
            assert UserModel().has_perm(user, perm_none) == False
            assert UserModel().has_perm(user, perm_fork) == False

            response = self.app.post(url('edit_user_perms_update', id=uid),
                                     params=dict(create_repo_perm=True,
                                                 _session_csrf_secret_token=self.session_csrf_secret_token()))

            perm_none = Permission.get_by_key('hg.create.none')
            perm_create = Permission.get_by_key('hg.create.repository')

            # User should have None permission on creation repository
            assert UserModel().has_perm(uid, perm_none) == False
            assert UserModel().has_perm(uid, perm_create) == True
        finally:
            UserModel().delete(uid)
            Session().commit()

    def test_revoke_perm_fork_repo(self):
        self.log_user()
        perm_none = Permission.get_by_key('hg.fork.none')
        perm_fork = Permission.get_by_key('hg.fork.repository')

        user = UserModel().create_or_update(username='dummy', password='qwe',
                                            email='dummy', firstname=u'a',
                                            lastname=u'b')
        Session().commit()
        uid = user.user_id

        try:
            # User should have None permission on creation repository
            assert UserModel().has_perm(user, perm_none) == False
            assert UserModel().has_perm(user, perm_fork) == False

            response = self.app.post(url('edit_user_perms_update', id=uid),
                                     params=dict(_session_csrf_secret_token=self.session_csrf_secret_token()))

            perm_none = Permission.get_by_key('hg.create.none')
            perm_create = Permission.get_by_key('hg.create.repository')

            # User should have None permission on creation repository
            assert UserModel().has_perm(uid, perm_none) == True
            assert UserModel().has_perm(uid, perm_create) == False
        finally:
            UserModel().delete(uid)
            Session().commit()

    def test_ips(self):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        response = self.app.get(url('edit_user_ips', id=user.user_id))
        response.mustcontain('All IP addresses are allowed')

    @parametrize('test_name,ip,ip_range,failure', [
        ('127/24', '127.0.0.1/24', '127.0.0.0 - 127.0.0.255', False),
        ('10/32', '10.0.0.10/32', '10.0.0.10 - 10.0.0.10', False),
        ('0/16', '0.0.0.0/16', '0.0.0.0 - 0.0.255.255', False),
        ('0/8', '0.0.0.0/8', '0.0.0.0 - 0.255.255.255', False),
        ('127_bad_mask', '127.0.0.1/99', '127.0.0.1 - 127.0.0.1', True),
        ('127_bad_ip', 'foobar', 'foobar', True),
    ])
    def test_add_ip(self, test_name, ip, ip_range, failure, auto_clear_ip_permissions):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id

        response = self.app.post(url('edit_user_ips_update', id=user_id),
                                 params=dict(new_ip=ip, _session_csrf_secret_token=self.session_csrf_secret_token()))

        if failure:
            self.checkSessionFlash(response, 'Please enter a valid IPv4 or IPv6 address')
            response = self.app.get(url('edit_user_ips', id=user_id))
            response.mustcontain(no=[ip])
            response.mustcontain(no=[ip_range])

        else:
            response = self.app.get(url('edit_user_ips', id=user_id))
            response.mustcontain(ip)
            response.mustcontain(ip_range)

    def test_delete_ip(self, auto_clear_ip_permissions):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id
        ip = '127.0.0.1/32'
        ip_range = '127.0.0.1 - 127.0.0.1'
        with test_context(self.app):
            new_ip = UserModel().add_extra_ip(user_id, ip)
            Session().commit()
        new_ip_id = new_ip.ip_id

        response = self.app.get(url('edit_user_ips', id=user_id))
        response.mustcontain(ip)
        response.mustcontain(ip_range)

        self.app.post(url('edit_user_ips_delete', id=user_id),
                      params=dict(del_ip_id=new_ip_id, _session_csrf_secret_token=self.session_csrf_secret_token()))

        response = self.app.get(url('edit_user_ips', id=user_id))
        response.mustcontain('All IP addresses are allowed')
        response.mustcontain(no=[ip])
        response.mustcontain(no=[ip_range])

    def test_api_keys(self):
        self.log_user()

        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        response = self.app.get(url('edit_user_api_keys', id=user.user_id))
        response.mustcontain(user.api_key)
        response.mustcontain('Expires: Never')

    @parametrize('desc,lifetime', [
        ('forever', -1),
        ('5mins', 60*5),
        ('30days', 60*60*24*30),
    ])
    def test_add_api_keys(self, desc, lifetime):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id

        response = self.app.post(url('edit_user_api_keys_update', id=user_id),
                 {'description': desc, 'lifetime': lifetime, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully created')
        try:
            response = response.follow()
            user = User.get(user_id)
            for api_key in user.api_keys:
                response.mustcontain(api_key)
        finally:
            for api_key in UserApiKeys.query().filter(UserApiKeys.user_id == user_id).all():
                Session().delete(api_key)
                Session().commit()

    def test_remove_api_key(self):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id

        response = self.app.post(url('edit_user_api_keys_update', id=user_id),
                {'description': 'desc', 'lifetime': -1, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully created')
        response = response.follow()

        # now delete our key
        keys = UserApiKeys.query().filter(UserApiKeys.user_id == user_id).all()
        assert 1 == len(keys)

        response = self.app.post(url('edit_user_api_keys_delete', id=user_id),
                 {'del_api_key': keys[0].api_key, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully deleted')
        keys = UserApiKeys.query().filter(UserApiKeys.user_id == user_id).all()
        assert 0 == len(keys)

    def test_reset_main_api_key(self):
        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id
        api_key = user.api_key
        response = self.app.get(url('edit_user_api_keys', id=user_id))
        response.mustcontain(api_key)
        response.mustcontain('Expires: Never')

        response = self.app.post(url('edit_user_api_keys_delete', id=user_id),
                 {'del_api_key_builtin': api_key, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully reset')
        response = response.follow()
        response.mustcontain(no=[api_key])

    def test_add_ssh_key(self):
        description = u'something'
        public_key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== me@localhost'
        fingerprint = u'Ke3oUCNJM87P0jJTb3D+e3shjceP2CqMpQKVd75E9I8'

        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id

        response = self.app.post(url('edit_user_ssh_keys', id=user_id),
                                 {'description': description,
                                  'public_key': public_key,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key %s successfully added' % fingerprint)

        response = response.follow()
        response.mustcontain(fingerprint)
        ssh_key = UserSshKeys.query().filter(UserSshKeys.user_id == user_id).one()
        assert ssh_key.fingerprint == fingerprint
        assert ssh_key.description == description
        Session().delete(ssh_key)
        Session().commit()

    def test_remove_ssh_key(self):
        description = u''
        public_key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== me@localhost'
        fingerprint = u'Ke3oUCNJM87P0jJTb3D+e3shjceP2CqMpQKVd75E9I8'

        self.log_user()
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        user_id = user.user_id

        response = self.app.post(url('edit_user_ssh_keys', id=user_id),
                                 {'description': description,
                                  'public_key': public_key,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key %s successfully added' % fingerprint)
        response.follow()
        ssh_key = UserSshKeys.query().filter(UserSshKeys.user_id == user_id).one()
        assert ssh_key.description == u'me@localhost'

        response = self.app.post(url('edit_user_ssh_keys_delete', id=user_id),
                                 {'del_public_key_fingerprint': ssh_key.fingerprint,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key successfully deleted')
        keys = UserSshKeys.query().all()
        assert 0 == len(keys)


class TestAdminUsersController_unittest(TestController):
    """ Unit tests for the users controller """

    def test_get_user_or_raise_if_default(self, monkeypatch, test_context_fixture):
        # flash complains about an non-existing session
        def flash_mock(*args, **kwargs):
            pass
        monkeypatch.setattr(h, 'flash', flash_mock)

        u = UsersController()
        # a regular user should work correctly
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        assert u._get_user_or_raise_if_default(user.user_id) == user
        # the default user should raise
        with pytest.raises(HTTPNotFound):
            u._get_user_or_raise_if_default(User.get_default_user().user_id)


class TestAdminUsersControllerForDefaultUser(TestController):
    """
    Edit actions on the default user are not allowed.
    Validate that they throw a 404 exception.
    """
    def test_edit_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user', id=user.user_id), status=404)

    def test_edit_advanced_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user_advanced', id=user.user_id), status=404)

    # API keys
    def test_edit_api_keys_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user_api_keys', id=user.user_id), status=404)

    def test_add_api_keys_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.post(url('edit_user_api_keys_update', id=user.user_id),
                 {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=404)

    def test_delete_api_keys_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.post(url('edit_user_api_keys_delete', id=user.user_id),
                 {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=404)

    # Permissions
    def test_edit_perms_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user_perms', id=user.user_id), status=404)

    def test_update_perms_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.post(url('edit_user_perms_update', id=user.user_id),
                 {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=404)

    # Emails
    def test_edit_emails_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user_emails', id=user.user_id), status=404)

    def test_add_emails_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.post(url('edit_user_emails_update', id=user.user_id),
                 {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=404)

    def test_delete_emails_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.post(url('edit_user_emails_delete', id=user.user_id),
                 {'_session_csrf_secret_token': self.session_csrf_secret_token()}, status=404)

    # IP addresses
    # Add/delete of IP addresses for the default user is used to maintain
    # the global IP whitelist and thus allowed. Only 'edit' is forbidden.
    def test_edit_ip_default_user(self):
        self.log_user()
        user = User.get_default_user()
        response = self.app.get(url('edit_user_ips', id=user.user_id), status=404)
