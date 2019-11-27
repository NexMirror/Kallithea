import uuid

import pytest

from kallithea.lib.auth_modules import auth_ldap, authenticate
from kallithea.model.db import User


@pytest.fixture
def arrange_ldap_auth(set_test_settings):
    set_test_settings(
        ('auth_plugins', 'kallithea.lib.auth_modules.auth_ldap', 'list'),
        ('auth_ldap_enabled', True, 'bool'),
        ('auth_ldap_attr_firstname', 'test_ldap_firstname'),
        ('auth_ldap_attr_lastname', 'test_ldap_lastname'),
        ('auth_ldap_attr_email', 'test_ldap_email'))


class _AuthLdapMock():

    def __init__(self, **kwargs):
        pass

    def authenticate_ldap(self, username, password):
        return 'spam dn', dict(test_ldap_firstname=[u'spam ldap first name'],
                               test_ldap_lastname=[u'spam ldap last name'],
                               test_ldap_email=['spam ldap email'])


def test_update_user_attributes_from_ldap(monkeypatch, create_test_user,
                                          arrange_ldap_auth):
    """Authenticate user with mocked LDAP, verify attributes are updated.
    """

    # Arrange test user.
    uniqifier = uuid.uuid4()
    username = 'test-user-{0}'.format(uniqifier)
    assert User.get_by_username(username) is None
    user_input = dict(username='test-user-{0}'.format(uniqifier),
                      password='spam password',
                      email='spam-email-{0}'.format(uniqifier),
                      firstname=u'spam first name',
                      lastname=u'spam last name',
                      active=True,
                      admin=False)
    user = create_test_user(user_input)

    # Arrange LDAP auth.
    monkeypatch.setattr(auth_ldap, 'AuthLdap', _AuthLdapMock)

    # Authenticate with LDAP.
    user_data = authenticate(username, 'password')

    # Verify that authenication succeeded and retrieved correct attributes
    # from LDAP.
    assert user_data is not None
    assert user_data.get('firstname') == u'spam ldap first name'
    assert user_data.get('lastname') == u'spam ldap last name'
    assert user_data.get('email') == 'spam ldap email'

    # Verify that authentication overwrote user attributes with the ones
    # retrieved from LDAP.
    assert user.firstname == u'spam ldap first name'
    assert user.lastname == u'spam ldap last name'
    assert user.email == 'spam ldap email'


def test_init_user_attributes_from_ldap(monkeypatch, arrange_ldap_auth):
    """Authenticate unknown user with mocked LDAP, verify user is created.
    """

    # Arrange test user.
    uniqifier = uuid.uuid4()
    username = 'test-user-{0}'.format(uniqifier)
    assert User.get_by_username(username) is None

    # Arrange LDAP auth.
    monkeypatch.setattr(auth_ldap, 'AuthLdap', _AuthLdapMock)

    # Authenticate with LDAP.
    user_data = authenticate(username, 'password')

    # Verify that authenication succeeded and retrieved correct attributes
    # from LDAP.
    assert user_data is not None
    assert user_data.get('firstname') == u'spam ldap first name'
    assert user_data.get('lastname') == u'spam ldap last name'
    assert user_data.get('email') == 'spam ldap email'

    # Verify that authentication created new user with attributes
    # retrieved from LDAP.
    new_user = User.get_by_username(username)
    assert new_user is not None
    assert new_user.firstname == u'spam ldap first name'
    assert new_user.lastname == u'spam ldap last name'
    assert new_user.email == 'spam ldap email'


class _AuthLdapNoEmailMock():

    def __init__(self, **kwargs):
        pass

    def authenticate_ldap(self, username, password):
        return 'spam dn', dict(test_ldap_firstname=['spam ldap first name'],
                               test_ldap_lastname=['spam ldap last name'],
                               test_ldap_email=[''])


def test_init_user_attributes_from_ldap_with_missing_email(monkeypatch,
                                                           arrange_ldap_auth):
    """Authenticate unknown user with mocked LDAP where email is missing.
    """

    # Arrange test user.
    uniqifier = uuid.uuid4()
    username = 'test-user-{0}'.format(uniqifier)
    assert User.get_by_username(username) is None

    # Arrange LDAP auth.
    monkeypatch.setattr(auth_ldap, 'AuthLdap', _AuthLdapNoEmailMock)

    # Authenticate with LDAP.
    user_data = authenticate(username, 'password')

    # Verify that authenication succeeded and retrieved correct attributes
    # from LDAP, with empty email.
    assert user_data is not None
    assert user_data.get('firstname') == u'spam ldap first name'
    assert user_data.get('lastname') == u'spam ldap last name'
    assert user_data.get('email') == ''

    # Verify that authentication created new user with attributes
    # retrieved from LDAP, with email == None.
    new_user = User.get_by_username(username)
    assert new_user is not None
    assert new_user.firstname == u'spam ldap first name'
    assert new_user.lastname == u'spam ldap last name'
    assert new_user.email is None
