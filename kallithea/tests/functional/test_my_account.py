# -*- coding: utf-8 -*-

from tg.util.webtest import test_context

from kallithea.lib import helpers as h
from kallithea.model.db import Repository, User, UserApiKeys, UserFollowing, UserSshKeys
from kallithea.model.meta import Session
from kallithea.model.user import UserModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class TestMyAccountController(TestController):
    test_user_1 = 'testme'

    @classmethod
    def teardown_class(cls):
        if User.get_by_username(cls.test_user_1):
            UserModel().delete(cls.test_user_1)
            Session().commit()

    def test_my_account(self):
        self.log_user()
        response = self.app.get(url('my_account'))

        response.mustcontain('value="%s' % TEST_USER_ADMIN_LOGIN)

    def test_my_account_my_repos(self):
        self.log_user()
        response = self.app.get(url('my_account_repos'))
        cnt = Repository.query().filter(Repository.owner ==
                           User.get_by_username(TEST_USER_ADMIN_LOGIN)).count()
        response.mustcontain('"raw_name": "%s"' % HG_REPO)
        response.mustcontain('"just_name": "%s"' % GIT_REPO)

    def test_my_account_my_watched(self):
        self.log_user()
        response = self.app.get(url('my_account_watched'))

        cnt = UserFollowing.query().filter(UserFollowing.user ==
                            User.get_by_username(TEST_USER_ADMIN_LOGIN)).count()
        response.mustcontain('"raw_name": "%s"' % HG_REPO)
        response.mustcontain('"just_name": "%s"' % GIT_REPO)

    def test_my_account_my_emails(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')

    def test_my_account_my_emails_add_existing_email(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')
        response = self.app.post(url('my_account_emails'),
                                 {'new_email': TEST_USER_REGULAR_EMAIL, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'This email address is already in use')

    def test_my_account_my_emails_add_missing_email_in_form(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')
        response = self.app.post(url('my_account_emails'),
            {'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Please enter an email address')

    def test_my_account_my_emails_add_remove(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')

        response = self.app.post(url('my_account_emails'),
                                 {'new_email': 'barz@example.com', '_session_csrf_secret_token': self.session_csrf_secret_token()})

        response = self.app.get(url('my_account_emails'))

        from kallithea.model.db import UserEmailMap
        email_id = UserEmailMap.query() \
            .filter(UserEmailMap.user == User.get_by_username(TEST_USER_ADMIN_LOGIN)) \
            .filter(UserEmailMap.email == 'barz@example.com').one().email_id

        response.mustcontain('barz@example.com')
        response.mustcontain('<input id="del_email_id" name="del_email_id" type="hidden" value="%s" />' % email_id)

        response = self.app.post(url('my_account_emails_delete'),
                                 {'del_email_id': email_id, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Removed email from user')
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')


    @parametrize('name,attrs',
        [('firstname', {'firstname': 'new_username'}),
         ('lastname', {'lastname': 'new_username'}),
         ('admin', {'admin': True}),
         ('admin', {'admin': False}),
         ('extern_type', {'extern_type': 'ldap'}),
         ('extern_type', {'extern_type': None}),
         #('extern_name', {'extern_name': 'test'}),
         #('extern_name', {'extern_name': None}),
         ('active', {'active': False}),
         ('active', {'active': True}),
         ('email', {'email': 'someemail@example.com'}),
        # ('new_password', {'new_password': 'foobar123',
        #                   'password_confirmation': 'foobar123'})
        ])
    def test_my_account_update(self, name, attrs):
        usr = fixture.create_user(self.test_user_1, password='qweqwe',
                                  email='testme@example.com',
                                  extern_type='internal',
                                  extern_name=self.test_user_1,
                                  skip_if_exists=True)
        params = usr.get_api_data(True)  # current user data
        user_id = usr.user_id
        self.log_user(username=self.test_user_1, password='qweqwe')

        params.update({'password_confirmation': ''})
        params.update({'new_password': ''})
        params.update({'extern_type': 'internal'})
        params.update({'extern_name': self.test_user_1})
        params.update({'_session_csrf_secret_token': self.session_csrf_secret_token()})

        params.update(attrs)
        response = self.app.post(url('my_account'), params)

        self.checkSessionFlash(response,
                               'Your account was updated successfully')

        updated_user = User.get_by_username(self.test_user_1)
        updated_params = updated_user.get_api_data(True)
        updated_params.update({'password_confirmation': ''})
        updated_params.update({'new_password': ''})

        params['last_login'] = updated_params['last_login']
        if name == 'email':
            params['emails'] = [attrs['email']]
        if name == 'extern_type':
            # cannot update this via form, expected value is original one
            params['extern_type'] = "internal"
        if name == 'extern_name':
            # cannot update this via form, expected value is original one
            params['extern_name'] = str(user_id)
        if name == 'active':
            # my account cannot deactivate account
            params['active'] = True
        if name == 'admin':
            # my account cannot make you an admin !
            params['admin'] = False

        params.pop('_session_csrf_secret_token')
        assert params == updated_params

    def test_my_account_update_err_email_exists(self):
        self.log_user()

        new_email = TEST_USER_REGULAR_EMAIL  # already existing email
        response = self.app.post(url('my_account'),
                                params=dict(
                                    username=TEST_USER_ADMIN_LOGIN,
                                    new_password=TEST_USER_ADMIN_PASS,
                                    password_confirmation='test122',
                                    firstname=u'NewName',
                                    lastname=u'NewLastname',
                                    email=new_email,
                                    _session_csrf_secret_token=self.session_csrf_secret_token())
                                )

        response.mustcontain('This email address is already in use')

    def test_my_account_update_err(self):
        self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)

        new_email = 'newmail.pl'
        response = self.app.post(url('my_account'),
                                 params=dict(
                                            username=TEST_USER_ADMIN_LOGIN,
                                            new_password=TEST_USER_ADMIN_PASS,
                                            password_confirmation='test122',
                                            firstname=u'NewName',
                                            lastname=u'NewLastname',
                                            email=new_email,
                                            _session_csrf_secret_token=self.session_csrf_secret_token()))

        response.mustcontain('An email address must contain a single @')
        from kallithea.model import validators
        with test_context(self.app):
            msg = validators.ValidUsername(edit=False, old_data={}) \
                    ._messages['username_exists']
        msg = h.html_escape(msg % {'username': TEST_USER_ADMIN_LOGIN})
        response.mustcontain(msg)

    def test_my_account_api_keys(self):
        usr = self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        user = User.get(usr['user_id'])
        response = self.app.get(url('my_account_api_keys'))
        response.mustcontain(user.api_key)
        response.mustcontain('Expires: Never')

    @parametrize('desc,lifetime', [
        ('forever', -1),
        ('5mins', 60*5),
        ('30days', 60*60*24*30),
    ])
    def test_my_account_add_api_keys(self, desc, lifetime):
        usr = self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        user = User.get(usr['user_id'])
        response = self.app.post(url('my_account_api_keys'),
                                 {'description': desc, 'lifetime': lifetime, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully created')
        try:
            response = response.follow()
            user = User.get(usr['user_id'])
            for api_key in user.api_keys:
                response.mustcontain(api_key)
        finally:
            for api_key in UserApiKeys.query().all():
                Session().delete(api_key)
                Session().commit()

    def test_my_account_remove_api_key(self):
        usr = self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        user = User.get(usr['user_id'])
        response = self.app.post(url('my_account_api_keys'),
                                 {'description': 'desc', 'lifetime': -1, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully created')
        response = response.follow()

        # now delete our key
        keys = UserApiKeys.query().all()
        assert 1 == len(keys)

        response = self.app.post(url('my_account_api_keys_delete'),
                 {'del_api_key': keys[0].api_key, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully deleted')
        keys = UserApiKeys.query().all()
        assert 0 == len(keys)

    def test_my_account_reset_main_api_key(self):
        usr = self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        user = User.get(usr['user_id'])
        api_key = user.api_key
        response = self.app.get(url('my_account_api_keys'))
        response.mustcontain(api_key)
        response.mustcontain('Expires: Never')

        response = self.app.post(url('my_account_api_keys_delete'),
                 {'del_api_key_builtin': api_key, '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'API key successfully reset')
        response = response.follow()
        response.mustcontain(no=[api_key])

    def test_my_account_add_ssh_key(self):
        description = u'something'
        public_key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== me@localhost'
        fingerprint = u'Ke3oUCNJM87P0jJTb3D+e3shjceP2CqMpQKVd75E9I8'

        self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        response = self.app.post(url('my_account_ssh_keys'),
                                 {'description': description,
                                  'public_key': public_key,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key %s successfully added' % fingerprint)

        response = response.follow()
        response.mustcontain(fingerprint)
        user_id = response.session['authuser']['user_id']
        ssh_key = UserSshKeys.query().filter(UserSshKeys.user_id == user_id).one()
        assert ssh_key.fingerprint == fingerprint
        assert ssh_key.description == description
        Session().delete(ssh_key)
        Session().commit()

    def test_my_account_remove_ssh_key(self):
        description = u''
        public_key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== me@localhost'
        fingerprint = u'Ke3oUCNJM87P0jJTb3D+e3shjceP2CqMpQKVd75E9I8'

        self.log_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS)
        response = self.app.post(url('my_account_ssh_keys'),
                                 {'description': description,
                                  'public_key': public_key,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key %s successfully added' % fingerprint)
        response.follow()
        user_id = response.session['authuser']['user_id']
        ssh_key = UserSshKeys.query().filter(UserSshKeys.user_id == user_id).one()
        assert ssh_key.description == u'me@localhost'

        response = self.app.post(url('my_account_ssh_keys_delete'),
                                 {'del_public_key_fingerprint': ssh_key.fingerprint,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'SSH key successfully deleted')
        keys = UserSshKeys.query().all()
        assert 0 == len(keys)
