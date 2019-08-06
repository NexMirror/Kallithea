import os
import shutil

import pytest

from kallithea.lib.utils2 import safe_str
from kallithea.lib.vcs import VCSError, get_backend, get_repo
from kallithea.lib.vcs.backends.hg import MercurialRepository
from kallithea.tests.vcs.conf import TEST_GIT_REPO, TEST_HG_REPO, TESTS_TMP_PATH


class TestVCS(object):
    """
    Tests for main module's methods.
    """

    def test_get_backend(self):
        hg = get_backend('hg')
        assert hg == MercurialRepository

    def test_alias_detect_hg(self):
        alias = 'hg'
        path = TEST_HG_REPO
        backend = get_backend(alias)
        repo = backend(safe_str(path))
        assert 'hg' == repo.alias

    def test_alias_detect_git(self):
        alias = 'git'
        path = TEST_GIT_REPO
        backend = get_backend(alias)
        repo = backend(safe_str(path))
        assert 'git' == repo.alias

    def test_wrong_alias(self):
        alias = 'wrong_alias'
        with pytest.raises(VCSError):
            get_backend(alias)

    def test_get_repo(self):
        alias = 'hg'
        path = TEST_HG_REPO
        backend = get_backend(alias)
        repo = backend(safe_str(path))

        assert repo.__class__ == get_repo(safe_str(path), alias).__class__
        assert repo.path == get_repo(safe_str(path), alias).path

    def test_get_repo_autoalias_hg(self):
        alias = 'hg'
        path = TEST_HG_REPO
        backend = get_backend(alias)
        repo = backend(safe_str(path))

        assert repo.__class__ == get_repo(safe_str(path)).__class__
        assert repo.path == get_repo(safe_str(path)).path

    def test_get_repo_autoalias_git(self):
        alias = 'git'
        path = TEST_GIT_REPO
        backend = get_backend(alias)
        repo = backend(safe_str(path))

        assert repo.__class__ == get_repo(safe_str(path)).__class__
        assert repo.path == get_repo(safe_str(path)).path

    def test_get_repo_err(self):
        blank_repo_path = os.path.join(TESTS_TMP_PATH, 'blank-error-repo')
        if os.path.isdir(blank_repo_path):
            shutil.rmtree(blank_repo_path)

        os.mkdir(blank_repo_path)
        with pytest.raises(VCSError):
            get_repo(blank_repo_path)
        with pytest.raises(VCSError):
            get_repo(blank_repo_path + 'non_existing')

    def test_get_repo_multialias(self):
        multialias_repo_path = os.path.join(TESTS_TMP_PATH, 'hg-git-repo')
        if os.path.isdir(multialias_repo_path):
            shutil.rmtree(multialias_repo_path)

        os.mkdir(multialias_repo_path)

        os.mkdir(os.path.join(multialias_repo_path, '.git'))
        os.mkdir(os.path.join(multialias_repo_path, '.hg'))
        with pytest.raises(VCSError):
            get_repo(multialias_repo_path)
