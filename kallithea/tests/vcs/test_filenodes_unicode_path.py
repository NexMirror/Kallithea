# encoding: utf-8

import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin


class FileNodeUnicodePathTestsMixin(_BackendTestMixin):

    fname = 'ąśðąęłąć.txt'
    ufname = (fname).decode('utf-8')

    @classmethod
    def _get_commits(cls):
        cls.nodes = [
            FileNode(cls.fname, content='Foobar'),
        ]

        commits = [
            {
                'message': 'Initial commit',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': cls.nodes,
            },
        ]
        return commits

    def test_filenode_path(self):
        node = self.tip.get_node(self.fname)
        unode = self.tip.get_node(self.ufname)
        assert node == unode


class TestGitFileNodeUnicodePath(FileNodeUnicodePathTestsMixin):
    backend_alias = 'git'


class TestHgFileNodeUnicodePath(FileNodeUnicodePathTestsMixin):
    backend_alias = 'hg'
