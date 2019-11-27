# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import time

import mock
import pytest

from kallithea.lib.vcs.exceptions import VCSError
from kallithea.lib.vcs.utils import author_email, author_name
from kallithea.lib.vcs.utils.helpers import get_dict_for_attrs, get_scm, get_scms_for_path, parse_changesets, parse_datetime
from kallithea.lib.vcs.utils.paths import get_dirs_for_path, get_user_home
from kallithea.tests.vcs.conf import TEST_GIT_REPO, TEST_HG_REPO, TESTS_TMP_PATH


class TestPaths(object):

    def _test_get_dirs_for_path(self, path, expected):
        """
        Tests if get_dirs_for_path returns same as expected.
        """
        expected = sorted(expected)
        result = sorted(get_dirs_for_path(path))
        assert result == expected, \
            "%s != %s which was expected result for path %s" % (result, expected, path)

    def test_get_dirs_for_path(self):
        path = 'foo/bar/baz/file'
        paths_and_results = (
            ('foo/bar/baz/file', ['foo', 'foo/bar', 'foo/bar/baz']),
            ('foo/bar/', ['foo', 'foo/bar']),
            ('foo/bar', ['foo']),
        )
        for path, expected in paths_and_results:
            self._test_get_dirs_for_path(path, expected)

    def test_get_scm(self):
        assert ('hg', TEST_HG_REPO) == get_scm(TEST_HG_REPO)
        assert ('git', TEST_GIT_REPO) == get_scm(TEST_GIT_REPO)

    def test_get_two_scms_for_path(self):
        multialias_repo_path = os.path.join(TESTS_TMP_PATH, 'hg-git-repo-2')
        if os.path.isdir(multialias_repo_path):
            shutil.rmtree(multialias_repo_path)

        os.mkdir(multialias_repo_path)

        with pytest.raises(VCSError):
            get_scm(multialias_repo_path)

    def test_get_scm_error_path(self):
        with pytest.raises(VCSError):
            get_scm('err')

    def test_get_scms_for_path(self):
        new = os.path.join(TESTS_TMP_PATH, 'vcs-scms-for-path-%s' % time.time())
        os.mkdir(new)
        assert get_scms_for_path(new) == []

        os.mkdir(os.path.join(new, '.tux'))
        assert get_scms_for_path(new) == []

        os.mkdir(os.path.join(new, '.git'))
        assert set(get_scms_for_path(new)) == set(['git'])

        os.mkdir(os.path.join(new, '.hg'))
        assert set(get_scms_for_path(new)) == set(['git', 'hg'])


class TestParseChangesets(object):

    def test_main_is_returned_correctly(self):
        assert parse_changesets('123456') == {
            'start': None,
            'main': '123456',
            'end': None,
        }

    def test_start_is_returned_correctly(self):
        assert parse_changesets('aaabbb..') == {
            'start': 'aaabbb',
            'main': None,
            'end': None,
        }

    def test_end_is_returned_correctly(self):
        assert parse_changesets('..cccddd') == {
            'start': None,
            'main': None,
            'end': 'cccddd',
        }

    def test_that_two_or_three_dots_are_allowed(self):
        text1 = 'a..b'
        text2 = 'a...b'
        assert parse_changesets(text1) == parse_changesets(text2)

    def test_that_input_is_stripped_first(self):
        text1 = 'a..bb'
        text2 = '  a..bb\t\n\t '
        assert parse_changesets(text1) == parse_changesets(text2)

    def test_that_exception_is_raised(self):
        text = '123456.789012' # single dot is not recognized
        with pytest.raises(ValueError):
            parse_changesets(text)

    def test_non_alphanumeric_raises_exception(self):
        with pytest.raises(ValueError):
            parse_changesets('aaa@bbb')


class TestParseDatetime(object):

    def test_datetime_text(self):
        assert parse_datetime('2010-04-07 21:29:41') == datetime.datetime(2010, 4, 7, 21, 29, 41)

    def test_no_seconds(self):
        assert parse_datetime('2010-04-07 21:29') == datetime.datetime(2010, 4, 7, 21, 29)

    def test_date_only(self):
        assert parse_datetime('2010-04-07') == datetime.datetime(2010, 4, 7)

    def test_another_format(self):
        assert parse_datetime('04/07/10 21:29:41') == datetime.datetime(2010, 4, 7, 21, 29, 41)

    def test_now(self):
        assert parse_datetime('now') - datetime.datetime.now() < datetime.timedelta(seconds=1)

    def test_today(self):
        today = datetime.date.today()
        assert parse_datetime('today') == datetime.datetime(*today.timetuple()[:3])

    def test_yesterday(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        assert parse_datetime('yesterday') == datetime.datetime(*yesterday.timetuple()[:3])

    def test_tomorrow(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        args = tomorrow.timetuple()[:3] + (23, 59, 59)
        assert parse_datetime('tomorrow') == datetime.datetime(*args)

    def test_days(self):
        timestamp = datetime.datetime.today() - datetime.timedelta(days=3)
        args = timestamp.timetuple()[:3] + (0, 0, 0, 0)
        expected = datetime.datetime(*args)
        assert parse_datetime('3d') == expected
        assert parse_datetime('3 d') == expected
        assert parse_datetime('3 day') == expected
        assert parse_datetime('3 days') == expected

    def test_weeks(self):
        timestamp = datetime.datetime.today() - datetime.timedelta(days=3 * 7)
        args = timestamp.timetuple()[:3] + (0, 0, 0, 0)
        expected = datetime.datetime(*args)
        assert parse_datetime('3w') == expected
        assert parse_datetime('3 w') == expected
        assert parse_datetime('3 week') == expected
        assert parse_datetime('3 weeks') == expected

    def test_mixed(self):
        timestamp = datetime.datetime.today() - datetime.timedelta(days=2 * 7 + 3)
        args = timestamp.timetuple()[:3] + (0, 0, 0, 0)
        expected = datetime.datetime(*args)
        assert parse_datetime('2w3d') == expected
        assert parse_datetime('2w 3d') == expected
        assert parse_datetime('2w 3 days') == expected
        assert parse_datetime('2 weeks 3 days') == expected


class TestAuthorExtractors(object):
    TEST_AUTHORS = [("Username Last'o'Name <username@example.com>",
                    ("Username Last'o'Name", "username@example.com")),
                  ("Username Last'o'Name Spaces < username@example.com >",
                    ("Username Last'o'Name Spaces", "username@example.com")),
                  ("Username Last'o'Name <username.lastname@example.com>",
                    ("Username Last'o'Name", "username.lastname@example.com")),
                  ('mrf RFC_SPEC <username+lastname@example.com>',
                    ('mrf RFC_SPEC', 'username+lastname@example.com')),
                  ('username <user@example.com>',
                    ('username', 'user@example.com')),
                  ('username <user@example.com',
                   ('username', 'user@example.com')),
                  ('broken missing@example.com',
                   ('broken', 'missing@example.com')),
                  ('<justemail@example.com>',
                   ('', 'justemail@example.com')),
                  ('justname',
                   ('justname', '')),
                  ('Mr Double Name withemail@example.com ',
                   ('Mr Double Name', 'withemail@example.com')),
                  (u'John Doe <джондо à éẋàṁṗłê.ç°ḿ>',
                   (u'John Doe <\u0434\u0436\u043e\u043d\u0434\u043e \xe0 \xe9\u1e8b\xe0\u1e41\u1e57\u0142\xea.\xe7\xb0\u1e3f>', '')),
                  ]

    def test_author_email(self):
        for test_str, result in self.TEST_AUTHORS:
            assert result[1] == author_email(test_str)

    def test_author_name(self):
        for test_str, result in self.TEST_AUTHORS:
            assert result[0] == author_name(test_str)


class TestGetDictForAttrs(object):

    def test_returned_dict_has_expected_attrs(self):
        obj = mock.Mock()
        obj.NOT_INCLUDED = 'this key/value should not be included'
        obj.CONST = True
        obj.foo = 'aaa'
        obj.attrs = {'foo': 'bar'}
        obj.date = datetime.datetime(2010, 12, 31)
        obj.count = 1001

        assert get_dict_for_attrs(obj, ['CONST', 'foo', 'attrs', 'date', 'count']) ==  {
            'CONST': True,
            'foo': 'aaa',
            'attrs': {'foo': 'bar'},
            'date': datetime.datetime(2010, 12, 31),
            'count': 1001,
        }


class TestGetUserHome(object):

    @mock.patch.object(os, 'environ', {})
    def test_defaults_to_none(self):
        assert get_user_home() == ''

    @mock.patch.object(os, 'environ', {'HOME': '/home/foobar'})
    def test_unix_like(self):
        assert get_user_home() == '/home/foobar'

    @mock.patch.object(os, 'environ', {'USERPROFILE': '/Users/foobar'})
    def test_windows_like(self):
        assert get_user_home() == '/Users/foobar'

    @mock.patch.object(os, 'environ', {'HOME': '/home/foobar',
        'USERPROFILE': '/Users/foobar'})
    def test_prefers_home_over_userprofile(self):
        assert get_user_home() == '/home/foobar'
