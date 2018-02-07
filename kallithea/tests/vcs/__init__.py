"""
Unit tests for vcs_ library.

In order to run tests we need to prepare our environment first. Tests would be
run for each engine listed at ``conf.SCM_TESTS`` - keys are aliases from
``vcs.backends.BACKENDS``.

For each SCM we run tests for, we need some repository. We would use
repositories location from system environment variables or test suite defaults
- see ``conf`` module for more detail. We simply try to check if repository at
certain location exists, if not we would try to fetch them. At ``test_vcs`` or
``test_common`` we run unit tests common for each repository type and for
example specific mercurial tests are located at ``test_hg`` module.

Oh, and tests are run with ``unittest.collector`` wrapped by ``collector``
function at ``tests/__init__.py``.

.. _vcs: http://bitbucket.org/marcinkuzminski/vcs
.. _unittest: http://pypi.python.org/pypi/unittest

"""

import os
import shutil

from kallithea.tests.base import TEST_HG_REPO, HG_REMOTE_REPO, TEST_GIT_REPO, GIT_REMOTE_REPO
from kallithea.tests.vcs.utils import SCMFetcher

from kallithea.tests.base import *


# Base directory for the VCS tests.
VCS_TEST_MODULE_BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Path to user configuration file used during tests.
TEST_USER_CONFIG_FILE = os.path.join(TESTS_TMP_PATH, 'aconfig')


def setup_package():
    """
    Prepares whole package for tests which mainly means it would try to fetch
    test repositories or use already existing ones.
    """
    fetchers = {
        'hg': {
            'alias': 'hg',
            'test_repo_path': TEST_HG_REPO,
            'remote_repo': HG_REMOTE_REPO,
            'clone_cmd': 'hg clone --insecure',
        },
        'git': {
            'alias': 'git',
            'test_repo_path': TEST_GIT_REPO,
            'remote_repo': GIT_REMOTE_REPO,
            'clone_cmd': 'git clone --bare',
        },
    }

    for scm, fetcher_info in fetchers.items():
        fetcher = SCMFetcher(**fetcher_info)
        fetcher.setup()

    # Copy the test user configuration file to location where
    # temporary test data is stored at.
    shutil.copy(os.path.join(VCS_TEST_MODULE_BASE_DIR, 'aconfig'), TEST_USER_CONFIG_FILE)
