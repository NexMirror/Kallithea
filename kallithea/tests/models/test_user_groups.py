from kallithea.model.db import User, UserGroup
from kallithea.model.meta import Session
from kallithea.model.user_group import UserGroupModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class TestUserGroups(TestController):

    def teardown_method(self, method):
        # delete all groups
        for gr in UserGroup.query():
            fixture.destroy_user_group(gr)
        Session().commit()

    @parametrize('pre_existing,regular_should_be,external_should_be,groups,expected', [
        ([], [], [], [], []),
        ([], [u'regular'], [], [], [u'regular']),  # no changes of regular
        ([u'some_other'], [], [], [u'some_other'], []),   # not added to regular group
        ([], [u'regular'], [u'container'], [u'container'], [u'regular', u'container']),
        ([], [u'regular'], [], [u'container', u'container2'], [u'regular', u'container', u'container2']),
        ([], [u'regular'], [u'other'], [], [u'regular']),  # remove not used
        ([u'some_other'], [u'regular'], [u'other', u'container'], [u'container', u'container2'], [u'regular', u'container', u'container2']),
    ])
    def test_enforce_groups(self, pre_existing, regular_should_be,
                            external_should_be, groups, expected):
        # delete all groups
        for gr in UserGroup.query():
            fixture.destroy_user_group(gr)
        Session().commit()

        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        for gr in pre_existing:
            gr = fixture.create_user_group(gr)
        Session().commit()

        # make sure use is just in those groups
        for gr in regular_should_be:
            gr = fixture.create_user_group(gr)
            Session().commit()
            UserGroupModel().add_user_to_group(gr, user)
            Session().commit()

        # now special external groups created by auth plugins
        for gr in external_should_be:
            gr = fixture.create_user_group(gr, user_group_data={'extern_type': 'container'})
            Session().commit()
            UserGroupModel().add_user_to_group(gr, user)
            Session().commit()

        UserGroupModel().enforce_groups(user, groups, 'container')
        Session().commit()

        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        in_groups = user.group_member
        assert expected == [x.users_group.users_group_name for x in in_groups]
