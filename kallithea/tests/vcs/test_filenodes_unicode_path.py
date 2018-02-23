# encoding: utf8

import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.test_inmemchangesets import BackendBaseTestCase


class FileNodeUnicodePathTestsMixin(object):

    fname = 'ąśðąęłąć.txt'
    ufname = (fname).decode('utf-8')

    def get_commits(self):
        self.nodes = [
            FileNode(self.fname, content='Foobar'),
        ]

        commits = [
            {
                'message': 'Initial commit',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': self.nodes,
            },
        ]
        return commits

    def test_filenode_path(self):
        node = self.tip.get_node(self.fname)
        unode = self.tip.get_node(self.ufname)
        assert node == unode


class TestGitFileNodeUnicodePath(FileNodeUnicodePathTestsMixin, BackendBaseTestCase):
    backend_alias = 'git'


class TestHgFileNodeUnicodePath(FileNodeUnicodePathTestsMixin, BackendBaseTestCase):
    backend_alias = 'hg'
