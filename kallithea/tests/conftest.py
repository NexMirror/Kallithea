import logging
import os
import sys
import time

import formencode
import pkg_resources
import pytest
from paste.deploy import loadwsgi
from pytest_localserver.http import WSGIServer
from routes.util import URLGenerator
from tg.util.webtest import test_context

import kallithea.tests.base  # FIXME: needed for setting testapp instance!!!
from kallithea.controllers.root import RootController
from kallithea.lib import inifile
from kallithea.lib.utils import repo2db_mapper
from kallithea.model.db import Setting, User, UserIpMap
from kallithea.model.meta import Session
from kallithea.model.scm import ScmModel
from kallithea.model.user import UserModel
from kallithea.tests.base import TEST_USER_ADMIN_LOGIN, TEST_USER_ADMIN_PASS, TEST_USER_REGULAR_LOGIN, TESTS_TMP_PATH, invalidate_all_caches


def pytest_configure():
    os.environ['TZ'] = 'UTC'
    if not kallithea.is_windows:
        time.tzset() # only available on Unix

    path = os.getcwd()
    sys.path.insert(0, path)
    pkg_resources.working_set.add_entry(path)

    # Disable INFO logging of test database creation, restore with NOTSET
    logging.disable(logging.INFO)

    ini_settings = {
        '[server:main]': {
            'port': '4999',
        },
        '[app:main]': {
            'ssh_enabled': 'true',
            # Mainly to safeguard against accidentally overwriting the real one:
            'ssh_authorized_keys': os.path.join(TESTS_TMP_PATH, 'authorized_keys'),
            #'ssh_locale': 'C',
            'app_instance_uuid': 'test',
            'show_revision_number': 'true',
            'beaker.cache.sql_cache_short.expire': '1',
            'session.secret': '{74e0cd75-b339-478b-b129-07dd221def1f}',
            #'i18n.lang': '',
        },
        '[handler_console]': {
            'formatter': 'color_formatter',
        },
        # The 'handler_console_sql' block is very similar to the one in
        # development.ini, but without the explicit 'level=DEBUG' setting:
        # it causes duplicate sqlalchemy debug logs, one through
        # handler_console_sql and another through another path.
        '[handler_console_sql]': {
            'formatter': 'color_formatter_sql',
        },
    }
    if os.environ.get('TEST_DB'):
        ini_settings['[app:main]']['sqlalchemy.url'] = os.environ.get('TEST_DB')

    test_ini_file = os.path.join(TESTS_TMP_PATH, 'test.ini')
    inifile.create(test_ini_file, None, ini_settings)

    context = loadwsgi.loadcontext(loadwsgi.APP, 'config:%s' % test_ini_file)
    from kallithea.tests.fixture import create_test_env, create_test_index

    # set KALLITHEA_NO_TMP_PATH=1 to disable re-creating the database and test repos
    if not int(os.environ.get('KALLITHEA_NO_TMP_PATH', 0)):
        create_test_env(TESTS_TMP_PATH, context.config())

    # set KALLITHEA_WHOOSH_TEST_DISABLE=1 to disable whoosh index during tests
    if not int(os.environ.get('KALLITHEA_WHOOSH_TEST_DISABLE', 0)):
        create_test_index(TESTS_TMP_PATH, context.config(), True)

    kallithea.tests.base.testapp = context.create()
    # do initial repo scan
    repo2db_mapper(ScmModel().repo_scan(TESTS_TMP_PATH))

    logging.disable(logging.NOTSET)

    kallithea.tests.base.url = URLGenerator(RootController().mapper, {'HTTP_HOST': 'example.com'})

    # set fixed language for form messages, regardless of environment settings
    formencode.api.set_stdtranslation(languages=[])


@pytest.fixture
def create_test_user():
    """Provide users that automatically disappear after test is over."""
    test_user_ids = []

    def _create_test_user(user_form):
        user = UserModel().create(user_form)
        test_user_ids.append(user.user_id)
        return user
    yield _create_test_user
    for user_id in test_user_ids:
        UserModel().delete(user_id)
    Session().commit()


def _set_settings(*kvtseq):
    session = Session()
    for kvt in kvtseq:
        assert len(kvt) in (2, 3)
        k = kvt[0]
        v = kvt[1]
        t = kvt[2] if len(kvt) == 3 else 'unicode'
        Setting.create_or_update(k, v, t)
    session.commit()


@pytest.fixture
def set_test_settings():
    """Restore settings after test is over."""
    # Save settings.
    settings_snapshot = [
        (s.app_settings_name, s.app_settings_value, s.app_settings_type)
        for s in Setting.query().all()]
    yield _set_settings
    # Restore settings.
    session = Session()
    keys = frozenset(k for (k, v, t) in settings_snapshot)
    for s in Setting.query().all():
        if s.app_settings_name not in keys:
            session.delete(s)
    for k, v, t in settings_snapshot:
        if t == 'list' and hasattr(v, '__iter__'):
            v = ','.join(v) # Quirk: must format list value manually.
        Setting.create_or_update(k, v, t)
    session.commit()


@pytest.fixture
def auto_clear_ip_permissions():
    """Fixture that provides nothing but clearing IP permissions upon test
    exit. This clearing is needed to avoid other test failing to make fake http
    accesses."""
    yield
    # cleanup
    user_model = UserModel()

    user_ids = []
    user_ids.append(User.get_default_user().user_id)
    user_ids.append(User.get_by_username(TEST_USER_REGULAR_LOGIN).user_id)

    for user_id in user_ids:
        for ip in UserIpMap.query().filter(UserIpMap.user_id == user_id):
            user_model.delete_extra_ip(user_id, ip.ip_id)

    # IP permissions are cached, need to invalidate this cache explicitly
    invalidate_all_caches()
    session = Session()
    session.commit()


@pytest.fixture
def test_context_fixture(app_fixture):
    """
    Encompass the entire test using this fixture in a test_context,
    making sure that certain functionality still works even if no call to
    self.app.get/post has been made.
    The typical error message indicating you need a test_context is:
        TypeError: No object (name: context) has been registered for this thread

    The standard way to fix this is simply using the test_context context
    manager directly inside your test:
        with test_context(self.app):
            <actions>
    but if test setup code (xUnit-style or pytest fixtures) also needs to be
    executed inside the test context, that method is not possible.
    Even if there is no such setup code, the fixture may reduce code complexity
    if the entire test needs to run inside a test context.

    To apply this fixture (like any other fixture) to all test methods of a
    class, use the following class decorator:
        @pytest.mark.usefixtures("test_context_fixture")
        class TestFoo(TestController):
            ...
    """
    with test_context(app_fixture):
        yield


class MyWSGIServer(WSGIServer):
    def repo_url(self, repo_name, username=TEST_USER_ADMIN_LOGIN, password=TEST_USER_ADMIN_PASS):
        """Return URL to repo on this web server."""
        host, port = self.server_address
        proto = 'http' if self._server.ssl_context is None else 'https'
        auth = ''
        if username is not None:
            auth = username
            if password is not None:
                auth += ':' + password
        if auth:
            auth += '@'
        return '%s://%s%s:%s/%s' % (proto, auth, host, port, repo_name)


@pytest.yield_fixture(scope="session")
def webserver():
    """Start web server while tests are running.
    Useful for debugging and necessary for vcs operation tests."""
    server = MyWSGIServer(application=kallithea.tests.base.testapp)
    server.start()

    yield server

    server.stop()
