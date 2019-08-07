# encoding: utf-8

import datetime

import pytest

from kallithea.lib import vcs
from kallithea.lib.vcs.backends.base import BaseChangeset
from kallithea.lib.vcs.exceptions import BranchDoesNotExistError, ChangesetDoesNotExistError, EmptyRepositoryError, RepositoryError
from kallithea.lib.vcs.nodes import AddedFileNodesGenerator, ChangedFileNodesGenerator, FileNode, RemovedFileNodesGenerator
from kallithea.tests.vcs.base import _BackendTestMixin


class TestBaseChangeset(object):

    def test_as_dict(self):
        changeset = BaseChangeset()
        changeset.id = 'ID'
        changeset.raw_id = 'RAW_ID'
        changeset.short_id = 'SHORT_ID'
        changeset.revision = 1009
        changeset.date = datetime.datetime(2011, 1, 30, 1, 45)
        changeset.message = 'Message of a commit'
        changeset.author = 'Joe Doe <joe.doe@example.com>'
        changeset.added = [FileNode('foo/bar/baz'), FileNode(u'foobar'), FileNode(u'blåbærgrød')]
        changeset.changed = []
        changeset.removed = []
        assert changeset.as_dict() == {
            'id': 'ID',
            'raw_id': 'RAW_ID',
            'short_id': 'SHORT_ID',
            'revision': 1009,
            'date': datetime.datetime(2011, 1, 30, 1, 45),
            'message': 'Message of a commit',
            'author': {
                'name': 'Joe Doe',
                'email': 'joe.doe@example.com',
            },
            'added': ['foo/bar/baz', 'foobar', u'bl\xe5b\xe6rgr\xf8d'],
            'changed': [],
            'removed': [],
        }


class _ChangesetsWithCommitsTestCaseixin(_BackendTestMixin):

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

    def test_new_branch(self):
        self.imc.add(vcs.nodes.FileNode('docs/index.txt',
            content='Documentation\n'))
        foobar_tip = self.imc.commit(
            message=u'New branch: foobar',
            author=u'joe',
            branch='foobar',
        )
        assert 'foobar' in self.repo.branches
        assert foobar_tip.branch == 'foobar'
        assert foobar_tip.branches == ['foobar']
        # 'foobar' should be the only branch that contains the new commit
        branch_tips = self.repo.branches.values()
        assert branch_tips.count(str(foobar_tip.raw_id)) == 1

    def test_new_head_in_default_branch(self):
        tip = self.repo.get_changeset()
        self.imc.add(vcs.nodes.FileNode('docs/index.txt',
            content='Documentation\n'))
        foobar_tip = self.imc.commit(
            message=u'New branch: foobar',
            author=u'joe',
            branch='foobar',
            parents=[tip],
        )
        self.imc.change(vcs.nodes.FileNode('docs/index.txt',
            content='Documentation\nand more...\n'))
        newtip = self.imc.commit(
            message=u'At default branch',
            author=u'joe',
            branch=foobar_tip.branch,
            parents=[foobar_tip],
        )

        newest_tip = self.imc.commit(
            message=u'Merged with %s' % foobar_tip.raw_id,
            author=u'joe',
            branch=self.backend_class.DEFAULT_BRANCH_NAME,
            parents=[newtip, foobar_tip],
        )

        assert newest_tip.branch == self.backend_class.DEFAULT_BRANCH_NAME
        assert newest_tip.branches == [self.backend_class.DEFAULT_BRANCH_NAME]

    def test_get_changesets_respects_branch_name(self):
        tip = self.repo.get_changeset()
        self.imc.add(vcs.nodes.FileNode('docs/index.txt',
            content='Documentation\n'))
        doc_changeset = self.imc.commit(
            message=u'New branch: docs',
            author=u'joe',
            branch='docs',
        )
        self.imc.add(vcs.nodes.FileNode('newfile', content=''))
        self.imc.commit(
            message=u'Back in default branch',
            author=u'joe',
            parents=[tip],
        )
        default_branch_changesets = self.repo.get_changesets(
            branch_name=self.repo.DEFAULT_BRANCH_NAME)
        assert doc_changeset not in default_branch_changesets

    def test_get_changeset_by_branch(self):
        for branch, sha in self.repo.branches.iteritems():
            assert sha == self.repo.get_changeset(branch).raw_id

    def test_get_changeset_by_tag(self):
        for tag, sha in self.repo.tags.iteritems():
            assert sha == self.repo.get_changeset(tag).raw_id

    def test_get_changeset_parents(self):
        for test_rev in [1, 2, 3]:
            sha = self.repo.get_changeset(test_rev-1)
            assert [sha] == self.repo.get_changeset(test_rev).parents

    def test_get_changeset_children(self):
        for test_rev in [1, 2, 3]:
            sha = self.repo.get_changeset(test_rev+1)
            assert [sha] == self.repo.get_changeset(test_rev).children


class _ChangesetsTestCaseMixin(_BackendTestMixin):
    recreate_repo_per_test = False

    @classmethod
    def _get_commits(cls):
        start_date = datetime.datetime(2010, 1, 1, 20)
        for x in xrange(5):
            yield {
                'message': u'Commit %d' % x,
                'author': u'Joe Doe <joe.doe@example.com>',
                'date': start_date + datetime.timedelta(hours=12 * x),
                'added': [
                    FileNode('file_%d.txt' % x, content='Foobar %d' % x),
                ],
            }

    def test_simple(self):
        tip = self.repo.get_changeset()
        assert tip.date == datetime.datetime(2010, 1, 3, 20)

    def test_get_changesets_is_ordered_by_date(self):
        changesets = list(self.repo.get_changesets())
        ordered_by_date = sorted(changesets,
            key=lambda cs: cs.date)

        assert changesets == ordered_by_date

    def test_get_changesets_respects_start(self):
        second_id = self.repo.revisions[1]
        changesets = list(self.repo.get_changesets(start=second_id))
        assert len(changesets) == 4

    def test_get_changesets_numerical_id_respects_start(self):
        second_id = 1
        changesets = list(self.repo.get_changesets(start=second_id))
        assert len(changesets) == 4

    def test_get_changesets_includes_start_changeset(self):
        second_id = self.repo.revisions[1]
        changesets = list(self.repo.get_changesets(start=second_id))
        assert changesets[0].raw_id == second_id

    def test_get_changesets_respects_end(self):
        second_id = self.repo.revisions[1]
        changesets = list(self.repo.get_changesets(end=second_id))
        assert changesets[-1].raw_id == second_id
        assert len(changesets) == 2

    def test_get_changesets_numerical_id_respects_end(self):
        second_id = 1
        changesets = list(self.repo.get_changesets(end=second_id))
        assert changesets.index(changesets[-1]) == second_id
        assert len(changesets) == 2

    def test_get_changesets_respects_both_start_and_end(self):
        second_id = self.repo.revisions[1]
        third_id = self.repo.revisions[2]
        changesets = list(self.repo.get_changesets(start=second_id,
            end=third_id))
        assert len(changesets) == 2

    def test_get_changesets_numerical_id_respects_both_start_and_end(self):
        changesets = list(self.repo.get_changesets(start=2, end=3))
        assert len(changesets) == 2

    def test_get_changesets_on_empty_repo_raises_EmptyRepository_error(self):
        repo = self.setup_empty_repo(self.backend_class)
        with pytest.raises(EmptyRepositoryError):
            list(repo.get_changesets(start='foobar'))

    def test_get_changesets_includes_end_changeset(self):
        second_id = self.repo.revisions[1]
        changesets = list(self.repo.get_changesets(end=second_id))
        assert changesets[-1].raw_id == second_id

    def test_get_changesets_respects_start_date(self):
        start_date = datetime.datetime(2010, 2, 1)
        for cs in self.repo.get_changesets(start_date=start_date):
            assert cs.date >= start_date

    def test_get_changesets_respects_end_date(self):
        start_date = datetime.datetime(2010, 1, 1)
        end_date = datetime.datetime(2010, 2, 1)
        for cs in self.repo.get_changesets(start_date=start_date,
                                           end_date=end_date):
            assert cs.date >= start_date
            assert cs.date <= end_date

    def test_get_changesets_respects_start_date_and_end_date(self):
        end_date = datetime.datetime(2010, 2, 1)
        for cs in self.repo.get_changesets(end_date=end_date):
            assert cs.date <= end_date

    def test_get_changesets_respects_reverse(self):
        changesets_id_list = [cs.raw_id for cs in
            self.repo.get_changesets(reverse=True)]
        assert changesets_id_list == list(reversed(self.repo.revisions))

    def test_get_filenodes_generator(self):
        tip = self.repo.get_changeset()
        filepaths = [node.path for node in tip.get_filenodes_generator()]
        assert filepaths == ['file_%d.txt' % x for x in xrange(5)]

    def test_size(self):
        tip = self.repo.get_changeset()
        size = 5 * len('Foobar N') # Size of 5 files
        assert tip.size == size

    def test_author(self):
        tip = self.repo.get_changeset()
        assert tip.author == u'Joe Doe <joe.doe@example.com>'

    def test_author_name(self):
        tip = self.repo.get_changeset()
        assert tip.author_name == u'Joe Doe'

    def test_author_email(self):
        tip = self.repo.get_changeset()
        assert tip.author_email == u'joe.doe@example.com'

    def test_get_changesets_raise_changesetdoesnotexist_for_wrong_start(self):
        with pytest.raises(ChangesetDoesNotExistError):
            list(self.repo.get_changesets(start='foobar'))

    def test_get_changesets_raise_changesetdoesnotexist_for_wrong_end(self):
        with pytest.raises(ChangesetDoesNotExistError):
            list(self.repo.get_changesets(end='foobar'))

    def test_get_changesets_raise_branchdoesnotexist_for_wrong_branch_name(self):
        with pytest.raises(BranchDoesNotExistError):
            list(self.repo.get_changesets(branch_name='foobar'))

    def test_get_changesets_raise_repositoryerror_for_wrong_start_end(self):
        start = self.repo.revisions[-1]
        end = self.repo.revisions[0]
        with pytest.raises(RepositoryError):
            list(self.repo.get_changesets(start=start, end=end))

    def test_get_changesets_numerical_id_reversed(self):
        with pytest.raises(RepositoryError):
            [x for x in self.repo.get_changesets(start=3, end=2)]

    def test_get_changesets_numerical_id_respects_both_start_and_end_last(self):
        with pytest.raises(RepositoryError):
            last = len(self.repo.revisions)
            list(self.repo.get_changesets(start=last-1, end=last-2))

    def test_get_changesets_numerical_id_last_zero_error(self):
        with pytest.raises(RepositoryError):
            last = len(self.repo.revisions)
            list(self.repo.get_changesets(start=last-1, end=0))


class _ChangesetsChangesTestCaseMixin(_BackendTestMixin):
    recreate_repo_per_test = False

    @classmethod
    def _get_commits(cls):
        return [
            {
                'message': u'Initial',
                'author': u'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [
                    FileNode('foo/bar', content='foo'),
                    FileNode('foo/bał', content='foo'),
                    FileNode('foobar', content='foo'),
                    FileNode('qwe', content='foo'),
                ],
            },
            {
                'message': u'Massive changes',
                'author': u'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'added': [FileNode('fallout', content='War never changes')],
                'changed': [
                    FileNode('foo/bar', content='baz'),
                    FileNode('foobar', content='baz'),
                ],
                'removed': [FileNode('qwe')],
            },
        ]

    def test_initial_commit(self):
        changeset = self.repo.get_changeset(0)
        assert sorted(list(changeset.added)) == sorted([
            changeset.get_node('foo/bar'),
            changeset.get_node('foo/bał'),
            changeset.get_node('foobar'),
            changeset.get_node('qwe'),
        ])
        assert list(changeset.changed) == []
        assert list(changeset.removed) == []
        assert u'foo/ba\u0142' in changeset.as_dict()['added']
        assert u'foo/ba\u0142' in changeset.__json__(with_file_list=True)['added']

    def test_head_added(self):
        changeset = self.repo.get_changeset()
        assert isinstance(changeset.added, AddedFileNodesGenerator)
        assert list(changeset.added) == [
            changeset.get_node('fallout'),
        ]
        assert isinstance(changeset.changed, ChangedFileNodesGenerator)
        assert list(changeset.changed) == [
            changeset.get_node('foo/bar'),
            changeset.get_node('foobar'),
        ]
        assert isinstance(changeset.removed, RemovedFileNodesGenerator)
        assert len(changeset.removed) == 1
        assert list(changeset.removed)[0].path == 'qwe'

    def test_get_filemode(self):
        changeset = self.repo.get_changeset()
        assert 33188 == changeset.get_file_mode('foo/bar')

    def test_get_filemode_non_ascii(self):
        changeset = self.repo.get_changeset()
        assert 33188 == changeset.get_file_mode('foo/bał')
        assert 33188 == changeset.get_file_mode(u'foo/bał')


class TestGitChangesetsWithCommits(_ChangesetsWithCommitsTestCaseixin):
    backend_alias = 'git'


class TestGitChangesets(_ChangesetsTestCaseMixin):
    backend_alias = 'git'


class TestGitChangesetsChanges(_ChangesetsChangesTestCaseMixin):
    backend_alias = 'git'


class TestHgChangesetsWithCommits(_ChangesetsWithCommitsTestCaseixin):
    backend_alias = 'hg'


class TestHgChangesets(_ChangesetsTestCaseMixin):
    backend_alias = 'hg'


class TestHgChangesetsChanges(_ChangesetsChangesTestCaseMixin):
    backend_alias = 'hg'
