from kallithea.tests.base import *
from kallithea.model.db import Setting


class TestDefaultsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('defaults'))
        response.mustcontain('default_repo_private')
        response.mustcontain('default_repo_enable_statistics')
        response.mustcontain('default_repo_enable_downloads')
        response.mustcontain('default_repo_enable_locking')

    def test_update_params_true_hg(self):
        self.log_user()
        params = {
            'default_repo_enable_locking': True,
            'default_repo_enable_downloads': True,
            'default_repo_enable_statistics': True,
            'default_repo_private': True,
            'default_repo_type': 'hg',
            '_authentication_token': self.authentication_token(),
        }
        response = self.app.post(url('defaults_update', id='default'), params=params)
        self.checkSessionFlash(response, 'Default settings updated successfully')

        params.pop('_authentication_token')
        defs = Setting.get_default_repo_settings()
        assert params == defs

    def test_update_params_false_git(self):
        self.log_user()
        params = {
            'default_repo_enable_locking': False,
            'default_repo_enable_downloads': False,
            'default_repo_enable_statistics': False,
            'default_repo_private': False,
            'default_repo_type': 'git',
            '_authentication_token': self.authentication_token(),
        }
        response = self.app.post(url('defaults_update', id='default'), params=params)
        self.checkSessionFlash(response, 'Default settings updated successfully')

        params.pop('_authentication_token')
        defs = Setting.get_default_repo_settings()
        assert params == defs
