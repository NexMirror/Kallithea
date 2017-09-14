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
kallithea.lib.inifile
~~~~~~~~~~~~~~~~~~~~~

Handling of .ini files, mainly creating them from Mako templates and adding
other custom values.
"""

import logging
import re

import mako.template


log = logging.getLogger(__name__)


def expand(template, desc, mako_variable_values, settings):
    """Expand mako template and tweak it.
    Not entirely stable for random templates as input, but good enough for our
    single template.

    >>> template = '''
    ... [first-section]
    ...
    ... variable=${mako_variable}
    ... variable2  =\tvalue after tab
    ... ## This section had some whitespace and stuff
    ...
    ...
    ... # ${mako_function()}
    ... [second-section]
    ... %if conditional_options == 'option-a':
    ... # Kallithea - config file generated with kallithea-config                      #
    ... %elif conditional_options == 'option-b':
    ... some_variable = "never mind - option-b will not be used anyway ..."
    ... %endif
    ... '''
    >>> desc = 'Description\\nof this config file'
    >>> selected_mako_conditionals = []
    >>> mako_variable_values = {'mako_variable': 'VALUE', 'mako_function': (lambda: 'FUNCTION RESULT'),
    ...                         'conditional_options': 'option-a'}
    >>> settings = { # only partially used
    ...     '[first-section]': {'variable2': 'VAL2', 'first_extra': 'EXTRA'},
    ...     '[third-section]': {'third_extra': ' 3'},
    ...     '[fourth-section]': {'fourth_extra': '4', 'fourth': '"four"'},
    ... }
    >>> print expand(template, desc, mako_variable_values, settings)
    <BLANKLINE>
    [first-section]
    <BLANKLINE>
    variable=VALUE
    #variable2  =    value after tab
    variable2 = VAL2
    <BLANKLINE>
    first_extra = EXTRA
    <BLANKLINE>
    <BLANKLINE>
    # FUNCTION RESULT
    [second-section]
    # Description                                                                  #
    # of this config file                                                          #
    <BLANKLINE>
    [fourth-section]
    fourth = "four"
    fourth_extra = 4
    <BLANKLINE>
    [third-section]
    third_extra =  3
    <BLANKLINE>
    """
    settings = dict((k, dict(v)) for k, v in settings.items()) # deep copy before mutating

    ini_lines = mako.template.Template(template).render(**mako_variable_values)

    ini_lines = re.sub(
        '# Kallithea - config file generated with kallithea-config *#\n',
        ''.join('# %-77s#\n' % l.strip() for l in desc.strip().split('\n')),
        ini_lines)

    def process_section(m):
        """process a ini section, replacing values as necessary"""
        sectionname, lines = m.groups()
        if sectionname in settings:
            section_settings = settings.pop(sectionname)

            def process_line(m):
                """process a section line and update value if necessary"""
                key, value = m.groups()
                line = m.group(0)
                if key in section_settings:
                    # keep old entry as example - comments might refer to it
                    line = '#%s\n%s = %s' % (line, key, section_settings.pop(key))
                return line.rstrip()

            # process lines that not are comments or empty and look like name=value
            lines = re.sub(r'^([^#\n\s]*)[ \t]*=[ \t]*(.*)$', process_line, lines, flags=re.MULTILINE)
            # add unused section settings
            if section_settings:
                lines += '\n' + ''.join('%s = %s\n' % (key, value) for key, value in sorted(section_settings.items()))

        return sectionname + '\n' + lines

    # process sections until comments before next section or end
    ini_lines = re.sub(r'''^
        (\[.*\])\n
        # after the section name, a number of chunks with:
        (
            (?:
                # a number of comments or empty lines
                (?:[#].*\n|\n)*
                # one or more non-empty non-comments non-section-start lines
                (?:[^\n#[].*\n)+
                # a number of comments - not empty lines
                (?:[#].*\n)*
            )*
        )
        ''',
        process_section, ini_lines, flags=re.MULTILINE|re.VERBOSE) \
        + \
        ''.join(
            '\n' + sectionname + '\n' + ''.join('%s = %s\n' % (key, value) for key, value in sorted(section_settings.items()))
            for sectionname, section_settings in sorted(settings.items())
            if section_settings)

    return ini_lines
