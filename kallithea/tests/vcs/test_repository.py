
import pytest

from kallithea.tests.vcs.base import _BackendTestMixin
from kallithea.tests.vcs.conf import SCM_TESTS
from kallithea.tests.vcs import TEST_USER_CONFIG_FILE

        assert self.repo.get_config_value('universal', 'foo', TEST_USER_CONFIG_FILE) == 'bar'
        assert self.repo.get_config_value('universal', 'nonexist', TEST_USER_CONFIG_FILE) == None
        assert self.repo.get_user_name(TEST_USER_CONFIG_FILE) == 'Foo Bar'
        assert self.repo.get_user_email(TEST_USER_CONFIG_FILE) == 'foo.bar@example.com'
        assert self.repo == self.repo
        assert self.repo != _repo
        assert self.repo != dummy()
            {
                'message': u'Commit that contains glob pattern in filename',
                'author': 'Jane Doe <jane.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'added': [
                    FileNode('README{', content='Strangely-named README file'),
                ],
            },
        with pytest.raises(ChangesetDoesNotExistError):
    def test_glob_patterns_in_filename_do_not_raise_exception(self):
        revs = self.repo.revisions

        diff = self.repo.get_diff(revs[2], revs[3], path='README{') # should not raise

class TestGitRepositoryGetDiff(RepositoryGetDiffTest):
        assert self.repo.get_diff(self.repo.EMPTY_CHANGESET, initial_rev) == '''diff --git a/foobar b/foobar