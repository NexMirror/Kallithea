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
import logging
import os
import sys


log = logging.getLogger(__name__)

def current_locale_is_valid():
    """Verify that things work when Dulwich passes unicode paths to the file system layer.

    Note: UTF-8 is preferred, but for example ISO-8859-1 or mbcs should also
    work under the right circumstances."""
    try:
        u'\xe9'.encode(sys.getfilesystemencoding()) # Test using é (&eacute;)
    except UnicodeEncodeError:
        log.error("Cannot encode Unicode paths to file system encoding %r", sys.getfilesystemencoding())
        for var in ['LC_ALL', 'LC_CTYPE', 'LANG']:
            if var in os.environ:
                val = os.environ[var]
                log.error("Note: Environment variable %s is %r - perhaps change it to some other value from 'locale -a', like 'C.UTF-8' or 'en_US.UTF-8'", var, val)
                break
        else:
            log.error("Note: No locale setting found in environment variables - perhaps set LC_CTYPE to some value from 'locale -a', like 'C.UTF-8' or 'en_US.UTF-8'")
        return False
    return True

def get_current_locale():
    """Return the current locale based on environment variables.
    There does not seem to be a good (and functional) way to get it via Python.
    """
    for var in ['LC_ALL', 'LC_CTYPE', 'LANG']:
        val = os.environ.get(var)
        if val:
            log.debug('Determined current locale via environment variable %s (%s)', var, val)
            return val
    return None
