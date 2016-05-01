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
