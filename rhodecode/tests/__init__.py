"""Pylons application test package

This package assumes the Pylons environment is already loaded, such as
when this script is imported from the `nosetests --with-pylons=test.ini`
command.

This module initializes the application via ``websetup`` (`paster
setup-app`) and provides the base testing objects.
"""
from unittest import TestCase

from paste.deploy import loadapp
from paste.script.appinstall import SetupCommand
from pylons import config, url
from routes.util import URLGenerator
from webtest import TestApp
import os
from rhodecode.model import meta
import logging


log = logging.getLogger(__name__)

import pylons.test

__all__ = ['environ', 'url', 'TestController', 'TESTS_TMP_PATH', 'HG_REPO',
           'GIT_REPO', 'NEW_HG_REPO', 'NEW_GIT_REPO', 'HG_FORK', 'GIT_FORK', ]

# Invoke websetup with the current config file
#SetupCommand('setup-app').run([config_file])

##RUNNING DESIRED TESTS
#nosetests -x rhodecode.tests.functional.test_admin_settings:TestSettingsController.test_my_account

environ = {}

#SOME GLOBALS FOR TESTS
TESTS_TMP_PATH = '/tmp'

HG_REPO = 'vcs_test_hg'
GIT_REPO = 'vcs_test_git'

NEW_HG_REPO = 'vcs_test_hg_new'
NEW_GIT_REPO = 'vcs_test_git_new'

HG_FORK = 'vcs_test_hg_fork'
GIT_FORK = 'vcs_test_git_fork'

class TestController(TestCase):

    def __init__(self, *args, **kwargs):
        wsgiapp = pylons.test.pylonsapp
        config = wsgiapp.config

        self.app = TestApp(wsgiapp)
        url._push_object(URLGenerator(config['routes.map'], environ))
        self.sa = meta.Session
        self.index_location = config['app_conf']['index_dir']
        TestCase.__init__(self, *args, **kwargs)

    def log_user(self, username='test_admin', password='test12'):
        response = self.app.post(url(controller='login', action='index'),
                                 {'username':username,
                                  'password':password})
        print response

        if 'invalid user name' in response.body:
            assert False, 'could not login using %s %s' % (username, password)

        assert response.status == '302 Found', 'Wrong response code from login got %s' % response.status
        assert response.session['rhodecode_user'].username == username, 'wrong logged in user got %s expected %s' % (response.session['rhodecode_user'].username, username)
        return response.follow()
