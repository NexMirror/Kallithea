import pytest

from kallithea.lib.vcs.exceptions import TagAlreadyExistError, TagDoesNotExistError
from kallithea.tests.vcs.base import _BackendTestMixin


class TagsTestCaseMixin(_BackendTestMixin):

    def test_new_tag(self):
        tip = self.repo.get_changeset()
        tagsize = len(self.repo.tags)
        tag = self.repo.tag('last-commit', 'joe', tip.raw_id)

        assert len(self.repo.tags) == tagsize + 1
        for top, dirs, files in tip.walk():
            assert top == tag.get_node(top.path)

    def test_tag_already_exist(self):
        tip = self.repo.get_changeset()
        self.repo.tag('last-commit', 'joe', tip.raw_id)

        with pytest.raises(TagAlreadyExistError):
            self.repo.tag('last-commit', 'joe', tip.raw_id)

        chset = self.repo.get_changeset(0)
        with pytest.raises(TagAlreadyExistError):
            self.repo.tag('last-commit', 'jane', chset.raw_id)

    def test_remove_tag(self):
        tip = self.repo.get_changeset()
        self.repo.tag('last-commit', 'joe', tip.raw_id)
        tagsize = len(self.repo.tags)

        self.repo.remove_tag('last-commit', user='evil joe')
        assert len(self.repo.tags) == tagsize - 1

    def test_remove_tag_which_does_not_exist(self):
        with pytest.raises(TagDoesNotExistError):
            self.repo.remove_tag('last-commit', user='evil joe')

    def test_name_with_slash(self):
        self.repo.tag('19/10/11', 'joe')
        assert '19/10/11' in self.repo.tags


class TestGitTags(TagsTestCaseMixin):
    backend_alias = 'git'


class TestHgTags(TagsTestCaseMixin):
    backend_alias = 'hg'
