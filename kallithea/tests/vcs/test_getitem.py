import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin


class GetitemTestCaseMixin(_BackendTestMixin):

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

    def test__getitem__last_item_is_tip(self):
        assert self.repo[-1] == self.repo.get_changeset()

    def test__getitem__returns_correct_items(self):
        changesets = [self.repo[x] for x in xrange(len(self.repo.revisions))]
        assert changesets == list(self.repo.get_changesets())


class TestGitGetitem(GetitemTestCaseMixin):
    backend_alias = 'git'


class TestHgGetitem(GetitemTestCaseMixin):
    backend_alias = 'hg'
