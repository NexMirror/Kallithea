#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import platform
import sys

import setuptools
# monkey patch setuptools to use distutils owner/group functionality
from setuptools.command import sdist


if sys.version_info < (3, 6):
    raise Exception('Kallithea requires Python 3.6 or later')


here = os.path.abspath(os.path.dirname(__file__))


def _get_meta_var(name, data, callback_handler=None):
    import re
    matches = re.compile(r'(?:%s)\s*=\s*(.*)' % name).search(data)
    if matches:
        s = eval(matches.groups()[0])
        if callable(callback_handler):
            return callback_handler(s)
        return s

_meta = open(os.path.join(here, 'kallithea', '__init__.py'), 'r')
_metadata = _meta.read()
_meta.close()

def callback(V):
    return '.'.join(map(str, V[:3])) + '.'.join(V[3:])
__version__ = _get_meta_var('VERSION', _metadata, callback)
__license__ = _get_meta_var('__license__', _metadata)
__author__ = _get_meta_var('__author__', _metadata)
__url__ = _get_meta_var('__url__', _metadata)
# defines current platform
__platform__ = platform.system()

is_windows = __platform__ in ['Windows']

requirements = [
    "alembic >= 1.0.10, < 1.5",
    "gearbox >= 0.1.0, < 1",
    "waitress >= 0.8.8, < 1.5",
    "WebOb >= 1.8, < 1.9",
    "backlash >= 0.1.2, < 1",
    "TurboGears2 >= 2.4, < 2.5",
    "tgext.routes >= 0.2.0, < 1",
    "Beaker >= 1.10.1, < 2",
    "WebHelpers2 >= 2.0, < 2.1",
    "FormEncode >= 1.3.1, < 1.4",
    "SQLAlchemy >= 1.2.9, < 1.4",
    "Mako >= 0.9.1, < 1.2",
    "Pygments >= 2.2.0, < 2.6",
    "Whoosh >= 2.7.1, < 2.8",
    "celery >= 4.3, < 4.5",
    "Babel >= 1.3, < 2.9",
    "python-dateutil >= 2.1.0, < 2.9",
    "Markdown >= 2.2.1, < 3.2",
    "docutils >= 0.11, < 0.17",
    "URLObject >= 2.3.4, < 2.5",
    "Routes >= 2.0, < 2.5",
    "dulwich >= 0.19.0, < 0.20",
    "mercurial >= 5.2, < 5.5",
    "decorator >= 4.2.1, < 4.5",
    "Paste >= 2.0.3, < 3.4",
    "bleach >= 3.0, < 3.1.4",
    "Click >= 7.0, < 8",
    "ipaddr >= 2.2.0, < 2.3",
    "paginate >= 0.5, < 0.6",
    "paginate_sqlalchemy >= 0.3.0, < 0.4",
    "bcrypt >= 3.1.0, < 3.2",
    "pip >= 20.0, < 999",
]

dependency_links = [
]

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Framework :: Pylons',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Software Development :: Version Control',
]


# additional files from project that goes somewhere in the filesystem
# relative to sys.prefix
data_files = []

description = ('Kallithea is a fast and powerful management tool '
               'for Mercurial and Git with a built in push/pull server, '
               'full text search and code-review.')

keywords = ' '.join([
    'kallithea', 'mercurial', 'git', 'code review',
    'repo groups', 'ldap', 'repository management', 'hgweb replacement',
    'hgwebdir', 'gitweb replacement', 'serving hgweb',
])

# long description
README_FILE = 'README.rst'
try:
    long_description = open(README_FILE).read()
except IOError as err:
    sys.stderr.write(
        "[WARNING] Cannot find file specified as long_description (%s): %s\n"
        % (README_FILE, err)
    )
    long_description = description


sdist_org = sdist.sdist
class sdist_new(sdist_org):
    def initialize_options(self):
        sdist_org.initialize_options(self)
        self.owner = self.group = 'root'
sdist.sdist = sdist_new

packages = setuptools.find_packages(exclude=['ez_setup'])

setuptools.setup(
    name='Kallithea',
    version=__version__,
    description=description,
    long_description=long_description,
    keywords=keywords,
    license=__license__,
    author=__author__,
    author_email='kallithea@sfconservancy.org',
    dependency_links=dependency_links,
    url=__url__,
    install_requires=requirements,
    classifiers=classifiers,
    data_files=data_files,
    packages=packages,
    include_package_data=True,
    message_extractors={'kallithea': [
            ('**.py', 'python', None),
            ('templates/**.mako', 'mako', {'input_encoding': 'utf-8'}),
            ('templates/**.html', 'mako', {'input_encoding': 'utf-8'}),
            ('public/**', 'ignore', None)]},
    zip_safe=False,
    entry_points="""
    [console_scripts]
    kallithea-api =    kallithea.bin.kallithea_api:main
    kallithea-gist =   kallithea.bin.kallithea_gist:main
    kallithea-config = kallithea.bin.kallithea_config:main
    kallithea-cli =    kallithea.bin.kallithea_cli:cli

    [paste.app_factory]
    main = kallithea.config.middleware:make_app
    """,
)
