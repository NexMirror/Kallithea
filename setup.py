#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import os
import sys
import platform

if sys.version_info < (2, 6) or sys.version_info >= (3,):
    raise Exception('Kallithea requires python 2.6 or 2.7')


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
    "alembic>=0.8.0,<0.9",
    "GearBox<1",
    "waitress>=0.8.8,<1.0",
    "webob>=1.7,<2",
    "Pylons>=1.0.0,<=1.0.2",
    "Beaker>=1.7.0,<2",
    "WebHelpers==1.3",
    "formencode>=1.2.4,<=1.2.6",
    "SQLAlchemy>=1.0,<1.1",
    "Mako>=0.9.0,<=1.0.0",
    "pygments>=1.5",
    "whoosh>=2.5.0,<=2.5.7",
    "celery>=3.1,<3.2",
    "babel>=0.9.6,<2.4",
    "python-dateutil>=1.5.0,<2.0.0",
    "markdown==2.2.1",
    "docutils>=0.8.1",
    "URLObject==2.3.4",
    "Routes==1.13",
    "dulwich>=0.14.1",
    "mercurial>=2.9,<4.2",
]

if sys.version_info < (2, 7):
    requirements.append("importlib==1.0.1")
    requirements.append("argparse")

if not is_windows:
    requirements.append("bcrypt>=3.1.0")

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
    'Programming Language :: Python :: 2.6',
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

import setuptools

# monkey patch setuptools to use distutils owner/group functionality
from setuptools.command import sdist
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

    [paste.app_factory]
    main = kallithea.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [gearbox.commands]
    make-config=kallithea.lib.paster_commands.make_config:Command
    setup-db=kallithea.lib.paster_commands.setup_db:Command
    cleanup-repos=kallithea.lib.paster_commands.cleanup:Command
    update-repoinfo=kallithea.lib.paster_commands.update_repoinfo:Command
    make-rcext=kallithea.lib.paster_commands.make_rcextensions:Command
    repo-scan=kallithea.lib.paster_commands.repo_scan:Command
    cache-keys=kallithea.lib.paster_commands.cache_keys:Command
    ishell=kallithea.lib.paster_commands.ishell:Command
    make-index=kallithea.lib.paster_commands.make_index:Command
    upgrade-db=kallithea.lib.dbmigrate:UpgradeDb
    celeryd=kallithea.lib.paster_commands.celeryd:Command
    install-iis=kallithea.lib.paster_commands.install_iis:Command
    """,
)
