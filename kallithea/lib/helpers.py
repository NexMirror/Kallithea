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
import hashlib
import json
import logging
import random
import re
import StringIO
import textwrap
import urlparse

from beaker.cache import cache_region
from pygments import highlight as code_highlight
from pygments.formatters.html import HtmlFormatter
from tg.i18n import ugettext as _
from webhelpers2.html import HTML, escape, literal
from webhelpers2.html.tags import NotGiven, Option, Options, _input, _make_safe_id_component, checkbox, end_form
from webhelpers2.html.tags import form as insecure_form
from webhelpers2.html.tags import hidden, link_to, password, radio
from webhelpers2.html.tags import select as webhelpers2_select
from webhelpers2.html.tags import submit, text, textarea
from webhelpers2.number import format_byte_size
from webhelpers2.text import chop_at, truncate, wrap_paragraphs

from kallithea.config.routing import url
from kallithea.lib.annotate import annotate_highlight
#==============================================================================
# PERMS
#==============================================================================
from kallithea.lib.auth import HasPermissionAny, HasRepoGroupPermissionLevel, HasRepoPermissionLevel
from kallithea.lib.markup_renderer import url_re
from kallithea.lib.pygmentsutils import get_custom_lexer
from kallithea.lib.utils2 import MENTIONS_REGEX, AttributeDict
from kallithea.lib.utils2 import age as _age
from kallithea.lib.utils2 import credentials_filter, safe_int, safe_str, safe_unicode, str2bool, time_to_datetime
from kallithea.lib.vcs.backends.base import BaseChangeset, EmptyChangeset
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError
#==============================================================================
# SCM FILTERS available via h.
#==============================================================================
from kallithea.lib.vcs.utils import author_email, author_name


log = logging.getLogger(__name__)


def canonical_url(*args, **kargs):
    '''Like url(x, qualified=True), but returns url that not only is qualified
    but also canonical, as configured in canonical_url'''
    from kallithea import CONFIG
    try:
        parts = CONFIG.get('canonical_url', '').split('://', 1)
        kargs['host'] = parts[1]
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


def html_escape(s):
    """Return string with all html escaped.
    This is also safe for javascript in html but not necessarily correct.
    """
    return (s
        .replace('&', '&amp;')
        .replace(">", "&gt;")
        .replace("<", "&lt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;") # Note: this is HTML5 not HTML4 and might not work in mails
        )

def js(value):
    """Convert Python value to the corresponding JavaScript representation.

    This is necessary to safely insert arbitrary values into HTML <script>
    sections e.g. using Mako template expression substitution.

    Note: Rather than using this function, it's preferable to avoid the
    insertion of values into HTML <script> sections altogether. Instead,
    data should (to the extent possible) be passed to JavaScript using
    data attributes or AJAX calls, eliminating the need for JS specific
    escaping.

    Note: This is not safe for use in attributes (e.g. onclick), because
    quotes are not escaped.

    Because the rules for parsing <script> varies between XHTML (where
    normal rules apply for any special characters) and HTML (where
    entities are not interpreted, but the literal string "</script>"
    is forbidden), the function ensures that the result never contains
    '&', '<' and '>', thus making it safe in both those contexts (but
    not in attributes).
    """
    return literal(
        ('(' + json.dumps(value) + ')')
        # In JSON, the following can only appear in string literals.
        .replace('&', r'\x26')
        .replace('<', r'\x3c')
        .replace('>', r'\x3e')
    )


def jshtml(val):
    """HTML escapes a string value, then converts the resulting string
    to its corresponding JavaScript representation (see `js`).

    This is used when a plain-text string (possibly containing special
    HTML characters) will be used by a script in an HTML context (e.g.
    element.innerHTML or jQuery's 'html' method).

    If in doubt, err on the side of using `jshtml` over `js`, since it's
    better to escape too much than too little.
    """
    return js(escape(val))


def shorter(s, size=20, firstline=False, postfix='...'):
    """Truncate s to size, including the postfix string if truncating.
    If firstline, truncate at newline.
    """
    if firstline:
        s = s.split('\n', 1)[0].rstrip()
    if len(s) > size:
        return s[:size - len(postfix)] + postfix
    return s


def reset(name, value, id=NotGiven, **attrs):
    """Create a reset button, similar to webhelpers2.html.tags.submit ."""
    return _input("reset", name, value, id, attrs)


def select(name, selected_values, options, id=NotGiven, **attrs):
    """Convenient wrapper of webhelpers2 to let it accept options as a tuple list"""
    if isinstance(options, list):
        option_list = options
        # Handle old value,label lists ... where value also can be value,label lists
        options = Options()
        for x in option_list:
            if isinstance(x, tuple) and len(x) == 2:
                value, label = x
            elif isinstance(x, basestring):
                value = label = x
            else:
                log.error('invalid select option %r', x)
                raise
            if isinstance(value, list):
                og = options.add_optgroup(label)
                for x in value:
                    if isinstance(x, tuple) and len(x) == 2:
                        group_value, group_label = x
                    elif isinstance(x, basestring):
                        group_value = group_label = x
                    else:
                        log.error('invalid select option %r', x)
                        raise
                    og.add_option(group_label, group_value)
            else:
                options.add_option(label, value)
    return webhelpers2_select(name, selected_values, options, id=id, **attrs)


safeid = _make_safe_id_component


def FID(raw_id, path):
    """
    Creates a unique ID for filenode based on it's hash of path and revision
    it's safe to use in urls

    :param raw_id:
    :param path:
    """

    return 'C-%s-%s' % (short_id(raw_id), hashlib.md5(safe_str(path)).hexdigest()[:12])


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
            t = '<span id="L%s">%s</span>' % (cnt + 1, t)
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
                      '<tr><td><div class="linenodiv">'
                      '<pre>' + ls + '</pre></div></td>'
                      '<td id="hlcode" class="code">')
        else:
            yield 0, ('<table class="%stable">' % self.cssclass +
                      '<tr><td class="linenos"><div class="linenodiv">'
                      '<pre>' + ls + '</pre></div></td>'
                      '<td id="hlcode" class="code">')
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
            author = escape(changeset.author)
            date = changeset.date
            message = escape(changeset.message)
            tooltip_html = ("<b>Author:</b> %s<br/>"
                            "<b>Date:</b> %s</b><br/>"
                            "<b>Message:</b> %s") % (author, date, message)

            lnk_format = show_id(changeset)
            uri = link_to(
                    lnk_format,
                    url('changeset_home', repo_name=repo_name,
                        revision=changeset.raw_id),
                    style=get_color_string(changeset.raw_id),
                    **{'data-toggle': 'popover',
                       'data-content': tooltip_html}
                  )

            uri += '\n'
            return uri
        return _url_func

    return literal(markup_whitespace(annotate_highlight(filenode, url_func(repo_name), **kwargs)))


class _Message(object):
    """A message returned by ``pop_flash_messages()``.

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


def _session_flash_messages(append=None, clear=False):
    """Manage a message queue in tg.session: return the current message queue
    after appending the given message, and possibly clearing the queue."""
    key = 'flash'
    from tg import session
    if key in session:
        flash_messages = session[key]
    else:
        if append is None:  # common fast path - also used for clearing empty queue
            return []  # don't bother saving
        flash_messages = []
        session[key] = flash_messages
    if append is not None and append not in flash_messages:
        flash_messages.append(append)
    if clear:
        session.pop(key, None)
    session.save()
    return flash_messages


def flash(message, category=None, logf=None):
    """
    Show a message to the user _and_ log it through the specified function

    category: notice (default), warning, error, success
    logf: a custom log function - such as log.debug

    logf defaults to log.info, unless category equals 'success', in which
    case logf defaults to log.debug.
    """
    if logf is None:
        logf = log.info
        if category == 'success':
            logf = log.debug

    logf('Flash %s: %s', category, message)

    _session_flash_messages(append=(category, message))


def pop_flash_messages():
    """Return all accumulated messages and delete them from the session.

    The return value is a list of ``Message`` objects.
    """
    return [_Message(*m) for m in _session_flash_messages(clear=True)]


age = lambda x, y=False: _age(x, y)
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
        return raw_id


def fmt_date(date):
    if date:
        return date.strftime("%Y-%m-%d %H:%M:%S").decode('utf-8')

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


@cache_region('long_term', 'user_attr_or_none')
def user_attr_or_none(author, show_attr):
    """Try to match email part of VCS committer string with a local user and return show_attr
    - or return None if user not found"""
    email = author_email(author)
    if email:
        from kallithea.model.db import User
        user = User.get_by_email(email, cache=True) # cache will only use sql_cache_short
        if user is not None:
            return getattr(user, show_attr)
    return None


def email_or_none(author):
    """Try to match email part of VCS committer string with a local user.
    Return primary email of user, email part of the specified author name, or None."""
    if not author:
        return None
    email = user_attr_or_none(author, 'email')
    if email is not None:
        return email # always use user's main email address - not necessarily the one used to find user

    # extract email from the commit string
    email = author_email(author)
    if email:
        return email

    # No valid email, not a valid user in the system, none!
    return None


def person(author, show_attr="username"):
    """Find the user identified by 'author', return one of the users attributes,
    default to the username attribute, None if there is no user"""
    from kallithea.model.db import User
    # if author is already an instance use it for extraction
    if isinstance(author, User):
        return getattr(author, show_attr)

    value = user_attr_or_none(author, show_attr)
    if value is not None:
        return value

    # Still nothing?  Just pass back the author name if any, else the email
    return author_name(author) or email(author)


def person_by_id(id_, show_attr="username"):
    from kallithea.model.db import User
    # attr to return from fetched user
    person_getter = lambda usr: getattr(usr, show_attr)

    # maybe it's an ID ?
    if str(id_).isdigit() or isinstance(id_, int):
        id_ = int(id_)
        user = User.get(id_)
        if user is not None:
            return person_getter(user)
    return id_


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
            lazy_cs = False
            title_ = None
            url_ = '#'
            if isinstance(rev, BaseChangeset) or isinstance(rev, AttributeDict):
                if rev.op and rev.ref_name:
                    if rev.op == 'delete_branch':
                        lbl = _('Deleted branch: %s') % rev.ref_name
                    elif rev.op == 'tag':
                        lbl = _('Created tag: %s') % rev.ref_name
                    else:
                        lbl = 'Unknown operation %s' % rev.op
                else:
                    lazy_cs = True
                    lbl = rev.short_id[:8]
                    url_ = url('changeset_home', repo_name=repo_name,
                               revision=rev.raw_id)
            else:
                # changeset cannot be found - it might have been stripped or removed
                lbl = rev[:12]
                title_ = _('Changeset %s not found') % lbl
            if parse_cs:
                return link_to(lbl, url_, title=title_, **{'data-toggle': 'tooltip'})
            return link_to(lbl, url_, class_='lazy-cs' if lazy_cs else '',
                           **{'data-raw_id': rev.raw_id, 'data-repo_name': repo_name})

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
                        log.error('cannot find revision %s in this repo', rev)
                        revs.append(rev)
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
            ' <div class="compare_view" data-toggle="tooltip" title="%s">'
            '<a href="%s">%s</a> </div>' % (
                _('Show all combined changesets %s->%s') % (
                    revs_ids[0][:12], revs_ids[-1][:12]
                ),
                url('changeset_home', repo_name=repo_name,
                    revision=_rev
                ),
                _('Compare view')
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
        url_ = url('summary_home', repo_name=repo_name)
        return _('Fork name %s') % link_to(action_params, url_)

    def get_user_name():
        user_name = action_params
        return user_name

    def get_users_group():
        group_name = action_params
        return group_name

    def get_pull_request():
        from kallithea.model.db import PullRequest
        pull_request_id = action_params
        nice_id = PullRequest.make_nice_id(pull_request_id)

        deleted = user_log.repository is None
        if deleted:
            repo_name = user_log.repository_name
        else:
            repo_name = user_log.repository.repo_name

        return link_to(_('Pull request %s') % nice_id,
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
        action = action_str[0] \
            .replace('[', '<b>') \
            .replace(']', '</b>')

    action_params_func = lambda: ""

    if callable(action_str[1]):
        action_params_func = action_str[1]

    def action_parser_icon():
        action = user_log.action
        action_params = None
        x = action.split(':')

        if len(x) > 1:
            action, action_params = x

        ico = action_map.get(action, ['', '', ''])[2]
        html = """<i class="%s"></i>""" % ico
        return literal(html)

    # returned callbacks we need to call to get
    return [lambda: literal(action), action_params_func, action_parser_icon]


#==============================================================================
# GRAVATAR URL
#==============================================================================
def gravatar_div(email_address, cls='', size=30, **div_attributes):
    """Return an html literal with a span around a gravatar if they are enabled.
    Extra keyword parameters starting with 'div_' will get the prefix removed
    and '_' changed to '-' and be used as attributes on the div. The default
    class is 'gravatar'.
    """
    from tg import tmpl_context as c
    if not c.visual.use_gravatar:
        return ''
    if 'div_class' not in div_attributes:
        div_attributes['div_class'] = "gravatar"
    attributes = []
    for k, v in sorted(div_attributes.items()):
        assert k.startswith('div_'), k
        attributes.append(' %s="%s"' % (k[4:].replace('_', '-'), escape(v)))
    return literal("""<span%s>%s</span>""" %
                   (''.join(attributes),
                    gravatar(email_address, cls=cls, size=size)))


def gravatar(email_address, cls='', size=30):
    """return html element of the gravatar

    This method will return an <img> with the resolution double the size (for
    retina screens) of the image. If the url returned from gravatar_url is
    empty then we fallback to using an icon.

    """
    from tg import tmpl_context as c
    if not c.visual.use_gravatar:
        return ''

    src = gravatar_url(email_address, size * 2)

    if src:
        # here it makes sense to use style="width: ..." (instead of, say, a
        # stylesheet) because we using this to generate a high-res (retina) size
        html = ('<i class="icon-gravatar {cls}"'
                ' style="font-size: {size}px;background-size: {size}px;background-image: url(\'{src}\')"'
                '></i>').format(cls=cls, size=size, src=src)

    else:
        # if src is empty then there was no gravatar, so we use a font icon
        html = ("""<i class="icon-user {cls}" style="font-size: {size}px;"></i>"""
            .format(cls=cls, size=size, src=src))

    return literal(html)


def gravatar_url(email_address, size=30, default=''):
    # doh, we need to re-import those to mock it later
    from kallithea.config.routing import url
    from kallithea.model.db import User
    from tg import tmpl_context as c
    if not c.visual.use_gravatar:
        return ""

    _def = 'anonymous@kallithea-scm.org'  # default gravatar
    email_address = email_address or _def

    if email_address == _def:
        return default

    parsed_url = urlparse.urlparse(url.current(qualified=True))
    url = (c.visual.gravatar_url or User.DEFAULT_GRAVATAR_URL) \
               .replace('{email}', email_address) \
               .replace('{md5email}', hashlib.md5(safe_str(email_address).lower()).hexdigest()) \
               .replace('{netloc}', parsed_url.netloc) \
               .replace('{scheme}', parsed_url.scheme) \
               .replace('{size}', safe_str(size))
    return url


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
        return ': ' + _('No files')


def fancy_file_stats(stats):
    """
    Displays a fancy two colored bar for number of added/deleted
    lines of code on file

    :param stats: two element list of added/deleted lines of code
    """
    from kallithea.lib.diffs import NEW_FILENODE, DEL_FILENODE, \
        MOD_FILENODE, RENAMED_FILENODE, CHMOD_FILENODE, BIN_FILENODE

    a, d = stats['added'], stats['deleted']
    width = 100

    if stats['binary']:
        # binary mode
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

        # chmod can go with other operations
        if CHMOD_FILENODE in stats['ops']:
            _org_lbl = _('chmod')
            lbl += _org_lbl if lbl.endswith('+') else '+%s' % _org_lbl

        #import ipdb;ipdb.set_trace()
        b_d = '<div class="bin bin%s progress-bar" style="width:100%%">%s</div>' % (bin_op, lbl)
        b_a = '<div class="bin bin1" style="width:0%"></div>'
        return literal('<div style="width:%spx" class="progress">%s%s</div>' % (width, b_a, b_d))

    t = stats['added'] + stats['deleted']
    unit = float(width) / (t or 1)

    # needs > 9% of width to be visible or 0 to be hidden
    a_p = max(9, unit * a) if a > 0 else 0
    d_p = max(9, unit * d) if d > 0 else 0
    p_sum = a_p + d_p

    if p_sum > width:
        # adjust the percentage to be == 100% since we adjusted to 9
        if a_p > d_p:
            a_p = a_p - (p_sum - width)
        else:
            d_p = d_p - (p_sum - width)

    a_v = a if a > 0 else ''
    d_v = d if d > 0 else ''

    d_a = '<div class="added progress-bar" style="width:%s%%">%s</div>' % (
        a_p, a_v
    )
    d_d = '<div class="deleted progress-bar" style="width:%s%%">%s</div>' % (
        d_p, d_v
    )
    return literal('<div class="progress" style="width:%spx">%s%s</div>' % (width, d_a, d_d))


_URLIFY_RE = re.compile(r'''
# URL markup
(?P<url>%s) |
# @mention markup
(?P<mention>%s) |
# Changeset hash markup
(?<!\w|[-_])
  (?P<hash>[0-9a-f]{12,40})
(?!\w|[-_]) |
# Markup of *bold text*
(?:
  (?:^|(?<=\s))
  (?P<bold> [*] (?!\s) [^*\n]* (?<!\s) [*] )
  (?![*\w])
) |
# "Stylize" markup
\[see\ \=&gt;\ *(?P<seen>[a-zA-Z0-9\/\=\?\&\ \:\/\.\-]*)\] |
\[license\ \=&gt;\ *(?P<license>[a-zA-Z0-9\/\=\?\&\ \:\/\.\-]*)\] |
\[(?P<tagtype>requires|recommends|conflicts|base)\ \=&gt;\ *(?P<tagvalue>[a-zA-Z0-9\-\/]*)\] |
\[(?:lang|language)\ \=&gt;\ *(?P<lang>[a-zA-Z\-\/\#\+]*)\] |
\[(?P<tag>[a-z]+)\]
''' % (url_re.pattern, MENTIONS_REGEX.pattern),
    re.VERBOSE | re.MULTILINE | re.IGNORECASE)


def urlify_text(s, repo_name=None, link_=None, truncate=None, stylize=False, truncatef=truncate):
    """
    Parses given text message and make literal html with markup.
    The text will be truncated to the specified length.
    Hashes are turned into changeset links to specified repository.
    URLs links to what they say.
    Issues are linked to given issue-server.
    If link_ is provided, all text not already linking somewhere will link there.
    """

    def _replace(match_obj):
        url = match_obj.group('url')
        if url is not None:
            return '<a href="%(url)s">%(url)s</a>' % {'url': url}
        mention = match_obj.group('mention')
        if mention is not None:
            return '<b>%s</b>' % mention
        hash_ = match_obj.group('hash')
        if hash_ is not None and repo_name is not None:
            from kallithea.config.routing import url  # doh, we need to re-import url to mock it later
            return '<a class="changeset_hash" href="%(url)s">%(hash)s</a>' % {
                 'url': url('changeset_home', repo_name=repo_name, revision=hash_),
                 'hash': hash_,
                }
        bold = match_obj.group('bold')
        if bold is not None:
            return '<b>*%s*</b>' % _urlify(bold[1:-1])
        if stylize:
            seen = match_obj.group('seen')
            if seen:
                return '<div class="label label-meta" data-tag="see">see =&gt; %s</div>' % seen
            license = match_obj.group('license')
            if license:
                return '<div class="label label-meta" data-tag="license"><a href="http://www.opensource.org/licenses/%s">%s</a></div>' % (license, license)
            tagtype = match_obj.group('tagtype')
            if tagtype:
                tagvalue = match_obj.group('tagvalue')
                return '<div class="label label-meta" data-tag="%s">%s =&gt; <a href="/%s">%s</a></div>' % (tagtype, tagtype, tagvalue, tagvalue)
            lang = match_obj.group('lang')
            if lang:
                return '<div class="label label-meta" data-tag="lang">%s</div>' % lang
            tag = match_obj.group('tag')
            if tag:
                return '<div class="label label-meta" data-tag="%s">%s</div>' % (tag, tag)
        return match_obj.group(0)

    def _urlify(s):
        """
        Extract urls from text and make html links out of them
        """
        return _URLIFY_RE.sub(_replace, s)

    if truncate is None:
        s = s.rstrip()
    else:
        s = truncatef(s, truncate, whole_word=True)
    s = html_escape(s)
    s = _urlify(s)
    if repo_name is not None:
        s = urlify_issues(s, repo_name)
    if link_ is not None:
        # make href around everything that isn't a href already
        s = linkify_others(s, link_)
    s = s.replace('\r\n', '<br/>').replace('\n', '<br/>')
    # Turn HTML5 into more valid HTML4 as required by some mail readers.
    # (This is not done in one step in html_escape, because character codes like
    # &#123; risk to be seen as an issue reference due to the presence of '#'.)
    s = s.replace("&apos;", "&#39;")
    return literal(s)


def linkify_others(t, l):
    """Add a default link to html with links.
    HTML doesn't allow nesting of links, so the outer link must be broken up
    in pieces and give space for other links.
    """
    urls = re.compile(r'(\<a.*?\<\/a\>)',)
    links = []
    for e in urls.split(t):
        if e.strip() and not urls.match(e):
            links.append('<a class="message-link" href="%s">%s</a>' % (l, e))
        else:
            links.append(e)

    return ''.join(links)


# Global variable that will hold the actual urlify_issues function body.
# Will be set on first use when the global configuration has been read.
_urlify_issues_f = None


def urlify_issues(newtext, repo_name):
    """Urlify issue references according to .ini configuration"""
    global _urlify_issues_f
    if _urlify_issues_f is None:
        from kallithea import CONFIG
        from kallithea.model.db import URL_SEP
        assert CONFIG['sqlalchemy.url'] # make sure config has been loaded

        # Build chain of urlify functions, starting with not doing any transformation
        tmp_urlify_issues_f = lambda s: s

        issue_pat_re = re.compile(r'issue_pat(.*)')
        for k in CONFIG.keys():
            # Find all issue_pat* settings that also have corresponding server_link and prefix configuration
            m = issue_pat_re.match(k)
            if m is None:
                continue
            suffix = m.group(1)
            issue_pat = CONFIG.get(k)
            issue_server_link = CONFIG.get('issue_server_link%s' % suffix)
            issue_sub = CONFIG.get('issue_sub%s' % suffix)
            if not issue_pat or not issue_server_link or issue_sub is None: # issue_sub can be empty but should be present
                log.error('skipping incomplete issue pattern %r: %r -> %r %r', suffix, issue_pat, issue_server_link, issue_sub)
                continue

            # Wrap tmp_urlify_issues_f with substitution of this pattern, while making sure all loop variables (and compiled regexpes) are bound
            try:
                issue_re = re.compile(issue_pat)
            except re.error as e:
                log.error('skipping invalid issue pattern %r: %r -> %r %r. Error: %s', suffix, issue_pat, issue_server_link, issue_sub, str(e))
                continue

            log.debug('issue pattern %r: %r -> %r %r', suffix, issue_pat, issue_server_link, issue_sub)

            def issues_replace(match_obj,
                               issue_server_link=issue_server_link, issue_sub=issue_sub):
                try:
                    issue_url = match_obj.expand(issue_server_link)
                except (IndexError, re.error) as e:
                    log.error('invalid issue_url setting %r -> %r %r. Error: %s', issue_pat, issue_server_link, issue_sub, str(e))
                    issue_url = issue_server_link
                issue_url = issue_url.replace('{repo}', repo_name)
                issue_url = issue_url.replace('{repo_name}', repo_name.split(URL_SEP)[-1])
                # if issue_sub is empty use the matched issue reference verbatim
                if not issue_sub:
                    issue_text = match_obj.group()
                else:
                    try:
                        issue_text = match_obj.expand(issue_sub)
                    except (IndexError, re.error) as e:
                        log.error('invalid issue_sub setting %r -> %r %r. Error: %s', issue_pat, issue_server_link, issue_sub, str(e))
                        issue_text = match_obj.group()

                return (
                    '<a class="issue-tracker-link" href="%(url)s">'
                    '%(text)s'
                    '</a>'
                    ) % {
                     'url': issue_url,
                     'text': issue_text,
                    }
            tmp_urlify_issues_f = (lambda s,
                                          issue_re=issue_re, issues_replace=issues_replace, chain_f=tmp_urlify_issues_f:
                                   issue_re.sub(issues_replace, chain_f(s)))

        # Set tmp function globally - atomically
        _urlify_issues_f = tmp_urlify_issues_f

    return _urlify_issues_f(newtext)


def render_w_mentions(source, repo_name=None):
    """
    Render plain text with revision hashes and issue references urlified
    and with @mention highlighting.
    """
    s = safe_unicode(source)
    s = urlify_text(s, repo_name=repo_name)
    return literal('<div class="formatted-fixed">%s</div>' % s)


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
    from kallithea.model.changeset_status import ChangesetStatusModel
    return ChangesetStatusModel().get_status(repo, revision)


def changeset_status_lbl(changeset_status):
    from kallithea.model.db import ChangesetStatus
    return ChangesetStatus.get_status_lbl(changeset_status)


def get_permission_name(key):
    from kallithea.model.db import Permission
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


session_csrf_secret_name = "_session_csrf_secret_token"

def session_csrf_secret_token():
    """Return (and create) the current session's CSRF protection token."""
    from tg import session
    if not session_csrf_secret_name in session:
        session[session_csrf_secret_name] = str(random.getrandbits(128))
        session.save()
    return session[session_csrf_secret_name]

def form(url, method="post", **attrs):
    """Like webhelpers.html.tags.form , but automatically adding
    session_csrf_secret_token for POST. The secret is thus never leaked in GET
    URLs.
    """
    form = insecure_form(url, method, **attrs)
    if method.lower() == 'get':
        return form
    return form + HTML.div(hidden(session_csrf_secret_name, session_csrf_secret_token()), style="display: none;")
