import datetime

import pytest

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin


class WorkdirTestCaseMixin(_BackendTestMixin):

    @classmethod
    def _get_commits(cls):
        commits = [
            {
                'message': u'Initial commit',
                'author': u'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [
                    FileNode('foobar', content='Foobar'),
                    FileNode('foobar2', content='Foobar II'),
                    FileNode('foo/bar/baz', content='baz here!'),
                ],
            },
            {
                'message': u'Changes...',
                'author': u'Jane Doe <jane.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 21),
                'added': [
                    FileNode('some/new.txt', content='news...'),
                ],
                'changed': [
                    FileNode('foobar', 'Foobar I'),
                ],
                'removed': [],
            },
        ]
        return commits

    def test_get_branch_for_default_branch(self):
        assert self.repo.workdir.get_branch() == self.repo.DEFAULT_BRANCH_NAME

    def test_get_branch_after_adding_one(self):
        self.imc.add(FileNode('docs/index.txt',
            content='Documentation\n'))
        self.imc.commit(
            message=u'New branch: foobar',
            author=u'joe',
            branch='foobar',
        )
        assert self.repo.workdir.get_branch() == self.default_branch

    def test_get_changeset(self):
        old_head = self.repo.get_changeset()
        self.imc.add(FileNode('docs/index.txt',
            content='Documentation\n'))
        head = self.imc.commit(
            message=u'New branch: foobar',
            author=u'joe',
            branch='foobar',
        )
        assert self.repo.workdir.get_branch() == self.default_branch
        self.repo.workdir.checkout_branch('foobar')
        assert self.repo.workdir.get_changeset() == head

        # Make sure that old head is still there after update to default branch
        self.repo.workdir.checkout_branch(self.default_branch)
        assert self.repo.workdir.get_changeset() == old_head

    def test_checkout_branch(self):
        from kallithea.lib.vcs.exceptions import BranchDoesNotExistError
        # first, 'foobranch' does not exist.
        with pytest.raises(BranchDoesNotExistError):
            self.repo.workdir.checkout_branch(branch='foobranch')
        # create new branch 'foobranch'.
        self.imc.add(FileNode('file1', content='blah'))
        self.imc.commit(message=u'asd', author=u'john', branch='foobranch')
        # go back to the default branch
        self.repo.workdir.checkout_branch()
        assert self.repo.workdir.get_branch() == self.backend_class.DEFAULT_BRANCH_NAME
        # checkout 'foobranch'
        self.repo.workdir.checkout_branch('foobranch')
        assert self.repo.workdir.get_branch() == 'foobranch'


class TestGitBranch(WorkdirTestCaseMixin):
    backend_alias = 'git'


class TestHgBranch(WorkdirTestCaseMixin):
    backend_alias = 'hg'
