#!/usr/bin/env python2
"""
Based on kallithea/lib/paster_commands/template.ini.mako, generate
  development.ini
  kallithea/tests/test.ini
"""

import re

from kallithea.lib import inifile

# files to be generated from the mako template
ini_files = [
    ('kallithea/tests/test.ini',
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
    makofile = inifile.template_file
    print 'reading:', makofile
    mako_org = open(makofile).read()
    mako_no_text_markup = re.sub(r'</?%text>', '', mako_org)
    mako_marked_up = re.sub(r'\n(##.*)', r'\n<%text>\1</%text>', mako_no_text_markup, flags=re.MULTILINE)
    if mako_marked_up != mako_org:
        print 'writing:', makofile
        open(makofile, 'w').write(mako_marked_up)

    # create ini files
    for fn, settings in ini_files:
        print 'updating:', fn
        inifile.create(fn, None, settings)


if __name__ == '__main__':
    main()
