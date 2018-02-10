# encoding: utf8

import datetime

from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.test_inmemchangesets import BackendBaseTestCase
from kallithea.tests.vcs.conf import SCM_TESTS


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


for alias in SCM_TESTS:
    attrs = {
        'backend_alias': alias,
    }
    cls_name = ''.join(('test %s file node unicode path' % alias).title()
        .split())
    bases = (FileNodeUnicodePathTestsMixin, BackendBaseTestCase)
    globals()[cls_name] = type(cls_name, bases, attrs)
