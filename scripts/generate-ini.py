#!/usr/bin/env python2
"""
Based on kallithea/lib/paster_commands/template.ini.mako, generate development.ini
"""

from __future__ import print_function

import re

from kallithea.lib import inifile


# files to be generated from the mako template
ini_files = [
    ('development.ini',
        {
            '[server:main]': {
                'host': '0.0.0.0',
            },
            '[app:main]': {
                'debug': 'true',
                'app_instance_uuid': 'development-not-secret',
                'session.secret': 'development-not-secret',
            },
            '[logger_root]': {
                'handlers': 'console_color',
            },
            '[logger_routes]': {
                'level': 'DEBUG',
            },
            '[logger_beaker]': {
                'level': 'DEBUG',
            },
            '[logger_templates]': {
                'level': 'INFO',
            },
            '[logger_kallithea]': {
                'level': 'DEBUG',
            },
            '[logger_tg]': {
                'level': 'DEBUG',
            },
            '[logger_gearbox]': {
                'level': 'DEBUG',
            },
            '[logger_whoosh_indexer]': {
                'level': 'DEBUG',
            },
        },
    ),
]


def main():
    # make sure all mako lines starting with '#' (the '##' comments) are marked up as <text>
    makofile = inifile.template_file
    print('reading:', makofile)
    mako_org = open(makofile).read()
    mako_no_text_markup = re.sub(r'</?%text>', '', mako_org)
    mako_marked_up = re.sub(r'\n(##.*)', r'\n<%text>\1</%text>', mako_no_text_markup, flags=re.MULTILINE)
    if mako_marked_up != mako_org:
        print('writing:', makofile)
        open(makofile, 'w').write(mako_marked_up)

    # create ini files
    for fn, settings in ini_files:
        print('updating:', fn)
        inifile.create(fn, None, settings)


if __name__ == '__main__':
    main()
