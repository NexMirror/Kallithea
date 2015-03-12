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


import os
import functools
import importlib
from kallithea import __py_version__, is_windows

#==============================================================================
# json
#==============================================================================
from kallithea.lib.ext_json import json

# alias for formatted json
formatted_json = functools.partial(json.dumps, indent=4, sort_keys=True)

if __py_version__ >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

#==============================================================================
# izip_longest
#==============================================================================
try:
    from itertools import izip_longest
except ImportError:
    import itertools

    def izip_longest(*args, **kwds):
        fillvalue = kwds.get("fillvalue")

        def sentinel(counter=([fillvalue] * (len(args) - 1)).pop):
            yield counter()  # yields the fillvalue, or raises IndexError

        fillers = itertools.repeat(fillvalue)
        iters = [itertools.chain(it, sentinel(), fillers)
                    for it in args]
        try:
            for tup in itertools.izip(*iters):
                yield tup
        except IndexError:
            pass


#==============================================================================
# OrderedDict
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


class _odict(object):
    """Ordered dict data structure, with O(1) complexity for dict operations
    that modify one element.

    Overwriting values doesn't change their original sequential order.
    """

    def _dict_impl(self):
        return None

    def __init__(self, data=(), **kwds):
        """This doesn't accept keyword initialization as normal dicts to avoid
        a trap - inside a function or method the keyword args are accessible
        only as a dict, without a defined order, so their original order is
        lost.
        """
        if kwds:
            raise TypeError("__init__() of ordered dict takes no keyword "
                            "arguments to avoid an ordering trap.")
        self._dict_impl().__init__(self)
        # If you give a normal dict, then the order of elements is undefined
        if hasattr(data, "iteritems"):
            for key, val in data.iteritems():
                self[key] = val
        else:
            for key, val in data:
                self[key] = val

    # Double-linked list header
    def _get_lh(self):
        dict_impl = self._dict_impl()
        if not hasattr(self, '_lh'):
            dict_impl.__setattr__(self, '_lh', _nil)
        return dict_impl.__getattribute__(self, '_lh')

    def _set_lh(self, val):
        self._dict_impl().__setattr__(self, '_lh', val)

    lh = property(_get_lh, _set_lh)

    # Double-linked list tail
    def _get_lt(self):
        dict_impl = self._dict_impl()
        if not hasattr(self, '_lt'):
            dict_impl.__setattr__(self, '_lt', _nil)
        return dict_impl.__getattribute__(self, '_lt')

    def _set_lt(self, val):
        self._dict_impl().__setattr__(self, '_lt', val)

    lt = property(_get_lt, _set_lt)

    def __getitem__(self, key):
        return self._dict_impl().__getitem__(self, key)[1]

    def __setitem__(self, key, val):
        dict_impl = self._dict_impl()
        try:
            dict_impl.__getitem__(self, key)[1] = val
        except KeyError:
            new = [dict_impl.__getattribute__(self, 'lt'), val, _nil]
            dict_impl.__setitem__(self, key, new)
            if dict_impl.__getattribute__(self, 'lt') == _nil:
                dict_impl.__setattr__(self, 'lh', key)
            else:
                dict_impl.__getitem__(
                    self, dict_impl.__getattribute__(self, 'lt'))[2] = key
            dict_impl.__setattr__(self, 'lt', key)

    def __delitem__(self, key):
        dict_impl = self._dict_impl()
        pred, _, succ = self._dict_impl().__getitem__(self, key)
        if pred == _nil:
            dict_impl.__setattr__(self, 'lh', succ)
        else:
            dict_impl.__getitem__(self, pred)[2] = succ
        if succ == _nil:
            dict_impl.__setattr__(self, 'lt', pred)
        else:
            dict_impl.__getitem__(self, succ)[0] = pred
        dict_impl.__delitem__(self, key)

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
            return self._dict_impl().__getitem__(self, k)[1]
        else:
            return x

    def __iter__(self):
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lh')
        while curr_key != _nil:
            yield curr_key
            curr_key = dict_impl.__getitem__(self, curr_key)[2]

    iterkeys = __iter__

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lh')
        while curr_key != _nil:
            _, val, curr_key = dict_impl.__getitem__(self, curr_key)
            yield val

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lh')
        while curr_key != _nil:
            _, val, next_key = dict_impl.__getitem__(self, curr_key)
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
        dict_impl = self._dict_impl()
        dict_impl.clear(self)
        dict_impl.__setattr__(self, 'lh', _nil)
        dict_impl.__setattr__(self, 'lt', _nil)

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
            dict_impl = self._dict_impl()
            key = dict_impl.__getattribute__(self, 'lt')
            return key, self.pop(key)
        except KeyError:
            raise KeyError("'popitem(): ordered dictionary is empty'")

    def riterkeys(self):
        """To iterate on keys in reversed order.
        """
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lt')
        while curr_key != _nil:
            yield curr_key
            curr_key = dict_impl.__getitem__(self, curr_key)[0]

    __reversed__ = riterkeys

    def rkeys(self):
        """List of the keys in reversed order.
        """
        return list(self.riterkeys())

    def ritervalues(self):
        """To iterate on values in reversed order.
        """
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lt')
        while curr_key != _nil:
            curr_key, val, _ = dict_impl.__getitem__(self, curr_key)
            yield val

    def rvalues(self):
        """List of the values in reversed order.
        """
        return list(self.ritervalues())

    def riteritems(self):
        """To iterate on (key, value) in reversed order.
        """
        dict_impl = self._dict_impl()
        curr_key = dict_impl.__getattribute__(self, 'lt')
        while curr_key != _nil:
            pred_key, val, _ = dict_impl.__getitem__(self, curr_key)
            yield curr_key, val
            curr_key = pred_key

    def ritems(self):
        """List of the (key, value) in reversed order.
        """
        return list(self.riteritems())

    def firstkey(self):
        if self:
            return self._dict_impl().__getattribute__(self, 'lh')
        else:
            raise KeyError("'firstkey(): ordered dictionary is empty'")

    def lastkey(self):
        if self:
            return self._dict_impl().__getattribute__(self, 'lt')
        else:
            raise KeyError("'lastkey(): ordered dictionary is empty'")

    def as_dict(self):
        return self._dict_impl()(self.items())

    def _repr(self):
        """_repr(): low level repr of the whole data contained in the odict.
        Useful for debugging.
        """
        dict_impl = self._dict_impl()
        form = "odict low level repr lh,lt,data: %r, %r, %s"
        return form % (dict_impl.__getattribute__(self, 'lh'),
                       dict_impl.__getattribute__(self, 'lt'),
                       dict_impl.__repr__(self))


class OrderedDict(_odict, dict):

    def _dict_impl(self):
        return dict


#==============================================================================
# OrderedSet
#==============================================================================
from sqlalchemy.util import OrderedSet


#==============================================================================
# Hybrid property/method
#==============================================================================
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property


#==============================================================================
# kill FUNCTIONS
#==============================================================================
if is_windows:
    import ctypes

    def kill(pid, sig):
        """kill function for Win32"""
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(1, 0, pid)
        return (0 != kernel32.TerminateProcess(handle, 0))

else:
    kill = os.kill


#==============================================================================
# itertools.product
#==============================================================================

try:
    from itertools import product
except ImportError:
    def product(*args, **kwds):
        # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
        # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x + [y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)


#==============================================================================
# BytesIO
#==============================================================================

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO


#==============================================================================
# bytes
#==============================================================================
if __py_version__ >= (2, 6):
    _bytes = bytes
else:
    # in py2.6 bytes is a synonym for str
    _bytes = str

if __py_version__ >= (2, 6):
    _bytearray = bytearray
else:
    import array
    # no idea if this is correct but all integration tests are passing
    # i think we never use bytearray anyway
    _bytearray = array


#==============================================================================
# deque
#==============================================================================

if __py_version__ >= (2, 6):
    from collections import deque
else:
    #need to implement our own deque with maxlen
    class deque(object):

        def __init__(self, iterable=(), maxlen= -1):
            if not hasattr(self, 'data'):
                self.left = self.right = 0
                self.data = {}
            self.maxlen = maxlen or -1
            self.extend(iterable)

        def append(self, x):
            self.data[self.right] = x
            self.right += 1
            if self.maxlen != -1 and len(self) > self.maxlen:
                self.popleft()

        def appendleft(self, x):
            self.left -= 1
            self.data[self.left] = x
            if self.maxlen != -1 and len(self) > self.maxlen:
                self.pop()

        def pop(self):
            if self.left == self.right:
                raise IndexError('cannot pop from empty deque')
            self.right -= 1
            elem = self.data[self.right]
            del self.data[self.right]
            return elem

        def popleft(self):
            if self.left == self.right:
                raise IndexError('cannot pop from empty deque')
            elem = self.data[self.left]
            del self.data[self.left]
            self.left += 1
            return elem

        def clear(self):
            self.data.clear()
            self.left = self.right = 0

        def extend(self, iterable):
            for elem in iterable:
                self.append(elem)

        def extendleft(self, iterable):
            for elem in iterable:
                self.appendleft(elem)

        def rotate(self, n=1):
            if self:
                n %= len(self)
                for i in xrange(n):
                    self.appendleft(self.pop())

        def __getitem__(self, i):
            if i < 0:
                i += len(self)
            try:
                return self.data[i + self.left]
            except KeyError:
                raise IndexError

        def __setitem__(self, i, value):
            if i < 0:
                i += len(self)
            try:
                self.data[i + self.left] = value
            except KeyError:
                raise IndexError

        def __delitem__(self, i):
            size = len(self)
            if not (-size <= i < size):
                raise IndexError
            data = self.data
            if i < 0:
                i += size
            for j in xrange(self.left + i, self.right - 1):
                data[j] = data[j + 1]
            self.pop()

        def __len__(self):
            return self.right - self.left

        def __cmp__(self, other):
            if type(self) != type(other):
                return cmp(type(self), type(other))
            return cmp(list(self), list(other))

        def __repr__(self, _track=[]):
            if id(self) in _track:
                return '...'
            _track.append(id(self))
            r = 'deque(%r, maxlen=%s)' % (list(self), self.maxlen)
            _track.remove(id(self))
            return r

        def __getstate__(self):
            return (tuple(self),)

        def __setstate__(self, s):
            self.__init__(s[0])

        def __hash__(self):
            raise TypeError

        def __copy__(self):
            return self.__class__(self)

        def __deepcopy__(self, memo={}):
            from copy import deepcopy
            result = self.__class__()
            memo[id(self)] = result
            result.__init__(deepcopy(tuple(self), memo))
            return result
