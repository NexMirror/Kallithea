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
kallithea.lib.pygmentsutils
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Functions for extracting internal Pygments data.

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jan 5, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from collections import defaultdict
from itertools import ifilter

from pygments import lexers


def get_extension_descriptions():
    """
    Based on what's inside pygments lexers, return a mapping from lowercase
    extensions to lists of very brief descriptions.
    """
    ext_descs = defaultdict(list)

    for lx, t in sorted(lexers.LEXERS.items()):
        desc = lx.replace('Lexer', '')
        for glob in t[-2]:
            s = glob.lstrip('*').lstrip('.').lower()
            start = s.find('[')
            if start > -1 and s.endswith(']'):
                # expand trailing [] range
                prefix = s[:start]
                for char in s[start + 1:-1]:
                    ext_descs[prefix + char].append(desc)
            else:
                # use stripped glob as extension
                ext_descs[s].append(desc)

    return dict(ext_descs)


def get_index_filenames():
    """
    Get list of known indexable filenames from pygment lexer internals
    """

    filenames = []

    def likely_filename(s):
        return s.find('*') == -1 and s.find('[') == -1

    for lx, t in sorted(lexers.LEXERS.items()):
        for f in ifilter(likely_filename, t[-2]):
            filenames.append(f)

    return filenames


def get_custom_lexer(extension):
    """
    returns a custom lexer if it's defined in rcextensions module, or None
    if there's no custom lexer defined
    """
    import kallithea
    lexer_name = getattr(kallithea.EXTENSIONS, 'EXTRA_LEXERS', {}).get(extension)
    if lexer_name is None:
        return None
    return lexers.get_lexer_by_name(lexer_name)
