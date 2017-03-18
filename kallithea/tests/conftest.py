import os
import sys
import logging
import pkg_resources

from paste.deploy import loadapp
from routes.util import URLGenerator
from tg import config

import pytest
from kallithea.controllers.root import RootController
from kallithea.model.user import UserModel
from kallithea.model.meta import Session
from kallithea.model.db import Setting, User, UserIpMap
from kallithea.tests.base import invalidate_all_caches, TEST_USER_REGULAR_LOGIN
import kallithea.tests.base # FIXME: needed for setting testapp instance!!!

from tg.util.webtest import test_context

def pytest_configure():
    path = os.getcwd()
    sys.path.insert(0, path)
    pkg_resources.working_set.add_entry(path)

    # Disable INFO logging of test database creation, restore with NOTSET
    logging.disable(logging.INFO)
    kallithea.tests.base.testapp = loadapp('config:kallithea/tests/test.ini', relative_to=path)
    logging.disable(logging.NOTSET)

    kallithea.tests.base.url = URLGenerator(RootController().mapper, kallithea.tests.base.environ)


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
