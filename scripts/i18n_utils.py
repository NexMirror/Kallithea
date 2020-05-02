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

from __future__ import print_function

import os
import re
import shutil
import subprocess
import tempfile


do_debug = False  # set from scripts/i18n --debug

def debug(*args, **kwargs):
    if do_debug:
        print(*args, **kwargs)

def runcmd(cmd, *args, **kwargs):
    debug('... Executing command: %s' % ' '.join(cmd))
    subprocess.check_call(cmd, *args, **kwargs)

header_comment_strip_re = re.compile(r'''
    ^
    [#][ ]Translations[ ]template[ ]for[ ]Kallithea[.] \n
    |
    ^
    [#][ ]FIRST[ ]AUTHOR[ ]<EMAIL@ADDRESS>,[ ]\d+[.] \n
    (?:[#] \n)?
    |
    ^
    (?:[#] \n)?
    [#],[ ]fuzzy \n
    |
    ^
    [#][ ][#],[ ]fuzzy \n
    ''',
    re.MULTILINE|re.VERBOSE)

header_normalize_re = re.compile(r'''
    ^ "
    (POT-Creation-Date|PO-Revision-Date|Last-Translator|Language-Team|X-Generator|Generated-By|Project-Id-Version):
    [ ][^\\]*\\n
    " \n
    ''',
    re.MULTILINE|re.IGNORECASE|re.VERBOSE)

def _normalize_po(raw_content):
    r"""
    >>> print(_normalize_po(r'''
    ... # header comment
    ...
    ...
    ... # comment before header
    ... msgid ""
    ... msgstr "yada"
    ... "POT-Creation-Date: 2019-05-04 21:13+0200\n"
    ... "MIME-Version: "
    ... "1.0\n"
    ... "Last-Translator: Jabba"
    ... "the Hutt\n"
    ... "X-Generator: Weblate 1.2.3\n"
    ...
    ... # comment, but not in header
    ... msgid "None"
    ... msgstr "Ingen"
    ...
    ...
    ... line 2
    ... # third comment
    ...
    ... msgid "Special"
    ... msgstr ""
    ...
    ... msgid "Specialist"
    ... # odd comment
    ... msgstr ""
    ... "Expert"
    ...
    ... # crazy fuzzy auto translation by msgmerge, using foo for bar
    ... #, fuzzy
    ... #| msgid "some foo string"
    ... msgid "some bar string."
    ... msgstr "translation of foo string"
    ...
    ... msgid "%d minute"
    ... msgid_plural "%d minutes"
    ... msgstr[0] "minut"
    ... msgstr[1] "minutter"
    ... msgstr[2] ""
    ...
    ... msgid "%d year"
    ... msgid_plural "%d years"
    ... msgstr[0] ""
    ... msgstr[1] ""
    ...
    ... # last comment
    ... ''') + '^^^')
    # header comment
    <BLANKLINE>
    <BLANKLINE>
    # comment before header
    <BLANKLINE>
    msgid ""
    msgstr "yada"
    "MIME-Version: "
    "1.0\n"
    <BLANKLINE>
    msgid "None"
    msgstr "Ingen"
    <BLANKLINE>
    line 2
    <BLANKLINE>
    msgid "Specialist"
    msgstr ""
    "Expert"
    <BLANKLINE>
    msgid "%d minute"
    msgid_plural "%d minutes"
    msgstr[0] "minut"
    msgstr[1] "minutter"
    msgstr[2] ""
    ^^^
    """
    header_start = raw_content.find('\nmsgid ""\n') + 1
    header_end = raw_content.find('\n\n', header_start) + 1 or len(raw_content)
    chunks = [
        header_comment_strip_re.sub('', raw_content[0:header_start])
            .strip(),
        '',
        header_normalize_re.sub('', raw_content[header_start:header_end])
            .replace(
                r'"Content-Type: text/plain; charset=utf-8\n"',
                r'"Content-Type: text/plain; charset=UTF-8\n"')  # maintain msgmerge casing
            .strip(),
        '']  # preserve normalized header
    # all chunks are separated by empty line
    for raw_chunk in raw_content[header_end:].split('\n\n'):
        if '\n#, fuzzy' in raw_chunk:  # might be like "#, fuzzy, python-format"
            continue  # drop crazy auto translation that is worse than useless
        # strip all comment lines from chunk
        chunk_lines = [
            line
            for line in raw_chunk.splitlines()
            if line
            and not line.startswith('#')
        ]
        if not chunk_lines:
            continue
        # check lines starting from first msgstr, skip chunk if no translation lines
        msgstr_i = [i for i, line in enumerate(chunk_lines) if line.startswith('msgstr')]
        if (
            chunk_lines[0].startswith('msgid') and
            msgstr_i and
            all(line.endswith(' ""') for line in chunk_lines[msgstr_i[0]:])
        ):  # skip translation chunks that doesn't have any actual translations
            continue
        chunks.append('\n'.join(chunk_lines) + '\n')
    return '\n'.join(chunks)

def _normalize_po_file(po_file, merge_pot_file=None, strip=False):
    if merge_pot_file:
        runcmd(['msgmerge', '--width=76', '--backup=none', '--previous',
                '--update', po_file, '-q', merge_pot_file])
    if strip:
        po_tmp = po_file + '.tmp'
        with open(po_file, 'r') as src, open(po_tmp, 'w') as dest:
            raw_content = src.read()
            normalized_content = _normalize_po(raw_content)
            dest.write(normalized_content)
        os.rename(po_tmp, po_file)

def _normalized_diff(file1, file2, merge_pot_file=None, strip=False):
    # Create temporary copies of both files
    temp1 = tempfile.NamedTemporaryFile(prefix=os.path.basename(file1))
    temp2 = tempfile.NamedTemporaryFile(prefix=os.path.basename(file2))
    debug('normalized_diff: %s -> %s / %s -> %s' % (file1, temp1.name, file2, temp2.name))
    shutil.copyfile(file1, temp1.name)
    shutil.copyfile(file2, temp2.name)
    # Normalize them in place
    _normalize_po_file(temp1.name, merge_pot_file=merge_pot_file, strip=strip)
    _normalize_po_file(temp2.name, merge_pot_file=merge_pot_file, strip=strip)
    # Now compare
    try:
        runcmd(['diff', '-u', temp1.name, temp2.name])
    except subprocess.CalledProcessError as e:
        return e.returncode
