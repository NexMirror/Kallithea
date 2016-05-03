from kallithea.tests import *

from kallithea.model.db import User, UserGroup, UserGroupMember, UserEmailMap, \
    Permission
from kallithea.model.user import UserModel

from kallithea.model.meta import Session
from kallithea.model.user_group import UserGroupModel
from kallithea.tests.fixture import Fixture

fixture = Fixture()


class TestUser(TestControllerPytest):

    @classmethod
    def setup_class(cls):
        Session.remove()

    def teardown_method(self, method):
        Session.remove()

    def test_create_and_remove(self):
        usr = UserModel().create_or_update(username=u'test_user',
                                           password=u'qweqwe',
                                           email=u'u232@example.com',
                                           firstname=u'u1', lastname=u'u1')
        Session().commit()
        self.assertEqual(User.get_by_username(u'test_user'), usr)
        self.assertEqual(User.get_by_username(u'test_USER', case_insensitive=True), usr)
        self.assertEqual(User.get_by_username(u'test_USER', case_insensitive=False), None)

        # make user group
        user_group = fixture.create_user_group(u'some_example_group')
        Session().commit()

        UserGroupModel().add_user_to_group(user_group, usr)
        Session().commit()

        self.assertEqual(UserGroup.get(user_group.users_group_id), user_group)
        self.assertEqual(UserGroupMember.query().count(), 1)
        UserModel().delete(usr.user_id)
        Session().commit()

        self.assertEqual(UserGroupMember.query().all(), [])

    def test_additional_email_as_main(self):
        usr = UserModel().create_or_update(username=u'test_user',
                                           password=u'qweqwe',
                                     email=u'main_email@example.com',
                                     firstname=u'u1', lastname=u'u1')
        Session().commit()

        def do():
            m = UserEmailMap()
            m.email = u'main_email@example.com'
            m.user = usr
            Session().add(m)
            Session().commit()
        self.assertRaises(AttributeError, do)

        UserModel().delete(usr.user_id)
        Session().commit()

    def test_extra_email_map(self):
        usr = UserModel().create_or_update(username=u'test_user',
                                           password=u'qweqwe',
                                     email=u'main_email@example.com',
                                     firstname=u'u1', lastname=u'u1')
        Session().commit()

        m = UserEmailMap()
        m.email = u'main_email2@example.com'
        m.user = usr
        Session().add(m)
        Session().commit()

        u = User.get_by_email(email='MAIN_email@example.com')
        self.assertEqual(usr.user_id, u.user_id)
        self.assertEqual(usr.username, u.username)

        u = User.get_by_email(email='main_email@example.com')
        self.assertEqual(usr.user_id, u.user_id)
        self.assertEqual(usr.username, u.username)

        u = User.get_by_email(email='main_email2@example.com')
        self.assertEqual(usr.user_id, u.user_id)
        self.assertEqual(usr.username, u.username)
        u = User.get_by_email(email='main_email3@example.com')
        self.assertEqual(None, u)

        u = User.get_by_email(email='main_e%ail@example.com')
        self.assertEqual(None, u)
        u = User.get_by_email(email='main_emai_@example.com')
        self.assertEqual(None, u)


        UserModel().delete(usr.user_id)
        Session().commit()


class TestUsers(TestControllerPytest):

    def setup_method(self, method):
        self.u1 = UserModel().create_or_update(username=u'u1',
                                        password=u'qweqwe',
                                        email=u'u1@example.com',
                                        firstname=u'u1', lastname=u'u1')

    def teardown_method(self, method):
        perm = Permission.query().all()
        for p in perm:
            UserModel().revoke_perm(self.u1, p)

        UserModel().delete(self.u1)
        Session().commit()
        Session.remove()

    def test_add_perm(self):
        perm = Permission.query().all()[0]
        UserModel().grant_perm(self.u1, perm)
        Session().commit()
        self.assertEqual(UserModel().has_perm(self.u1, perm), True)

    def test_has_perm(self):
        perm = Permission.query().all()
        for p in perm:
            has_p = UserModel().has_perm(self.u1, p)
            self.assertEqual(False, has_p)

    def test_revoke_perm(self):
        perm = Permission.query().all()[0]
        UserModel().grant_perm(self.u1, perm)
        Session().commit()
        self.assertEqual(UserModel().has_perm(self.u1, perm), True)

        #revoke
        UserModel().revoke_perm(self.u1, perm)
        Session().commit()
        self.assertEqual(UserModel().has_perm(self.u1, perm), False)
