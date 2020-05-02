import os

import mock
import pytest
import tg


here = os.path.dirname(__file__)

# HACK:
def pytest_configure():
    # Register global dummy tg.context to avoid "TypeError: No object (name: context) has been registered for this thread"
    tg.request_local.context._push_object(tg.util.bunch.Bunch())
    # could be removed again after use with
    # tg.request_local.context._pop_object ... but we keep it around forever as
    # a reasonable sentinel

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

if getattr(pytest, 'register_assert_rewrite', None):
    # make sure that all asserts under kallithea/tests benefit from advanced
    # assert reporting with pytest-3.0.0+, including api/api_base.py,
    # models/common.py etc.
    # See also: https://docs.pytest.org/en/latest/assert.html#advanced-assertion-introspection
    pytest.register_assert_rewrite('kallithea.tests')
