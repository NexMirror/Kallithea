import os

import mock
import pytest


here = os.path.dirname(__file__)

def pytest_ignore_collect(path):
    # ignore all files outside the 'kallithea' directory
    if not str(path).startswith(os.path.join(here, 'kallithea')):
        return True

    # during doctest verification, normally all python files will be imported.
    # Thus, files that cannot be imported normally should be ignored.
    # Files that generate ImportErrors are ignored via
    # '--doctest-ignore-import-errors' (pytest.ini)
    kallithea_ignore_paths = (
        # AttributeError: 'module' object has no attribute 'config'
        '/kallithea/alembic/env.py',
        # collection of the following file messes up the rest of test execution
        '/kallithea/tests/scripts/manual_test_concurrency.py',
    )
    if str(path).endswith(kallithea_ignore_paths):
        return True

@pytest.fixture()
def doctest_mock_ugettext(request):
    """Mock ugettext ('_') in the module using this fixture.

    Intended to be used for doctests.

    In a doctest, enable this fixture using:
        >>> getfixture('doctest_mock_ugettext')
    """
    m = __import__(request.module.__name__, globals(), locals(), [None], 0)
    with mock.patch.object(m, '_', lambda s: s):
        yield
