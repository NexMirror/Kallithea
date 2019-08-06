import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin


class GetsliceTestCaseMixin(_BackendTestMixin):

    @classmethod
    def _get_commits(cls):
        start_date = datetime.datetime(2010, 1, 1, 20)
        for x in xrange(5):
            yield {
                'message': 'Commit %d' % x,
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': start_date + datetime.timedelta(hours=12 * x),
                'added': [
                    FileNode('file_%d.txt' % x, content='Foobar %d' % x),
                ],
            }

    def test__getslice__last_item_is_tip(self):
        assert list(self.repo[-1:])[0] == self.repo.get_changeset()

    def test__getslice__respects_start_index(self):
        assert list(self.repo[2:]) == [self.repo.get_changeset(rev) for rev in self.repo.revisions[2:]]

    def test__getslice__respects_negative_start_index(self):
        assert list(self.repo[-2:]) == [self.repo.get_changeset(rev) for rev in self.repo.revisions[-2:]]

    def test__getslice__respects_end_index(self):
        assert list(self.repo[:2]) == [self.repo.get_changeset(rev) for rev in self.repo.revisions[:2]]

    def test__getslice__respects_negative_end_index(self):
        assert list(self.repo[:-2]) == [self.repo.get_changeset(rev) for rev in self.repo.revisions[:-2]]


class TestGitGetslice(GetsliceTestCaseMixin):
    backend_alias = 'git'


class TestHgGetslice(GetsliceTestCaseMixin):
    backend_alias = 'hg'
