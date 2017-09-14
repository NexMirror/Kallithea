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


log = logging.getLogger(__name__)


def expand(template, desc, selected_mako_conditionals, mako_variable_values, settings):
    """Expand mako template and tweak it.
    Not entirely stable for random templates as input, but good enough for our
    single template.
    """
    # select the right mako conditionals for the other less sophisticated formats
    def sub_conditionals(m):
        """given a %if...%endif match, replace with just the selected
        conditional sections enabled and the rest as comments
        """
        conditional_lines = m.group(1)
        def sub_conditional(m):
            """given a conditional and the corresponding lines, return them raw
            or commented out, based on whether conditional is selected
            """
            criteria, lines = m.groups()
            if criteria not in selected_mako_conditionals:
                lines = '\n'.join((l if not l or l.startswith('#') else '#' + l) for l in lines.split('\n'))
            return lines
        conditional_lines = re.sub(r'^%(?:el)?if (.*):\n((?:^[^%\n].*\n|\n)*)',
            sub_conditional, conditional_lines, flags=re.MULTILINE)
        return conditional_lines
    mako_no_conditionals = re.sub(r'^(%if .*\n(?:[^%\n].*\n|%elif .*\n|\n)*)%endif\n',
        sub_conditionals, template, flags=re.MULTILINE)

    # expand mako variables
    def pyrepl(m):
        return mako_variable_values.get(m.group(1), m.group(0))
    mako_no_variables = re.sub(r'\${([^}]*)}', pyrepl, mako_no_conditionals)

    # remove utf-8 coding header
    ini_lines = re.sub(r'^## -\*- coding: utf-8 -\*-\n', '', mako_no_variables)

    ini_lines = re.sub(
        '# Kallithea - config file generated with kallithea-config *#\n',
        ''.join('# %-77s#\n' % l.strip() for l in desc.strip().split('\n')),
        ini_lines)
    def process_section(m):
        """process a ini section, replacing values as necessary"""
        sectionname, lines = m.groups()
        if sectionname in settings:
            section_settings = settings[sectionname]
            def process_line(m):
                """process a section line and update value if necessary"""
                key, value = m.groups()
                line = m.group(0)
                if key in section_settings:
                    line = '%s = %s' % (key, section_settings[key])
                    if '$' not in value:
                        line = '#%s = %s\n%s' % (key, value, line)
                return line.rstrip()
            lines = re.sub(r'^([^#\n].*) = ?(.*)', process_line, lines, flags=re.MULTILINE)
        return sectionname + '\n' + lines
    ini_lines = re.sub(r'^(\[.*\])\n((?:(?:[^[\n].*)?\n)*)', process_section, ini_lines, flags=re.MULTILINE)

    return ini_lines
