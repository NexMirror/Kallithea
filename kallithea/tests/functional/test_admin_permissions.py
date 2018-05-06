from kallithea.model.db import User, UserIpMap
from kallithea.tests import *

class TestAdminPermissionsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('admin_permissions'))
        # Test response...

    def test_index_ips(self):
        self.log_user()
        response = self.app.get(url('admin_permissions_ips'))
        # Test response...
        response.mustcontain('All IP addresses are allowed')

    def test_add_ips(self):
        self.log_user()
        default_user_id = User.get_default_user().user_id
        response = self.app.put(url('edit_user_ips', id=default_user_id),
                                 params=dict(new_ip='127.0.0.0/24',
                                 _authentication_token=self.authentication_token()))

        response = self.app.get(url('admin_permissions_ips'))
        response.mustcontain('127.0.0.0/24')
        response.mustcontain('127.0.0.0 - 127.0.0.255')

        ## delete
        default_user_id = User.get_default_user().user_id
        del_ip_id = UserIpMap.query().filter(UserIpMap.user_id ==
                                             default_user_id).first().ip_id

        response = self.app.post(url('edit_user_ips', id=default_user_id),
                                 params=dict(_method='delete',
                                             del_ip_id=del_ip_id,
                                             _authentication_token=self.authentication_token()))

        response = self.app.get(url('admin_permissions_ips'))
        response.mustcontain('All IP addresses are allowed')
        response.mustcontain(no=['127.0.0.0/24'])
        response.mustcontain(no=['127.0.0.0 - 127.0.0.255'])


    def test_index_overview(self):
        self.log_user()
        response = self.app.get(url('admin_permissions_perms'))
        # Test response...

    def test_edit_permissions_permissions(self):
        user = User.get_by_username(TEST_USER_REGULAR_LOGIN)

        # Test unauthenticated access - it will redirect to login page
        response = self.app.post(
            url('edit_repo_perms_update', repo_name=HG_REPO),
            params=dict(
                _method='put',
                perm_new_member_1='repository.read',
                perm_new_member_name_1=user.username,
                perm_new_member_type_1='user',
                _authentication_token=self.authentication_token()),
            status=302)

        assert not response.location.endswith(url('edit_repo_perms_update', repo_name=HG_REPO))
        assert response.location.endswith(url('login_home', came_from=url('edit_repo_perms_update', repo_name=HG_REPO)))

        response = self.app.post(
            url('edit_repo_perms_revoke', repo_name=HG_REPO),
            params=dict(
                _method='delete',
                obj_type='user',
                user_id=user.user_id,
                _authentication_token=self.authentication_token()),
            status=302)

        assert response.location.endswith(url('login_home', came_from=url('edit_repo_perms_update', repo_name=HG_REPO)))

        # Test authenticated access
        self.log_user()

        response = self.app.post(
            url('edit_repo_perms_update', repo_name=HG_REPO),
            params=dict(
                _method='put',
                perm_new_member_1='repository.read',
                perm_new_member_name_1=user.username,
                perm_new_member_type_1='user',
                _authentication_token=self.authentication_token()),
            status=302)

        assert response.location.endswith(url('edit_repo_perms_update', repo_name=HG_REPO))

        response = self.app.post(
            url('edit_repo_perms_revoke', repo_name=HG_REPO),
            params=dict(
                _method='delete',
                obj_type='user',
                user_id=user.user_id,
                _authentication_token=self.authentication_token()),
            status=200) # success has no content
        assert not response.body
