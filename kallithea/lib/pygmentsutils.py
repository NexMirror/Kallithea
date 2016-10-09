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
from string import lower

from pygments import lexers


def get_lem():
    """
    Get language extension map based on what's inside pygments lexers
    """
    d = defaultdict(lambda: [])

    def __clean(s):
        s = s.lstrip('*')
        s = s.lstrip('.')

        if s.find('[') != -1:
            exts = []
            start, stop = s.find('['), s.find(']')

            for suffix in s[start + 1:stop]:
                exts.append(s[:s.find('[')] + suffix)
            return map(lower, exts)
        else:
            return map(lower, [s])

    for lx, t in sorted(lexers.LEXERS.items()):
        m = map(__clean, t[-2])
        if m:
            m = reduce(lambda x, y: x + y, m)
            for ext in m:
                desc = lx.replace('Lexer', '')
                d[ext].append(desc)

    return dict(d)


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
    #check if we didn't define this extension as other lexer
    if kallithea.EXTENSIONS and extension in kallithea.EXTENSIONS.EXTRA_LEXERS:
        _lexer_name = kallithea.EXTENSIONS.EXTRA_LEXERS[extension]
        return lexers.get_lexer_by_name(_lexer_name)
