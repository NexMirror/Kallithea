#!/usr/bin/env python2
"""
Based on kallithea/lib/paster_commands/template.ini.mako, generate
  development.ini
  kallithea/tests/test.ini
"""

import re

from kallithea.lib import inifile

makofile = 'kallithea/lib/paster_commands/template.ini.mako'

# the mako variables used in all other ini files and templates
mako_variable_values = {
    'database_engine': 'sqlite',
    'http_server': 'waitress',
    'host': '127.0.0.1',
    'port': '5000',
    'uuid': lambda: 'VERY-SECRET',
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
                'formatter': 'color_formatter',
            },
            '[handler_console_sql]': {
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

    # create ini files
    for fn, desc, settings in ini_files:
        print 'updating:', fn
        ini_lines = inifile.expand(mako_marked_up, desc, mako_variable_values, settings)
        open(fn, 'w').write(ini_lines)

if __name__ == '__main__':
    main()
