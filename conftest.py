import mock
import os
import pytest
import sys

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
