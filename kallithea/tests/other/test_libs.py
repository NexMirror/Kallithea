# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.tests.other.test_libs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Package for testing various lib/helper functions in kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jun 9, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import datetime
import hashlib

import mock
from tg.util.webtest import test_context

from kallithea.lib.utils2 import AttributeDict
from kallithea.model.db import Repository
from kallithea.tests.base import *


proto = 'http'
TEST_URLS = [
    ('%s://127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://username@127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://username:pass@127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://127.0.0.1:8080' % proto, ['%s://' % proto, '127.0.0.1', '8080'],
     '%s://127.0.0.1:8080' % proto),
    ('%s://example.com' % proto, ['%s://' % proto, 'example.com'],
     '%s://example.com' % proto),
    ('%s://user:pass@example.com:8080' % proto, ['%s://' % proto, 'example.com',
                                                '8080'],
     '%s://example.com:8080' % proto),
]

proto = 'https'
TEST_URLS += [
    ('%s://127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://username@127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://username:pass@127.0.0.1' % proto, ['%s://' % proto, '127.0.0.1'],
     '%s://127.0.0.1' % proto),
    ('%s://127.0.0.1:8080' % proto, ['%s://' % proto, '127.0.0.1', '8080'],
     '%s://127.0.0.1:8080' % proto),
    ('%s://example.com' % proto, ['%s://' % proto, 'example.com'],
     '%s://example.com' % proto),
    ('%s://user:pass@example.com:8080' % proto, ['%s://' % proto, 'example.com',
                                                '8080'],
     '%s://example.com:8080' % proto),
]


class FakeUrlGenerator(object):

    def __init__(self, current_url=None, default_route=None, **routes):
        """Initialize using specified 'current' URL template,
        default route template, and all other aguments describing known
        routes (format: route=template)"""
        self.current_url = current_url
        self.default_route = default_route
        self.routes = routes

    def __call__(self, route_name, *args, **kwargs):
        if route_name in self.routes:
            return self.routes[route_name] % kwargs

        return self.default_route % kwargs

    def current(self, *args, **kwargs):
        return self.current_url % kwargs


class TestLibs(TestController):

    @parametrize('test_url,expected,expected_creds', TEST_URLS)
    def test_uri_filter(self, test_url, expected, expected_creds):
        from kallithea.lib.utils2 import uri_filter
        assert uri_filter(test_url) == expected

    @parametrize('test_url,expected,expected_creds', TEST_URLS)
    def test_credentials_filter(self, test_url, expected, expected_creds):
        from kallithea.lib.utils2 import credentials_filter
        assert credentials_filter(test_url) == expected_creds

    @parametrize('str_bool,expected', [
                           ('t', True),
                           ('true', True),
                           ('y', True),
                           ('yes', True),
                           ('on', True),
                           ('1', True),
                           ('Y', True),
                           ('yeS', True),
                           ('Y', True),
                           ('TRUE', True),
                           ('T', True),
                           ('False', False),
                           ('F', False),
                           ('FALSE', False),
                           ('0', False),
                           ('-1', False),
                           ('', False)
    ])
    def test_str2bool(self, str_bool, expected):
        from kallithea.lib.utils2 import str2bool
        assert str2bool(str_bool) == expected

    def test_mention_extractor(self):
        from kallithea.lib.utils2 import extract_mentioned_usernames
        sample = (
            "@first hi there @world here's my email username@example.com "
            "@lukaszb check @one_more22 it pls @ ttwelve @D[] @one@two@three "
            "@UPPER    @cAmEL @2one_more22 @john please see this http://org.pl "
            "@marian.user just do it @marco-polo and next extract @marco_polo "
            "user.dot  hej ! not-needed maril@example.com"
        )

        expected = set([
            '2one_more22', 'first', 'lukaszb', 'one', 'one_more22', 'UPPER', 'cAmEL', 'john',
            'marian.user', 'marco-polo', 'marco_polo', 'world'])
        assert expected == set(extract_mentioned_usernames(sample))

    @parametrize('age_args,expected', [
        (dict(), u'just now'),
        (dict(seconds= -1), u'1 second ago'),
        (dict(seconds= -60 * 2), u'2 minutes ago'),
        (dict(hours= -1), u'1 hour ago'),
        (dict(hours= -24), u'1 day ago'),
        (dict(hours= -24 * 5), u'5 days ago'),
        (dict(months= -1), u'1 month ago'),
        (dict(months= -1, days= -2), u'1 month and 2 days ago'),
        (dict(months= -1, days= -20), u'1 month and 19 days ago'),
        (dict(years= -1, months= -1), u'1 year and 1 month ago'),
        (dict(years= -1, months= -10), u'1 year and 10 months ago'),
        (dict(years= -2, months= -4), u'2 years and 4 months ago'),
        (dict(years= -2, months= -11), u'2 years and 11 months ago'),
        (dict(years= -3, months= -2), u'3 years and 2 months ago'),
    ])
    def test_age(self, age_args, expected):
        from kallithea.lib.utils2 import age
        from dateutil import relativedelta
        with test_context(self.app):
            n = datetime.datetime(year=2012, month=5, day=17)
            delt = lambda *args, **kwargs: relativedelta.relativedelta(*args, **kwargs)
            assert age(n + delt(**age_args), now=n) == expected

    @parametrize('age_args,expected', [
        (dict(), u'just now'),
        (dict(seconds= -1), u'1 second ago'),
        (dict(seconds= -60 * 2), u'2 minutes ago'),
        (dict(hours= -1), u'1 hour ago'),
        (dict(hours= -24), u'1 day ago'),
        (dict(hours= -24 * 5), u'5 days ago'),
        (dict(months= -1), u'1 month ago'),
        (dict(months= -1, days= -2), u'1 month ago'),
        (dict(months= -1, days= -20), u'1 month ago'),
        (dict(years= -1, months= -1), u'13 months ago'),
        (dict(years= -1, months= -10), u'22 months ago'),
        (dict(years= -2, months= -4), u'2 years ago'),
        (dict(years= -2, months= -11), u'3 years ago'),
        (dict(years= -3, months= -2), u'3 years ago'),
        (dict(years= -4, months= -8), u'5 years ago'),
    ])
    def test_age_short(self, age_args, expected):
        from kallithea.lib.utils2 import age
        from dateutil import relativedelta
        with test_context(self.app):
            n = datetime.datetime(year=2012, month=5, day=17)
            delt = lambda *args, **kwargs: relativedelta.relativedelta(*args, **kwargs)
            assert age(n + delt(**age_args), show_short_version=True, now=n) == expected

    @parametrize('age_args,expected', [
        (dict(), u'just now'),
        (dict(seconds=1), u'in 1 second'),
        (dict(seconds=60 * 2), u'in 2 minutes'),
        (dict(hours=1), u'in 1 hour'),
        (dict(hours=24), u'in 1 day'),
        (dict(hours=24 * 5), u'in 5 days'),
        (dict(months=1), u'in 1 month'),
        (dict(months=1, days=1), u'in 1 month and 1 day'),
        (dict(years=1, months=1), u'in 1 year and 1 month')
    ])
    def test_age_in_future(self, age_args, expected):
        from kallithea.lib.utils2 import age
        from dateutil import relativedelta
        with test_context(self.app):
            n = datetime.datetime(year=2012, month=5, day=17)
            delt = lambda *args, **kwargs: relativedelta.relativedelta(*args, **kwargs)
            assert age(n + delt(**age_args), now=n) == expected

    def test_tag_extractor(self):
        sample = (
            "hello pta[tag] gog [[]] [[] sda ero[or]d [me =>>< sa]"
            "[requires] [stale] [see<>=>] [see => http://example.com]"
            "[requires => url] [lang => python] [just a tag]"
            "[,d] [ => ULR ] [obsolete] [desc]]"
        )
        from kallithea.lib.helpers import urlify_text
        res = urlify_text(sample, stylize=True)
        assert '<div class="label label-meta" data-tag="tag">tag</div>' in res
        assert '<div class="label label-meta" data-tag="obsolete">obsolete</div>' in res
        assert '<div class="label label-meta" data-tag="stale">stale</div>' in res
        assert '<div class="label label-meta" data-tag="lang">python</div>' in res
        assert '<div class="label label-meta" data-tag="requires">requires =&gt; <a href="/url">url</a></div>' in res
        assert '<div class="label label-meta" data-tag="tag">tag</div>' in res

    def test_alternative_gravatar(self):
        from kallithea.lib.helpers import gravatar_url
        _md5 = lambda s: hashlib.md5(s).hexdigest()

        # mock tg.tmpl_context
        def fake_tmpl_context(_url):
            _c = AttributeDict()
            _c.visual = AttributeDict()
            _c.visual.use_gravatar = True
            _c.visual.gravatar_url = _url

            return _c

        fake_url = FakeUrlGenerator(current_url='https://example.com')
        with mock.patch('kallithea.config.routing.url', fake_url):
            fake = fake_tmpl_context(_url='http://example.com/{email}')
            with mock.patch('tg.tmpl_context', fake):
                    from kallithea.config.routing import url
                    assert url.current() == 'https://example.com'
                    grav = gravatar_url(email_address='test@example.com', size=24)
                    assert grav == 'http://example.com/test@example.com'

            fake = fake_tmpl_context(_url='http://example.com/{email}')
            with mock.patch('tg.tmpl_context', fake):
                grav = gravatar_url(email_address='test@example.com', size=24)
                assert grav == 'http://example.com/test@example.com'

            fake = fake_tmpl_context(_url='http://example.com/{md5email}')
            with mock.patch('tg.tmpl_context', fake):
                em = 'test@example.com'
                grav = gravatar_url(email_address=em, size=24)
                assert grav == 'http://example.com/%s' % (_md5(em))

            fake = fake_tmpl_context(_url='http://example.com/{md5email}/{size}')
            with mock.patch('tg.tmpl_context', fake):
                em = 'test@example.com'
                grav = gravatar_url(email_address=em, size=24)
                assert grav == 'http://example.com/%s/%s' % (_md5(em), 24)

            fake = fake_tmpl_context(_url='{scheme}://{netloc}/{md5email}/{size}')
            with mock.patch('tg.tmpl_context', fake):
                em = 'test@example.com'
                grav = gravatar_url(email_address=em, size=24)
                assert grav == 'https://example.com/%s/%s' % (_md5(em), 24)

    @parametrize('clone_uri_tmpl,repo_name,username,prefix,expected', [
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', None, '', 'http://vps1:8000/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', 'username', '', 'http://username@vps1:8000/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', None, '/prefix', 'http://vps1:8000/prefix/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', 'user', '/prefix', 'http://user@vps1:8000/prefix/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', 'username', '/prefix', 'http://username@vps1:8000/prefix/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', 'user', '/prefix/', 'http://user@vps1:8000/prefix/group/repo1'),
        (Repository.DEFAULT_CLONE_URI, 'group/repo1', 'username', '/prefix/', 'http://username@vps1:8000/prefix/group/repo1'),
        ('{scheme}://{user}@{netloc}/_{repoid}', 'group/repo1', None, '', 'http://vps1:8000/_23'),
        ('{scheme}://{user}@{netloc}/_{repoid}', 'group/repo1', 'username', '', 'http://username@vps1:8000/_23'),
        ('http://{user}@{netloc}/_{repoid}', 'group/repo1', 'username', '', 'http://username@vps1:8000/_23'),
        ('http://{netloc}/_{repoid}', 'group/repo1', 'username', '', 'http://vps1:8000/_23'),
        ('https://{user}@proxy1.example.com/{repo}', 'group/repo1', 'username', '', 'https://username@proxy1.example.com/group/repo1'),
        ('https://{user}@proxy1.example.com/{repo}', 'group/repo1', None, '', 'https://proxy1.example.com/group/repo1'),
        ('https://proxy1.example.com/{user}/{repo}', 'group/repo1', 'username', '', 'https://proxy1.example.com/username/group/repo1'),
    ])
    def test_clone_url_generator(self, clone_uri_tmpl, repo_name, username, prefix, expected):
        from kallithea.lib.utils2 import get_clone_url
        clone_url = get_clone_url(clone_uri_tmpl=clone_uri_tmpl, prefix_url='http://vps1:8000' + prefix,
                                  repo_name=repo_name, repo_id=23, username=username)
        assert clone_url == expected

    def _quick_url(self, text, tmpl="""<a class="changeset_hash" href="%s">%s</a>""", url_=None):
        """
        Changes `some text url[foo]` => `some text <a href="/">foo</a>

        :param text:
        """
        import re
        # quickly change expected url[] into a link
        url_pattern = re.compile(r'(?:url\[)(.+?)(?:\])')

        def url_func(match_obj):
            _url = match_obj.groups()[0]
            return tmpl % (url_ or '/repo_name/changeset/%s' % _url, _url)
        return url_pattern.sub(url_func, text)

    @parametrize('sample,expected', [
      ("",
       ""),
      ("git-svn-id: https://svn.apache.org/repos/asf/libcloud/trunk@1441655 13f79535-47bb-0310-9956-ffa450edef68",
       """git-svn-id: <a href="https://svn.apache.org/repos/asf/libcloud/trunk@1441655">https://svn.apache.org/repos/asf/libcloud/trunk@1441655</a> 13f79535-47bb-0310-9956-ffa450edef68"""),
      ("from rev 000000000000",
       """from rev url[000000000000]"""),
      ("from rev 000000000000123123 also rev 000000000000",
       """from rev url[000000000000123123] also rev url[000000000000]"""),
      ("this should-000 00",
       """this should-000 00"""),
      ("longtextffffffffff rev 123123123123",
       """longtextffffffffff rev url[123123123123]"""),
      ("rev ffffffffffffffffffffffffffffffffffffffffffffffffff",
       """rev ffffffffffffffffffffffffffffffffffffffffffffffffff"""),
      ("ffffffffffff some text traalaa",
       """url[ffffffffffff] some text traalaa"""),
       ("""Multi line
       123123123123
       some text 123123123123
       sometimes !
       """,
       """Multi line<br/>"""
       """       url[123123123123]<br/>"""
       """       some text url[123123123123]<br/>"""
       """       sometimes !"""),
    ])
    def test_urlify_text(self, sample, expected):
        expected = self._quick_url(expected)
        fake_url = FakeUrlGenerator(changeset_home='/%(repo_name)s/changeset/%(revision)s')
        with mock.patch('kallithea.config.routing.url', fake_url):
            from kallithea.lib.helpers import urlify_text
            assert urlify_text(sample, 'repo_name') == expected

    @parametrize('sample,expected,url_', [
      ("",
       "",
       ""),
      ("https://svn.apache.org/repos",
       """url[https://svn.apache.org/repos]""",
       "https://svn.apache.org/repos"),
      ("http://svn.apache.org/repos",
       """url[http://svn.apache.org/repos]""",
       "http://svn.apache.org/repos"),
      ("from rev a also rev http://google.com",
       """from rev a also rev url[http://google.com]""",
       "http://google.com"),
      ("http://imgur.com/foo.gif inline http://imgur.com/foo.gif ending http://imgur.com/foo.gif",
       """url[http://imgur.com/foo.gif] inline url[http://imgur.com/foo.gif] ending url[http://imgur.com/foo.gif]""",
       "http://imgur.com/foo.gif"),
      ("""Multi line
       https://foo.bar.example.com
       some text lalala""",
       """Multi line<br/>"""
       """       url[https://foo.bar.example.com]<br/>"""
       """       some text lalala""",
       "https://foo.bar.example.com"),
      ("@mention @someone",
       """<b>@mention</b> <b>@someone</b>""",
       ""),
      ("deadbeefcafe 123412341234",
       """<a class="changeset_hash" href="/repo_name/changeset/deadbeefcafe">deadbeefcafe</a> <a class="changeset_hash" href="/repo_name/changeset/123412341234">123412341234</a>""",
       ""),
      ("We support * markup for *bold* markup of *single or multiple* words, "
       "*a bit @like http://slack.com*. "
       "The first * must come after whitespace and not be followed by whitespace, "
       "contain anything but * and newline until the next *, "
       "which must not come after whitespace "
       "and not be followed by * or alphanumerical *characters*.",
       """We support * markup for <b>*bold*</b> markup of <b>*single or multiple*</b> words, """
       """<b>*a bit <b>@like</b> <a href="http://slack.com">http://slack.com</a>*</b>. """
       """The first * must come after whitespace and not be followed by whitespace, """
       """contain anything but * and newline until the next *, """
       """which must not come after whitespace """
       """and not be followed by * or alphanumerical <b>*characters*</b>.""",
       "-"),
      ("HTML escaping: <abc> 'single' \"double\" &pointer",
       "HTML escaping: &lt;abc&gt; &#39;single&#39; &quot;double&quot; &amp;pointer",
       "-"),
      # tags are covered by test_tag_extractor
    ])
    def test_urlify_test(self, sample, expected, url_):
        expected = self._quick_url(expected,
                                   tmpl="""<a href="%s">%s</a>""", url_=url_)
        fake_url = FakeUrlGenerator(changeset_home='/%(repo_name)s/changeset/%(revision)s')
        with mock.patch('kallithea.config.routing.url', fake_url):
            from kallithea.lib.helpers import urlify_text
            assert urlify_text(sample, 'repo_name', stylize=True) == expected

    @parametrize('sample,expected', [
      ("deadbeefcafe @mention, and http://foo.bar/ yo",
       """<a class="changeset_hash" href="/repo_name/changeset/deadbeefcafe">deadbeefcafe</a>"""
       """<a class="message-link" href="#the-link"> <b>@mention</b>, and </a>"""
       """<a href="http://foo.bar/">http://foo.bar/</a>"""
       """<a class="message-link" href="#the-link"> yo</a>"""),
    ])
    def test_urlify_link(self, sample, expected):
        fake_url = FakeUrlGenerator(changeset_home='/%(repo_name)s/changeset/%(revision)s')
        with mock.patch('kallithea.config.routing.url', fake_url):
            from kallithea.lib.helpers import urlify_text
            assert urlify_text(sample, 'repo_name', link_='#the-link') == expected

    @parametrize('issue_pat,issue_server,issue_sub,sample,expected', [
        (r'#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'issue #123 and issue#456',
            """issue <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a> and """
            """issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/456">#456</a>"""),
        (r'(?:\s*#)(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'issue #123 and issue#456',
            """issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a> and """
            """issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/456">#456</a>"""),
        # to require whitespace before the issue reference, one may be tempted to use \b...
        (r'\bPR(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'issue PR123 and issuePR456',
            """issue <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a> and """
            """issuePR456"""),
        # ... but it turns out that \b does not work well in combination with '#': the expectations
        # are reversed from what is actually happening.
        (r'\b#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'issue #123 and issue#456',
            """issue #123 and """
            """issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/456">#456</a>"""),
        # ... so maybe try to be explicit? Unfortunately the whitespace before the issue
        # reference is not retained, again, because it is part of the pattern.
        (r'(?:^|\s)#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            '#15 and issue #123 and issue#456',
            """<a class="issue-tracker-link" href="http://foo/repo_name/issue/15">#15</a> and """
            """issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a> and """
            """issue#456"""),
        # ... instead, use lookbehind assertions.
        (r'(?:^|(?<=\s))#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            '#15 and issue #123 and issue#456',
            """<a class="issue-tracker-link" href="http://foo/repo_name/issue/15">#15</a> and """
            """issue <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a> and """
            """issue#456"""),
        (r'(?:pullrequest|pull request|PR|pr) ?#?(\d+)', 'http://foo/{repo}/issue/\\1', 'PR#\\1',
            'fixed with pullrequest #1, pull request#2, PR 3, pr4',
            """fixed with <a class="issue-tracker-link" href="http://foo/repo_name/issue/1">PR#1</a>, """
            """<a class="issue-tracker-link" href="http://foo/repo_name/issue/2">PR#2</a>, """
            """<a class="issue-tracker-link" href="http://foo/repo_name/issue/3">PR#3</a>, """
            """<a class="issue-tracker-link" href="http://foo/repo_name/issue/4">PR#4</a>"""),
        (r'#(\d+)', 'http://foo/{repo}/issue/\\1', 'PR\\1',
            'interesting issue #123',
            """interesting issue <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">PR123</a>"""),
        (r'BUG\d{5}', 'https://bar/{repo}/\\1', '\\1',
            'silly me, I did not parenthesize the id, BUG12345.',
            """silly me, I did not parenthesize the id, <a class="issue-tracker-link" href="https://bar/repo_name/\\1">BUG12345</a>."""),
        (r'BUG(\d{5})', 'https://bar/{repo}/', 'BUG\\1',
            'silly me, the URL does not contain id, BUG12345.',
            """silly me, the URL does not contain id, <a class="issue-tracker-link" href="https://bar/repo_name/">BUG12345</a>."""),
        (r'(PR-\d+)', 'http://foo/{repo}/issue/\\1', '',
            'interesting issue #123, err PR-56',
            """interesting issue #123, err <a class="issue-tracker-link" href="http://foo/repo_name/issue/PR-56">PR-56</a>"""),
        (r'#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            "some 'standard' text with apostrophes",
            """some &#39;standard&#39; text with apostrophes"""),
        (r'#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            "some 'standard' issue #123",
            """some &#39;standard&#39; issue <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a>"""),
        (r'#(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'an issue   #123       with extra whitespace',
            """an issue   <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a>       with extra whitespace"""),
        (r'(?:\s*#)(\d+)', 'http://foo/{repo}/issue/\\1', '#\\1',
            'an issue   #123       with extra whitespace',
            """an issue<a class="issue-tracker-link" href="http://foo/repo_name/issue/123">#123</a>       with extra whitespace"""),
        # invalid issue pattern
        (r'(PR\d+', 'http://foo/{repo}/issue/{id}', '',
            'PR135',
            """PR135"""),
        # other character than #
        (r'(?:^|(?<=\s))\$(\d+)', 'http://foo/{repo}/issue/\\1', '',
            'empty issue_sub $123 and issue$456',
            """empty issue_sub <a class="issue-tracker-link" href="http://foo/repo_name/issue/123">$123</a> and """
            """issue$456"""),
        # named groups
        (r'(PR|pullrequest|pull request) ?(?P<sitecode>BRU|CPH|BER)-(?P<id>\d+)', 'http://foo/\g<sitecode>/pullrequest/\g<id>/', 'PR-\g<sitecode>-\g<id>',
            'pullrequest CPH-789 is similar to PRBRU-747',
            """<a class="issue-tracker-link" href="http://foo/CPH/pullrequest/789/">PR-CPH-789</a> is similar to """
            """<a class="issue-tracker-link" href="http://foo/BRU/pullrequest/747/">PR-BRU-747</a>"""),
    ])
    def test_urlify_issues(self, issue_pat, issue_server, issue_sub, sample, expected):
        from kallithea.lib.helpers import urlify_text
        config_stub = {
            'sqlalchemy.url': 'foo',
            'issue_pat': issue_pat,
            'issue_server_link': issue_server,
            'issue_sub': issue_sub,
        }
        # force recreation of lazy function
        with mock.patch('kallithea.lib.helpers._urlify_issues_f', None):
            with mock.patch('kallithea.CONFIG', config_stub):
                assert urlify_text(sample, 'repo_name') == expected

    @parametrize('sample,expected', [
        ('abc X5', 'abc <a class="issue-tracker-link" href="http://main/repo_name/main/5/">#5</a>'),
        ('abc pullrequest #6 xyz', 'abc <a class="issue-tracker-link" href="http://pr/repo_name/pr/6">PR#6</a> xyz'),
        ('pull request7 #', '<a class="issue-tracker-link" href="http://pr/repo_name/pr/7">PR#7</a> #'),
        ('look PR9 and pr #11', 'look <a class="issue-tracker-link" href="http://pr/repo_name/pr/9">PR#9</a> and <a class="issue-tracker-link" href="http://pr/repo_name/pr/11">PR#11</a>'),
        ('pullrequest#10 solves issue 9', '<a class="issue-tracker-link" href="http://pr/repo_name/pr/10">PR#10</a> solves <a class="issue-tracker-link" href="http://bug/repo_name/bug/9">bug#9</a>'),
        ('issue FAIL67', 'issue <a class="issue-tracker-link" href="http://fail/repo_name/67">FAIL67</a>'),
        ('issue FAILMORE89', 'issue FAILMORE89'), # no match because absent prefix
    ])
    def test_urlify_issues_multiple_issue_patterns(self, sample, expected):
        from kallithea.lib.helpers import urlify_text
        config_stub = {
            'sqlalchemy.url': 'foo',
            'issue_pat': 'X(\d+)',
            'issue_server_link': 'http://main/{repo}/main/\\1/',
            'issue_sub': '#\\1',
            'issue_pat_pr': '(?:pullrequest|pull request|PR|pr) ?#?(\d+)',
            'issue_server_link_pr': 'http://pr/{repo}/pr/\\1',
            'issue_sub_pr': 'PR#\\1',
            'issue_pat_bug': '(?:BUG|bug|issue) ?#?(\d+)',
            'issue_server_link_bug': 'http://bug/{repo}/bug/\\1',
            'issue_sub_bug': 'bug#\\1',
            'issue_pat_empty_prefix': 'FAIL(\d+)',
            'issue_server_link_empty_prefix': 'http://fail/{repo}/\\1',
            'issue_sub_empty_prefix': '',
            'issue_pat_absent_prefix': 'FAILMORE(\d+)',
            'issue_server_link_absent_prefix': 'http://failmore/{repo}/\\1',
        }
        # force recreation of lazy function
        with mock.patch('kallithea.lib.helpers._urlify_issues_f', None):
            with mock.patch('kallithea.CONFIG', config_stub):
                assert urlify_text(sample, 'repo_name') == expected

    @parametrize('test,expected', [
      ("", None),
      ("/_2", None),
      ("_2", 2),
      ("_2/", None),
    ])
    def test_get_permanent_id(self, test, expected):
        from kallithea.lib.utils import _get_permanent_id
        extracted = _get_permanent_id(test)
        assert extracted == expected, 'url:%s, got:`%s` expected: `%s`' % (test, _test, expected)

    @parametrize('test,expected', [
      ("", ""),
      ("/", "/"),
      ("/_ID", '/_ID'),
      ("ID", "ID"),
      ("_ID", 'NAME'),
      ("_ID/", 'NAME/'),
      ("_ID/1/2", 'NAME/1/2'),
      ("_IDa", '_IDa'),
    ])
    def test_fix_repo_id_name(self, test, expected):
        repo = Repository.get_by_repo_name(HG_REPO)
        test = test.replace('ID', str(repo.repo_id))
        expected = expected.replace('NAME', repo.repo_name).replace('ID', str(repo.repo_id))
        from kallithea.lib.utils import fix_repo_id_name
        replaced = fix_repo_id_name(test)
        assert replaced == expected, 'url:%s, got:`%s` expected: `%s`' % (test, replaced, expected)

    @parametrize('canonical,test,expected', [
        ('http://www.example.org/', '/abc/xyz', 'http://www.example.org/abc/xyz'),
        ('http://www.example.org', '/abc/xyz', 'http://www.example.org/abc/xyz'),
        ('http://www.example.org', '/abc/xyz/', 'http://www.example.org/abc/xyz/'),
        ('http://www.example.org', 'abc/xyz/', 'http://www.example.org/abc/xyz/'),
        ('http://www.example.org', 'about', 'http://www.example.org/about-page'),
        ('http://www.example.org/repos/', 'abc/xyz/', 'http://www.example.org/repos/abc/xyz/'),
        ('http://www.example.org/kallithea/repos/', 'abc/xyz/', 'http://www.example.org/kallithea/repos/abc/xyz/'),
    ])
    def test_canonical_url(self, canonical, test, expected):
        from kallithea.lib.helpers import canonical_url
        from tg import request

        # setup url(), used by canonical_url
        import routes
        m = routes.Mapper()
        m.connect('about', '/about-page')
        url = routes.URLGenerator(m, {'HTTP_HOST': 'http_host.example.org'})

        config_mock = {
            'canonical_url': canonical,
        }

        with test_context(self.app):
            request.environ['routes.url'] = url
            with mock.patch('kallithea.CONFIG', config_mock):
                assert canonical_url(test) == expected

    @parametrize('canonical,expected', [
        ('http://www.example.org', 'www.example.org'),
        ('http://www.example.org/repos/', 'www.example.org'),
        ('http://www.example.org/kallithea/repos/', 'www.example.org'),
    ])
    def test_canonical_hostname(self, canonical, expected):
        from kallithea.lib.helpers import canonical_hostname
        from tg import request

        # setup url(), used by canonical_hostname
        import routes
        m = routes.Mapper()
        url = routes.URLGenerator(m, {'HTTP_HOST': 'http_host.example.org'})

        config_mock = {
            'canonical_url': canonical,
        }

        with test_context(self.app):
            request.environ['routes.url'] = url
            with mock.patch('kallithea.CONFIG', config_mock):
                assert canonical_hostname() == expected
