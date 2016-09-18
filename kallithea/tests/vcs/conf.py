"""
Unit tests configuration module for vcs.
"""
import os
import time
import hashlib
import tempfile
import datetime
import shutil
import uuid

__all__ = (
    'TEST_HG_REPO', 'TEST_GIT_REPO', 'HG_REMOTE_REPO', 'GIT_REMOTE_REPO',
    'SCM_TESTS',
)

SCM_TESTS = ['hg', 'git']
uniq_suffix = str(int(time.mktime(datetime.datetime.now().timetuple())))

THIS = os.path.abspath(os.path.dirname(__file__))

GIT_REMOTE_REPO = 'git://github.com/codeinn/vcs.git'

TEST_TMP_PATH = os.environ.get('VCS_TEST_ROOT', tempfile.gettempdir())
TEST_GIT_REPO = os.environ.get('VCS_TEST_GIT_REPO',
                               os.path.join(TEST_TMP_PATH, 'vcs-git'))
TEST_GIT_REPO_CLONE = os.environ.get('VCS_TEST_GIT_REPO_CLONE',
                                     os.path.join(TEST_TMP_PATH, 'vcsgitclone%s' % uniq_suffix))
TEST_GIT_REPO_PULL = os.environ.get('VCS_TEST_GIT_REPO_PULL',
                                    os.path.join(TEST_TMP_PATH, 'vcsgitpull%s' % uniq_suffix))

HG_REMOTE_REPO = 'http://bitbucket.org/marcinkuzminski/vcs'
TEST_HG_REPO = os.environ.get('VCS_TEST_HG_REPO',
                              os.path.join(TEST_TMP_PATH, 'vcs-hg'))
TEST_HG_REPO_CLONE = os.environ.get('VCS_TEST_HG_REPO_CLONE',
                                    os.path.join(TEST_TMP_PATH, 'vcshgclone%s' % uniq_suffix))
TEST_HG_REPO_PULL = os.environ.get('VCS_TEST_HG_REPO_PULL',
                                   os.path.join(TEST_TMP_PATH, 'vcshgpull%s' % uniq_suffix))

TEST_DIR = os.environ.get('VCS_TEST_ROOT', tempfile.gettempdir())
TEST_REPO_PREFIX = 'vcs-test'


def get_new_dir(title=None):
    """
    Calculates a path for a new, non-existant, unique sub-directory in TEST_DIR.

    Resulting directory name will have format:

    prefix-[title-]hexuuid

    Prefix is equal to value of variable TEST_REPO_PREFIX. The "hexuuid" is a
    hexadecimal value of a randomly generated UUID. Title will be added if
    specified.

    Args:
        title: Custom title to include as part of the resulting sub-directory
            name. Can be useful for debugging to identify destination. Defaults
            to None.

    Returns:
        Path to the new directory as a string.
    """

    if title:
        name = "%s-%s" % (TEST_REPO_PREFIX, title)
    else:
        name = TEST_REPO_PREFIX

    path = os.path.join(TEST_DIR, name)

    # Generate new hexes until we get a unique name (just in case).
    hex_uuid = uuid.uuid4().hex
    while os.path.exists("%s-%s" % (path, hex_uuid)):
        hex_uuid = uuid.uuid4().hex

    return "%s-%s" % (path, hex_uuid)


PACKAGE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..'))
_dest = os.path.join(TEST_TMP_PATH, 'aconfig')
shutil.copy(os.path.join(THIS, 'aconfig'), _dest)
TEST_USER_CONFIG_FILE = _dest

#overide default configurations with kallithea ones
from kallithea.tests.base import *
