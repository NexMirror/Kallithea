import time

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
        response = self.app.post(url('edit_user_ips_update', id=default_user_id),
                                 params=dict(new_ip='127.0.0.0/24',
                                 _authentication_token=self.authentication_token()))

        # IP permissions are cached, need to invalidate this cache explicitly
        invalidate_all_caches()

        self.app.get(url('admin_permissions_ips'), status=302)

        # REMOTE_ADDR must match 127.0.0.0/24
        response = self.app.get(url('admin_permissions_ips'),
                                extra_environ={'REMOTE_ADDR': '127.0.0.1'})
        response.mustcontain('127.0.0.0/24')
        response.mustcontain('127.0.0.0 - 127.0.0.255')

        ## delete
        default_user_id = User.get_default_user().user_id
        del_ip_id = UserIpMap.query().filter(UserIpMap.user_id ==
                                             default_user_id).first().ip_id

        response = self.app.post(url('edit_user_ips_delete', id=default_user_id),
                                 params=dict(del_ip_id=del_ip_id,
                                             _authentication_token=self.authentication_token()),
                                 extra_environ={'REMOTE_ADDR': '127.0.0.1'})

        # IP permissions are cached, need to invalidate this cache explicitly
        invalidate_all_caches()

        response = self.app.get(url('admin_permissions_ips'))
        response.mustcontain('All IP addresses are allowed')
        response.mustcontain(no=['127.0.0.0/24'])
        response.mustcontain(no=['127.0.0.0 - 127.0.0.255'])


    def test_index_overview(self):
        self.log_user()
        response = self.app.get(url('admin_permissions_perms'))
        # Test response...
