# -*- coding: utf-8 -*-
"""
    rhodecode.__init__
    ~~~~~~~~~~~~~~~~~~

    RhodeCode, a web based repository management based on pylons
    versioning implementation: http://www.python.org/dev/peps/pep-0386/

    :created_on: Apr 9, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
    :license: GPLv3, see COPYING for more details.
"""
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
import sys
import platform

VERSION = (1, 3, 4)

try:
    from rhodecode.lib import get_current_revision
    _rev = get_current_revision()
    if _rev:
        VERSION += ('dev%s' % _rev[0],)
except ImportError:
    pass

__version__ = ('.'.join((str(each) for each in VERSION[:3])) +
               '.'.join(VERSION[3:]))
__dbversion__ = 5  # defines current db version for migrations
__platform__ = platform.system()
__license__ = 'GPLv3'
__py_version__ = sys.version_info

PLATFORM_WIN = ('Windows')
PLATFORM_OTHERS = ('Linux', 'Darwin', 'FreeBSD', 'OpenBSD', 'SunOS')

requirements = [
    "Pylons==1.0.0",
    "Beaker==1.6.3",
    "WebHelpers==1.3",
    "formencode==1.2.4",
    "SQLAlchemy==0.7.6",
    "Mako==0.6.2",
    "pygments>=1.4",
    "whoosh>=2.3.0,<2.4",
    "celery>=2.2.5,<2.3",
    "babel",
    "python-dateutil>=1.5.0,<2.0.0",
    "dulwich>=0.8.4,<0.9.0",
    "webob==1.0.8",
    "markdown==2.1.1",
    "docutils==0.8.1",
]

if __py_version__ < (2, 6):
    requirements.append("simplejson")
    requirements.append("pysqlite")

if __platform__ in PLATFORM_WIN:
    requirements.append("mercurial>=2.1,<2.2")
else:
    requirements.append("py-bcrypt")
    requirements.append("mercurial>=2.1,<2.2")


def get_version():
    """Returns shorter version (digit parts only) as string."""

    return '.'.join((str(each) for each in VERSION[:3]))

BACKENDS = {
    'hg': 'Mercurial repository',
    'git': 'Git repository',
}

CELERY_ON = False

# link to config for pylons
CONFIG = {}

# Linked module for extensions
EXTENSIONS = {}
