# encoding: utf-8
"""
Tests so called "in memory changesets" commit API of vcs.
"""

import datetime

import pytest

from kallithea.lib import vcs
from kallithea.lib.vcs.exceptions import (
    EmptyRepositoryError, NodeAlreadyAddedError, NodeAlreadyChangedError, NodeAlreadyExistsError, NodeAlreadyRemovedError, NodeDoesNotExistError, NodeNotChangedError)
from kallithea.lib.vcs.nodes import DirNode, FileNode
from kallithea.lib.vcs.utils import safe_unicode
from kallithea.tests.vcs.base import _BackendTestMixin


class InMemoryChangesetTestMixin(_BackendTestMixin):

    @classmethod
    def _get_commits(cls):
        # Note: this is slightly different than the regular _get_commits methods
        # as we don't actually return any commits. The creation of commits is
        # handled in the tests themselves.
        cls.nodes = [
            FileNode('foobar', content='Foo & bar'),
            FileNode('foobar2', content='Foo & bar, doubled!'),
            FileNode('foo bar with spaces', content=''),
            FileNode('foo/bar/baz', content='Inside'),
            FileNode('foo/bar/file.bin', content='\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00;\x00\x03\x00\xfe\xff\t\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x1a\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x18\x00\x00\x00\x01\x00\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'),
        ]
        commits = []
        return commits

    def test_add(self):
        rev_count = len(self.repo.revisions)
        to_add = [FileNode(node.path, content=node.content)
            for node in self.nodes]
        for node in to_add:
            self.imc.add(node)
        message = u'Added: %s' % ', '.join((node.path for node in self.nodes))
        author = unicode(self.__class__)
        changeset = self.imc.commit(message=message, author=author)

        newtip = self.repo.get_changeset()
        assert changeset == newtip
        assert rev_count + 1 == len(self.repo.revisions)
        assert newtip.message == message
        assert newtip.author == author
        assert not any((
            self.imc.added,
            self.imc.changed,
            self.imc.removed
        ))
        for node in to_add:
            assert newtip.get_node(node.path).content == node.content

    def test_add_in_bulk(self):
        rev_count = len(self.repo.revisions)
        to_add = [FileNode(node.path, content=node.content)
            for node in self.nodes]
        self.imc.add(*to_add)
        message = u'Added: %s' % ', '.join((node.path for node in self.nodes))
        author = unicode(self.__class__)
        changeset = self.imc.commit(message=message, author=author)

        newtip = self.repo.get_changeset()
        assert changeset == newtip
        assert rev_count + 1 == len(self.repo.revisions)
        assert newtip.message == message
        assert newtip.author == author
        assert not any((
            self.imc.added,
            self.imc.changed,
            self.imc.removed
        ))
        for node in to_add:
            assert newtip.get_node(node.path).content == node.content

    def test_add_actually_adds_all_nodes_at_second_commit_too(self):
        self.imc.add(FileNode('foo/bar/image.png', content='\0'))
        self.imc.add(FileNode('foo/README.txt', content='readme!'))
        changeset = self.imc.commit(u'Initial', u'joe.doe@example.com')
        assert isinstance(changeset.get_node('foo'), DirNode)
        assert isinstance(changeset.get_node('foo/bar'), DirNode)
        assert changeset.get_node('foo/bar/image.png').content == '\0'
        assert changeset.get_node('foo/README.txt').content == 'readme!'

        # commit some more files again
        to_add = [
            FileNode('foo/bar/foobaz/bar', content='foo'),
            FileNode('foo/bar/another/bar', content='foo'),
            FileNode('foo/baz.txt', content='foo'),
            FileNode('foobar/foobaz/file', content='foo'),
            FileNode('foobar/barbaz', content='foo'),
        ]
        self.imc.add(*to_add)
        changeset = self.imc.commit(u'Another', u'joe.doe@example.com')
        changeset.get_node('foo/bar/foobaz/bar').content == 'foo'
        changeset.get_node('foo/bar/another/bar').content == 'foo'
        changeset.get_node('foo/baz.txt').content == 'foo'
        changeset.get_node('foobar/foobaz/file').content == 'foo'
        changeset.get_node('foobar/barbaz').content == 'foo'

    def test_add_non_ascii_files(self):
        rev_count = len(self.repo.revisions)
        to_add = [
            FileNode('żółwik/zwierzątko', content='ćććć'),
            FileNode(u'żółwik/zwierzątko_uni', content=u'ćććć'),
        ]
        for node in to_add:
            self.imc.add(node)
        message = u'Added: %s' % ', '.join((node.path for node in self.nodes))
        author = unicode(self.__class__)
        changeset = self.imc.commit(message=message, author=author)

        newtip = self.repo.get_changeset()
        assert changeset == newtip
        assert rev_count + 1 == len(self.repo.revisions)
        assert newtip.message == message
        assert newtip.author == author
        assert not any((
            self.imc.added,
            self.imc.changed,
            self.imc.removed
        ))
        for node in to_add:
            assert newtip.get_node(node.path).content == node.content

    def test_add_raise_already_added(self):
        node = FileNode('foobar', content='baz')
        self.imc.add(node)
        with pytest.raises(NodeAlreadyAddedError):
            self.imc.add(node)

    def test_check_integrity_raise_already_exist(self):
        node = FileNode('foobar', content='baz')
        self.imc.add(node)
        self.imc.commit(message=u'Added foobar', author=unicode(self))
        self.imc.add(node)
        with pytest.raises(NodeAlreadyExistsError):
            self.imc.commit(message='new message',
                            author=str(self))

    def test_change(self):
        self.imc.add(FileNode('foo/bar/baz', content='foo'))
        self.imc.add(FileNode('foo/fbar', content='foobar'))
        tip = self.imc.commit(u'Initial', u'joe.doe@example.com')

        # Change node's content
        node = FileNode('foo/bar/baz', content='My **changed** content')
        self.imc.change(node)
        self.imc.commit(u'Changed %s' % node.path, u'joe.doe@example.com')

        newtip = self.repo.get_changeset()
        assert tip != newtip
        assert tip.id != newtip.id
        assert newtip.get_node('foo/bar/baz').content == 'My **changed** content'

    def test_change_non_ascii(self):
        to_add = [
            FileNode('żółwik/zwierzątko', content='ćććć'),
            FileNode(u'żółwik/zwierzątko_uni', content=u'ćććć'),
        ]
        for node in to_add:
            self.imc.add(node)

        tip = self.imc.commit(u'Initial', u'joe.doe@example.com')

        # Change node's content
        node = FileNode('żółwik/zwierzątko', content='My **changed** content')
        self.imc.change(node)
        self.imc.commit(u'Changed %s' % safe_unicode(node.path),
                        u'joe.doe@example.com')

        node = FileNode(u'żółwik/zwierzątko_uni', content=u'My **changed** content')
        self.imc.change(node)
        self.imc.commit(u'Changed %s' % safe_unicode(node.path),
                        u'joe.doe@example.com')

        newtip = self.repo.get_changeset()
        assert tip != newtip
        assert tip.id != newtip.id

        assert newtip.get_node('żółwik/zwierzątko').content == 'My **changed** content'
        assert newtip.get_node('żółwik/zwierzątko_uni').content == 'My **changed** content'

    def test_change_raise_empty_repository(self):
        node = FileNode('foobar')
        with pytest.raises(EmptyRepositoryError):
            self.imc.change(node)

    def test_check_integrity_change_raise_node_does_not_exist(self):
        node = FileNode('foobar', content='baz')
        self.imc.add(node)
        self.imc.commit(message=u'Added foobar', author=unicode(self))
        node = FileNode('not-foobar', content='')
        self.imc.change(node)
        with pytest.raises(NodeDoesNotExistError):
            self.imc.commit(message='Changed not existing node', author=str(self))

    def test_change_raise_node_already_changed(self):
        node = FileNode('foobar', content='baz')
        self.imc.add(node)
        self.imc.commit(message=u'Added foobar', author=unicode(self))
        node = FileNode('foobar', content='more baz')
        self.imc.change(node)
        with pytest.raises(NodeAlreadyChangedError):
            self.imc.change(node)

    def test_check_integrity_change_raise_node_not_changed(self):
        self.test_add()  # Performs first commit

        node = FileNode(self.nodes[0].path, content=self.nodes[0].content)
        self.imc.change(node)
        with pytest.raises(NodeNotChangedError):
            self.imc.commit(
                message=u'Trying to mark node as changed without touching it',
                author=unicode(self)
            )

    def test_change_raise_node_already_removed(self):
        node = FileNode('foobar', content='baz')
        self.imc.add(node)
        self.imc.commit(message=u'Added foobar', author=unicode(self))
        self.imc.remove(FileNode('foobar'))
        with pytest.raises(NodeAlreadyRemovedError):
            self.imc.change(node)

    def test_remove(self):
        self.test_add()  # Performs first commit

        tip = self.repo.get_changeset()
        node = self.nodes[0]
        assert node.content == tip.get_node(node.path).content
        self.imc.remove(node)
        self.imc.commit(message=u'Removed %s' % node.path, author=unicode(self))

        newtip = self.repo.get_changeset()
        assert tip != newtip
        assert tip.id != newtip.id
        with pytest.raises(NodeDoesNotExistError):
            newtip.get_node(node.path)

    def test_remove_last_file_from_directory(self):
        node = FileNode('omg/qwe/foo/bar', content='foobar')
        self.imc.add(node)
        self.imc.commit(u'added', u'joe doe')

        self.imc.remove(node)
        tip = self.imc.commit(u'removed', u'joe doe')
        with pytest.raises(NodeDoesNotExistError):
            tip.get_node('omg/qwe/foo/bar')

    def test_remove_raise_node_does_not_exist(self):
        self.imc.remove(self.nodes[0])
        with pytest.raises(NodeDoesNotExistError):
            self.imc.commit(
                message='Trying to remove node at empty repository',
                author=str(self)
            )

    def test_check_integrity_remove_raise_node_does_not_exist(self):
        self.test_add()  # Performs first commit

        node = FileNode('no-such-file')
        self.imc.remove(node)
        with pytest.raises(NodeDoesNotExistError):
            self.imc.commit(
                message=u'Trying to remove not existing node',
                author=unicode(self)
            )

    def test_remove_raise_node_already_removed(self):
        self.test_add() # Performs first commit

        node = FileNode(self.nodes[0].path)
        self.imc.remove(node)
        with pytest.raises(NodeAlreadyRemovedError):
            self.imc.remove(node)

    def test_remove_raise_node_already_changed(self):
        self.test_add()  # Performs first commit

        node = FileNode(self.nodes[0].path, content='Bending time')
        self.imc.change(node)
        with pytest.raises(NodeAlreadyChangedError):
            self.imc.remove(node)

    def test_reset(self):
        self.imc.add(FileNode('foo', content='bar'))
        #self.imc.change(FileNode('baz', content='new'))
        #self.imc.remove(FileNode('qwe'))
        self.imc.reset()
        assert not any((
            self.imc.added,
            self.imc.changed,
            self.imc.removed
        ))

    def test_multiple_commits(self):
        N = 3  # number of commits to perform
        last = None
        for x in xrange(N):
            fname = 'file%s' % str(x).rjust(5, '0')
            content = 'foobar\n' * x
            node = FileNode(fname, content=content)
            self.imc.add(node)
            commit = self.imc.commit(u"Commit no. %s" % (x + 1), author=u'vcs')
            assert last != commit
            last = commit

        # Check commit number for same repo
        assert len(self.repo.revisions) == N

        # Check commit number for recreated repo
        assert len(self.repo.revisions) == N

    def test_date_attr(self):
        node = FileNode('foobar.txt', content='Foobared!')
        self.imc.add(node)
        date = datetime.datetime(1985, 1, 30, 1, 45)
        commit = self.imc.commit(u"Committed at time when I was born ;-)",
            author=u'lb <lb@example.com>', date=date)

        assert commit.date == date


class TestGitInMemoryChangeset(InMemoryChangesetTestMixin):
    backend_alias = 'git'


class TestHgInMemoryChangeset(InMemoryChangesetTestMixin):
    backend_alias = 'hg'
