"""
Unit tests configuration module for vcs.
"""
import os
import shutil
import uuid

# Retrieve the necessary configuration options from the test base
# module. Some of these configuration options are subsequently
# consumed by the VCS test module.
from kallithea.tests.base import (
    TESTS_TMP_PATH, SCM_TESTS,
    TEST_HG_REPO, HG_REMOTE_REPO,
    TEST_GIT_REPO, GIT_REMOTE_REPO,
)

__all__ = (
    'TEST_HG_REPO', 'TEST_GIT_REPO', 'HG_REMOTE_REPO', 'GIT_REMOTE_REPO',
    'SCM_TESTS',
)

THIS = os.path.abspath(os.path.dirname(__file__))

def get_new_dir(title=None):
    """
    Calculates a path for a new, non-existant, unique sub-directory in TESTS_TMP_PATH.

    Resulting directory name will have format:

    vcs-test-[title-]hexuuid

    The "hexuuid" is a hexadecimal value of a randomly generated
    UUID. Title will be added if specified.

    Args:
        title: Custom title to include as part of the resulting sub-directory
            name. Can be useful for debugging to identify destination. Defaults
            to None.

    Returns:
        Path to the new directory as a string.
    """

    test_repo_prefix = 'vcs-test'

    if title:
        name = "%s-%s" % (test_repo_prefix, title)
    else:
        name = test_repo_prefix

    path = os.path.join(TESTS_TMP_PATH, name)

    # Generate new hexes until we get a unique name (just in case).
    hex_uuid = uuid.uuid4().hex
    while os.path.exists("%s-%s" % (path, hex_uuid)):
        hex_uuid = uuid.uuid4().hex

    return "%s-%s" % (path, hex_uuid)


_dest = os.path.join(TESTS_TMP_PATH, 'aconfig')
shutil.copy(os.path.join(THIS, 'aconfig'), _dest)
TEST_USER_CONFIG_FILE = _dest

# overide default configurations with kallithea ones
from kallithea.tests.base import *
