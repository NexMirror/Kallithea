import pytest
from tg.util.webtest import test_context

from kallithea.model.comment import ChangesetCommentsModel
from kallithea.model.db import Repository
from kallithea.tests.base import *


class TestComments(TestController):

    def _check_comment_count(self, repo_id, revision,
            expected_len_comments, expected_len_inline_comments,
            f_path=None, line_no=None
    ):
        comments = ChangesetCommentsModel().get_comments(repo_id,
                revision=revision)
        assert len(comments) == expected_len_comments
        inline_comments = ChangesetCommentsModel().get_inline_comments(repo_id,
                revision=revision, f_path=f_path, line_no=line_no)
        assert len(inline_comments) == expected_len_inline_comments

        return comments, inline_comments

    def test_create_delete_general_comment(self):
        with test_context(self.app):
            repo_id = Repository.get_by_repo_name(HG_REPO).repo_id
            revision = '9a7b4ff9e8b40bbda72fc75f162325b9baa45cda'

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

            text = u'a comment'
            new_comment = ChangesetCommentsModel().create(
                    text=text,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    send_email=False)

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=1, expected_len_inline_comments=0)

            ChangesetCommentsModel().delete(new_comment)

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

    def test_create_delete_inline_comment(self):
        with test_context(self.app):
            repo_id = Repository.get_by_repo_name(HG_REPO).repo_id
            revision = '9a7b4ff9e8b40bbda72fc75f162325b9baa45cda'

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

            text = u'an inline comment'
            f_path = u'vcs/tests/base.py'
            line_no = u'n50'
            new_comment = ChangesetCommentsModel().create(
                    text=text,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path,
                    line_no=line_no,
                    send_email=False)

            comments, inline_comments = self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=1)
            # inline_comments is a list of tuples (file_path, dict)
            # where the dict keys are line numbers and values are lists of comments
            assert inline_comments[0][0] == f_path
            assert len(inline_comments[0][1]) == 1
            assert line_no in inline_comments[0][1]
            assert inline_comments[0][1][line_no][0].text == text

            ChangesetCommentsModel().delete(new_comment)

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

    def test_create_delete_multiple_inline_comments(self):
        with test_context(self.app):
            repo_id = Repository.get_by_repo_name(HG_REPO).repo_id
            revision = '9a7b4ff9e8b40bbda72fc75f162325b9baa45cda'

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

            text = u'an inline comment'
            f_path = u'vcs/tests/base.py'
            line_no = u'n50'
            new_comment = ChangesetCommentsModel().create(
                    text=text,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path,
                    line_no=line_no,
                    send_email=False)

            text2 = u'another inline comment, same file'
            line_no2 = u'o41'
            new_comment2 = ChangesetCommentsModel().create(
                    text=text2,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path,
                    line_no=line_no2,
                    send_email=False)

            text3 = u'another inline comment, same file'
            f_path3 = u'vcs/tests/test_hg.py'
            line_no3 = u'n159'
            new_comment3 = ChangesetCommentsModel().create(
                    text=text3,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path3,
                    line_no=line_no3,
                    send_email=False)

            comments, inline_comments = self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=2)
            # inline_comments is a list of tuples (file_path, dict)
            # where the dict keys are line numbers and values are lists of comments
            assert inline_comments[1][0] == f_path
            assert len(inline_comments[1][1]) == 2
            assert inline_comments[1][1][line_no][0].text == text
            assert inline_comments[1][1][line_no2][0].text == text2

            assert inline_comments[0][0] == f_path3
            assert len(inline_comments[0][1]) == 1
            assert line_no3 in inline_comments[0][1]
            assert inline_comments[0][1][line_no3][0].text == text3

            # now delete only one comment
            ChangesetCommentsModel().delete(new_comment2)

            comments, inline_comments = self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=2)
            # inline_comments is a list of tuples (file_path, dict)
            # where the dict keys are line numbers and values are lists of comments
            assert inline_comments[1][0] == f_path
            assert len(inline_comments[1][1]) == 1
            assert inline_comments[1][1][line_no][0].text == text

            assert inline_comments[0][0] == f_path3
            assert len(inline_comments[0][1]) == 1
            assert line_no3 in inline_comments[0][1]
            assert inline_comments[0][1][line_no3][0].text == text3

            # now delete all others
            ChangesetCommentsModel().delete(new_comment)
            ChangesetCommentsModel().delete(new_comment3)

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

    def test_selective_retrieval_of_inline_comments(self):
        with test_context(self.app):
            repo_id = Repository.get_by_repo_name(HG_REPO).repo_id
            revision = '9a7b4ff9e8b40bbda72fc75f162325b9baa45cda'

            self._check_comment_count(repo_id, revision,
                    expected_len_comments=0, expected_len_inline_comments=0)

            text = u'an inline comment'
            f_path = u'vcs/tests/base.py'
            line_no = u'n50'
            new_comment = ChangesetCommentsModel().create(
                    text=text,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path,
                    line_no=line_no,
                    send_email=False)

            text2 = u'another inline comment, same file'
            line_no2 = u'o41'
            new_comment2 = ChangesetCommentsModel().create(
                    text=text2,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path,
                    line_no=line_no2,
                    send_email=False)

            text3 = u'another inline comment, same file'
            f_path3 = u'vcs/tests/test_hg.py'
            line_no3 = u'n159'
            new_comment3 = ChangesetCommentsModel().create(
                    text=text3,
                    repo=HG_REPO,
                    author=TEST_USER_REGULAR_LOGIN,
                    revision=revision,
                    f_path=f_path3,
                    line_no=line_no3,
                    send_email=False)

            # now selectively retrieve comments of one file
            comments, inline_comments = self._check_comment_count(repo_id, revision,
                    f_path=f_path,
                    expected_len_comments=0, expected_len_inline_comments=1)
            # inline_comments is a list of tuples (file_path, dict)
            # where the dict keys are line numbers and values are lists of comments
            assert inline_comments[0][0] == f_path
            assert len(inline_comments[0][1]) == 2
            assert inline_comments[0][1][line_no][0].text == text
            assert inline_comments[0][1][line_no2][0].text == text2

            # now selectively retrieve comments of one file, one line
            comments, inline_comments = self._check_comment_count(repo_id, revision,
                    f_path=f_path, line_no=line_no2,
                    expected_len_comments=0, expected_len_inline_comments=1)
            # inline_comments is a list of tuples (file_path, dict)
            # where the dict keys are line numbers and values are lists of comments
            assert inline_comments[0][0] == f_path
            assert len(inline_comments[0][1]) == 1
            assert inline_comments[0][1][line_no2][0].text == text2

            # verify that retrieval based on line_no but no f_path fails
            with pytest.raises(Exception) as excinfo:
                self._check_comment_count(repo_id, revision,
                        f_path=None, line_no=line_no2,
                        expected_len_comments=0, expected_len_inline_comments=0)
            assert 'line_no only makes sense if f_path is given' in str(excinfo.value)
