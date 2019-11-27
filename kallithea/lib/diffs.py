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
kallithea.lib.diffs
~~~~~~~~~~~~~~~~~~~

Set of diffing helpers, previously part of vcs


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 4, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
import difflib
import logging
import re

from tg.i18n import ugettext as _

from kallithea.lib import helpers as h
from kallithea.lib.utils2 import safe_unicode
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.exceptions import VCSError
from kallithea.lib.vcs.nodes import FileNode, SubModuleNode


log = logging.getLogger(__name__)


def _safe_id(idstring):
    r"""Make a string safe for including in an id attribute.

    The HTML spec says that id attributes 'must begin with
    a letter ([A-Za-z]) and may be followed by any number
    of letters, digits ([0-9]), hyphens ("-"), underscores
    ("_"), colons (":"), and periods (".")'. These regexps
    are slightly over-zealous, in that they remove colons
    and periods unnecessarily.

    Whitespace is transformed into underscores, and then
    anything which is not a hyphen or a character that
    matches \w (alphanumerics and underscore) is removed.

    """
    # Transform all whitespace to underscore
    idstring = re.sub(r'\s', "_", idstring)
    # Remove everything that is not a hyphen or a member of \w
    idstring = re.sub(r'(?!-)\W', "", idstring).lower()
    return idstring


def as_html(table_class='code-difftable', line_class='line',
            old_lineno_class='lineno old', new_lineno_class='lineno new',
            no_lineno_class='lineno',
            code_class='code', enable_comments=False, parsed_lines=None):
    """
    Return given diff as html table with customized css classes
    """
    def _link_to_if(condition, label, url):
        """
        Generates a link if condition is meet or just the label if not.
        """

        if condition:
            return '''<a href="%(url)s" data-pseudo-content="%(label)s"></a>''' % {
                'url': url,
                'label': label
            }
        else:
            return label

    _html_empty = True
    _html = []
    _html.append('''<table class="%(table_class)s">\n''' % {
        'table_class': table_class
    })

    for diff in parsed_lines:
        for line in diff['chunks']:
            _html_empty = False
            for change in line:
                _html.append('''<tr class="%(lc)s %(action)s">\n''' % {
                    'lc': line_class,
                    'action': change['action']
                })
                anchor_old_id = ''
                anchor_new_id = ''
                anchor_old = "%(filename)s_o%(oldline_no)s" % {
                    'filename': _safe_id(diff['filename']),
                    'oldline_no': change['old_lineno']
                }
                anchor_new = "%(filename)s_n%(oldline_no)s" % {
                    'filename': _safe_id(diff['filename']),
                    'oldline_no': change['new_lineno']
                }
                cond_old = (change['old_lineno'] != '...' and
                            change['old_lineno'])
                cond_new = (change['new_lineno'] != '...' and
                            change['new_lineno'])
                no_lineno = (change['old_lineno'] == '...' and
                             change['new_lineno'] == '...')
                if cond_old:
                    anchor_old_id = 'id="%s"' % anchor_old
                if cond_new:
                    anchor_new_id = 'id="%s"' % anchor_new
                ###########################################################
                # OLD LINE NUMBER
                ###########################################################
                _html.append('''\t<td %(a_id)s class="%(olc)s" %(colspan)s>''' % {
                    'a_id': anchor_old_id,
                    'olc': no_lineno_class if no_lineno else old_lineno_class,
                    'colspan': 'colspan="2"' if no_lineno else ''
                })

                _html.append('''%(link)s''' % {
                    'link': _link_to_if(not no_lineno, change['old_lineno'],
                                        '#%s' % anchor_old)
                })
                _html.append('''</td>\n''')
                ###########################################################
                # NEW LINE NUMBER
                ###########################################################

                if not no_lineno:
                    _html.append('''\t<td %(a_id)s class="%(nlc)s">''' % {
                        'a_id': anchor_new_id,
                        'nlc': new_lineno_class
                    })

                    _html.append('''%(link)s''' % {
                        'link': _link_to_if(True, change['new_lineno'],
                                            '#%s' % anchor_new)
                    })
                    _html.append('''</td>\n''')
                ###########################################################
                # CODE
                ###########################################################
                comments = '' if enable_comments else 'no-comment'
                _html.append('''\t<td class="%(cc)s %(inc)s">''' % {
                    'cc': code_class,
                    'inc': comments
                })
                _html.append('''\n\t\t<div class="add-bubble"><div>&nbsp;</div></div><pre>%(code)s</pre>\n''' % {
                    'code': change['line']
                })

                _html.append('''\t</td>''')
                _html.append('''\n</tr>\n''')
    _html.append('''</table>''')
    if _html_empty:
        return None
    return ''.join(_html)


def wrap_to_table(html):
    """Given a string with html, return it wrapped in a table, similar to what
    DiffProcessor returns."""
    return '''\
              <table class="code-difftable">
                <tr class="line no-comment">
                <td class="lineno new"></td>
                <td class="code no-comment"><pre>%s</pre></td>
                </tr>
              </table>''' % html


def wrapped_diff(filenode_old, filenode_new, diff_limit=None,
                ignore_whitespace=True, line_context=3,
                enable_comments=False):
    """
    Returns a file diff wrapped into a table.
    Checks for diff_limit and presents a message if the diff is too big.
    """
    if filenode_old is None:
        filenode_old = FileNode(filenode_new.path, '', EmptyChangeset())

    op = None
    a_path = filenode_old.path # default, might be overriden by actual rename in diff
    if filenode_old.is_binary or filenode_new.is_binary:
        html_diff = wrap_to_table(_('Binary file'))
        stats = (0, 0)

    elif diff_limit != -1 and (
            diff_limit is None or
            (filenode_old.size < diff_limit and filenode_new.size < diff_limit)):

        raw_diff = get_gitdiff(filenode_old, filenode_new,
                                ignore_whitespace=ignore_whitespace,
                                context=line_context)
        diff_processor = DiffProcessor(raw_diff)
        if diff_processor.parsed: # there should be exactly one element, for the specified file
            f = diff_processor.parsed[0]
            op = f['operation']
            a_path = f['old_filename']

        html_diff = as_html(parsed_lines=diff_processor.parsed, enable_comments=enable_comments)
        stats = diff_processor.stat()

    else:
        html_diff = wrap_to_table(_('Changeset was too big and was cut off, use '
                               'diff menu to display this diff'))
        stats = (0, 0)

    if not html_diff:
        submodules = filter(lambda o: isinstance(o, SubModuleNode),
                            [filenode_new, filenode_old])
        if submodules:
            html_diff = wrap_to_table(h.escape('Submodule %r' % submodules[0]))
        else:
            html_diff = wrap_to_table(_('No changes detected'))

    cs1 = filenode_old.changeset.raw_id
    cs2 = filenode_new.changeset.raw_id

    return cs1, cs2, a_path, html_diff, stats, op


def get_gitdiff(filenode_old, filenode_new, ignore_whitespace=True, context=3):
    """
    Returns git style diff between given ``filenode_old`` and ``filenode_new``.
    """
    # make sure we pass in default context
    context = context or 3
    submodules = filter(lambda o: isinstance(o, SubModuleNode),
                        [filenode_new, filenode_old])
    if submodules:
        return ''

    for filenode in (filenode_old, filenode_new):
        if not isinstance(filenode, FileNode):
            raise VCSError("Given object should be FileNode object, not %s"
                % filenode.__class__)

    repo = filenode_new.changeset.repository
    old_raw_id = getattr(filenode_old.changeset, 'raw_id', repo.EMPTY_CHANGESET)
    new_raw_id = getattr(filenode_new.changeset, 'raw_id', repo.EMPTY_CHANGESET)

    vcs_gitdiff = get_diff(repo, old_raw_id, new_raw_id, filenode_new.path,
                           ignore_whitespace, context)
    return vcs_gitdiff


def get_diff(scm_instance, rev1, rev2, path=None, ignore_whitespace=False, context=3):
    """
    A thin wrapper around vcs lib get_diff.
    """
    try:
        return scm_instance.get_diff(rev1, rev2, path=path,
                                     ignore_whitespace=ignore_whitespace, context=context)
    except MemoryError:
        h.flash('MemoryError: Diff is too big', category='error')
        return ''


NEW_FILENODE = 1
DEL_FILENODE = 2
MOD_FILENODE = 3
RENAMED_FILENODE = 4
COPIED_FILENODE = 5
CHMOD_FILENODE = 6
BIN_FILENODE = 7


class DiffProcessor(object):
    """
    Give it a unified or git diff and it returns a list of the files that were
    mentioned in the diff together with a dict of meta information that
    can be used to render it in a HTML template.
    """
    _diff_git_re = re.compile('^diff --git', re.MULTILINE)

    def __init__(self, diff, vcs='hg', diff_limit=None, inline_diff=True):
        """
        :param diff:   a text in diff format
        :param vcs: type of version control hg or git
        :param diff_limit: define the size of diff that is considered "big"
            based on that parameter cut off will be triggered, set to None
            to show full diff
        """
        if not isinstance(diff, basestring):
            raise Exception('Diff must be a basestring got %s instead' % type(diff))

        self._diff = diff
        self.adds = 0
        self.removes = 0
        self.diff_limit = diff_limit
        self.limited_diff = False
        self.vcs = vcs
        self.parsed = self._parse_gitdiff(inline_diff=inline_diff)

    def _parse_gitdiff(self, inline_diff):
        """Parse self._diff and return a list of dicts with meta info and chunks for each file.
        Might set limited_diff.
        Optionally, do an extra pass and to extra markup of one-liner changes.
        """
        _files = [] # list of dicts with meta info and chunks

        starts = [m.start() for m in self._diff_git_re.finditer(self._diff)]
        starts.append(len(self._diff))

        for start, end in zip(starts, starts[1:]):
            if self.diff_limit and end > self.diff_limit:
                self.limited_diff = True
                continue

            head, diff_lines = _get_header(self.vcs, buffer(self._diff, start, end - start))

            op = None
            stats = {
                'added': 0,
                'deleted': 0,
                'binary': False,
                'ops': {},
            }

            if head['deleted_file_mode']:
                op = 'removed'
                stats['binary'] = True
                stats['ops'][DEL_FILENODE] = 'deleted file'

            elif head['new_file_mode']:
                op = 'added'
                stats['binary'] = True
                stats['ops'][NEW_FILENODE] = 'new file %s' % head['new_file_mode']
            else:  # modify operation, can be cp, rename, chmod
                # CHMOD
                if head['new_mode'] and head['old_mode']:
                    op = 'modified'
                    stats['binary'] = True
                    stats['ops'][CHMOD_FILENODE] = ('modified file chmod %s => %s'
                                        % (head['old_mode'], head['new_mode']))
                # RENAME
                if (head['rename_from'] and head['rename_to']
                      and head['rename_from'] != head['rename_to']):
                    op = 'renamed'
                    stats['binary'] = True
                    stats['ops'][RENAMED_FILENODE] = ('file renamed from %s to %s'
                                    % (head['rename_from'], head['rename_to']))
                # COPY
                if head.get('copy_from') and head.get('copy_to'):
                    op = 'modified'
                    stats['binary'] = True
                    stats['ops'][COPIED_FILENODE] = ('file copied from %s to %s'
                                        % (head['copy_from'], head['copy_to']))
                # FALL BACK: detect missed old style add or remove
                if op is None:
                    if not head['a_file'] and head['b_file']:
                        op = 'added'
                        stats['binary'] = True
                        stats['ops'][NEW_FILENODE] = 'new file'

                    elif head['a_file'] and not head['b_file']:
                        op = 'removed'
                        stats['binary'] = True
                        stats['ops'][DEL_FILENODE] = 'deleted file'

                # it's not ADD not DELETE
                if op is None:
                    op = 'modified'
                    stats['binary'] = True
                    stats['ops'][MOD_FILENODE] = 'modified file'

            # a real non-binary diff
            if head['a_file'] or head['b_file']:
                chunks, added, deleted = _parse_lines(diff_lines)
                stats['binary'] = False
                stats['added'] = added
                stats['deleted'] = deleted
                # explicit mark that it's a modified file
                if op == 'modified':
                    stats['ops'][MOD_FILENODE] = 'modified file'
            else:  # Git binary patch (or empty diff)
                # Git binary patch
                if head['bin_patch']:
                    stats['ops'][BIN_FILENODE] = 'binary diff not shown'
                chunks = []

            if op == 'removed' and chunks:
                # a way of seeing deleted content could perhaps be nice - but
                # not with the current UI
                chunks = []

            chunks.insert(0, [{
                'old_lineno': '',
                'new_lineno': '',
                'action':     'context',
                'line':       msg,
                } for _op, msg in stats['ops'].iteritems()
                  if _op not in [MOD_FILENODE]])

            _files.append({
                'old_filename':     head['a_path'],
                'filename':         head['b_path'],
                'old_revision':     head['a_blob_id'],
                'new_revision':     head['b_blob_id'],
                'chunks':           chunks,
                'operation':        op,
                'stats':            stats,
            })

        if not inline_diff:
            return _files

        # highlight inline changes when one del is followed by one add
        for diff_data in _files:
            for chunk in diff_data['chunks']:
                lineiter = iter(chunk)
                try:
                    peekline = lineiter.next()
                    while True:
                        # find a first del line
                        while peekline['action'] != 'del':
                            peekline = lineiter.next()
                        delline = peekline
                        peekline = lineiter.next()
                        # if not followed by add, eat all following del lines
                        if peekline['action'] != 'add':
                            while peekline['action'] == 'del':
                                peekline = lineiter.next()
                            continue
                        # found an add - make sure it is the only one
                        addline = peekline
                        try:
                            peekline = lineiter.next()
                        except StopIteration:
                            # add was last line - ok
                            _highlight_inline_diff(delline, addline)
                            raise
                        if peekline['action'] != 'add':
                            # there was only one add line - ok
                            _highlight_inline_diff(delline, addline)
                except StopIteration:
                    pass

        return _files

    def stat(self):
        """
        Returns tuple of added, and removed lines for this instance
        """
        return self.adds, self.removes


_escape_re = re.compile(r'(&)|(<)|(>)|(\t)|(\r)|(?<=.)( \n| $)')


def _escaper(string):
    """
    Do HTML escaping/markup
    """

    def substitute(m):
        groups = m.groups()
        if groups[0]:
            return '&amp;'
        if groups[1]:
            return '&lt;'
        if groups[2]:
            return '&gt;'
        if groups[3]:
            return '<u>\t</u>'
        if groups[4]:
            return '<u class="cr"></u>'
        if groups[5]:
            return ' <i></i>'
        assert False

    return _escape_re.sub(substitute, safe_unicode(string))


_git_header_re = re.compile(r"""
    ^diff[ ]--git[ ]a/(?P<a_path>.+?)[ ]b/(?P<b_path>.+?)\n
    (?:^old[ ]mode[ ](?P<old_mode>\d+)\n
       ^new[ ]mode[ ](?P<new_mode>\d+)(?:\n|$))?
    (?:^similarity[ ]index[ ](?P<similarity_index>\d+)%\n
       ^rename[ ]from[ ](?P<rename_from>.+)\n
       ^rename[ ]to[ ](?P<rename_to>.+)(?:\n|$))?
    (?:^new[ ]file[ ]mode[ ](?P<new_file_mode>.+)(?:\n|$))?
    (?:^deleted[ ]file[ ]mode[ ](?P<deleted_file_mode>.+)(?:\n|$))?
    (?:^index[ ](?P<a_blob_id>[0-9A-Fa-f]+)
        \.\.(?P<b_blob_id>[0-9A-Fa-f]+)[ ]?(?P<b_mode>.+)?(?:\n|$))?
    (?:^(?P<bin_patch>GIT[ ]binary[ ]patch)(?:\n|$))?
    (?:^---[ ](a/(?P<a_file>.+?)|/dev/null)\t?(?:\n|$))?
    (?:^\+\+\+[ ](b/(?P<b_file>.+?)|/dev/null)\t?(?:\n|$))?
""", re.VERBOSE | re.MULTILINE)


_hg_header_re = re.compile(r"""
    ^diff[ ]--git[ ]a/(?P<a_path>.+?)[ ]b/(?P<b_path>.+?)\n
    (?:^old[ ]mode[ ](?P<old_mode>\d+)\n
       ^new[ ]mode[ ](?P<new_mode>\d+)(?:\n|$))?
    (?:^similarity[ ]index[ ](?P<similarity_index>\d+)%(?:\n|$))?
    (?:^rename[ ]from[ ](?P<rename_from>.+)\n
       ^rename[ ]to[ ](?P<rename_to>.+)(?:\n|$))?
    (?:^copy[ ]from[ ](?P<copy_from>.+)\n
       ^copy[ ]to[ ](?P<copy_to>.+)(?:\n|$))?
    (?:^new[ ]file[ ]mode[ ](?P<new_file_mode>.+)(?:\n|$))?
    (?:^deleted[ ]file[ ]mode[ ](?P<deleted_file_mode>.+)(?:\n|$))?
    (?:^index[ ](?P<a_blob_id>[0-9A-Fa-f]+)
        \.\.(?P<b_blob_id>[0-9A-Fa-f]+)[ ]?(?P<b_mode>.+)?(?:\n|$))?
    (?:^(?P<bin_patch>GIT[ ]binary[ ]patch)(?:\n|$))?
    (?:^---[ ](a/(?P<a_file>.+?)|/dev/null)\t?(?:\n|$))?
    (?:^\+\+\+[ ](b/(?P<b_file>.+?)|/dev/null)\t?(?:\n|$))?
""", re.VERBOSE | re.MULTILINE)


def _get_header(vcs, diff_chunk):
    """
    Parses a Git diff for a single file (header and chunks) and returns a tuple with:

    1. A dict with meta info:

        a_path, b_path, similarity_index, rename_from, rename_to,
        old_mode, new_mode, new_file_mode, deleted_file_mode,
        a_blob_id, b_blob_id, b_mode, a_file, b_file

    2. An iterator yielding lines with simple HTML markup.
    """
    match = None
    if vcs == 'git':
        match = _git_header_re.match(diff_chunk)
    elif vcs == 'hg':
        match = _hg_header_re.match(diff_chunk)
    if match is None:
        raise Exception('diff not recognized as valid %s diff' % vcs)
    meta_info = match.groupdict()
    rest = diff_chunk[match.end():]
    if rest and not rest.startswith('@') and not rest.startswith('literal ') and not rest.startswith('delta '):
        raise Exception('cannot parse %s diff header: %r followed by %r' % (vcs, diff_chunk[:match.end()], rest[:1000]))
    diff_lines = (_escaper(m.group(0)) for m in re.finditer(r'.*\n|.+$', rest)) # don't split on \r as str.splitlines do
    return meta_info, diff_lines


_chunk_re = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)')
_newline_marker = re.compile(r'^\\ No newline at end of file')


def _parse_lines(diff_lines):
    """
    Given an iterator of diff body lines, parse them and return a dict per
    line and added/removed totals.
    """
    added = deleted = 0
    old_line = old_end = new_line = new_end = None

    try:
        chunks = []
        line = diff_lines.next()

        while True:
            lines = []
            chunks.append(lines)

            match = _chunk_re.match(line)

            if not match:
                raise Exception('error parsing diff @@ line %r' % line)

            gr = match.groups()
            (old_line, old_end,
             new_line, new_end) = [int(x or 1) for x in gr[:-1]]
            old_line -= 1
            new_line -= 1

            context = len(gr) == 5
            old_end += old_line
            new_end += new_line

            if context:
                # skip context only if it's first line
                if int(gr[0]) > 1:
                    lines.append({
                        'old_lineno': '...',
                        'new_lineno': '...',
                        'action':     'context',
                        'line':       line,
                    })

            line = diff_lines.next()

            while old_line < old_end or new_line < new_end:
                if not line:
                    raise Exception('error parsing diff - empty line at -%s+%s' % (old_line, new_line))

                affects_old = affects_new = False

                command = line[0]
                if command == '+':
                    affects_new = True
                    action = 'add'
                    added += 1
                elif command == '-':
                    affects_old = True
                    action = 'del'
                    deleted += 1
                elif command == ' ':
                    affects_old = affects_new = True
                    action = 'unmod'
                else:
                    raise Exception('error parsing diff - unknown command in line %r at -%s+%s' % (line, old_line, new_line))

                if not _newline_marker.match(line):
                    old_line += affects_old
                    new_line += affects_new
                    lines.append({
                        'old_lineno':   affects_old and old_line or '',
                        'new_lineno':   affects_new and new_line or '',
                        'action':       action,
                        'line':         line[1:],
                    })

                line = diff_lines.next()

                if _newline_marker.match(line):
                    # we need to append to lines, since this is not
                    # counted in the line specs of diff
                    lines.append({
                        'old_lineno':   '...',
                        'new_lineno':   '...',
                        'action':       'context',
                        'line':         line,
                    })
                    line = diff_lines.next()
            if old_line > old_end:
                raise Exception('error parsing diff - more than %s "-" lines at -%s+%s' % (old_end, old_line, new_line))
            if new_line > new_end:
                raise Exception('error parsing diff - more than %s "+" lines at -%s+%s' % (new_end, old_line, new_line))
    except StopIteration:
        pass
    if old_line != old_end or new_line != new_end:
        raise Exception('diff processing broken when old %s<>%s or new %s<>%s line %r' % (old_line, old_end, new_line, new_end, line))

    return chunks, added, deleted

# Used for inline highlighter word split, must match the substitutions in _escaper
_token_re = re.compile(r'()(&amp;|&lt;|&gt;|<u>\t</u>|<u class="cr"></u>| <i></i>|\W+?)')


def _highlight_inline_diff(old, new):
    """
    Highlight simple add/remove in two lines given as info dicts. They are
    modified in place and given markup with <del>/<ins>.
    """
    assert old['action'] == 'del'
    assert new['action'] == 'add'

    oldwords = _token_re.split(old['line'])
    newwords = _token_re.split(new['line'])
    sequence = difflib.SequenceMatcher(None, oldwords, newwords)

    oldfragments, newfragments = [], []
    for tag, i1, i2, j1, j2 in sequence.get_opcodes():
        oldfrag = ''.join(oldwords[i1:i2])
        newfrag = ''.join(newwords[j1:j2])
        if tag != 'equal':
            if oldfrag:
                oldfrag = '<del>%s</del>' % oldfrag
            if newfrag:
                newfrag = '<ins>%s</ins>' % newfrag
        oldfragments.append(oldfrag)
        newfragments.append(newfrag)

    old['line'] = "".join(oldfragments)
    new['line'] = "".join(newfragments)
