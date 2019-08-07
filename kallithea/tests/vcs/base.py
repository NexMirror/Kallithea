"""
Module providing backend independent mixin class.
"""
import datetime
import time

import pytest

from kallithea.lib import vcs
from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.conf import get_new_dir


class _BackendTestMixin(object):
    """
    This is a backend independent test case class

    It is possible to set following attributes at subclass:

    - ``backend_alias``: alias of used backend (see ``vcs.BACKENDS``)
    - ``recreate_repo_per_test``: If set to ``False``, repo would NOT be created
      before every single test. Defaults to ``True``.
    """
    recreate_repo_per_test = True

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

    # Note: cannot use classmethod fixtures with pytest 3.7.1+
    @pytest.fixture(autouse=True,
                    scope='class')
    def _configure_backend(self, request):
        Backend = vcs.get_backend(self.backend_alias)
        type(self).backend_class = Backend
        type(self).setup_repo(Backend)

    @classmethod
    def setup_empty_repo(cls, backend):
        repo_path = get_new_dir(str(time.time()))
        repo = backend(repo_path, create=True)
        return repo

    @classmethod
    def setup_repo(cls, backend):
        cls.repo = cls.setup_empty_repo(backend)
        cls.imc = cls.repo.in_memory_changeset
        cls.default_branch = cls.repo.DEFAULT_BRANCH_NAME

        for commit in cls._get_commits():
            for node in commit.get('added', []):
                cls.imc.add(FileNode(node.path, content=node.content))
            for node in commit.get('changed', []):
                cls.imc.change(FileNode(node.path, content=node.content))
            for node in commit.get('removed', []):
                cls.imc.remove(FileNode(node.path))

            cls.tip = cls.imc.commit(message=unicode(commit['message']),
                                     author=unicode(commit['author']),
                                     date=commit['date'])

    @pytest.fixture(autouse=True)
    def _possibly_recreate_repo(self):
        if getattr(self, 'recreate_repo_per_test', False):
            self.setup_repo(self.backend_class)
