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
kallithea.lib.compat
~~~~~~~~~~~~~~~~~~~~

Python backward compatibility functions and common libs


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 7, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import functools
import os
import sys

#==============================================================================
# Hybrid property/method
#==============================================================================
from sqlalchemy.ext.hybrid import hybrid_property
#==============================================================================
# OrderedSet
#==============================================================================
from sqlalchemy.util import OrderedSet

#==============================================================================
# json
#==============================================================================
from kallithea.lib.ext_json import json


# alias for formatted json
formatted_json = functools.partial(json.dumps, indent=4, sort_keys=True)






#==============================================================================
# kill
#==============================================================================
if os.name == 'nt': # Windows
    import ctypes

    def kill(pid, sig):
        """kill function for Win32"""
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(1, 0, pid)
        return (0 != kernel32.TerminateProcess(handle, 0))

else:
    kill = os.kill
