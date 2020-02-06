# encoding: utf-8

import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin


class FileNodeUnicodePathTestsMixin(_BackendTestMixin):

    fname = 'ąśðąęłąć.txt'

    @classmethod
    def _get_commits(cls):
        return [
            {
                'message': 'Initial commit',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [FileNode(cls.fname, content='Foobar')],
            },
        ]

    def test_filenode_path(self):
        node = self.tip.get_node(self.fname)
        assert node.path == self.fname


class TestGitFileNodeUnicodePath(FileNodeUnicodePathTestsMixin):
    backend_alias = 'git'


class TestHgFileNodeUnicodePath(FileNodeUnicodePathTestsMixin):
    backend_alias = 'hg'
