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
Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to both as 'h'.
"""
import random
import hashlib
import StringIO
import math
import logging
import re
import urlparse
import textwrap

from pygments.formatters.html import HtmlFormatter
from pygments import highlight as code_highlight
from pylons import url
from pylons.i18n.translation import _, ungettext
from hashlib import md5

from webhelpers.html import literal, HTML, escape
from webhelpers.html.tools import *
from webhelpers.html.builder import make_tag
from webhelpers.html.tags import auto_discovery_link, checkbox, css_classes, \
    end_form, file, hidden, image, javascript_link, link_to, \
    link_to_if, link_to_unless, ol, required_legend, select, stylesheet_link, \
    submit, text, password, textarea, title, ul, xml_declaration, radio
from webhelpers.html.tools import auto_link, button_to, highlight, \
    js_obfuscate, mail_to, strip_links, strip_tags, tag_re
from webhelpers.number import format_byte_size, format_bit_size
from webhelpers.pylonslib import Flash as _Flash
from webhelpers.pylonslib.secure_form import secure_form as form, authentication_token
from webhelpers.text import chop_at, collapse, convert_accented_entities, \
    convert_misc_entities, lchop, plural, rchop, remove_formatting, \
    replace_whitespace, urlify, truncate, wrap_paragraphs
from webhelpers.date import time_ago_in_words
from webhelpers.paginate import Page as _Page
from webhelpers.html.tags import _set_input_attrs, _set_id_attr, \
    convert_boolean_attrs, NotGiven, _make_safe_id_component

from kallithea.lib.annotate import annotate_highlight
from kallithea.lib.utils import repo_name_slug, get_custom_lexer
from kallithea.lib.utils2 import str2bool, safe_unicode, safe_str, \
    get_changeset_safe, datetime_to_time, time_to_datetime, AttributeDict,\
    safe_int
from kallithea.lib.markup_renderer import MarkupRenderer, url_re
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError
from kallithea.lib.vcs.backends.base import BaseChangeset, EmptyChangeset
from kallithea.config.conf import DATE_FORMAT, DATETIME_FORMAT
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.db import URL_SEP, Permission

log = logging.getLogger(__name__)


def canonical_url(*args, **kargs):
    '''Like url(x, qualified=True), but returns url that not only is qualified
    but also canonical, as configured in canonical_url'''
    from kallithea import CONFIG
    try:
        parts = CONFIG.get('canonical_url', '').split('://', 1)
        kargs['host'] = parts[1].split('/', 1)[0]
        kargs['protocol'] = parts[0]
    except IndexError:
        kargs['qualified'] = True
    return url(*args, **kargs)

def canonical_hostname():
    '''Return canonical hostname of system'''
    from kallithea import CONFIG
    try:
        parts = CONFIG.get('canonical_url', '').split('://', 1)
        return parts[1].split('/', 1)[0]
    except IndexError:
        parts = url('home', qualified=True).split('://', 1)
        return parts[1].split('/', 1)[0]

def html_escape(text, html_escape_table=None):
    """Produce entities within text."""
    if not html_escape_table:
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
    return "".join(html_escape_table.get(c, c) for c in text)


def shorter(text, size=20):
    postfix = '...'
    if len(text) > size:
        return text[:size - len(postfix)] + postfix
    return text


def _reset(name, value=None, id=NotGiven, type="reset", **attrs):
    """
    Reset button
    """
    _set_input_attrs(attrs, type, name, value)
    _set_id_attr(attrs, id, name)
    convert_boolean_attrs(attrs, ["disabled"])
    return HTML.input(**attrs)

reset = _reset
safeid = _make_safe_id_component


def FID(raw_id, path):
    """
    Creates a unique ID for filenode based on it's hash of path and revision
    it's safe to use in urls

    :param raw_id:
    :param path:
    """

    return 'C-%s-%s' % (short_id(raw_id), md5(safe_str(path)).hexdigest()[:12])


class _GetError(object):
    """Get error from form_errors, and represent it as span wrapped error
    message

    :param field_name: field to fetch errors for
    :param form_errors: form errors dict
    """

    def __call__(self, field_name, form_errors):
        tmpl = """<span class="error_msg">%s</span>"""
        if form_errors and field_name in form_errors:
            return literal(tmpl % form_errors.get(field_name))

get_error = _GetError()


class _ToolTip(object):

    def __call__(self, tooltip_title, trim_at=50):
        """
        Special function just to wrap our text into nice formatted
        autowrapped text

        :param tooltip_title:
        """
        tooltip_title = escape(tooltip_title)
        tooltip_title = tooltip_title.replace('<', '&lt;').replace('>', '&gt;')
        return tooltip_title
tooltip = _ToolTip()


class _FilesBreadCrumbs(object):

    def __call__(self, repo_name, rev, paths):
        if isinstance(paths, str):
            paths = safe_unicode(paths)
        url_l = [link_to(repo_name, url('files_home',
                                        repo_name=repo_name,
                                        revision=rev, f_path=''),
                         class_='ypjax-link')]
        paths_l = paths.split('/')
        for cnt, p in enumerate(paths_l):
            if p != '':
                url_l.append(link_to(p,
                                     url('files_home',
                                         repo_name=repo_name,
                                         revision=rev,
                                         f_path='/'.join(paths_l[:cnt + 1])
                                         ),
                                     class_='ypjax-link'
                                     )
                             )

        return literal('/'.join(url_l))

files_breadcrumbs = _FilesBreadCrumbs()


class CodeHtmlFormatter(HtmlFormatter):
    """
    My code Html Formatter for source codes
    """

    def wrap(self, source, outfile):
        return self._wrap_div(self._wrap_pre(self._wrap_code(source)))

    def _wrap_code(self, source):
        for cnt, it in enumerate(source):
            i, t = it
            t = '<div id="L%s">%s</div>' % (cnt + 1, t)
            yield i, t

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = StringIO.StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1
            dummyoutfile.write(line)

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        la = self.lineanchors
        aln = self.anchorlinenos
        nocls = self.noclasses
        if sp:
            lines = []

            for i in range(fl, fl + lncount):
                if i % st == 0:
                    if i % sp == 0:
                        if aln:
                            lines.append('<a href="#%s%d" class="special">%*d</a>' %
                                         (la, i, mw, i))
                        else:
                            lines.append('<span class="special">%*d</span>' % (mw, i))
                    else:
                        if aln:
                            lines.append('<a href="#%s%d">%*d</a>' % (la, i, mw, i))
                        else:
                            lines.append('%*d' % (mw, i))
                else:
                    lines.append('')
            ls = '\n'.join(lines)
        else:
            lines = []
            for i in range(fl, fl + lncount):
                if i % st == 0:
                    if aln:
                        lines.append('<a href="#%s%d">%*d</a>' % (la, i, mw, i))
                    else:
                        lines.append('%*d' % (mw, i))
                else:
                    lines.append('')
            ls = '\n'.join(lines)

        # in case you wonder about the seemingly redundant <div> here: since the
        # content in the other cell also is wrapped in a div, some browsers in
        # some configurations seem to mess up the formatting...
        if nocls:
            yield 0, ('<table class="%stable">' % self.cssclass +
                      '<tr><td><div class="linenodiv" '
                      'style="background-color: #f0f0f0; padding-right: 10px">'
                      '<pre style="line-height: 125%">' +
                      ls + '</pre></div></td><td id="hlcode" class="code">')
        else:
            yield 0, ('<table class="%stable">' % self.cssclass +
                      '<tr><td class="linenos"><div class="linenodiv"><pre>' +
                      ls + '</pre></div></td><td id="hlcode" class="code">')
        yield 0, dummyoutfile.getvalue()
        yield 0, '</td></tr></table>'


_whitespace_re = re.compile(r'(\t)|( )(?=\n|</div>)')

def _markup_whitespace(m):
    groups = m.groups()
    if groups[0]:
        return '<u>\t</u>'
    if groups[1]:
        return ' <i></i>'

def markup_whitespace(s):
    return _whitespace_re.sub(_markup_whitespace, s)

def pygmentize(filenode, **kwargs):
    """
    pygmentize function using pygments

    :param filenode:
    """
    lexer = get_custom_lexer(filenode.extension) or filenode.lexer
    return literal(markup_whitespace(
        code_highlight(filenode.content, lexer, CodeHtmlFormatter(**kwargs))))


def pygmentize_annotation(repo_name, filenode, **kwargs):
    """
    pygmentize function for annotation

    :param filenode:
    """

    color_dict = {}

    def gen_color(n=10000):
        """generator for getting n of evenly distributed colors using
        hsv color and golden ratio. It always return same order of colors

        :returns: RGB tuple
        """

        def hsv_to_rgb(h, s, v):
            if s == 0.0:
                return v, v, v
            i = int(h * 6.0)  # XXX assume int() truncates!
            f = (h * 6.0) - i
            p = v * (1.0 - s)
            q = v * (1.0 - s * f)
            t = v * (1.0 - s * (1.0 - f))
            i = i % 6
            if i == 0:
                return v, t, p
            if i == 1:
                return q, v, p
            if i == 2:
                return p, v, t
            if i == 3:
                return p, q, v
            if i == 4:
                return t, p, v
            if i == 5:
                return v, p, q

        golden_ratio = 0.618033988749895
        h = 0.22717784590367374

        for _unused in xrange(n):
            h += golden_ratio
            h %= 1
            HSV_tuple = [h, 0.95, 0.95]
            RGB_tuple = hsv_to_rgb(*HSV_tuple)
            yield map(lambda x: str(int(x * 256)), RGB_tuple)

    cgenerator = gen_color()

    def get_color_string(cs):
        if cs in color_dict:
            col = color_dict[cs]
        else:
            col = color_dict[cs] = cgenerator.next()
        return "color: rgb(%s)! important;" % (', '.join(col))

    def url_func(repo_name):

        def _url_func(changeset):
            author = changeset.author
            date = changeset.date
            message = tooltip(changeset.message)

            tooltip_html = ("<div style='font-size:0.8em'><b>Author:</b>"
                            " %s<br/><b>Date:</b> %s</b><br/><b>Message:"
                            "</b> %s<br/></div>")

            tooltip_html = tooltip_html % (author, date, message)
            lnk_format = show_id(changeset)
            uri = link_to(
                    lnk_format,
                    url('changeset_home', repo_name=repo_name,
                        revision=changeset.raw_id),
                    style=get_color_string(changeset.raw_id),
                    class_='tooltip',
                    title=tooltip_html
                  )

            uri += '\n'
            return uri
        return _url_func

    return literal(markup_whitespace(annotate_highlight(filenode, url_func(repo_name), **kwargs)))


def is_following_repo(repo_name, user_id):
    from kallithea.model.scm import ScmModel
    return ScmModel().is_following_repo(repo_name, user_id)

class _Message(object):
    """A message returned by ``Flash.pop_messages()``.

    Converting the message to a string returns the message text. Instances
    also have the following attributes:

    * ``message``: the message text.
    * ``category``: the category specified when the message was created.
    """

    def __init__(self, category, message):
        self.category = category
        self.message = message

    def __str__(self):
        return self.message

    __unicode__ = __str__

    def __html__(self):
        return escape(safe_unicode(self.message))

class Flash(_Flash):

    def pop_messages(self):
        """Return all accumulated messages and delete them from the session.

        The return value is a list of ``Message`` objects.
        """
        from pylons import session
        messages = session.pop(self.session_key, [])
        session.save()
        return [_Message(*m) for m in messages]

flash = Flash()

#==============================================================================
# SCM FILTERS available via h.
#==============================================================================
from kallithea.lib.vcs.utils import author_name, author_email
from kallithea.lib.utils2 import credentials_filter, age as _age
from kallithea.model.db import User, ChangesetStatus

age = lambda  x, y=False: _age(x, y)
capitalize = lambda x: x.capitalize()
email = author_email
short_id = lambda x: x[:12]
hide_credentials = lambda x: ''.join(credentials_filter(x))


def show_id(cs):
    """
    Configurable function that shows ID
    by default it's r123:fffeeefffeee

    :param cs: changeset instance
    """
    from kallithea import CONFIG
    def_len = safe_int(CONFIG.get('show_sha_length', 12))
    show_rev = str2bool(CONFIG.get('show_revision_number', False))

    raw_id = cs.raw_id[:def_len]
    if show_rev:
        return 'r%s:%s' % (cs.revision, raw_id)
    else:
        return '%s' % (raw_id)


def fmt_date(date):
    if date:
        return date.strftime("%Y-%m-%d %H:%M:%S").decode('utf8')

    return ""


def is_git(repository):
    if hasattr(repository, 'alias'):
        _type = repository.alias
    elif hasattr(repository, 'repo_type'):
        _type = repository.repo_type
    else:
        _type = repository
    return _type == 'git'


def is_hg(repository):
    if hasattr(repository, 'alias'):
        _type = repository.alias
    elif hasattr(repository, 'repo_type'):
        _type = repository.repo_type
    else:
        _type = repository
    return _type == 'hg'


def user_or_none(author):
    email = author_email(author)
    if email is not None:
        user = User.get_by_email(email, case_insensitive=True, cache=True)
        if user is not None:
            return user

    user = User.get_by_username(author_name(author), case_insensitive=True, cache=True)
    if user is not None:
        return user

    return None

def email_or_none(author):
    if not author:
        return None
    user = user_or_none(author)
    if user is not None:
        return user.email # always use main email address - not necessarily the one used to find user

    # extract email from the commit string
    email = author_email(author)
    if email:
        return email

    # No valid email, not a valid user in the system, none!
    return None

def person(author, show_attr="username"):
    """Find the user identified by 'author', return one of the users attributes,
    default to the username attribute, None if there is no user"""
    # attr to return from fetched user
    person_getter = lambda usr: getattr(usr, show_attr)

    # if author is already an instance use it for extraction
    if isinstance(author, User):
        return person_getter(author)

    user = user_or_none(author)
    if user is not None:
        return person_getter(user)

    # Still nothing?  Just pass back the author name if any, else the email
    return author_name(author) or email(author)


def person_by_id(id_, show_attr="username"):
    # attr to return from fetched user
    person_getter = lambda usr: getattr(usr, show_attr)

    #maybe it's an ID ?
    if str(id_).isdigit() or isinstance(id_, int):
        id_ = int(id_)
        user = User.get(id_)
        if user is not None:
            return person_getter(user)
    return id_


def desc_stylize(value):
    """
    converts tags from value into html equivalent

    :param value:
    """
    if not value:
        return ''

    value = re.sub(r'\[see\ \=\>\ *([a-zA-Z0-9\/\=\?\&\ \:\/\.\-]*)\]',
                   '<div class="metatag" tag="see">see =&gt; \\1 </div>', value)
    value = re.sub(r'\[license\ \=\>\ *([a-zA-Z0-9\/\=\?\&\ \:\/\.\-]*)\]',
                   '<div class="metatag" tag="license"><a href="http:\/\/www.opensource.org/licenses/\\1">\\1</a></div>', value)
    value = re.sub(r'\[(requires|recommends|conflicts|base)\ \=\>\ *([a-zA-Z0-9\-\/]*)\]',
                   '<div class="metatag" tag="\\1">\\1 =&gt; <a href="/\\2">\\2</a></div>', value)
    value = re.sub(r'\[(lang|language)\ \=\>\ *([a-zA-Z\-\/\#\+]*)\]',
                   '<div class="metatag" tag="lang">\\2</div>', value)
    value = re.sub(r'\[([a-z]+)\]',
                  '<div class="metatag" tag="\\1">\\1</div>', value)

    return value


def boolicon(value):
    """Returns boolean value of a value, represented as small html image of true/false
    icons

    :param value: value
    """

    if value:
        return HTML.tag('i', class_="icon-ok")
    else:
        return HTML.tag('i', class_="icon-minus-circled")


def action_parser(user_log, feed=False, parse_cs=False):
    """
    This helper will action_map the specified string action into translated
    fancy names with icons and links

    :param user_log: user log instance
    :param feed: use output for feeds (no html and fancy icons)
    :param parse_cs: parse Changesets into VCS instances
    """

    action = user_log.action
    action_params = ' '

    x = action.split(':')

    if len(x) > 1:
        action, action_params = x

    def get_cs_links():
        revs_limit = 3  # display this amount always
        revs_top_limit = 50  # show upto this amount of changesets hidden
        revs_ids = action_params.split(',')
        deleted = user_log.repository is None
        if deleted:
            return ','.join(revs_ids)

        repo_name = user_log.repository.repo_name

        def lnk(rev, repo_name):
            if isinstance(rev, BaseChangeset) or isinstance(rev, AttributeDict):
                lazy_cs = True
                if getattr(rev, 'op', None) and getattr(rev, 'ref_name', None):
                    lazy_cs = False
                    lbl = '?'
                    if rev.op == 'delete_branch':
                        lbl = '%s' % _('Deleted branch: %s') % rev.ref_name
                        title = ''
                    elif rev.op == 'tag':
                        lbl = '%s' % _('Created tag: %s') % rev.ref_name
                        title = ''
                    _url = '#'

                else:
                    lbl = '%s' % (rev.short_id[:8])
                    _url = url('changeset_home', repo_name=repo_name,
                               revision=rev.raw_id)
                    title = tooltip(rev.message)
            else:
                ## changeset cannot be found/striped/removed etc.
                lbl = ('%s' % rev)[:12]
                _url = '#'
                title = _('Changeset not found')
            if parse_cs:
                return link_to(lbl, _url, title=title, class_='tooltip')
            return link_to(lbl, _url, raw_id=rev.raw_id, repo_name=repo_name,
                           class_='lazy-cs' if lazy_cs else '')

        def _get_op(rev_txt):
            _op = None
            _name = rev_txt
            if len(rev_txt.split('=>')) == 2:
                _op, _name = rev_txt.split('=>')
            return _op, _name

        revs = []
        if len(filter(lambda v: v != '', revs_ids)) > 0:
            repo = None
            for rev in revs_ids[:revs_top_limit]:
                _op, _name = _get_op(rev)

                # we want parsed changesets, or new log store format is bad
                if parse_cs:
                    try:
                        if repo is None:
                            repo = user_log.repository.scm_instance
                        _rev = repo.get_changeset(rev)
                        revs.append(_rev)
                    except ChangesetDoesNotExistError:
                        log.error('cannot find revision %s in this repo' % rev)
                        revs.append(rev)
                        continue
                else:
                    _rev = AttributeDict({
                        'short_id': rev[:12],
                        'raw_id': rev,
                        'message': '',
                        'op': _op,
                        'ref_name': _name
                    })
                    revs.append(_rev)
        cs_links = [" " + ', '.join(
            [lnk(rev, repo_name) for rev in revs[:revs_limit]]
        )]
        _op1, _name1 = _get_op(revs_ids[0])
        _op2, _name2 = _get_op(revs_ids[-1])

        _rev = '%s...%s' % (_name1, _name2)

        compare_view = (
            ' <div class="compare_view tooltip" title="%s">'
            '<a href="%s">%s</a> </div>' % (
                _('Show all combined changesets %s->%s') % (
                    revs_ids[0][:12], revs_ids[-1][:12]
                ),
                url('changeset_home', repo_name=repo_name,
                    revision=_rev
                ),
                _('compare view')
            )
        )

        # if we have exactly one more than normally displayed
        # just display it, takes less space than displaying
        # "and 1 more revisions"
        if len(revs_ids) == revs_limit + 1:
            cs_links.append(", " + lnk(revs[revs_limit], repo_name))

        # hidden-by-default ones
        if len(revs_ids) > revs_limit + 1:
            uniq_id = revs_ids[0]
            html_tmpl = (
                '<span> %s <a class="show_more" id="_%s" '
                'href="#more">%s</a> %s</span>'
            )
            if not feed:
                cs_links.append(html_tmpl % (
                      _('and'),
                      uniq_id, _('%s more') % (len(revs_ids) - revs_limit),
                      _('revisions')
                    )
                )

            if not feed:
                html_tmpl = '<span id="%s" style="display:none">, %s </span>'
            else:
                html_tmpl = '<span id="%s"> %s </span>'

            morelinks = ', '.join(
              [lnk(rev, repo_name) for rev in revs[revs_limit:]]
            )

            if len(revs_ids) > revs_top_limit:
                morelinks += ', ...'

            cs_links.append(html_tmpl % (uniq_id, morelinks))
        if len(revs) > 1:
            cs_links.append(compare_view)
        return ''.join(cs_links)

    def get_fork_name():
        repo_name = action_params
        _url = url('summary_home', repo_name=repo_name)
        return _('fork name %s') % link_to(action_params, _url)

    def get_user_name():
        user_name = action_params
        return user_name

    def get_users_group():
        group_name = action_params
        return group_name

    def get_pull_request():
        pull_request_id = action_params
        deleted = user_log.repository is None
        if deleted:
            repo_name = user_log.repository_name
        else:
            repo_name = user_log.repository.repo_name
        return link_to(_('Pull request #%s') % pull_request_id,
                    url('pullrequest_show', repo_name=repo_name,
                    pull_request_id=pull_request_id))

    def get_archive_name():
        archive_name = action_params
        return archive_name

    # action : translated str, callback(extractor), icon
    action_map = {
    'user_deleted_repo':           (_('[deleted] repository'),
                                    None, 'icon-trashcan'),
    'user_created_repo':           (_('[created] repository'),
                                    None, 'icon-plus'),
    'user_created_fork':           (_('[created] repository as fork'),
                                    None, 'icon-fork'),
    'user_forked_repo':            (_('[forked] repository'),
                                    get_fork_name, 'icon-fork'),
    'user_updated_repo':           (_('[updated] repository'),
                                    None, 'icon-pencil'),
    'user_downloaded_archive':      (_('[downloaded] archive from repository'),
                                    get_archive_name, 'icon-download-cloud'),
    'admin_deleted_repo':          (_('[delete] repository'),
                                    None, 'icon-trashcan'),
    'admin_created_repo':          (_('[created] repository'),
                                    None, 'icon-plus'),
    'admin_forked_repo':           (_('[forked] repository'),
                                    None, 'icon-fork'),
    'admin_updated_repo':          (_('[updated] repository'),
                                    None, 'icon-pencil'),
    'admin_created_user':          (_('[created] user'),
                                    get_user_name, 'icon-user'),
    'admin_updated_user':          (_('[updated] user'),
                                    get_user_name, 'icon-user'),
    'admin_created_users_group':   (_('[created] user group'),
                                    get_users_group, 'icon-pencil'),
    'admin_updated_users_group':   (_('[updated] user group'),
                                    get_users_group, 'icon-pencil'),
    'user_commented_revision':     (_('[commented] on revision in repository'),
                                    get_cs_links, 'icon-comment'),
    'user_commented_pull_request': (_('[commented] on pull request for'),
                                    get_pull_request, 'icon-comment'),
    'user_closed_pull_request':    (_('[closed] pull request for'),
                                    get_pull_request, 'icon-ok'),
    'push':                        (_('[pushed] into'),
                                    get_cs_links, 'icon-move-up'),
    'push_local':                  (_('[committed via Kallithea] into repository'),
                                    get_cs_links, 'icon-pencil'),
    'push_remote':                 (_('[pulled from remote] into repository'),
                                    get_cs_links, 'icon-move-up'),
    'pull':                        (_('[pulled] from'),
                                    None, 'icon-move-down'),
    'started_following_repo':      (_('[started following] repository'),
                                    None, 'icon-heart'),
    'stopped_following_repo':      (_('[stopped following] repository'),
                                    None, 'icon-heart-empty'),
    }

    action_str = action_map.get(action, action)
    if feed:
        action = action_str[0].replace('[', '').replace(']', '')
    else:
        action = action_str[0]\
            .replace('[', '<span class="journal_highlight">')\
            .replace(']', '</span>')

    action_params_func = lambda: ""

    if callable(action_str[1]):
        action_params_func = action_str[1]

    def action_parser_icon():
        action = user_log.action
        action_params = None
        x = action.split(':')

        if len(x) > 1:
            action, action_params = x

        tmpl = """<i class="%s" alt="%s"></i>"""
        ico = action_map.get(action, ['', '', ''])[2]
        return literal(tmpl % (ico, action))

    # returned callbacks we need to call to get
    return [lambda: literal(action), action_params_func, action_parser_icon]



#==============================================================================
# PERMS
#==============================================================================
from kallithea.lib.auth import HasPermissionAny, HasPermissionAll, \
HasRepoPermissionAny, HasRepoPermissionAll, HasRepoGroupPermissionAll, \
HasRepoGroupPermissionAny


#==============================================================================
# GRAVATAR URL
#==============================================================================
def gravatar(email_address, cls='', size=30, ssl_enabled=True):
    """return html element of the gravatar

    This method will return an <img> with the resolution double the size (for
    retina screens) of the image. If the url returned from gravatar_url is
    empty then we fallback to using an icon.

    """
    src = gravatar_url(email_address, size*2, ssl_enabled)

    #  here it makes sense to use style="width: ..." (instead of, say, a
    # stylesheet) because we using this to generate a high-res (retina) size
    tmpl = """<img alt="gravatar" class="{cls}" style="width: {size}px; height: {size}px" src="{src}"/>"""

    # if src is empty then there was no gravatar, so we use a font icon
    if not src:
        tmpl = """<i class="icon-user {cls}" style="font-size: {size}px;"></i>"""

    tmpl = tmpl.format(cls=cls, size=size, src=src)
    return literal(tmpl)

def gravatar_url(email_address, size=30, ssl_enabled=True):
    # doh, we need to re-import those to mock it later
    from pylons import url
    from pylons import tmpl_context as c

    _def = 'anonymous@kallithea-scm.org'  # default gravatar
    _use_gravatar = c.visual.use_gravatar
    _gravatar_url = c.visual.gravatar_url or User.DEFAULT_GRAVATAR_URL

    email_address = email_address or _def

    if not _use_gravatar or not email_address or email_address == _def:
        return ""

    if _use_gravatar:
        _md5 = lambda s: hashlib.md5(s).hexdigest()

        tmpl = _gravatar_url
        parsed_url = urlparse.urlparse(url.current(qualified=True))
        tmpl = tmpl.replace('{email}', email_address)\
                   .replace('{md5email}', _md5(safe_str(email_address).lower())) \
                   .replace('{netloc}', parsed_url.netloc)\
                   .replace('{scheme}', parsed_url.scheme)\
                   .replace('{size}', safe_str(size))
        return tmpl

class Page(_Page):
    """
    Custom pager to match rendering style with YUI paginator
    """

    def _get_pos(self, cur_page, max_page, items):
        edge = (items / 2) + 1
        if (cur_page <= edge):
            radius = max(items / 2, items - cur_page)
        elif (max_page - cur_page) < edge:
            radius = (items - 1) - (max_page - cur_page)
        else:
            radius = items / 2

        left = max(1, (cur_page - (radius)))
        right = min(max_page, cur_page + (radius))
        return left, cur_page, right

    def _range(self, regexp_match):
        """
        Return range of linked pages (e.g. '1 2 [3] 4 5 6 7 8').

        Arguments:

        regexp_match
            A "re" (regular expressions) match object containing the
            radius of linked pages around the current page in
            regexp_match.group(1) as a string

        This function is supposed to be called as a callable in
        re.sub.

        """
        radius = int(regexp_match.group(1))

        # Compute the first and last page number within the radius
        # e.g. '1 .. 5 6 [7] 8 9 .. 12'
        # -> leftmost_page  = 5
        # -> rightmost_page = 9
        leftmost_page, _cur, rightmost_page = self._get_pos(self.page,
                                                            self.last_page,
                                                            (radius * 2) + 1)
        nav_items = []

        # Create a link to the first page (unless we are on the first page
        # or there would be no need to insert '..' spacers)
        if self.page != self.first_page and self.first_page < leftmost_page:
            nav_items.append(self._pagerlink(self.first_page, self.first_page))

        # Insert dots if there are pages between the first page
        # and the currently displayed page range
        if leftmost_page - self.first_page > 1:
            # Wrap in a SPAN tag if nolink_attr is set
            text = '..'
            if self.dotdot_attr:
                text = HTML.span(c=text, **self.dotdot_attr)
            nav_items.append(text)

        for thispage in xrange(leftmost_page, rightmost_page + 1):
            # Highlight the current page number and do not use a link
            if thispage == self.page:
                text = '%s' % (thispage,)
                # Wrap in a SPAN tag if nolink_attr is set
                if self.curpage_attr:
                    text = HTML.span(c=text, **self.curpage_attr)
                nav_items.append(text)
            # Otherwise create just a link to that page
            else:
                text = '%s' % (thispage,)
                nav_items.append(self._pagerlink(thispage, text))

        # Insert dots if there are pages between the displayed
        # page numbers and the end of the page range
        if self.last_page - rightmost_page > 1:
            text = '..'
            # Wrap in a SPAN tag if nolink_attr is set
            if self.dotdot_attr:
                text = HTML.span(c=text, **self.dotdot_attr)
            nav_items.append(text)

        # Create a link to the very last page (unless we are on the last
        # page or there would be no need to insert '..' spacers)
        if self.page != self.last_page and rightmost_page < self.last_page:
            nav_items.append(self._pagerlink(self.last_page, self.last_page))

        #_page_link = url.current()
        #nav_items.append(literal('<link rel="prerender" href="%s?page=%s">' % (_page_link, str(int(self.page)+1))))
        #nav_items.append(literal('<link rel="prefetch" href="%s?page=%s">' % (_page_link, str(int(self.page)+1))))
        return self.separator.join(nav_items)

    def pager(self, format='~2~', page_param='page', partial_param='partial',
        show_if_single_page=False, separator=' ', onclick=None,
        symbol_first='<<', symbol_last='>>',
        symbol_previous='<', symbol_next='>',
        link_attr={'class': 'pager_link', 'rel': 'prerender'},
        curpage_attr={'class': 'pager_curpage'},
        dotdot_attr={'class': 'pager_dotdot'}, **kwargs):

        self.curpage_attr = curpage_attr
        self.separator = separator
        self.pager_kwargs = kwargs
        self.page_param = page_param
        self.partial_param = partial_param
        self.onclick = onclick
        self.link_attr = link_attr
        self.dotdot_attr = dotdot_attr

        # Don't show navigator if there is no more than one page
        if self.page_count == 0 or (self.page_count == 1 and not show_if_single_page):
            return ''

        from string import Template
        # Replace ~...~ in token format by range of pages
        result = re.sub(r'~(\d+)~', self._range, format)

        # Interpolate '%' variables
        result = Template(result).safe_substitute({
            'first_page': self.first_page,
            'last_page': self.last_page,
            'page': self.page,
            'page_count': self.page_count,
            'items_per_page': self.items_per_page,
            'first_item': self.first_item,
            'last_item': self.last_item,
            'item_count': self.item_count,
            'link_first': self.page > self.first_page and \
                    self._pagerlink(self.first_page, symbol_first) or '',
            'link_last': self.page < self.last_page and \
                    self._pagerlink(self.last_page, symbol_last) or '',
            'link_previous': self.previous_page and \
                    self._pagerlink(self.previous_page, symbol_previous) \
                    or HTML.span(symbol_previous, class_="yui-pg-previous"),
            'link_next': self.next_page and \
                    self._pagerlink(self.next_page, symbol_next) \
                    or HTML.span(symbol_next, class_="yui-pg-next")
        })

        return literal(result)


#==============================================================================
# REPO PAGER, PAGER FOR REPOSITORY
#==============================================================================
class RepoPage(Page):

    def __init__(self, collection, page=1, items_per_page=20,
                 item_count=None, url=None, **kwargs):

        """Create a "RepoPage" instance. special pager for paging
        repository
        """
        self._url_generator = url

        # Safe the kwargs class-wide so they can be used in the pager() method
        self.kwargs = kwargs

        # Save a reference to the collection
        self.original_collection = collection

        self.collection = collection

        # The self.page is the number of the current page.
        # The first page has the number 1!
        try:
            self.page = int(page)  # make it int() if we get it as a string
        except (ValueError, TypeError):
            self.page = 1

        self.items_per_page = items_per_page

        # Unless the user tells us how many items the collections has
        # we calculate that ourselves.
        if item_count is not None:
            self.item_count = item_count
        else:
            self.item_count = len(self.collection)

        # Compute the number of the first and last available page
        if self.item_count > 0:
            self.first_page = 1
            self.page_count = int(math.ceil(float(self.item_count) /
                                            self.items_per_page))
            self.last_page = self.first_page + self.page_count - 1

            # Make sure that the requested page number is the range of
            # valid pages
            if self.page > self.last_page:
                self.page = self.last_page
            elif self.page < self.first_page:
                self.page = self.first_page

            # Note: the number of items on this page can be less than
            #       items_per_page if the last page is not full
            self.first_item = max(0, (self.item_count) - (self.page *
                                                          items_per_page))
            self.last_item = ((self.item_count - 1) - items_per_page *
                              (self.page - 1))

            self.items = list(self.collection[self.first_item:self.last_item + 1])

            # Links to previous and next page
            if self.page > self.first_page:
                self.previous_page = self.page - 1
            else:
                self.previous_page = None

            if self.page < self.last_page:
                self.next_page = self.page + 1
            else:
                self.next_page = None

        # No items available
        else:
            self.first_page = None
            self.page_count = 0
            self.last_page = None
            self.first_item = None
            self.last_item = None
            self.previous_page = None
            self.next_page = None
            self.items = []

        # This is a subclass of the 'list' type. Initialise the list now.
        list.__init__(self, reversed(self.items))


def changed_tooltip(nodes):
    """
    Generates a html string for changed nodes in changeset page.
    It limits the output to 30 entries

    :param nodes: LazyNodesGenerator
    """
    if nodes:
        pref = ': <br/> '
        suf = ''
        if len(nodes) > 30:
            suf = '<br/>' + _(' and %s more') % (len(nodes) - 30)
        return literal(pref + '<br/> '.join([safe_unicode(x.path)
                                             for x in nodes[:30]]) + suf)
    else:
        return ': ' + _('No Files')


def repo_link(groups_and_repos):
    """
    Makes a breadcrumbs link to repo within a group
    joins &raquo; on each group to create a fancy link

    ex::
        group >> subgroup >> repo

    :param groups_and_repos:
    :param last_url:
    """
    groups, just_name, repo_name = groups_and_repos
    last_url = url('summary_home', repo_name=repo_name)
    last_link = link_to(just_name, last_url)

    def make_link(group):
        return link_to(group.name,
                       url('repos_group_home', group_name=group.group_name))
    return literal(' &raquo; '.join(map(make_link, groups) + ['<span>%s</span>' % last_link]))


def fancy_file_stats(stats):
    """
    Displays a fancy two colored bar for number of added/deleted
    lines of code on file

    :param stats: two element list of added/deleted lines of code
    """
    from kallithea.lib.diffs import NEW_FILENODE, DEL_FILENODE, \
        MOD_FILENODE, RENAMED_FILENODE, CHMOD_FILENODE, BIN_FILENODE

    def cgen(l_type, a_v, d_v):
        mapping = {'tr': 'top-right-rounded-corner-mid',
                   'tl': 'top-left-rounded-corner-mid',
                   'br': 'bottom-right-rounded-corner-mid',
                   'bl': 'bottom-left-rounded-corner-mid'}
        map_getter = lambda x: mapping[x]

        if l_type == 'a' and d_v:
            #case when added and deleted are present
            return ' '.join(map(map_getter, ['tl', 'bl']))

        if l_type == 'a' and not d_v:
            return ' '.join(map(map_getter, ['tr', 'br', 'tl', 'bl']))

        if l_type == 'd' and a_v:
            return ' '.join(map(map_getter, ['tr', 'br']))

        if l_type == 'd' and not a_v:
            return ' '.join(map(map_getter, ['tr', 'br', 'tl', 'bl']))

    a, d = stats['added'], stats['deleted']
    width = 100

    if stats['binary']:
        #binary mode
        lbl = ''
        bin_op = 1

        if BIN_FILENODE in stats['ops']:
            lbl = 'bin+'

        if NEW_FILENODE in stats['ops']:
            lbl += _('new file')
            bin_op = NEW_FILENODE
        elif MOD_FILENODE in stats['ops']:
            lbl += _('mod')
            bin_op = MOD_FILENODE
        elif DEL_FILENODE in stats['ops']:
            lbl += _('del')
            bin_op = DEL_FILENODE
        elif RENAMED_FILENODE in stats['ops']:
            lbl += _('rename')
            bin_op = RENAMED_FILENODE

        #chmod can go with other operations
        if CHMOD_FILENODE in stats['ops']:
            _org_lbl = _('chmod')
            lbl += _org_lbl if lbl.endswith('+') else '+%s' % _org_lbl

        #import ipdb;ipdb.set_trace()
        b_d = '<div class="bin bin%s %s" style="width:100%%">%s</div>' % (bin_op, cgen('a', a_v='', d_v=0), lbl)
        b_a = '<div class="bin bin1" style="width:0%%"></div>'
        return literal('<div style="width:%spx">%s%s</div>' % (width, b_a, b_d))

    t = stats['added'] + stats['deleted']
    unit = float(width) / (t or 1)

    # needs > 9% of width to be visible or 0 to be hidden
    a_p = max(9, unit * a) if a > 0 else 0
    d_p = max(9, unit * d) if d > 0 else 0
    p_sum = a_p + d_p

    if p_sum > width:
        #adjust the percentage to be == 100% since we adjusted to 9
        if a_p > d_p:
            a_p = a_p - (p_sum - width)
        else:
            d_p = d_p - (p_sum - width)

    a_v = a if a > 0 else ''
    d_v = d if d > 0 else ''

    d_a = '<div class="added %s" style="width:%s%%">%s</div>' % (
        cgen('a', a_v, d_v), a_p, a_v
    )
    d_d = '<div class="deleted %s" style="width:%s%%">%s</div>' % (
        cgen('d', a_v, d_v), d_p, d_v
    )
    return literal('<div style="width:%spx">%s%s</div>' % (width, d_a, d_d))


def urlify_text(text_, safe=True):
    """
    Extract urls from text and make html links out of them

    :param text_:
    """

    def url_func(match_obj):
        url_full = match_obj.groups()[0]
        return '<a href="%(url)s">%(url)s</a>' % ({'url': url_full})
    _newtext = url_re.sub(url_func, text_)
    if safe:
        return literal(_newtext)
    return _newtext


def urlify_changesets(text_, repository):
    """
    Extract revision ids from changeset and make link from them

    :param text_:
    :param repository: repo name to build the URL with
    """
    from pylons import url  # doh, we need to re-import url to mock it later

    def url_func(match_obj):
        rev = match_obj.group(0)
        return '<a class="revision-link" href="%(url)s">%(rev)s</a>' % {
         'url': url('changeset_home', repo_name=repository, revision=rev),
         'rev': rev,
        }

    return re.sub(r'(?:^|(?<=[\s(),]))([0-9a-fA-F]{12,40})(?=$|\s|[.,:()])', url_func, text_)

def linkify_others(t, l):
    urls = re.compile(r'(\<a.*?\<\/a\>)',)
    links = []
    for e in urls.split(t):
        if not urls.match(e):
            links.append('<a class="message-link" href="%s">%s</a>' % (l, e))
        else:
            links.append(e)

    return ''.join(links)

def urlify_commit(text_, repository, link_=None):
    """
    Parses given text message and makes proper links.
    issues are linked to given issue-server, and rest is a changeset link
    if link_ is given, in other case it's a plain text

    :param text_:
    :param repository:
    :param link_: changeset link
    """
    def escaper(string):
        return string.replace('<', '&lt;').replace('>', '&gt;')

    # urlify changesets - extract revisions and make link out of them
    newtext = urlify_changesets(escaper(text_), repository)

    # extract http/https links and make them real urls
    newtext = urlify_text(newtext, safe=False)

    newtext = urlify_issues(newtext, repository, link_)

    return literal(newtext)

def urlify_issues(newtext, repository, link_=None):
    from kallithea import CONFIG as conf

    # allow multiple issue servers to be used
    valid_indices = [
        x.group(1)
        for x in map(lambda x: re.match(r'issue_pat(.*)', x), conf.keys())
        if x and 'issue_server_link%s' % x.group(1) in conf
        and 'issue_prefix%s' % x.group(1) in conf
    ]

    if valid_indices:
        log.debug('found issue server suffixes `%s` during valuation of: %s'
                  % (','.join(valid_indices), newtext))

    for pattern_index in valid_indices:
        ISSUE_PATTERN = conf.get('issue_pat%s' % pattern_index)
        ISSUE_SERVER_LNK = conf.get('issue_server_link%s' % pattern_index)
        ISSUE_PREFIX = conf.get('issue_prefix%s' % pattern_index)

        log.debug('pattern suffix `%s` PAT:%s SERVER_LINK:%s PREFIX:%s'
                  % (pattern_index, ISSUE_PATTERN, ISSUE_SERVER_LNK,
                     ISSUE_PREFIX))

        URL_PAT = re.compile(r'%s' % ISSUE_PATTERN)

        def url_func(match_obj):
            pref = ''
            if match_obj.group().startswith(' '):
                pref = ' '

            issue_id = ''.join(match_obj.groups())
            issue_url = ISSUE_SERVER_LNK.replace('{id}', issue_id)
            if repository:
                issue_url = issue_url.replace('{repo}', repository)
                repo_name = repository.split(URL_SEP)[-1]
                issue_url = issue_url.replace('{repo_name}', repo_name)

            return (
                '%(pref)s<a class="%(cls)s" href="%(url)s">'
                '%(issue-prefix)s%(id-repr)s'
                '</a>'
                ) % {
                 'pref': pref,
                 'cls': 'issue-tracker-link',
                 'url': issue_url,
                 'id-repr': issue_id,
                 'issue-prefix': ISSUE_PREFIX,
                 'serv': ISSUE_SERVER_LNK,
                }
        newtext = URL_PAT.sub(url_func, newtext)
        log.debug('processed prefix:`%s` => %s' % (pattern_index, newtext))

    # if we actually did something above
    if link_:
        # wrap not links into final link => link_
        newtext = linkify_others(newtext, link_)
    return newtext


def rst(source):
    return literal('<div class="rst-block">%s</div>' %
                   MarkupRenderer.rst(source))


def rst_w_mentions(source):
    """
    Wrapped rst renderer with @mention highlighting

    :param source:
    """
    return literal('<div class="rst-block">%s</div>' %
                   MarkupRenderer.rst_with_mentions(source))

def short_ref(ref_type, ref_name):
    if ref_type == 'rev':
        return short_id(ref_name)
    return ref_name

def link_to_ref(repo_name, ref_type, ref_name, rev=None):
    """
    Return full markup for a href to changeset_home for a changeset.
    If ref_type is branch it will link to changelog.
    ref_name is shortened if ref_type is 'rev'.
    if rev is specified show it too, explicitly linking to that revision.
    """
    txt = short_ref(ref_type, ref_name)
    if ref_type == 'branch':
        u = url('changelog_home', repo_name=repo_name, branch=ref_name)
    else:
        u = url('changeset_home', repo_name=repo_name, revision=ref_name)
    l = link_to(repo_name + '#' + txt, u)
    if rev and ref_type != 'rev':
        l = literal('%s (%s)' % (l, link_to(short_id(rev), url('changeset_home', repo_name=repo_name, revision=rev))))
    return l

def changeset_status(repo, revision):
    return ChangesetStatusModel().get_status(repo, revision)


def changeset_status_lbl(changeset_status):
    return dict(ChangesetStatus.STATUSES).get(changeset_status)


def get_permission_name(key):
    return dict(Permission.PERMS).get(key)


def journal_filter_help():
    return _(textwrap.dedent('''
        Example filter terms:
            repository:vcs
            username:developer
            action:*push*
            ip:127.0.0.1
            date:20120101
            date:[20120101100000 TO 20120102]

        Generate wildcards using '*' character:
            "repository:vcs*" - search everything starting with 'vcs'
            "repository:*vcs*" - search for repository containing 'vcs'

        Optional AND / OR operators in queries
            "repository:vcs OR repository:test"
            "username:test AND repository:test*"
    '''))


def not_mapped_error(repo_name):
    flash(_('%s repository is not mapped to db perhaps'
            ' it was created or renamed from the filesystem'
            ' please run the application again'
            ' in order to rescan repositories') % repo_name, category='error')


def ip_range(ip_addr):
    from kallithea.model.db import UserIpMap
    s, e = UserIpMap._get_ip_range(ip_addr)
    return '%s - %s' % (s, e)
