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
import os
import re

import mako.template


log = logging.getLogger(__name__)


template_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'kallithea/lib/paster_commands/template.ini.mako')

default_variables = {
    'database_engine': 'sqlite',
    'http_server': 'waitress',
    'host': '127.0.0.1',
    'port': '5000',
    'uuid': lambda: 'VERY-SECRET',
}

variable_options = {
    'database_engine': ['sqlite', 'postgres', 'mysql'],
    'http_server': ['waitress', 'gearbox', 'gevent', 'gunicorn', 'uwsgi'],
}

def expand(template, mako_variable_values, settings):
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
    ... # option a was chosen
    ... %elif conditional_options == 'option-b':
    ... some_variable = "never mind - option-b will not be used anyway ..."
    ... %endif
    ...
    ... [comment-section]
    ... #variable3 = 3.0
    ... #variable4 = 4.0
    ... #variable5 = 5.0
    ... variable5 = 5.1
    ... #variable6 = 6.0
    ... #variable6 = 6.1
    ... #variable7 = 7.0
    ... variable7 = 7.1
    ... variable8 = 8.0
    ... '''
    >>> mako_variable_values = {'mako_variable': 'VALUE', 'mako_function': (lambda: 'FUNCTION RESULT'),
    ...                         'conditional_options': 'option-a', 'http_server': 'nc'}
    >>> settings = { # only partially used
    ...     '[first-section]': {'variable2': 'VAL2', 'first_extra': 'EXTRA', 'spacey': ' '},
    ...     '[comment-section]': {'variable3': '3.0', 'variable4': '4.1', 'variable5': '5.2', 'variable6': '6.2', 'variable7': '7.0', 'variable8': None, 'variable9': None},
    ...     '[third-section]': {'third_extra': ' 3'},
    ...     '[fourth-section]': {'fourth_extra': '4', 'fourth': '"four"'},
    ... }
    >>> print(expand(template, mako_variable_values, settings))
    ERROR: http_server is 'nc' - it should be one of 'waitress', 'gearbox', 'gevent', 'gunicorn', 'uwsgi'
    <BLANKLINE>
    [first-section]
    <BLANKLINE>
    variable=VALUE
    #variable2  =    value after tab
    variable2 = VAL2
    <BLANKLINE>
    first_extra = EXTRA
    spacey =
    <BLANKLINE>
    <BLANKLINE>
    # FUNCTION RESULT
    [second-section]
    # option a was chosen
    <BLANKLINE>
    [comment-section]
    variable3 = 3.0
    #variable4 = 4.0
    variable4 = 4.1
    #variable5 = 5.0
    #variable5 = 5.1
    variable5 = 5.2
    #variable6 = 6.0
    #variable6 = 6.1
    variable6 = 6.2
    variable7 = 7.0
    #variable7 = 7.1
    #variable8 = 8.0
    <BLANKLINE>
    variable8 = None
    variable9 = None
    <BLANKLINE>
    [fourth-section]
    fourth = "four"
    fourth_extra = 4
    <BLANKLINE>
    [third-section]
    third_extra =  3
    <BLANKLINE>
    """
    mako_variables = dict(default_variables)
    mako_variables.update(mako_variable_values or {})
    settings = dict((k, dict(v)) for k, v in settings.items()) # deep copy before mutating

    for key, value in mako_variables.items():
        if key in variable_options:
            if value not in variable_options[key]:
                print('ERROR: %s is %r - it should be one of %s' %
                      (key, value, ', '.join(repr(x) for x in variable_options[key])))

    ini_lines = mako.template.Template(template).render(**mako_variables)

    def process_section(m):
        """process a ini section, replacing values as necessary"""
        sectionname, lines = m.groups()
        if sectionname in settings:
            section_settings = settings.pop(sectionname)
            add_after_key_value = {}  # map key to value it should be added after

            # 1st pass:
            # comment out lines with keys that have new values
            # find best line for keeping or un-commenting (because it has the right value) or adding after (because it is the last with other value)
            def comment_out(m):
                """process a section line if in section_settings and comment out and track in add_after_key_value"""
                line = m.group(0)
                comment, key, line_value = m.groups()
                if key not in section_settings:
                    return line
                new_value = section_settings[key]
                if line_value == new_value or add_after_key_value.get(key) != new_value:
                    add_after_key_value[key] = line_value
                if comment:
                    return line
                return '#' + line

            lines = re.sub(r'^(#)?([^#\n\s]*)[ \t]*=[ \t]*(.*)$', comment_out, lines, flags=re.MULTILINE)

            # 2nd pass:
            # find the best comment line and un-comment or add after
            def add_after_comment(m):
                """process a section comment line and add new value"""
                line = m.group(0)
                key, line_value = m.groups()
                if key not in section_settings:
                    return line
                if line_value != add_after_key_value.get(key):
                    return line
                new_value = section_settings[key]
                if new_value == line_value:
                    line = line.lstrip('#')
                else:
                    line += '\n%s = %s' % (key, new_value)
                section_settings.pop(key)
                return line

            lines = re.sub(r'^#([^#\n\s]*)[ \t]*=[ \t]*(.*)$', add_after_comment, lines, flags=re.MULTILINE)

            # 3rd pass:
            # settings that haven't been consumed yet at is appended to section
            if section_settings:
                lines += '\n' + ''.join('%s = %s\n' % (key, value) for key, value in sorted(section_settings.items()))

        return sectionname + '\n' + re.sub('[ \t]+\n', '\n', lines)

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
        process_section, ini_lines, flags=re.MULTILINE | re.VERBOSE) \
        + \
        ''.join(
            '\n' + sectionname + '\n' + ''.join('%s = %s\n' % (key, value) for key, value in sorted(section_settings.items()))
            for sectionname, section_settings in sorted(settings.items())
            if section_settings)

    return ini_lines


def create(dest_file, mako_variable_values, settings):
    """Create an ini file at dest_file"""
    with open(template_file, 'rb') as f:
        template = f.read().decode('utf-8')

    ini_lines = expand(template, mako_variable_values, settings)

    with open(dest_file, 'wb') as f:
        f.write(ini_lines.encode('utf-8'))
