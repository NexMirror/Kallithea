import os

import mock
import pytest

from kallithea.lib.utils2 import safe_str
from kallithea.lib.vcs.backends.hg import MercurialChangeset, MercurialRepository
from kallithea.lib.vcs.exceptions import NodeDoesNotExistError, RepositoryError, VCSError
from kallithea.lib.vcs.nodes import NodeKind, NodeState
from kallithea.tests.vcs.conf import TEST_HG_REPO, TEST_HG_REPO_CLONE, TEST_HG_REPO_PULL, TESTS_TMP_PATH


class TestMercurialRepository(object):

    def __check_for_existing_repo(self):
        if os.path.exists(TEST_HG_REPO_CLONE):
            pytest.fail('Cannot test mercurial clone repo as location %s already '
                      'exists. You should manually remove it first.'
                      % TEST_HG_REPO_CLONE)

    def setup_method(self):
        self.repo = MercurialRepository(safe_str(TEST_HG_REPO))

    def test_wrong_repo_path(self):
        wrong_repo_path = os.path.join(TESTS_TMP_PATH, 'errorrepo')
        with pytest.raises(RepositoryError):
            MercurialRepository(wrong_repo_path)

    def test_unicode_path_repo(self):
        with pytest.raises(VCSError):
            MercurialRepository(u'iShouldFail')

    def test_repo_clone(self):
        self.__check_for_existing_repo()
        repo = MercurialRepository(safe_str(TEST_HG_REPO))
        repo_clone = MercurialRepository(TEST_HG_REPO_CLONE,
            src_url=TEST_HG_REPO, update_after_clone=True)
        assert len(repo.revisions) == len(repo_clone.revisions)
        # Checking hashes of changesets should be enough
        for changeset in repo.get_changesets():
            raw_id = changeset.raw_id
            assert raw_id == repo_clone.get_changeset(raw_id).raw_id

    def test_repo_clone_with_update(self):
        repo = MercurialRepository(safe_str(TEST_HG_REPO))
        repo_clone = MercurialRepository(TEST_HG_REPO_CLONE + '_w_update',
            src_url=TEST_HG_REPO, update_after_clone=True)
        assert len(repo.revisions) == len(repo_clone.revisions)

        # check if current workdir was updated
        assert os.path.isfile(
            os.path.join(
                TEST_HG_REPO_CLONE + '_w_update', 'MANIFEST.in'
            )
        )

    def test_repo_clone_without_update(self):
        repo = MercurialRepository(safe_str(TEST_HG_REPO))
        repo_clone = MercurialRepository(TEST_HG_REPO_CLONE + '_wo_update',
            src_url=TEST_HG_REPO, update_after_clone=False)
        assert len(repo.revisions) == len(repo_clone.revisions)
        assert not os.path.isfile(
            os.path.join(
                TEST_HG_REPO_CLONE + '_wo_update', 'MANIFEST.in'
            )
        )

    def test_pull(self):
        if os.path.exists(TEST_HG_REPO_PULL):
            pytest.fail('Cannot test mercurial pull command as location %s '
                      'already exists. You should manually remove it first'
                      % TEST_HG_REPO_PULL)
        repo_new = MercurialRepository(TEST_HG_REPO_PULL, create=True)
        assert len(self.repo.revisions) > len(repo_new.revisions)

        repo_new.pull(self.repo.path)
        repo_new = MercurialRepository(TEST_HG_REPO_PULL)
        assert len(self.repo.revisions) == len(repo_new.revisions)

    def test_revisions(self):
        # there are 21 revisions at bitbucket now
        # so we can assume they would be available from now on
        subset = set(['b986218ba1c9b0d6a259fac9b050b1724ed8e545',
                 '3d8f361e72ab303da48d799ff1ac40d5ac37c67e',
                 '6cba7170863a2411822803fa77a0a264f1310b35',
                 '56349e29c2af3ac913b28bde9a2c6154436e615b',
                 '2dda4e345facb0ccff1a191052dd1606dba6781d',
                 '6fff84722075f1607a30f436523403845f84cd9e',
                 '7d4bc8ec6be56c0f10425afb40b6fc315a4c25e7',
                 '3803844fdbd3b711175fc3da9bdacfcd6d29a6fb',
                 'dc5d2c0661b61928834a785d3e64a3f80d3aad9c',
                 'be90031137367893f1c406e0a8683010fd115b79',
                 'db8e58be770518cbb2b1cdfa69146e47cd481481',
                 '84478366594b424af694a6c784cb991a16b87c21',
                 '17f8e105dddb9f339600389c6dc7175d395a535c',
                 '20a662e756499bde3095ffc9bc0643d1def2d0eb',
                 '2e319b85e70a707bba0beff866d9f9de032aa4f9',
                 '786facd2c61deb9cf91e9534735124fb8fc11842',
                 '94593d2128d38210a2fcd1aabff6dda0d6d9edf8',
                 'aa6a0de05b7612707db567078e130a6cd114a9a7',
                 'eada5a770da98ab0dd7325e29d00e0714f228d09'
                ])
        assert subset.issubset(set(self.repo.revisions))

        # check if we have the proper order of revisions
        org = ['b986218ba1c9b0d6a259fac9b050b1724ed8e545',
                '3d8f361e72ab303da48d799ff1ac40d5ac37c67e',
                '6cba7170863a2411822803fa77a0a264f1310b35',
                '56349e29c2af3ac913b28bde9a2c6154436e615b',
                '2dda4e345facb0ccff1a191052dd1606dba6781d',
                '6fff84722075f1607a30f436523403845f84cd9e',
                '7d4bc8ec6be56c0f10425afb40b6fc315a4c25e7',
                '3803844fdbd3b711175fc3da9bdacfcd6d29a6fb',
                'dc5d2c0661b61928834a785d3e64a3f80d3aad9c',
                'be90031137367893f1c406e0a8683010fd115b79',
                'db8e58be770518cbb2b1cdfa69146e47cd481481',
                '84478366594b424af694a6c784cb991a16b87c21',
                '17f8e105dddb9f339600389c6dc7175d395a535c',
                '20a662e756499bde3095ffc9bc0643d1def2d0eb',
                '2e319b85e70a707bba0beff866d9f9de032aa4f9',
                '786facd2c61deb9cf91e9534735124fb8fc11842',
                '94593d2128d38210a2fcd1aabff6dda0d6d9edf8',
                'aa6a0de05b7612707db567078e130a6cd114a9a7',
                'eada5a770da98ab0dd7325e29d00e0714f228d09',
                '2c1885c735575ca478bf9e17b0029dca68824458',
                'd9bcd465040bf869799b09ad732c04e0eea99fe9',
                '469e9c847fe1f6f7a697b8b25b4bc5b48780c1a7',
                '4fb8326d78e5120da2c7468dcf7098997be385da',
                '62b4a097164940bd66030c4db51687f3ec035eed',
                '536c1a19428381cfea92ac44985304f6a8049569',
                '965e8ab3c44b070cdaa5bf727ddef0ada980ecc4',
                '9bb326a04ae5d98d437dece54be04f830cf1edd9',
                'f8940bcb890a98c4702319fbe36db75ea309b475',
                'ff5ab059786ebc7411e559a2cc309dfae3625a3b',
                '6b6ad5f82ad5bb6190037671bd254bd4e1f4bf08',
                'ee87846a61c12153b51543bf860e1026c6d3dcba', ]
        assert org == self.repo.revisions[:31]

    def test_iter_slice(self):
        sliced = list(self.repo[:10])
        itered = list(self.repo)[:10]
        assert sliced == itered

    def test_slicing(self):
        # 4 1 5 10 95
        for sfrom, sto, size in [(0, 4, 4), (1, 2, 1), (10, 15, 5),
                                 (10, 20, 10), (5, 100, 95)]:
            revs = list(self.repo[sfrom:sto])
            assert len(revs) == size
            assert revs[0] == self.repo.get_changeset(sfrom)
            assert revs[-1] == self.repo.get_changeset(sto - 1)

    def test_branches(self):
        # TODO: Need more tests here

        # active branches
        assert 'default' in self.repo.branches
        assert 'stable' in self.repo.branches

        # closed
        assert 'git' in self.repo._get_branches(closed=True)
        assert 'web' in self.repo._get_branches(closed=True)

        for name, id in self.repo.branches.items():
            assert isinstance(self.repo.get_changeset(id), MercurialChangeset)

    def test_tip_in_tags(self):
        # tip is always a tag
        assert 'tip' in self.repo.tags

    def test_tip_changeset_in_tags(self):
        tip = self.repo.get_changeset()
        assert self.repo.tags['tip'] == tip.raw_id

    def test_initial_changeset(self):

        init_chset = self.repo.get_changeset(0)
        assert init_chset.message == 'initial import'
        assert init_chset.author == 'Marcin Kuzminski <marcin@python-blog.com>'
        assert sorted(init_chset._file_paths) == sorted([
            'vcs/__init__.py',
            'vcs/backends/BaseRepository.py',
            'vcs/backends/__init__.py',
        ])

        assert sorted(init_chset._dir_paths) == sorted(['', 'vcs', 'vcs/backends'])

        with pytest.raises(NodeDoesNotExistError):
            init_chset.get_node(path='foobar')

        node = init_chset.get_node('vcs/')
        assert hasattr(node, 'kind')
        assert node.kind == NodeKind.DIR

        node = init_chset.get_node('vcs')
        assert hasattr(node, 'kind')
        assert node.kind == NodeKind.DIR

        node = init_chset.get_node('vcs/__init__.py')
        assert hasattr(node, 'kind')
        assert node.kind == NodeKind.FILE

    def test_not_existing_changeset(self):
        # rawid
        with pytest.raises(RepositoryError):
            self.repo.get_changeset('abcd' * 10)
        # shortid
        with pytest.raises(RepositoryError):
            self.repo.get_changeset('erro' * 4)
        # numeric
        with pytest.raises(RepositoryError):
            self.repo.get_changeset(self.repo.count() + 1)

        # Small chance we ever get to this one
        revision = pow(2, 30)
        with pytest.raises(RepositoryError):
            self.repo.get_changeset(revision)

    def test_changeset10(self):

        chset10 = self.repo.get_changeset(10)
        readme = """===
VCS
===

Various Version Control System management abstraction layer for Python.

Introduction
------------

TODO: To be written...

"""
        node = chset10.get_node('README.rst')
        assert node.kind == NodeKind.FILE
        assert node.content == readme

    @mock.patch('kallithea.lib.vcs.backends.hg.repository.diffopts')
    def test_get_diff_does_not_sanitize_zero_context(self, mock_diffopts):
        zero_context = 0

        self.repo.get_diff(0, 1, 'foo', context=zero_context)

        mock_diffopts.assert_called_once_with(git=True, showfunc=True, ignorews=False, context=zero_context)

    @mock.patch('kallithea.lib.vcs.backends.hg.repository.diffopts')
    def test_get_diff_sanitizes_negative_context(self, mock_diffopts):
        negative_context = -10
        zero_context = 0

        self.repo.get_diff(0, 1, 'foo', context=negative_context)

        mock_diffopts.assert_called_once_with(git=True, showfunc=True, ignorews=False, context=zero_context)


class TestMercurialChangeset(object):

    def setup_method(self):
        self.repo = MercurialRepository(safe_str(TEST_HG_REPO))

    def _test_equality(self, changeset):
        revision = changeset.revision
        assert changeset == self.repo.get_changeset(revision)

    def test_equality(self):
        revs = [0, 10, 20]
        changesets = [self.repo.get_changeset(rev) for rev in revs]
        for changeset in changesets:
            self._test_equality(changeset)

    def test_default_changeset(self):
        tip = self.repo.get_changeset('tip')
        assert tip == self.repo.get_changeset()
        assert tip == self.repo.get_changeset(revision=None)
        assert tip == list(self.repo[-1:])[0]

    def test_root_node(self):
        tip = self.repo.get_changeset('tip')
        assert tip.root is tip.get_node('')

    def test_lazy_fetch(self):
        """
        Test if changeset's nodes expands and are cached as we walk through
        the revision. This test is somewhat hard to write as order of tests
        is a key here. Written by running command after command in a shell.
        """
        chset = self.repo.get_changeset(45)
        assert len(chset.nodes) == 0
        root = chset.root
        assert len(chset.nodes) == 1
        assert len(root.nodes) == 8
        # accessing root.nodes updates chset.nodes
        assert len(chset.nodes) == 9

        docs = root.get_node('docs')
        # we haven't yet accessed anything new as docs dir was already cached
        assert len(chset.nodes) == 9
        assert len(docs.nodes) == 8
        # accessing docs.nodes updates chset.nodes
        assert len(chset.nodes) == 17

        assert docs is chset.get_node('docs')
        assert docs is root.nodes[0]
        assert docs is root.dirs[0]
        assert docs is chset.get_node('docs')

    def test_nodes_with_changeset(self):
        chset = self.repo.get_changeset(45)
        root = chset.root
        docs = root.get_node('docs')
        assert docs is chset.get_node('docs')
        api = docs.get_node('api')
        assert api is chset.get_node('docs/api')
        index = api.get_node('index.rst')
        assert index is chset.get_node('docs/api/index.rst')
        assert index is chset.get_node('docs').get_node('api').get_node('index.rst')

    def test_branch_and_tags(self):
        chset0 = self.repo.get_changeset(0)
        assert chset0.branch == 'default'
        assert chset0.branches == ['default']
        assert chset0.tags == []

        chset10 = self.repo.get_changeset(10)
        assert chset10.branch == 'default'
        assert chset10.branches == ['default']
        assert chset10.tags == []

        chset44 = self.repo.get_changeset(44)
        assert chset44.branch == 'web'
        assert chset44.branches == ['web']

        tip = self.repo.get_changeset('tip')
        assert 'tip' in tip.tags

    def _test_file_size(self, revision, path, size):
        node = self.repo.get_changeset(revision).get_node(path)
        assert node.is_file()
        assert node.size == size

    def test_file_size(self):
        to_check = (
            (10, 'setup.py', 1068),
            (20, 'setup.py', 1106),
            (60, 'setup.py', 1074),

            (10, 'vcs/backends/base.py', 2921),
            (20, 'vcs/backends/base.py', 3936),
            (60, 'vcs/backends/base.py', 6189),
        )
        for revision, path, size in to_check:
            self._test_file_size(revision, path, size)

    def _test_dir_size(self, revision, path, size):
        node = self.repo.get_changeset(revision).get_node(path)
        assert not node.is_file()
        assert node.size == size

    def test_dir_size(self):
        to_check = (
            ('96507bd11ecc', '/', 682421),
            ('a53d9201d4bc', '/', 682410),
            ('90243de06161', '/', 682006),
        )
        for revision, path, size in to_check:
            self._test_dir_size(revision, path, size)

    def test_repo_size(self):
        assert self.repo.size == 682421

    def test_file_history(self):
        # we can only check if those revisions are present in the history
        # as we cannot update this test every time file is changed
        files = {
            'setup.py': [7, 18, 45, 46, 47, 69, 77],
            'vcs/nodes.py': [7, 8, 24, 26, 30, 45, 47, 49, 56, 57, 58, 59, 60,
                61, 73, 76],
            'vcs/backends/hg.py': [4, 5, 6, 11, 12, 13, 14, 15, 16, 21, 22, 23,
                26, 27, 28, 30, 31, 33, 35, 36, 37, 38, 39, 40, 41, 44, 45, 47,
                48, 49, 53, 54, 55, 58, 60, 61, 67, 68, 69, 70, 73, 77, 78, 79,
                82],
        }
        for path, revs in files.items():
            tip = self.repo.get_changeset(revs[-1])
            node = tip.get_node(path)
            node_revs = [chset.revision for chset in node.history]
            assert set(revs).issubset(set(node_revs)), \
                "We assumed that %s is subset of revisions for which file %s " \
                "has been changed, and history of that node returned: %s" \
                % (revs, path, node_revs)

    def test_file_annotate(self):
        files = {
                 'vcs/backends/__init__.py':
                  {89: {'lines_no': 31,
                        'changesets': [32, 32, 61, 32, 32, 37, 32, 32, 32, 44,
                                       37, 37, 37, 37, 45, 37, 44, 37, 37, 37,
                                       32, 32, 32, 32, 37, 32, 37, 37, 32,
                                       32, 32]},
                   20: {'lines_no': 1,
                        'changesets': [4]},
                   55: {'lines_no': 31,
                        'changesets': [32, 32, 45, 32, 32, 37, 32, 32, 32, 44,
                                       37, 37, 37, 37, 45, 37, 44, 37, 37, 37,
                                       32, 32, 32, 32, 37, 32, 37, 37, 32,
                                       32, 32]}},
                 'vcs/exceptions.py':
                 {89: {'lines_no': 18,
                       'changesets': [16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
                                      16, 16, 17, 16, 16, 18, 18, 18]},
                  20: {'lines_no': 18,
                       'changesets': [16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
                                      16, 16, 17, 16, 16, 18, 18, 18]},
                  55: {'lines_no': 18, 'changesets': [16, 16, 16, 16, 16, 16,
                                                      16, 16, 16, 16, 16, 16,
                                                      17, 16, 16, 18, 18, 18]}},
                 'MANIFEST.in': {89: {'lines_no': 5,
                                      'changesets': [7, 7, 7, 71, 71]},
                                 20: {'lines_no': 3,
                                      'changesets': [7, 7, 7]},
                                 55: {'lines_no': 3,
                                     'changesets': [7, 7, 7]}}}

        for fname, revision_dict in files.items():
            for rev, data in revision_dict.items():
                cs = self.repo.get_changeset(rev)
                l1_1 = [x[1] for x in cs.get_file_annotate(fname)]
                l1_2 = [x[2]().raw_id for x in cs.get_file_annotate(fname)]
                assert l1_1 == l1_2
                l1 = l1_2 = [x[2]().revision for x in cs.get_file_annotate(fname)]
                l2 = files[fname][rev]['changesets']
                assert l1 == l2, "The lists of revision for %s@rev%s" \
                    "from annotation list should match each other," \
                    "got \n%s \nvs \n%s " % (fname, rev, l1, l2)

    def test_changeset_state(self):
        """
        Tests which files have been added/changed/removed at particular revision
        """

        # rev 46ad32a4f974:
        # hg st --rev 46ad32a4f974
        #    changed: 13
        #    added:   20
        #    removed: 1
        changed = set(['.hgignore'
            , 'README.rst' , 'docs/conf.py' , 'docs/index.rst' , 'setup.py'
            , 'tests/test_hg.py' , 'tests/test_nodes.py' , 'vcs/__init__.py'
            , 'vcs/backends/__init__.py' , 'vcs/backends/base.py'
            , 'vcs/backends/hg.py' , 'vcs/nodes.py' , 'vcs/utils/__init__.py'])

        added = set(['docs/api/backends/hg.rst'
            , 'docs/api/backends/index.rst' , 'docs/api/index.rst'
            , 'docs/api/nodes.rst' , 'docs/api/web/index.rst'
            , 'docs/api/web/simplevcs.rst' , 'docs/installation.rst'
            , 'docs/quickstart.rst' , 'setup.cfg' , 'vcs/utils/baseui_config.py'
            , 'vcs/utils/web.py' , 'vcs/web/__init__.py' , 'vcs/web/exceptions.py'
            , 'vcs/web/simplevcs/__init__.py' , 'vcs/web/simplevcs/exceptions.py'
            , 'vcs/web/simplevcs/middleware.py' , 'vcs/web/simplevcs/models.py'
            , 'vcs/web/simplevcs/settings.py' , 'vcs/web/simplevcs/utils.py'
            , 'vcs/web/simplevcs/views.py'])

        removed = set(['docs/api.rst'])

        chset64 = self.repo.get_changeset('46ad32a4f974')
        assert set((node.path for node in chset64.added)) == added
        assert set((node.path for node in chset64.changed)) == changed
        assert set((node.path for node in chset64.removed)) == removed

        # rev b090f22d27d6:
        # hg st --rev b090f22d27d6
        #    changed: 13
        #    added:   20
        #    removed: 1
        chset88 = self.repo.get_changeset('b090f22d27d6')
        assert set((node.path for node in chset88.added)) == set()
        assert set((node.path for node in chset88.changed)) == set(['.hgignore'])
        assert set((node.path for node in chset88.removed)) == set()

        # 85:
        #    added:   2 ['vcs/utils/diffs.py', 'vcs/web/simplevcs/views/diffs.py']
        #    changed: 4 ['vcs/web/simplevcs/models.py', ...]
        #    removed: 1 ['vcs/utils/web.py']
        chset85 = self.repo.get_changeset(85)
        assert set((node.path for node in chset85.added)) == set([
            'vcs/utils/diffs.py',
            'vcs/web/simplevcs/views/diffs.py'
        ])

        assert set((node.path for node in chset85.changed)) == set([
            'vcs/web/simplevcs/models.py',
            'vcs/web/simplevcs/utils.py',
            'vcs/web/simplevcs/views/__init__.py',
            'vcs/web/simplevcs/views/repository.py',
        ])

        assert set((node.path for node in chset85.removed)) == set([
            'vcs/utils/web.py'
        ])


    def test_files_state(self):
        """
        Tests state of FileNodes.
        """
        chset = self.repo.get_changeset(85)
        node = chset.get_node('vcs/utils/diffs.py')
        assert node.state, NodeState.ADDED
        assert node.added
        assert not node.changed
        assert not node.not_changed
        assert not node.removed

        chset = self.repo.get_changeset(88)
        node = chset.get_node('.hgignore')
        assert node.state, NodeState.CHANGED
        assert not node.added
        assert node.changed
        assert not node.not_changed
        assert not node.removed

        chset = self.repo.get_changeset(85)
        node = chset.get_node('setup.py')
        assert node.state, NodeState.NOT_CHANGED
        assert not node.added
        assert not node.changed
        assert node.not_changed
        assert not node.removed

        # If node has REMOVED state then trying to fetch it would raise
        # ChangesetError exception
        chset = self.repo.get_changeset(2)
        path = 'vcs/backends/BaseRepository.py'
        with pytest.raises(NodeDoesNotExistError):
            chset.get_node(path)
        # but it would be one of ``removed`` (changeset's attribute)
        assert path in [rf.path for rf in chset.removed]

    def test_commit_message_is_unicode(self):
        for cm in self.repo:
            assert type(cm.message) == unicode

    def test_changeset_author_is_unicode(self):
        for cm in self.repo:
            assert type(cm.author) == unicode

    def test_repo_files_content_is_unicode(self):
        test_changeset = self.repo.get_changeset(100)
        for node in test_changeset.get_node('/'):
            if node.is_file():
                assert type(node.content) == unicode

    def test_wrong_path(self):
        # There is 'setup.py' in the root dir but not there:
        path = 'foo/bar/setup.py'
        with pytest.raises(VCSError):
            self.repo.get_changeset().get_node(path)

    def test_archival_file(self):
        # TODO:
        pass

    def test_archival_as_generator(self):
        # TODO:
        pass

    def test_archival_wrong_kind(self):
        tip = self.repo.get_changeset()
        with pytest.raises(VCSError):
            tip.fill_archive(kind='error')

    def test_archival_empty_prefix(self):
        # TODO:
        pass

    def test_author_email(self):
        assert 'marcin@python-blog.com' == self.repo.get_changeset('b986218ba1c9').author_email
        assert 'lukasz.balcerzak@python-center.pl' == self.repo.get_changeset('3803844fdbd3').author_email
        assert '' == self.repo.get_changeset('84478366594b').author_email

    def test_author_username(self):
        assert 'Marcin Kuzminski' == self.repo.get_changeset('b986218ba1c9').author_name
        assert 'Lukasz Balcerzak' == self.repo.get_changeset('3803844fdbd3').author_name
        assert 'marcink' == self.repo.get_changeset('84478366594b').author_name

    def test_successors(self):
        init_chset = self.repo.get_changeset(0)
        assert init_chset.successors == []

    def test_predecessors(self):
        init_chset = self.repo.get_changeset(0)
        assert len(init_chset.predecessors) == 0
