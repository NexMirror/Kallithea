import pytest

from kallithea.lib.exceptions import AttachedForksError
from kallithea.model.db import Repository
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class TestRepos(TestController):

    def teardown_method(self, method):
        Session.remove()

    def test_remove_repo(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        RepoModel().delete(repo=repo)
        Session().commit()

        assert Repository.get_by_repo_name(repo_name=u'test-repo-1') is None

    def test_remove_repo_repo_raises_exc_when_attached_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        with pytest.raises(AttachedForksError):
            RepoModel().delete(repo=repo)
        # cleanup
        RepoModel().delete(repo=u'test-repo-fork-1')
        RepoModel().delete(repo=u'test-repo-1')
        Session().commit()

    def test_remove_repo_delete_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fork = fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        # fork of fork
        fixture.create_fork(fork.repo_name, u'test-repo-fork-fork-1')
        Session().commit()

        RepoModel().delete(repo=repo, forks='delete')
        Session().commit()

        assert Repository.get_by_repo_name(repo_name=u'test-repo-1') is None
        assert Repository.get_by_repo_name(repo_name=u'test-repo-fork-1') is None
        assert Repository.get_by_repo_name(repo_name=u'test-repo-fork-fork-1') is None

    def test_remove_repo_detach_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fork = fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        # fork of fork
        fixture.create_fork(fork.repo_name, u'test-repo-fork-fork-1')
        Session().commit()

        RepoModel().delete(repo=repo, forks='detach')
        Session().commit()

        try:
            assert Repository.get_by_repo_name(repo_name=u'test-repo-1') is None
            assert Repository.get_by_repo_name(repo_name=u'test-repo-fork-1') is not None
            assert Repository.get_by_repo_name(repo_name=u'test-repo-fork-fork-1') is not None
        finally:
            RepoModel().delete(repo=u'test-repo-fork-fork-1')
            RepoModel().delete(repo=u'test-repo-fork-1')
            Session().commit()
