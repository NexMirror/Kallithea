import datetime
import os
import sys
import urllib2

import mock
import pytest

from kallithea.lib.vcs.backends.git import GitChangeset, GitRepository
from kallithea.lib.vcs.exceptions import NodeDoesNotExistError, RepositoryError, VCSError
from kallithea.lib.vcs.nodes import DirNode, FileNode, NodeKind, NodeState
from kallithea.model.scm import ScmModel
from kallithea.tests.vcs.base import _BackendTestMixin
from kallithea.tests.vcs.conf import TEST_GIT_REPO, TEST_GIT_REPO_CLONE, TESTS_TMP_PATH, get_new_dir


class TestGitRepository(object):

    def __check_for_existing_repo(self):
        if os.path.exists(TEST_GIT_REPO_CLONE):
            pytest.fail('Cannot test git clone repo as location %s already '
                      'exists. You should manually remove it first.'
                      % TEST_GIT_REPO_CLONE)

    def setup_method(self):
        self.repo = GitRepository(TEST_GIT_REPO)

    def test_wrong_repo_path(self):
        wrong_repo_path = os.path.join(TESTS_TMP_PATH, 'errorrepo')
        with pytest.raises(RepositoryError):
            GitRepository(wrong_repo_path)

    def test_git_cmd_injection(self):
        repo_inject_path = TEST_GIT_REPO + '; echo "Cake";'
        with pytest.raises(urllib2.URLError):
            # Should fail because URL will contain the parts after ; too
            GitRepository(get_new_dir('injection-repo'), src_url=repo_inject_path, update_after_clone=True, create=True)

        with pytest.raises(RepositoryError):
            # Should fail on direct clone call, which as of this writing does not happen outside of class
            clone_fail_repo = GitRepository(get_new_dir('injection-repo'), create=True)
            clone_fail_repo.clone(repo_inject_path, update_after_clone=True,)

        # Verify correct quoting of evil characters that should work on posix file systems
        if sys.platform == 'win32':
            # windows does not allow '"' in dir names
            # and some versions of the git client don't like ` and '
            tricky_path = get_new_dir("tricky-path-repo-$")
        else:
            tricky_path = get_new_dir("tricky-path-repo-$'\"`")
        successfully_cloned = GitRepository(tricky_path, src_url=TEST_GIT_REPO, update_after_clone=True, create=True)
        # Repo should have been created
        assert not successfully_cloned._repo.bare

        if sys.platform == 'win32':
            # windows does not allow '"' in dir names
            # and some versions of the git client don't like ` and '
            tricky_path_2 = get_new_dir("tricky-path-2-repo-$")
        else:
            tricky_path_2 = get_new_dir("tricky-path-2-repo-$'\"`")
        successfully_cloned2 = GitRepository(tricky_path_2, src_url=tricky_path, bare=True, create=True)
        # Repo should have been created and thus used correct quoting for clone
        assert successfully_cloned2._repo.bare

        # Should pass because URL has been properly quoted
        successfully_cloned.pull(tricky_path_2)
        successfully_cloned2.fetch(tricky_path)

    def test_repo_create_with_spaces_in_path(self):
        repo_path = get_new_dir("path with spaces")
        repo = GitRepository(repo_path, src_url=None, bare=True, create=True)
        # Repo should have been created
        assert repo._repo.bare

    def test_repo_clone(self):
        self.__check_for_existing_repo()
        repo = GitRepository(TEST_GIT_REPO)
        repo_clone = GitRepository(TEST_GIT_REPO_CLONE,
            src_url=TEST_GIT_REPO, create=True, update_after_clone=True)
        assert len(repo.revisions) == len(repo_clone.revisions)
        # Checking hashes of changesets should be enough
        for changeset in repo.get_changesets():
            raw_id = changeset.raw_id
            assert raw_id == repo_clone.get_changeset(raw_id).raw_id

    def test_repo_clone_with_spaces_in_path(self):
        repo_path = get_new_dir("path with spaces")
        successfully_cloned = GitRepository(repo_path, src_url=TEST_GIT_REPO, update_after_clone=True, create=True)
        # Repo should have been created
        assert not successfully_cloned._repo.bare

        successfully_cloned.pull(TEST_GIT_REPO)
        self.repo.fetch(repo_path)

    def test_repo_clone_without_create(self):
        with pytest.raises(RepositoryError):
            GitRepository(TEST_GIT_REPO_CLONE + '_wo_create', src_url=TEST_GIT_REPO)

    def test_repo_clone_with_update(self):
        repo = GitRepository(TEST_GIT_REPO)
        clone_path = TEST_GIT_REPO_CLONE + '_with_update'
        repo_clone = GitRepository(clone_path,
            create=True, src_url=TEST_GIT_REPO, update_after_clone=True)
        assert len(repo.revisions) == len(repo_clone.revisions)

        # check if current workdir was updated
        fpath = os.path.join(clone_path, 'MANIFEST.in')
        assert os.path.isfile(fpath) == True, 'Repo was cloned and updated but file %s could not be found' % fpath

    def test_repo_clone_without_update(self):
        repo = GitRepository(TEST_GIT_REPO)
        clone_path = TEST_GIT_REPO_CLONE + '_without_update'
        repo_clone = GitRepository(clone_path,
            create=True, src_url=TEST_GIT_REPO, update_after_clone=False)
        assert len(repo.revisions) == len(repo_clone.revisions)
        # check if current workdir was *NOT* updated
        fpath = os.path.join(clone_path, 'MANIFEST.in')
        # Make sure it's not bare repo
        assert not repo_clone._repo.bare
        assert os.path.isfile(fpath) == False, 'Repo was cloned and updated but file %s was found' % fpath

    def test_repo_clone_into_bare_repo(self):
        repo = GitRepository(TEST_GIT_REPO)
        clone_path = TEST_GIT_REPO_CLONE + '_bare.git'
        repo_clone = GitRepository(clone_path, create=True,
            src_url=repo.path, bare=True)
        assert repo_clone._repo.bare

    def test_create_repo_is_not_bare_by_default(self):
        repo = GitRepository(get_new_dir('not-bare-by-default'), create=True)
        assert not repo._repo.bare

    def test_create_bare_repo(self):
        repo = GitRepository(get_new_dir('bare-repo'), create=True, bare=True)
        assert repo._repo.bare

    def test_revisions(self):
        # there are 112 revisions (by now)
        # so we can assume they would be available from now on
        subset = set([
            'c1214f7e79e02fc37156ff215cd71275450cffc3',
            '38b5fe81f109cb111f549bfe9bb6b267e10bc557',
            'fa6600f6848800641328adbf7811fd2372c02ab2',
            '102607b09cdd60e2793929c4f90478be29f85a17',
            '49d3fd156b6f7db46313fac355dca1a0b94a0017',
            '2d1028c054665b962fa3d307adfc923ddd528038',
            'd7e0d30fbcae12c90680eb095a4f5f02505ce501',
            'ff7ca51e58c505fec0dd2491de52c622bb7a806b',
            'dd80b0f6cf5052f17cc738c2951c4f2070200d7f',
            '8430a588b43b5d6da365400117c89400326e7992',
            'd955cd312c17b02143c04fa1099a352b04368118',
            'f67b87e5c629c2ee0ba58f85197e423ff28d735b',
            'add63e382e4aabc9e1afdc4bdc24506c269b7618',
            'f298fe1189f1b69779a4423f40b48edf92a703fc',
            'bd9b619eb41994cac43d67cf4ccc8399c1125808',
            '6e125e7c890379446e98980d8ed60fba87d0f6d1',
            'd4a54db9f745dfeba6933bf5b1e79e15d0af20bd',
            '0b05e4ed56c802098dfc813cbe779b2f49e92500',
            '191caa5b2c81ed17c0794bf7bb9958f4dcb0b87e',
            '45223f8f114c64bf4d6f853e3c35a369a6305520',
            'ca1eb7957a54bce53b12d1a51b13452f95bc7c7e',
            'f5ea29fc42ef67a2a5a7aecff10e1566699acd68',
            '27d48942240f5b91dfda77accd2caac94708cc7d',
            '622f0eb0bafd619d2560c26f80f09e3b0b0d78af',
            'e686b958768ee96af8029fe19c6050b1a8dd3b2b'])
        assert subset.issubset(set(self.repo.revisions))

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
        # Removed (those are 'remotes' branches for cloned repo)
        #assert 'master' in self.repo.branches
        #assert 'gittree' in self.repo.branches
        #assert 'web-branch' in self.repo.branches
        for name, id in self.repo.branches.items():
            assert isinstance(self.repo.get_changeset(id), GitChangeset)

    def test_tags(self):
        # TODO: Need more tests here
        assert 'v0.1.1' in self.repo.tags
        assert 'v0.1.2' in self.repo.tags
        for name, id in self.repo.tags.items():
            assert isinstance(self.repo.get_changeset(id), GitChangeset)

    def _test_single_changeset_cache(self, revision):
        chset = self.repo.get_changeset(revision)
        assert revision in self.repo.changesets
        assert chset is self.repo.changesets[revision]

    def test_initial_changeset(self):
        id = self.repo.revisions[0]
        init_chset = self.repo.get_changeset(id)
        assert init_chset.message == 'initial import\n'
        assert init_chset.author == 'Marcin Kuzminski <marcin@python-blog.com>'
        for path in ('vcs/__init__.py',
                     'vcs/backends/BaseRepository.py',
                     'vcs/backends/__init__.py'):
            assert isinstance(init_chset.get_node(path), FileNode)
        for path in ('', 'vcs', 'vcs/backends'):
            assert isinstance(init_chset.get_node(path), DirNode)

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
        with pytest.raises(RepositoryError):
            self.repo.get_changeset('f' * 40)

    def test_changeset10(self):

        chset10 = self.repo.get_changeset(self.repo.revisions[9])
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


class TestGitChangeset(object):

    def setup_method(self):
        self.repo = GitRepository(TEST_GIT_REPO)

    def test_default_changeset(self):
        tip = self.repo.get_changeset()
        assert tip == self.repo.get_changeset(None)
        assert tip == self.repo.get_changeset('tip')

    def test_root_node(self):
        tip = self.repo.get_changeset()
        assert tip.root is tip.get_node('')

    def test_lazy_fetch(self):
        """
        Test if changeset's nodes expands and are cached as we walk through
        the revision. This test is somewhat hard to write as order of tests
        is a key here. Written by running command after command in a shell.
        """
        commit_id = '2a13f185e4525f9d4b59882791a2d397b90d5ddc'
        assert commit_id in self.repo.revisions
        chset = self.repo.get_changeset(commit_id)
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
        commit_id = '2a13f185e4525f9d4b59882791a2d397b90d5ddc'
        chset = self.repo.get_changeset(commit_id)
        root = chset.root
        docs = root.get_node('docs')
        assert docs is chset.get_node('docs')
        api = docs.get_node('api')
        assert api is chset.get_node('docs/api')
        index = api.get_node('index.rst')
        assert index is chset.get_node('docs/api/index.rst')
        assert index is chset.get_node('docs') \
                             .get_node('api') \
                             .get_node('index.rst')

    def test_branch_and_tags(self):
        # Those tests seem to show wrong results:
        # in Git, only heads have a branch - most changesets don't
        rev0 = self.repo.revisions[0]
        chset0 = self.repo.get_changeset(rev0)
        assert chset0.branch is None # should be 'master'?
        assert chset0.branches == [] # should be 'master'?
        assert chset0.tags == []

        rev10 = self.repo.revisions[10]
        chset10 = self.repo.get_changeset(rev10)
        assert chset10.branch is None # should be 'master'?
        assert chset10.branches == [] # should be 'master'?
        assert chset10.tags == []

        rev44 = self.repo.revisions[44]
        chset44 = self.repo.get_changeset(rev44)
        assert chset44.branch is None # should be 'web-branch'?
        assert chset44.branches == [] # should be 'web-branch'?

        tip = self.repo.get_changeset('tip')
        assert 'tip' not in tip.tags # it should be?
        assert not tip.tags # how it is!

    def _test_slices(self, limit, offset):
        count = self.repo.count()
        changesets = self.repo.get_changesets(limit=limit, offset=offset)
        idx = 0
        for changeset in changesets:
            rev = offset + idx
            idx += 1
            rev_id = self.repo.revisions[rev]
            if idx > limit:
                pytest.fail("Exceeded limit already (getting revision %s, "
                    "there are %s total revisions, offset=%s, limit=%s)"
                    % (rev_id, count, offset, limit))
            assert changeset == self.repo.get_changeset(rev_id)
        result = list(self.repo.get_changesets(limit=limit, offset=offset))
        start = offset
        end = limit and offset + limit or None
        sliced = list(self.repo[start:end])
        pytest.failUnlessEqual(result, sliced,
            msg="Comparison failed for limit=%s, offset=%s"
            "(get_changeset returned: %s and sliced: %s"
            % (limit, offset, result, sliced))

    def _test_file_size(self, revision, path, size):
        node = self.repo.get_changeset(revision).get_node(path)
        assert node.is_file()
        assert node.size == size

    def test_file_size(self):
        to_check = (
            ('c1214f7e79e02fc37156ff215cd71275450cffc3',
                'vcs/backends/BaseRepository.py', 502),
            ('d7e0d30fbcae12c90680eb095a4f5f02505ce501',
                'vcs/backends/hg.py', 854),
            ('6e125e7c890379446e98980d8ed60fba87d0f6d1',
                'setup.py', 1068),
            ('d955cd312c17b02143c04fa1099a352b04368118',
                'vcs/backends/base.py', 2921),
            ('ca1eb7957a54bce53b12d1a51b13452f95bc7c7e',
                'vcs/backends/base.py', 3936),
            ('f50f42baeed5af6518ef4b0cb2f1423f3851a941',
                'vcs/backends/base.py', 6189),
        )
        for revision, path, size in to_check:
            self._test_file_size(revision, path, size)

    def _test_dir_size(self, revision, path, size):
        node = self.repo.get_changeset(revision).get_node(path)
        assert node.size == size

    def test_dir_size(self):
        to_check = (
            ('5f2c6ee195929b0be80749243c18121c9864a3b3', '/', 674076),
            ('7ab37bc680b4aa72c34d07b230c866c28e9fc204', '/', 674049),
            ('6892503fb8f2a552cef5f4d4cc2cdbd13ae1cd2f', '/', 671830),
        )
        for revision, path, size in to_check:
            self._test_dir_size(revision, path, size)

    def test_repo_size(self):
        assert self.repo.size == 674076

    def test_file_history(self):
        # we can only check if those revisions are present in the history
        # as we cannot update this test every time file is changed
        files = {
            'setup.py': [
                '54386793436c938cff89326944d4c2702340037d',
                '51d254f0ecf5df2ce50c0b115741f4cf13985dab',
                '998ed409c795fec2012b1c0ca054d99888b22090',
                '5e0eb4c47f56564395f76333f319d26c79e2fb09',
                '0115510b70c7229dbc5dc49036b32e7d91d23acd',
                '7cb3fd1b6d8c20ba89e2264f1c8baebc8a52d36e',
                '2a13f185e4525f9d4b59882791a2d397b90d5ddc',
                '191caa5b2c81ed17c0794bf7bb9958f4dcb0b87e',
                'ff7ca51e58c505fec0dd2491de52c622bb7a806b',
            ],
            'vcs/nodes.py': [
                '33fa3223355104431402a888fa77a4e9956feb3e',
                'fa014c12c26d10ba682fadb78f2a11c24c8118e1',
                'e686b958768ee96af8029fe19c6050b1a8dd3b2b',
                'ab5721ca0a081f26bf43d9051e615af2cc99952f',
                'c877b68d18e792a66b7f4c529ea02c8f80801542',
                '4313566d2e417cb382948f8d9d7c765330356054',
                '6c2303a793671e807d1cfc70134c9ca0767d98c2',
                '54386793436c938cff89326944d4c2702340037d',
                '54000345d2e78b03a99d561399e8e548de3f3203',
                '1c6b3677b37ea064cb4b51714d8f7498f93f4b2b',
                '2d03ca750a44440fb5ea8b751176d1f36f8e8f46',
                '2a08b128c206db48c2f0b8f70df060e6db0ae4f8',
                '30c26513ff1eb8e5ce0e1c6b477ee5dc50e2f34b',
                'ac71e9503c2ca95542839af0ce7b64011b72ea7c',
                '12669288fd13adba2a9b7dd5b870cc23ffab92d2',
                '5a0c84f3e6fe3473e4c8427199d5a6fc71a9b382',
                '12f2f5e2b38e6ff3fbdb5d722efed9aa72ecb0d5',
                '5eab1222a7cd4bfcbabc218ca6d04276d4e27378',
                'f50f42baeed5af6518ef4b0cb2f1423f3851a941',
                'd7e390a45f6aa96f04f5e7f583ad4f867431aa25',
                'f15c21f97864b4f071cddfbf2750ec2e23859414',
                'e906ef056cf539a4e4e5fc8003eaf7cf14dd8ade',
                'ea2b108b48aa8f8c9c4a941f66c1a03315ca1c3b',
                '84dec09632a4458f79f50ddbbd155506c460b4f9',
                '0115510b70c7229dbc5dc49036b32e7d91d23acd',
                '2a13f185e4525f9d4b59882791a2d397b90d5ddc',
                '3bf1c5868e570e39569d094f922d33ced2fa3b2b',
                'b8d04012574729d2c29886e53b1a43ef16dd00a1',
                '6970b057cffe4aab0a792aa634c89f4bebf01441',
                'dd80b0f6cf5052f17cc738c2951c4f2070200d7f',
                'ff7ca51e58c505fec0dd2491de52c622bb7a806b',
            ],
            'vcs/backends/git.py': [
                '4cf116ad5a457530381135e2f4c453e68a1b0105',
                '9a751d84d8e9408e736329767387f41b36935153',
                'cb681fb539c3faaedbcdf5ca71ca413425c18f01',
                '428f81bb652bcba8d631bce926e8834ff49bdcc6',
                '180ab15aebf26f98f714d8c68715e0f05fa6e1c7',
                '2b8e07312a2e89e92b90426ab97f349f4bce2a3a',
                '50e08c506174d8645a4bb517dd122ac946a0f3bf',
                '54000345d2e78b03a99d561399e8e548de3f3203',
            ],
        }
        for path, revs in files.items():
            node = self.repo.get_changeset(revs[0]).get_node(path)
            node_revs = [chset.raw_id for chset in node.history]
            assert set(revs).issubset(set(node_revs)), "We assumed that %s is subset of revisions for which file %s " \
                "has been changed, and history of that node returned: %s" \
                % (revs, path, node_revs)

    def test_file_annotate(self):
        files = {
            'vcs/backends/__init__.py': {
                'c1214f7e79e02fc37156ff215cd71275450cffc3': {
                    'lines_no': 1,
                    'changesets': [
                        'c1214f7e79e02fc37156ff215cd71275450cffc3',
                    ],
                },
                '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647': {
                    'lines_no': 21,
                    'changesets': [
                        '49d3fd156b6f7db46313fac355dca1a0b94a0017',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                    ],
                },
                'e29b67bd158580fc90fc5e9111240b90e6e86064': {
                    'lines_no': 32,
                    'changesets': [
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '5eab1222a7cd4bfcbabc218ca6d04276d4e27378',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '54000345d2e78b03a99d561399e8e548de3f3203',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '78c3f0c23b7ee935ec276acb8b8212444c33c396',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '2a13f185e4525f9d4b59882791a2d397b90d5ddc',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '78c3f0c23b7ee935ec276acb8b8212444c33c396',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '992f38217b979d0b0987d0bae3cc26dac85d9b19',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                        '16fba1ae9334d79b66d7afed2c2dfbfa2ae53647',
                    ],
                },
            },
        }

        for fname, revision_dict in files.items():
            for rev, data in revision_dict.items():
                cs = self.repo.get_changeset(rev)

                l1_1 = [x[1] for x in cs.get_file_annotate(fname)]
                l1_2 = [x[2]().raw_id for x in cs.get_file_annotate(fname)]
                assert l1_1 == l1_2
                l1 = l1_1
                l2 = files[fname][rev]['changesets']
                assert l1 == l2, "The lists of revision for %s@rev %s" \
                    "from annotation list should match each other, " \
                    "got \n%s \nvs \n%s " % (fname, rev, l1, l2)

    def test_files_state(self):
        """
        Tests state of FileNodes.
        """
        node = self.repo \
            .get_changeset('e6ea6d16e2f26250124a1f4b4fe37a912f9d86a0') \
            .get_node('vcs/utils/diffs.py')
        assert node.state, NodeState.ADDED
        assert node.added
        assert not node.changed
        assert not node.not_changed
        assert not node.removed

        node = self.repo \
            .get_changeset('33fa3223355104431402a888fa77a4e9956feb3e') \
            .get_node('.hgignore')
        assert node.state, NodeState.CHANGED
        assert not node.added
        assert node.changed
        assert not node.not_changed
        assert not node.removed

        node = self.repo \
            .get_changeset('e29b67bd158580fc90fc5e9111240b90e6e86064') \
            .get_node('setup.py')
        assert node.state, NodeState.NOT_CHANGED
        assert not node.added
        assert not node.changed
        assert node.not_changed
        assert not node.removed

        # If node has REMOVED state then trying to fetch it would raise
        # ChangesetError exception
        chset = self.repo.get_changeset(
            'fa6600f6848800641328adbf7811fd2372c02ab2')
        path = 'vcs/backends/BaseRepository.py'
        with pytest.raises(NodeDoesNotExistError):
            chset.get_node(path)
        # but it would be one of ``removed`` (changeset's attribute)
        assert path in [rf.path for rf in chset.removed]

        chset = self.repo.get_changeset(
            '54386793436c938cff89326944d4c2702340037d')
        changed = ['setup.py', 'tests/test_nodes.py', 'vcs/backends/hg.py',
            'vcs/nodes.py']
        assert set(changed) == set([f.path for f in chset.changed])

    def test_commit_message_is_unicode(self):
        for cs in self.repo:
            assert type(cs.message) == unicode

    def test_changeset_author_is_unicode(self):
        for cs in self.repo:
            assert type(cs.author) == unicode

    def test_repo_files_content_is_unicode(self):
        changeset = self.repo.get_changeset()
        for node in changeset.get_node('/'):
            if node.is_file():
                assert type(node.content) == unicode

    def test_wrong_path(self):
        # There is 'setup.py' in the root dir but not there:
        path = 'foo/bar/setup.py'
        tip = self.repo.get_changeset()
        with pytest.raises(VCSError):
            tip.get_node(path)

    def test_author_email(self):
        assert 'marcin@python-blog.com' == self.repo.get_changeset('c1214f7e79e02fc37156ff215cd71275450cffc3').author_email
        assert 'lukasz.balcerzak@python-center.pl' == self.repo.get_changeset('ff7ca51e58c505fec0dd2491de52c622bb7a806b').author_email
        assert '' == self.repo.get_changeset('8430a588b43b5d6da365400117c89400326e7992').author_email

    def test_author_username(self):
        assert 'Marcin Kuzminski' == self.repo.get_changeset('c1214f7e79e02fc37156ff215cd71275450cffc3').author_name
        assert 'Lukasz Balcerzak' == self.repo.get_changeset('ff7ca51e58c505fec0dd2491de52c622bb7a806b').author_name
        assert 'marcink none@none' == self.repo.get_changeset('8430a588b43b5d6da365400117c89400326e7992').author_name


class TestGitSpecific():

    def test_error_is_raised_for_added_if_diff_name_status_is_wrong(self):
        repo = mock.MagicMock()
        changeset = GitChangeset(repo, 'foobar')
        changeset._diff_name_status = 'foobar'
        with pytest.raises(VCSError):
            changeset.added

    def test_error_is_raised_for_changed_if_diff_name_status_is_wrong(self):
        repo = mock.MagicMock()
        changeset = GitChangeset(repo, 'foobar')
        changeset._diff_name_status = 'foobar'
        with pytest.raises(VCSError):
            changeset.added

    def test_error_is_raised_for_removed_if_diff_name_status_is_wrong(self):
        repo = mock.MagicMock()
        changeset = GitChangeset(repo, 'foobar')
        changeset._diff_name_status = 'foobar'
        with pytest.raises(VCSError):
            changeset.added


class TestGitSpecificWithRepo(_BackendTestMixin):
    backend_alias = 'git'

    @classmethod
    def _get_commits(cls):
        return [
            {
                'message': 'Initial',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [
                    FileNode('foobar/static/js/admin/base.js', content='base'),
                    FileNode('foobar/static/admin', content='admin',
                        mode=0120000), # this is a link
                    FileNode('foo', content='foo'),
                ],
            },
            {
                'message': 'Second',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'added': [
                    FileNode('foo2', content='foo2'),
                ],
            },
        ]

    def test_paths_slow_traversing(self):
        cs = self.repo.get_changeset()
        assert cs.get_node('foobar').get_node('static').get_node('js').get_node('admin').get_node('base.js').content == 'base'

    def test_paths_fast_traversing(self):
        cs = self.repo.get_changeset()
        assert cs.get_node('foobar/static/js/admin/base.js').content == 'base'

    def test_workdir_get_branch(self):
        self.repo.run_git_command(['checkout', '-b', 'production'])
        # Regression test: one of following would fail if we don't check
        # .git/HEAD file
        self.repo.run_git_command(['checkout', 'production'])
        assert self.repo.workdir.get_branch() == 'production'
        self.repo.run_git_command(['checkout', 'master'])
        assert self.repo.workdir.get_branch() == 'master'

    def test_get_diff_runs_git_command_with_hashes(self):
        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1)
        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U3', '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1)])

    def test_get_diff_runs_git_command_with_str_hashes(self):
        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(self.repo.EMPTY_CHANGESET, 1)
        self.repo.run_git_command.assert_called_once_with(
            ['show', '-U3', '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(1)])

    def test_get_diff_runs_git_command_with_path_if_its_given(self):
        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1, 'foo')
        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U3', '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1), '--', 'foo'])

    def test_get_diff_does_not_sanitize_valid_context(self):
        almost_overflowed_long_int = 2**31-1

        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1, 'foo', context=almost_overflowed_long_int)
        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U' + str(almost_overflowed_long_int), '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1), '--', 'foo'])

    def test_get_diff_sanitizes_overflowing_context(self):
        overflowed_long_int = 2**31
        sanitized_overflowed_long_int = overflowed_long_int-1

        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1, 'foo', context=overflowed_long_int)

        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U' + str(sanitized_overflowed_long_int), '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1), '--', 'foo'])

    def test_get_diff_does_not_sanitize_zero_context(self):
        zero_context = 0

        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1, 'foo', context=zero_context)

        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U' + str(zero_context), '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1), '--', 'foo'])

    def test_get_diff_sanitizes_negative_context(self):
        negative_context = -10

        self.repo.run_git_command = mock.Mock(return_value=['', ''])
        self.repo.get_diff(0, 1, 'foo', context=negative_context)

        self.repo.run_git_command.assert_called_once_with(
            ['diff', '-U0', '--full-index', '--binary', '-p', '-M', '--abbrev=40',
             self.repo._get_revision(0), self.repo._get_revision(1), '--', 'foo'])


class TestGitRegression(_BackendTestMixin):
    backend_alias = 'git'

    @classmethod
    def _get_commits(cls):
        return [
            {
                'message': 'Initial',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 20),
                'added': [
                    FileNode('bot/__init__.py', content='base'),
                    FileNode('bot/templates/404.html', content='base'),
                    FileNode('bot/templates/500.html', content='base'),
                ],
            },
            {
                'message': 'Second',
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': datetime.datetime(2010, 1, 1, 22),
                'added': [
                    FileNode('bot/build/migrations/1.py', content='foo2'),
                    FileNode('bot/build/migrations/2.py', content='foo2'),
                    FileNode('bot/build/static/templates/f.html', content='foo2'),
                    FileNode('bot/build/static/templates/f1.html', content='foo2'),
                    FileNode('bot/build/templates/err.html', content='foo2'),
                    FileNode('bot/build/templates/err2.html', content='foo2'),
                ],
            },
        ]

    def test_similar_paths(self):
        cs = self.repo.get_changeset()
        paths = lambda *n: [x.path for x in n]
        assert paths(*cs.get_nodes('bot')) == ['bot/build', 'bot/templates', 'bot/__init__.py']
        assert paths(*cs.get_nodes('bot/build')) == ['bot/build/migrations', 'bot/build/static', 'bot/build/templates']
        assert paths(*cs.get_nodes('bot/build/static')) == ['bot/build/static/templates']
        # this get_nodes below causes troubles !
        assert paths(*cs.get_nodes('bot/build/static/templates')) == ['bot/build/static/templates/f.html', 'bot/build/static/templates/f1.html']
        assert paths(*cs.get_nodes('bot/build/templates')) == ['bot/build/templates/err.html', 'bot/build/templates/err2.html']
        assert paths(*cs.get_nodes('bot/templates/')) == ['bot/templates/404.html', 'bot/templates/500.html']


class TestGitHooks(object):
    """
    Tests related to hook functionality of Git repositories.
    """

    def setup_method(self):
        # For each run we want a fresh repo.
        self.repo_directory = get_new_dir("githookrepo")
        self.repo = GitRepository(self.repo_directory, create=True)

        # Create a dictionary where keys are hook names, and values are paths to
        # them. Deduplicates code in tests a bit.
        self.hook_directory = self.repo.get_hook_location()
        self.kallithea_hooks = dict((h, os.path.join(self.hook_directory, h)) for h in ("pre-receive", "post-receive"))

    def test_hooks_created_if_missing(self):
        """
        Tests if hooks are installed in repository if they are missing.
        """

        for hook, hook_path in self.kallithea_hooks.iteritems():
            if os.path.exists(hook_path):
                os.remove(hook_path)

        ScmModel().install_git_hooks(repo=self.repo)

        for hook, hook_path in self.kallithea_hooks.iteritems():
            assert os.path.exists(hook_path)

    def test_kallithea_hooks_updated(self):
        """
        Tests if hooks are updated if they are Kallithea hooks already.
        """

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path, "w") as f:
                f.write("KALLITHEA_HOOK_VER=0.0.0\nJUST_BOGUS")

        ScmModel().install_git_hooks(repo=self.repo)

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path) as f:
                assert "JUST_BOGUS" not in f.read()

    def test_custom_hooks_untouched(self):
        """
        Tests if hooks are left untouched if they are not Kallithea hooks.
        """

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path, "w") as f:
                f.write("#!/bin/bash\n#CUSTOM_HOOK")

        ScmModel().install_git_hooks(repo=self.repo)

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path) as f:
                assert "CUSTOM_HOOK" in f.read()

    def test_custom_hooks_forced_update(self):
        """
        Tests if hooks are forcefully updated even though they are custom hooks.
        """

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path, "w") as f:
                f.write("#!/bin/bash\n#CUSTOM_HOOK")

        ScmModel().install_git_hooks(repo=self.repo, force_create=True)

        for hook, hook_path in self.kallithea_hooks.iteritems():
            with open(hook_path) as f:
                assert "KALLITHEA_HOOK_VER" in f.read()
