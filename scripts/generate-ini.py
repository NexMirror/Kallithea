#!/usr/bin/env python2
"""
Based on kallithea/lib/paster_commands/template.ini.mako, generate
  development.ini
  kallithea/tests/test.ini
"""

import re

makofile = 'kallithea/lib/paster_commands/template.ini.mako'

# the mako conditionals used in all other ini files and templates
selected_mako_conditionals = set([
    "database_engine == 'sqlite'",
    "http_server == 'waitress'",
    "error_aggregation_service == 'appenlight'",
    "error_aggregation_service == 'sentry'",
])

# the mako variables used in all other ini files and templates
mako_variable_values = {
    'host': '127.0.0.1',
    'port': '5000',
    'uuid()': '${app_instance_uuid}',
}

# files to be generated from the mako template
ini_files = [
    ('kallithea/tests/test.ini',
        '''
        Kallithea - config for tests:
        sqlalchemy and kallithea_test.sqlite
        custom logging
        ''',
        {
            '[server:main]': {
                'port': '4999',
            },
            '[app:main]': {
                'app_instance_uuid': 'test',
                'show_revision_number': 'true',
                'beaker.cache.sql_cache_short.expire': '1',
                'beaker.session.secret': '{74e0cd75-b339-478b-b129-07dd221def1f}',
            },
            '[handler_console]': {
                'level': 'DEBUG',
                'formatter': 'color_formatter',
            },
            # The 'handler_console_sql' block is very similar to the one in
            # development.ini, but without the explicit 'level=DEBUG' setting:
            # it causes duplicate sqlalchemy debug logs, one through
            # handler_console_sql and another through another path.
            '[handler_console_sql]': {
                'formatter': 'color_formatter_sql',
            },
        },
    ),
    ('development.ini',
        '''
        Kallithea - Development config:
        listening on *:5000
        sqlite and kallithea.db
        initial_repo_scan = true
        debug = true
        verbose and colorful logging
        ''',
        {
            '[server:main]': {
                'host': '0.0.0.0',
            },
            '[app:main]': {
                'initial_repo_scan': 'true',
                'debug': 'true',
                'app_instance_uuid': 'development-not-secret',
                'beaker.session.secret': 'development-not-secret',
            },
            '[handler_console]': {
                'level': 'DEBUG',
                'formatter': 'color_formatter',
            },
            '[handler_console_sql]': {
                'level': 'DEBUG',
                'formatter': 'color_formatter_sql',
            },
        },
    ),
]


def main():
    # make sure all mako lines starting with '#' (the '##' comments) are marked up as <text>
    print 'reading:', makofile
    mako_org = open(makofile).read()
    mako_no_text_markup = re.sub(r'</?%text>', '', mako_org)
    mako_marked_up = re.sub(r'\n(##.*)', r'\n<%text>\1</%text>', mako_no_text_markup, flags=re.MULTILINE)
    if mako_marked_up != mako_org:
        print 'writing:', makofile
        open(makofile, 'w').write(mako_marked_up)

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
        sub_conditionals, mako_no_text_markup, flags=re.MULTILINE)

    # expand mako variables
    def pyrepl(m):
        return mako_variable_values.get(m.group(1), m.group(0))
    mako_no_variables = re.sub(r'\${([^}]*)}', pyrepl, mako_no_conditionals)

    # remove utf-8 coding header
    base_ini = re.sub(r'^## -\*- coding: utf-8 -\*-\n', '', mako_no_variables)

    # create ini files
    for fn, desc, settings in ini_files:
        print 'updating:', fn
        ini_lines = re.sub(
            '# Kallithea - config file generated with kallithea-config *#\n',
            ''.join('# %-77s#\n' % l.strip() for l in desc.strip().split('\n')),
            base_ini)
        def process_section(m):
            """process a ini section, replacing values as necessary"""
            sectionname, lines = m.groups()
            if sectionname in settings:
                section_settings = settings[sectionname]
                def process_line(m):
                    """process a section line and update value if necessary"""
                    setting, value = m.groups()
                    line = m.group(0)
                    if setting in section_settings:
                        line = '%s = %s' % (setting, section_settings[setting])
                        if '$' not in value:
                            line = '#%s = %s\n%s' % (setting, value, line)
                    return line.rstrip()
                lines = re.sub(r'^([^#\n].*) = ?(.*)', process_line, lines, flags=re.MULTILINE)
            return sectionname + '\n' + lines
        ini_lines = re.sub(r'^(\[.*\])\n((?:(?:[^[\n].*)?\n)*)', process_section, ini_lines, flags=re.MULTILINE)
        open(fn, 'w').write(ini_lines)

if __name__ == '__main__':
    main()
