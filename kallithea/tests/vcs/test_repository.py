import datetime

import pytest

from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError
from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs import TEST_USER_CONFIG_FILE
from kallithea.tests.vcs.base import _BackendTestMixin


class RepositoryBaseTest(_BackendTestMixin):
    recreate_repo_per_test = False

    @classmethod
    def _get_commits(cls):
        return super(RepositoryBaseTest, cls)._get_commits()[:1]

    def test_get_config_value(self):
        assert self.repo.get_config_value('universal', 'foo', TEST_USER_CONFIG_FILE) == 'bar'

    def test_get_config_value_defaults_to_None(self):
        assert self.repo.get_config_value('universal', 'nonexist', TEST_USER_CONFIG_FILE) == None

    def test_get_user_name(self):
        assert self.repo.get_user_name(TEST_USER_CONFIG_FILE) == 'Foo Bar'

    def test_get_user_email(self):
        assert self.repo.get_user_email(TEST_USER_CONFIG_FILE) == 'foo.bar@example.com'

    def test_repo_equality(self):
        assert self.repo == self.repo

    def test_repo_equality_broken_object(self):
        import copy
        _repo = copy.copy(self.repo)
        delattr(_repo, 'path')
        assert self.repo != _repo

    def test_repo_equality_other_object(self):
        class dummy(object):
            path = self.repo.path
        assert self.repo != dummy()


class TestGitRepositoryBase(RepositoryBaseTest):
    backend_alias = 'git'


class TestHgRepositoryBase(RepositoryBaseTest):
    backend_alias = 'hg'


class RepositoryGetDiffTest(_BackendTestMixin):

    @classmethod
    def _get_commits(cls):
        commits = [
            {
                'message': 'Initial commit',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [
                    FileNode('foobar', content='foobar'),
                    FileNode('foobar2', content='foobar2'),
                ],
            },
            {
                'message': 'Changed foobar, added foobar3',
                'author': 'Jane Doe <jane.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 21),
                'added': [
                    FileNode('foobar3', content='foobar3'),
                ],
                'changed': [
                    FileNode('foobar', 'FOOBAR'),
                ],
            },
            {
                'message': 'Removed foobar, changed foobar3',
                'author': 'Jane Doe <jane.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'changed': [
                    FileNode('foobar3', content='FOOBAR\nFOOBAR\nFOOBAR\n'),
                ],
                'removed': [FileNode('foobar')],
            },
            {
                'message': u'Commit that contains glob pattern in filename',
                'author': 'Jane Doe <jane.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'added': [
                    FileNode('README{', content='Strangely-named README file'),
                ],
            },
        ]
        return commits

    def test_raise_for_wrong(self):
        with pytest.raises(ChangesetDoesNotExistError):
            self.repo.get_diff('a' * 40, 'b' * 40)

    def test_glob_patterns_in_filename_do_not_raise_exception(self):
        revs = self.repo.revisions

        diff = self.repo.get_diff(revs[2], revs[3], path='README{') # should not raise


class TestGitRepositoryGetDiff(RepositoryGetDiffTest):
    backend_alias = 'git'

    def test_initial_commit_diff(self):
        initial_rev = self.repo.revisions[0]
        assert self.repo.get_diff(self.repo.EMPTY_CHANGESET, initial_rev) == '''diff --git a/foobar b/foobar
new file mode 100644
index 0000000000000000000000000000000000000000..f6ea0495187600e7b2288c8ac19c5886383a4632
--- /dev/null
+++ b/foobar
@@ -0,0 +1 @@
+foobar
\ No newline at end of file
diff --git a/foobar2 b/foobar2
new file mode 100644
index 0000000000000000000000000000000000000000..e8c9d6b98e3dce993a464935e1a53f50b56a3783
--- /dev/null
+++ b/foobar2
@@ -0,0 +1 @@
+foobar2
\ No newline at end of file
'''

    def test_second_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[0], revs[1]) == '''diff --git a/foobar b/foobar
index f6ea0495187600e7b2288c8ac19c5886383a4632..389865bb681b358c9b102d79abd8d5f941e96551 100644
--- a/foobar
+++ b/foobar
@@ -1 +1 @@
-foobar
\ No newline at end of file
+FOOBAR
\ No newline at end of file
diff --git a/foobar3 b/foobar3
new file mode 100644
index 0000000000000000000000000000000000000000..c11c37d41d33fb47741cff93fa5f9d798c1535b0
--- /dev/null
+++ b/foobar3
@@ -0,0 +1 @@
+foobar3
\ No newline at end of file
'''

    def test_third_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[1], revs[2]) == '''diff --git a/foobar b/foobar
deleted file mode 100644
index 389865bb681b358c9b102d79abd8d5f941e96551..0000000000000000000000000000000000000000
--- a/foobar
+++ /dev/null
@@ -1 +0,0 @@
-FOOBAR
\ No newline at end of file
diff --git a/foobar3 b/foobar3
index c11c37d41d33fb47741cff93fa5f9d798c1535b0..f9324477362684ff692aaf5b9a81e01b9e9a671c 100644
--- a/foobar3
+++ b/foobar3
@@ -1 +1,3 @@
-foobar3
\ No newline at end of file
+FOOBAR
+FOOBAR
+FOOBAR
'''

    def test_fourth_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[2], revs[3]) == '''diff --git a/README{ b/README{
new file mode 100644
index 0000000000000000000000000000000000000000..cdc0c1b5d234feedb37bbac19cd1b6442061102d
--- /dev/null
+++ b/README{
@@ -0,0 +1 @@
+Strangely-named README file
\ No newline at end of file
'''


class TestHgRepositoryGetDiff(RepositoryGetDiffTest):
    backend_alias = 'hg'

    def test_initial_commit_diff(self):
        initial_rev = self.repo.revisions[0]
        assert self.repo.get_diff(self.repo.EMPTY_CHANGESET, initial_rev) == '''diff --git a/foobar b/foobar
new file mode 100644
--- /dev/null
+++ b/foobar
@@ -0,0 +1,1 @@
+foobar
\ No newline at end of file
diff --git a/foobar2 b/foobar2
new file mode 100644
--- /dev/null
+++ b/foobar2
@@ -0,0 +1,1 @@
+foobar2
\ No newline at end of file
'''

    def test_second_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[0], revs[1]) == '''diff --git a/foobar b/foobar
--- a/foobar
+++ b/foobar
@@ -1,1 +1,1 @@
-foobar
\ No newline at end of file
+FOOBAR
\ No newline at end of file
diff --git a/foobar3 b/foobar3
new file mode 100644
--- /dev/null
+++ b/foobar3
@@ -0,0 +1,1 @@
+foobar3
\ No newline at end of file
'''

    def test_third_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[1], revs[2]) == '''diff --git a/foobar b/foobar
deleted file mode 100644
--- a/foobar
+++ /dev/null
@@ -1,1 +0,0 @@
-FOOBAR
\ No newline at end of file
diff --git a/foobar3 b/foobar3
--- a/foobar3
+++ b/foobar3
@@ -1,1 +1,3 @@
-foobar3
\ No newline at end of file
+FOOBAR
+FOOBAR
+FOOBAR
'''

    def test_fourth_changeset_diff(self):
        revs = self.repo.revisions
        assert self.repo.get_diff(revs[2], revs[3]) == '''diff --git a/README{ b/README{
new file mode 100644
--- /dev/null
+++ b/README{
@@ -0,0 +1,1 @@
+Strangely-named README file
\ No newline at end of file
'''
