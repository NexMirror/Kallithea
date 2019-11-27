#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import os
import platform
import sys

import setuptools
# monkey patch setuptools to use distutils owner/group functionality
from setuptools.command import sdist


if sys.version_info < (2, 6) or sys.version_info >= (3,):
    raise Exception('Kallithea requires python 2.7')


here = os.path.abspath(os.path.dirname(__file__))


def _get_meta_var(name, data, callback_handler=None):
    import re
    matches = re.compile(r'(?:%s)\s*=\s*(.*)' % name).search(data)
    if matches:
        if not callable(callback_handler):
            callback_handler = lambda v: v

        return callback_handler(eval(matches.groups()[0]))

_meta = open(os.path.join(here, 'kallithea', '__init__.py'), 'rb')
_metadata = _meta.read()
_meta.close()

callback = lambda V: ('.'.join(map(str, V[:3])) + '.'.join(V[3:]))
__version__ = _get_meta_var('VERSION', _metadata, callback)
__license__ = _get_meta_var('__license__', _metadata)
__author__ = _get_meta_var('__author__', _metadata)
__url__ = _get_meta_var('__url__', _metadata)
# defines current platform
__platform__ = platform.system()

is_windows = __platform__ in ['Windows']

requirements = [
    "alembic >= 0.8.0, < 1.1",
    "gearbox >= 0.1.0, < 1",
    "waitress >= 0.8.8, < 1.4",
    "WebOb >= 1.7, < 1.9",
    "backlash >= 0.1.2, < 1",
    "TurboGears2 >= 2.3.10, < 2.5",
    "tgext.routes >= 0.2.0, < 1",
    "Beaker >= 1.7.0, < 2",
    "WebHelpers >= 1.3, < 1.4",
    "WebHelpers2 >= 2.0, < 2.1",
    "FormEncode >= 1.3.0, < 1.4",
    "SQLAlchemy >= 1.1, < 1.4",
    "Mako >= 0.9.0, < 1.1",
    "Pygments >= 2.2.0, < 2.5",
    "Whoosh >= 2.5.0, < 2.8",
    "celery >= 3.1, < 4.0", # TODO: celery 4 doesn't work
    "Babel >= 1.3, < 2.8",
    "python-dateutil >= 1.5.0, < 2.9",
    "Markdown >= 2.2.1, < 3.2",
    "docutils >= 0.11, < 0.15",
    "URLObject >= 2.3.4, < 2.5",
    "Routes >= 1.13, < 2", # TODO: bumping to 2.0 will make test_file_annotation fail
    "dulwich >= 0.14.1, < 0.20",
    "mercurial >= 4.5, < 5.3",
    "decorator >= 3.3.2, < 4.5",
    "Paste >= 2.0.3, < 3.1",
    "bleach >= 3.0, < 3.2",
    "Click >= 7.0, < 8",
    "ipaddr >= 2.1.10, < 2.3",
]

if not is_windows:
    requirements.append("bcrypt >= 3.1.0, < 3.2")

dependency_links = [
]

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Framework :: Pylons',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.7',
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
        "[WARNING] Cannot find file specified as long_description (%s)\n"
        % README_FILE
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
