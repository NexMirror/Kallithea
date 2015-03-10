from __future__ import with_statement
from kallithea.tests.vcs.base import BackendTestMixin
from kallithea.tests.vcs.conf import SCM_TESTS
from kallithea.tests.vcs.conf import TEST_USER_CONFIG_FILE
from kallithea.lib.vcs.utils.compat import unittest
class RepositoryBaseTest(BackendTestMixin):
        self.assertEqual(self.repo.get_config_value('universal', 'foo',
            TEST_USER_CONFIG_FILE), 'bar')
        self.assertEqual(self.repo.get_config_value('universal', 'nonexist',
            TEST_USER_CONFIG_FILE), None)
        self.assertEqual(self.repo.get_user_name(TEST_USER_CONFIG_FILE),
            'Foo Bar')
        self.assertEqual(self.repo.get_user_email(TEST_USER_CONFIG_FILE),
            'foo.bar@example.com')
        self.assertTrue(self.repo == self.repo)
        self.assertTrue(self.repo != _repo)
        self.assertTrue(self.repo != dummy())
class RepositoryGetDiffTest(BackendTestMixin):
        with self.assertRaises(ChangesetDoesNotExistError):
class GitRepositoryGetDiffTest(RepositoryGetDiffTest, unittest.TestCase):
        self.assertEqual(self.repo.get_diff(self.repo.EMPTY_CHANGESET, initial_rev), '''diff --git a/foobar b/foobar