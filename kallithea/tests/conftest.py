import os
import sys
import logging

import pkg_resources
from paste.deploy import loadapp
import pylons.test
from pylons.i18n.translation import _get_translator
import pytest
from kallithea.model.user import UserModel
from kallithea.model.meta import Session
from kallithea.model.db import Setting


def pytest_configure():
    path = os.getcwd()
    sys.path.insert(0, path)
    pkg_resources.working_set.add_entry(path)

    # Disable INFO logging of test database creation, restore with NOTSET
    logging.disable(logging.INFO)
    pylons.test.pylonsapp = loadapp('config:kallithea/tests/test.ini', relative_to=path)
    logging.disable(logging.NOTSET)

    # Setup the config and app_globals, only works if we can get
    # to the config object
    conf = getattr(pylons.test.pylonsapp, 'config')
    if conf:
        pylons.config._push_object(conf)

        if 'pylons.app_globals' in conf:
            pylons.app_globals._push_object(conf['pylons.app_globals'])

    # Initialize a translator for tests that utilize i18n
    translator = _get_translator(pylons.config.get('lang'))
    pylons.translator._push_object(translator)

    return pylons.test.pylonsapp


@pytest.yield_fixture
def create_test_user():
    """Provide users that automatically disappear after test is over."""
    test_users = []
    def _create_test_user(user_form):
        user = UserModel().create(user_form)
        test_users.append(user)
        return user
    yield _create_test_user
    for user in test_users:
        UserModel().delete(user)
    Session().commit()


def _set_settings(*kvtseq):
    session = Session()
    for kvt in kvtseq:
        assert len(kvt) in (2, 3)
        k = kvt[0]
        v = kvt[1]
        t = kvt[2] if len(kvt) == 3 else 'unicode'
        setting = Setting.create_or_update(k, v, t)
        session.add(setting)
    session.commit()


@pytest.yield_fixture
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
        s = Setting.create_or_update(k, v, t)
        session.add(s)
    session.commit()
