from kallithea.tests import *

from kallithea.model.meta import Session
from kallithea.tests.fixture import Fixture
from kallithea.model.repo import RepoModel
from kallithea.model.db import Repository
from kallithea.lib.exceptions import AttachedForksError

fixture = Fixture()


class TestRepos(TestControllerPytest):

    def teardown_method(self, method):
        Session.remove()

    def test_remove_repo(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        RepoModel().delete(repo=repo)
        Session().commit()

        self.assertEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-1'))

    def test_remove_repo_repo_raises_exc_when_attached_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        self.assertRaises(AttachedForksError, lambda: RepoModel().delete(repo=repo))
        # cleanup
        RepoModel().delete(repo=u'test-repo-fork-1')
        RepoModel().delete(repo=u'test-repo-1')
        Session().commit()

    def test_remove_repo_delete_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fork = fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        #fork of fork
        fixture.create_fork(fork.repo_name, u'test-repo-fork-fork-1')
        Session().commit()

        RepoModel().delete(repo=repo, forks='delete')
        Session().commit()

        self.assertEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-1'))
        self.assertEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-fork-1'))
        self.assertEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-fork-fork-1'))

    def test_remove_repo_detach_forks(self):
        repo = fixture.create_repo(name=u'test-repo-1')
        Session().commit()

        fork = fixture.create_fork(repo.repo_name, u'test-repo-fork-1')
        Session().commit()

        #fork of fork
        fixture.create_fork(fork.repo_name, u'test-repo-fork-fork-1')
        Session().commit()

        RepoModel().delete(repo=repo, forks='detach')
        Session().commit()

        try:
            self.assertEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-1'))
            self.assertNotEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-fork-1'))
            self.assertNotEqual(None, Repository.get_by_repo_name(repo_name=u'test-repo-fork-fork-1'))
        finally:
            RepoModel().delete(repo=u'test-repo-fork-fork-1')
            RepoModel().delete(repo=u'test-repo-fork-1')
            Session().commit()
