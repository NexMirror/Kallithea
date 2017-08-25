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


import sys
import os
import functools

#==============================================================================
# json
#==============================================================================
from kallithea.lib.ext_json import json

# alias for formatted json
formatted_json = functools.partial(json.dumps, indent=4, sort_keys=True)


#==============================================================================
# unittest
#==============================================================================
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest


#==============================================================================
# OrderedDict - Python 2.7 could perhaps use collections.OrderedDict
#==============================================================================

# Python Software Foundation License


# XXX: it feels like using the class with "is" and "is not" instead of "==" and
# "!=" should be faster.
class _Nil(object):

    def __repr__(self):
        return "nil"

    def __eq__(self, other):
        if (isinstance(other, _Nil)):
            return True
        else:
            return NotImplemented

    def __ne__(self, other):
        if (isinstance(other, _Nil)):
            return False
        else:
            return NotImplemented


_nil = _Nil()


class OrderedDict(dict):
    """Ordered dict data structure, with O(1) complexity for dict operations
    that modify one element.

    Overwriting values doesn't change their original sequential order.
    """

    def __init__(self, data=(), **kwds):
        """This doesn't accept keyword initialization as normal dicts to avoid
        a trap - inside a function or method the keyword args are accessible
        only as a dict, without a defined order, so their original order is
        lost.
        """
        if kwds:
            raise TypeError("__init__() of ordered dict takes no keyword "
                            "arguments to avoid an ordering trap.")
        dict.__init__(self)
        # If you give a normal dict, then the order of elements is undefined
        if hasattr(data, "iteritems"):
            for key, val in data.iteritems():
                self[key] = val
        else:
            for key, val in data:
                self[key] = val

    # Double-linked list header
    def _get_lh(self):
        if not hasattr(self, '_lh'):
            dict.__setattr__(self, '_lh', _nil)
        return dict.__getattribute__(self, '_lh')

    def _set_lh(self, val):
        dict.__setattr__(self, '_lh', val)

    lh = property(_get_lh, _set_lh)

    # Double-linked list tail
    def _get_lt(self):
        if not hasattr(self, '_lt'):
            dict.__setattr__(self, '_lt', _nil)
        return dict.__getattribute__(self, '_lt')

    def _set_lt(self, val):
        dict.__setattr__(self, '_lt', val)

    lt = property(_get_lt, _set_lt)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)[1]

    def __setitem__(self, key, val):
        try:
            dict.__getitem__(self, key)[1] = val
        except KeyError:
            new = [dict.__getattribute__(self, 'lt'), val, _nil]
            dict.__setitem__(self, key, new)
            if dict.__getattribute__(self, 'lt') == _nil:
                dict.__setattr__(self, 'lh', key)
            else:
                dict.__getitem__(
                    self, dict.__getattribute__(self, 'lt'))[2] = key
            dict.__setattr__(self, 'lt', key)

    def __delitem__(self, key):
        pred, _, succ = dict.__getitem__(self, key)
        if pred == _nil:
            dict.__setattr__(self, 'lh', succ)
        else:
            dict.__getitem__(self, pred)[2] = succ
        if succ == _nil:
            dict.__setattr__(self, 'lt', pred)
        else:
            dict.__getitem__(self, succ)[0] = pred
        dict.__delitem__(self, key)

    def __contains__(self, key):
        return key in self.keys()

    def __len__(self):
        return len(self.keys())

    def __str__(self):
        pairs = ("%r: %r" % (k, v) for k, v in self.iteritems())
        return "{%s}" % ", ".join(pairs)

    def __repr__(self):
        if self:
            pairs = ("(%r, %r)" % (k, v) for k, v in self.iteritems())
            return "odict([%s])" % ", ".join(pairs)
        else:
            return "odict()"

    def get(self, k, x=None):
        if k in self:
            return dict.__getitem__(self, k)[1]
        else:
            return x

    def __iter__(self):
        curr_key = dict.__getattribute__(self, 'lh')
        while curr_key != _nil:
            yield curr_key
            curr_key = dict.__getitem__(self, curr_key)[2]

    iterkeys = __iter__

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        curr_key = dict.__getattribute__(self, 'lh')
        while curr_key != _nil:
            _, val, curr_key = dict.__getitem__(self, curr_key)
            yield val

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        curr_key = dict.__getattribute__(self, 'lh')
        while curr_key != _nil:
            _, val, next_key = dict.__getitem__(self, curr_key)
            yield curr_key, val
            curr_key = next_key

    def items(self):
        return list(self.iteritems())

    def sort(self, cmp=None, key=None, reverse=False):
        items = [(k, v) for k, v in self.items()]
        if cmp is not None:
            items = sorted(items, cmp=cmp)
        elif key is not None:
            items = sorted(items, key=key)
        else:
            items = sorted(items, key=lambda x: x[1])
        if reverse:
            items.reverse()
        self.clear()
        self.__init__(items)

    def clear(self):
        dict.clear(self)
        dict.__setattr__(self, 'lh', _nil)
        dict.__setattr__(self, 'lt', _nil)

    def copy(self):
        return self.__class__(self)

    def update(self, data=(), **kwds):
        if kwds:
            raise TypeError("update() of ordered dict takes no keyword "
                            "arguments to avoid an ordering trap.")
        if hasattr(data, "iteritems"):
            data = data.iteritems()
        for key, val in data:
            self[key] = val

    def setdefault(self, k, x=None):
        try:
            return self[k]
        except KeyError:
            self[k] = x
            return x

    def pop(self, k, x=_nil):
        try:
            val = self[k]
            del self[k]
            return val
        except KeyError:
            if x == _nil:
                raise
            return x

    def popitem(self):
        try:
            key = dict.__getattribute__(self, 'lt')
            return key, self.pop(key)
        except KeyError:
            raise KeyError("'popitem(): ordered dictionary is empty'")

    def riterkeys(self):
        """To iterate on keys in reversed order.
        """
        curr_key = dict.__getattribute__(self, 'lt')
        while curr_key != _nil:
            yield curr_key
            curr_key = dict.__getitem__(self, curr_key)[0]

    __reversed__ = riterkeys

    def rkeys(self):
        """List of the keys in reversed order.
        """
        return list(self.riterkeys())

    def ritervalues(self):
        """To iterate on values in reversed order.
        """
        curr_key = dict.__getattribute__(self, 'lt')
        while curr_key != _nil:
            curr_key, val, _ = dict.__getitem__(self, curr_key)
            yield val

    def rvalues(self):
        """List of the values in reversed order.
        """
        return list(self.ritervalues())

    def riteritems(self):
        """To iterate on (key, value) in reversed order.
        """
        curr_key = dict.__getattribute__(self, 'lt')
        while curr_key != _nil:
            pred_key, val, _ = dict.__getitem__(self, curr_key)
            yield curr_key, val
            curr_key = pred_key

    def ritems(self):
        """List of the (key, value) in reversed order.
        """
        return list(self.riteritems())

    def firstkey(self):
        if self:
            return dict.__getattribute__(self, 'lh')
        else:
            raise KeyError("'firstkey(): ordered dictionary is empty'")

    def lastkey(self):
        if self:
            return dict.__getattribute__(self, 'lt')
        else:
            raise KeyError("'lastkey(): ordered dictionary is empty'")

    def as_dict(self):
        return dict(self.items())

    def _repr(self):
        """_repr(): low level repr of the whole data contained in the odict.
        Useful for debugging.
        """
        form = "odict low level repr lh,lt,data: %r, %r, %s"
        return form % (dict.__getattribute__(self, 'lh'),
                       dict.__getattribute__(self, 'lt'),
                       dict.__repr__(self))


#==============================================================================
# OrderedSet
#==============================================================================
from sqlalchemy.util import OrderedSet


#==============================================================================
# Hybrid property/method
#==============================================================================
from sqlalchemy.ext.hybrid import hybrid_property


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
