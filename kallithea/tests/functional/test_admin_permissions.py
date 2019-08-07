from kallithea.model.db import User, UserIpMap
from kallithea.tests.base import *


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

    def test_add_delete_ips(self, auto_clear_ip_permissions):
        self.log_user()
        default_user_id = User.get_default_user().user_id

        # Add IP and verify it is shown in UI and both gives access and rejects

        response = self.app.post(url('edit_user_ips_update', id=default_user_id),
                                 params=dict(new_ip='0.0.0.0/24',
                                 _session_csrf_secret_token=self.session_csrf_secret_token()))
        invalidate_all_caches()
        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '0.0.0.1'})
        response.mustcontain('0.0.0.0/24')
        response.mustcontain('0.0.0.0 - 0.0.0.255')

        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '0.0.1.1'}, status=403)

        # Add another IP and verify previously rejected now works

        response = self.app.post(url('edit_user_ips_update', id=default_user_id),
                                 params=dict(new_ip='0.0.1.0/24',
                                 _session_csrf_secret_token=self.session_csrf_secret_token()))
        invalidate_all_caches()

        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '0.0.1.1'})

        # Delete latest IP and verify same IP is rejected again

        x = UserIpMap.query().filter_by(ip_addr='0.0.1.0/24').first()
        response = self.app.post(url('edit_user_ips_delete', id=default_user_id),
                                 params=dict(del_ip_id=x.ip_id,
                                             _session_csrf_secret_token=self.session_csrf_secret_token()))
        invalidate_all_caches()

        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '0.0.1.1'}, status=403)

        # Delete first IP and verify unlimited access again

        x = UserIpMap.query().filter_by(ip_addr='0.0.0.0/24').first()
        response = self.app.post(url('edit_user_ips_delete', id=default_user_id),
                                 params=dict(del_ip_id=x.ip_id,
                                             _session_csrf_secret_token=self.session_csrf_secret_token()))
        invalidate_all_caches()

        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '0.0.1.1'})

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
                perm_new_member_1='repository.read',
                perm_new_member_name_1=user.username,
                perm_new_member_type_1='user',
                _session_csrf_secret_token=self.session_csrf_secret_token()),
            status=302)

        assert not response.location.endswith(url('edit_repo_perms_update', repo_name=HG_REPO))
        assert response.location.endswith(url('login_home', came_from=url('edit_repo_perms_update', repo_name=HG_REPO)))

        response = self.app.post(
            url('edit_repo_perms_revoke', repo_name=HG_REPO),
            params=dict(
                obj_type='user',
                user_id=user.user_id,
                _session_csrf_secret_token=self.session_csrf_secret_token()),
            status=302)

        assert response.location.endswith(url('login_home', came_from=url('edit_repo_perms_revoke', repo_name=HG_REPO)))

        # Test authenticated access
        self.log_user()

        response = self.app.post(
            url('edit_repo_perms_update', repo_name=HG_REPO),
            params=dict(
                perm_new_member_1='repository.read',
                perm_new_member_name_1=user.username,
                perm_new_member_type_1='user',
                _session_csrf_secret_token=self.session_csrf_secret_token()),
            status=302)

        assert response.location.endswith(url('edit_repo_perms_update', repo_name=HG_REPO))

        response = self.app.post(
            url('edit_repo_perms_revoke', repo_name=HG_REPO),
            params=dict(
                obj_type='user',
                user_id=user.user_id,
                _session_csrf_secret_token=self.session_csrf_secret_token()),
            status=200)
        assert not response.body
