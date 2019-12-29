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
kallithea.lib.utils2
~~~~~~~~~~~~~~~~~~~~

Some simple helper functions.
Note: all these functions should be independent of Kallithea classes, i.e.
models, controllers, etc.  to prevent import cycles.

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jan 5, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import print_function

import binascii
import datetime
import os
import pwd
import re
import time
import urllib

import urlobject
from tg.i18n import ugettext as _
from tg.i18n import ungettext
from webhelpers2.text import collapse, remove_formatting, strip_tags

from kallithea.lib.compat import json
from kallithea.lib.vcs.utils.lazy import LazyProperty


def str2bool(_str):
    """
    returns True/False value from given string, it tries to translate the
    string into boolean

    :param _str: string value to translate into boolean
    :rtype: boolean
    :returns: boolean from given string
    """
    if _str is None:
        return False
    if _str in (True, False):
        return _str
    _str = str(_str).strip().lower()
    return _str in ('t', 'true', 'y', 'yes', 'on', '1')


def aslist(obj, sep=None, strip=True):
    """
    Returns given string separated by sep as list

    :param obj:
    :param sep:
    :param strip:
    """
    if isinstance(obj, (basestring)):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]


def convert_line_endings(line, mode):
    """
    Converts a given line  "line end" according to given mode

    Available modes are::
        0 - Unix
        1 - Mac
        2 - DOS

    :param line: given line to convert
    :param mode: mode to convert to
    :rtype: str
    :return: converted line according to mode
    """
    from string import replace

    if mode == 0:
        line = replace(line, '\r\n', '\n')
        line = replace(line, '\r', '\n')
    elif mode == 1:
        line = replace(line, '\r\n', '\r')
        line = replace(line, '\n', '\r')
    elif mode == 2:
        line = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", line)
    return line


def detect_mode(line, default):
    """
    Detects line break for given line, if line break couldn't be found
    given default value is returned

    :param line: str line
    :param default: default
    :rtype: int
    :return: value of line end on of 0 - Unix, 1 - Mac, 2 - DOS
    """
    if line.endswith('\r\n'):
        return 2
    elif line.endswith('\n'):
        return 0
    elif line.endswith('\r'):
        return 1
    else:
        return default


def generate_api_key():
    """
    Generates a random (presumably unique) API key.

    This value is used in URLs and "Bearer" HTTP Authorization headers,
    which in practice means it should only contain URL-safe characters
    (RFC 3986):

        unreserved = ALPHA / DIGIT / "-" / "." / "_" / "~"
    """
    # Hexadecimal certainly qualifies as URL-safe.
    return binascii.hexlify(os.urandom(20))


def safe_int(val, default=None):
    """
    Returns int() of val if val is not convertable to int use default
    instead

    :param val:
    :param default:
    """

    try:
        val = int(val)
    except (ValueError, TypeError):
        val = default

    return val


def safe_unicode(str_, from_encoding=None):
    """
    safe unicode function. Does few trick to turn str_ into unicode

    In case of UnicodeDecode error we try to return it with encoding detected
    by chardet library if it fails fallback to unicode with errors replaced

    :param str_: string to decode
    :rtype: unicode
    :returns: unicode object
    """
    if isinstance(str_, unicode):
        return str_

    if not from_encoding:
        import kallithea
        DEFAULT_ENCODINGS = aslist(kallithea.CONFIG.get('default_encoding',
                                                        'utf-8'), sep=',')
        from_encoding = DEFAULT_ENCODINGS

    if not isinstance(from_encoding, (list, tuple)):
        from_encoding = [from_encoding]

    try:
        return unicode(str_)
    except UnicodeDecodeError:
        pass

    for enc in from_encoding:
        try:
            return unicode(str_, enc)
        except UnicodeDecodeError:
            pass

    try:
        import chardet
        encoding = chardet.detect(str_)['encoding']
        if encoding is None:
            raise Exception()
        return str_.decode(encoding)
    except (ImportError, UnicodeDecodeError, Exception):
        return unicode(str_, from_encoding[0], 'replace')


def safe_str(unicode_, to_encoding=None):
    """
    safe str function. Does few trick to turn unicode_ into string

    In case of UnicodeEncodeError we try to return it with encoding detected
    by chardet library if it fails fallback to string with errors replaced

    :param unicode_: unicode to encode
    :rtype: str
    :returns: str object
    """

    # if it's not basestr cast to str
    if not isinstance(unicode_, basestring):
        return str(unicode_)

    if isinstance(unicode_, str):
        return unicode_

    if not to_encoding:
        import kallithea
        DEFAULT_ENCODINGS = aslist(kallithea.CONFIG.get('default_encoding',
                                                        'utf-8'), sep=',')
        to_encoding = DEFAULT_ENCODINGS

    if not isinstance(to_encoding, (list, tuple)):
        to_encoding = [to_encoding]

    for enc in to_encoding:
        try:
            return unicode_.encode(enc)
        except UnicodeEncodeError:
            pass

    try:
        import chardet
        encoding = chardet.detect(unicode_)['encoding']
        if encoding is None:
            raise UnicodeEncodeError()

        return unicode_.encode(encoding)
    except (ImportError, UnicodeEncodeError):
        return unicode_.encode(to_encoding[0], 'replace')


def remove_suffix(s, suffix):
    if s.endswith(suffix):
        s = s[:-1 * len(suffix)]
    return s


def remove_prefix(s, prefix):
    if s.startswith(prefix):
        s = s[len(prefix):]
    return s


def age(prevdate, show_short_version=False, now=None):
    """
    turns a datetime into an age string.
    If show_short_version is True, then it will generate a not so accurate but shorter string,
    example: 2days ago, instead of 2 days and 23 hours ago.

    :param prevdate: datetime object
    :param show_short_version: if it should approximate the date and return a shorter string
    :rtype: unicode
    :returns: unicode words describing age
    """
    now = now or datetime.datetime.now()
    order = ['year', 'month', 'day', 'hour', 'minute', 'second']
    deltas = {}
    future = False

    if prevdate > now:
        now, prevdate = prevdate, now
        future = True
    if future:
        prevdate = prevdate.replace(microsecond=0)
    # Get date parts deltas
    from dateutil import relativedelta
    for part in order:
        d = relativedelta.relativedelta(now, prevdate)
        deltas[part] = getattr(d, part + 's')

    # Fix negative offsets (there is 1 second between 10:59:59 and 11:00:00,
    # not 1 hour, -59 minutes and -59 seconds)
    for num, length in [(5, 60), (4, 60), (3, 24)]:  # seconds, minutes, hours
        part = order[num]
        carry_part = order[num - 1]

        if deltas[part] < 0:
            deltas[part] += length
            deltas[carry_part] -= 1

    # Same thing for days except that the increment depends on the (variable)
    # number of days in the month
    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if deltas['day'] < 0:
        if prevdate.month == 2 and (prevdate.year % 4 == 0 and
            (prevdate.year % 100 != 0 or prevdate.year % 400 == 0)
        ):
            deltas['day'] += 29
        else:
            deltas['day'] += month_lengths[prevdate.month - 1]

        deltas['month'] -= 1

    if deltas['month'] < 0:
        deltas['month'] += 12
        deltas['year'] -= 1

    # In short version, we want nicer handling of ages of more than a year
    if show_short_version:
        if deltas['year'] == 1:
            # ages between 1 and 2 years: show as months
            deltas['month'] += 12
            deltas['year'] = 0
        if deltas['year'] >= 2:
            # ages 2+ years: round
            if deltas['month'] > 6:
                deltas['year'] += 1
                deltas['month'] = 0

    # Format the result
    fmt_funcs = {
        'year': lambda d: ungettext(u'%d year', '%d years', d) % d,
        'month': lambda d: ungettext(u'%d month', '%d months', d) % d,
        'day': lambda d: ungettext(u'%d day', '%d days', d) % d,
        'hour': lambda d: ungettext(u'%d hour', '%d hours', d) % d,
        'minute': lambda d: ungettext(u'%d minute', '%d minutes', d) % d,
        'second': lambda d: ungettext(u'%d second', '%d seconds', d) % d,
    }

    for i, part in enumerate(order):
        value = deltas[part]
        if value == 0:
            continue

        if i < 5:
            sub_part = order[i + 1]
            sub_value = deltas[sub_part]
        else:
            sub_value = 0

        if sub_value == 0 or show_short_version:
            if future:
                return _('in %s') % fmt_funcs[part](value)
            else:
                return _('%s ago') % fmt_funcs[part](value)
        if future:
            return _('in %s and %s') % (fmt_funcs[part](value),
                fmt_funcs[sub_part](sub_value))
        else:
            return _('%s and %s ago') % (fmt_funcs[part](value),
                fmt_funcs[sub_part](sub_value))

    return _('just now')


def uri_filter(uri):
    """
    Removes user:password from given url string

    :param uri:
    :rtype: unicode
    :returns: filtered list of strings
    """
    if not uri:
        return ''

    proto = ''

    for pat in ('https://', 'http://', 'git://'):
        if uri.startswith(pat):
            uri = uri[len(pat):]
            proto = pat
            break

    # remove passwords and username
    uri = uri[uri.find('@') + 1:]

    # get the port
    cred_pos = uri.find(':')
    if cred_pos == -1:
        host, port = uri, None
    else:
        host, port = uri[:cred_pos], uri[cred_pos + 1:]

    return filter(None, [proto, host, port])


def credentials_filter(uri):
    """
    Returns a url with removed credentials

    :param uri:
    """

    uri = uri_filter(uri)
    # check if we have port
    if len(uri) > 2 and uri[2]:
        uri[2] = ':' + uri[2]

    return ''.join(uri)


def get_clone_url(clone_uri_tmpl, prefix_url, repo_name, repo_id, username=None):
    parsed_url = urlobject.URLObject(prefix_url)
    prefix = safe_unicode(urllib.unquote(parsed_url.path.rstrip('/')))
    try:
        system_user = pwd.getpwuid(os.getuid()).pw_name
    except Exception: # TODO: support all systems - especially Windows
        system_user = 'kallithea' # hardcoded default value ...
    args = {
        'scheme': parsed_url.scheme,
        'user': safe_unicode(urllib.quote(safe_str(username or ''))),
        'netloc': parsed_url.netloc + prefix,  # like "hostname:port/prefix" (with optional ":port" and "/prefix")
        'prefix': prefix, # undocumented, empty or starting with /
        'repo': repo_name,
        'repoid': str(repo_id),
        'system_user': safe_unicode(system_user),
        'hostname': parsed_url.hostname,
    }
    url = re.sub('{([^{}]+)}', lambda m: args.get(m.group(1), m.group(0)), clone_uri_tmpl)

    # remove leading @ sign if it's present. Case of empty user
    url_obj = urlobject.URLObject(url)
    if not url_obj.username:
        url_obj = url_obj.with_username(None)

    return safe_unicode(url_obj)


def get_changeset_safe(repo, rev):
    """
    Safe version of get_changeset if this changeset doesn't exists for a
    repo it returns a Dummy one instead

    :param repo:
    :param rev:
    """
    from kallithea.lib.vcs.backends.base import BaseRepository
    from kallithea.lib.vcs.exceptions import RepositoryError
    from kallithea.lib.vcs.backends.base import EmptyChangeset
    if not isinstance(repo, BaseRepository):
        raise Exception('You must pass an Repository '
                        'object as first argument got %s' % type(repo))

    try:
        cs = repo.get_changeset(rev)
    except (RepositoryError, LookupError):
        cs = EmptyChangeset(requested_revision=rev)
    return cs


def datetime_to_time(dt):
    if dt:
        return time.mktime(dt.timetuple())


def time_to_datetime(tm):
    if tm:
        if isinstance(tm, basestring):
            try:
                tm = float(tm)
            except ValueError:
                return
        return datetime.datetime.fromtimestamp(tm)


# Must match regexp in kallithea/public/js/base.js MentionsAutoComplete()
# Check char before @ - it must not look like we are in an email addresses.
# Matching is greedy so we don't have to look beyond the end.
MENTIONS_REGEX = re.compile(r'(?:^|(?<=[^a-zA-Z0-9]))@([a-zA-Z0-9][-_.a-zA-Z0-9]*[a-zA-Z0-9])')


def extract_mentioned_usernames(text):
    r"""
    Returns list of (possible) usernames @mentioned in given text.

    >>> extract_mentioned_usernames('@1-2.a_X,@1234 not@not @ddd@not @n @ee @ff @gg, @gg;@hh @n\n@zz,')
    ['1-2.a_X', '1234', 'ddd', 'ee', 'ff', 'gg', 'gg', 'hh', 'zz']
    """
    return MENTIONS_REGEX.findall(text)


def extract_mentioned_users(text):
    """ Returns set of actual database Users @mentioned in given text. """
    from kallithea.model.db import User
    result = set()
    for name in extract_mentioned_usernames(text):
        user = User.get_by_username(name, case_insensitive=True)
        if user is not None and not user.is_default_user:
            result.add(user)
    return result


class AttributeDict(dict):
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def obfuscate_url_pw(engine):
    from sqlalchemy.engine import url as sa_url
    from sqlalchemy.exc import ArgumentError
    try:
        _url = sa_url.make_url(engine or '')
    except ArgumentError:
        return engine
    if _url.password:
        _url.password = 'XXXXX'
    return str(_url)


class HookEnvironmentError(Exception): pass


def get_hook_environment():
    """
    Get hook context by deserializing the global KALLITHEA_EXTRAS environment
    variable.

    Called early in Git out-of-process hooks to get .ini config path so the
    basic environment can be configured properly. Also used in all hooks to get
    information about the action that triggered it.
    """

    try:
        kallithea_extras = os.environ['KALLITHEA_EXTRAS']
    except KeyError:
        raise HookEnvironmentError("Environment variable KALLITHEA_EXTRAS not found")

    extras = json.loads(kallithea_extras)
    try:
        for k in ['username', 'repository', 'scm', 'action', 'ip', 'config']:
            extras[k]
    except KeyError:
        raise HookEnvironmentError('Missing key %s in KALLITHEA_EXTRAS %s' % (k, extras))

    return AttributeDict(extras)


def set_hook_environment(username, ip_addr, repo_name, repo_alias, action=None):
    """Prepare global context for running hooks by serializing data in the
    global KALLITHEA_EXTRAS environment variable.

    Most importantly, this allow Git hooks to do proper logging and updating of
    caches after pushes.

    Must always be called before anything with hooks are invoked.
    """
    from kallithea import CONFIG
    extras = {
        'ip': ip_addr, # used in log_push/pull_action action_logger
        'username': username,
        'action': action or 'push_local', # used in log_push_action_raw_ids action_logger
        'repository': repo_name,
        'scm': repo_alias, # used to pick hack in log_push_action_raw_ids
        'config': CONFIG['__file__'], # used by git hook to read config
    }
    os.environ['KALLITHEA_EXTRAS'] = json.dumps(extras)


def get_current_authuser():
    """
    Gets kallithea user from threadlocal tmpl_context variable if it's
    defined, else returns None.
    """
    from tg import tmpl_context
    if hasattr(tmpl_context, 'authuser'):
        return tmpl_context.authuser

    return None


class OptionalAttr(object):
    """
    Special Optional Option that defines other attribute. Example::

        def test(apiuser, userid=Optional(OAttr('apiuser')):
            user = Optional.extract(userid)
            # calls

    """

    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __repr__(self):
        return '<OptionalAttr:%s>' % self.attr_name

    def __call__(self):
        return self


# alias
OAttr = OptionalAttr


class Optional(object):
    """
    Defines an optional parameter::

        param = param.getval() if isinstance(param, Optional) else param
        param = param() if isinstance(param, Optional) else param

    is equivalent of::

        param = Optional.extract(param)

    """

    def __init__(self, type_):
        self.type_ = type_

    def __repr__(self):
        return '<Optional:%s>' % self.type_.__repr__()

    def __call__(self):
        return self.getval()

    def getval(self):
        """
        returns value from this Optional instance
        """
        if isinstance(self.type_, OAttr):
            # use params name
            return self.type_.attr_name
        return self.type_

    @classmethod
    def extract(cls, val):
        """
        Extracts value from Optional() instance

        :param val:
        :return: original value if it's not Optional instance else
            value of instance
        """
        if isinstance(val, cls):
            return val.getval()
        return val


def urlreadable(s, _cleanstringsub=re.compile('[^-a-zA-Z0-9./]+').sub):
    return _cleanstringsub('_', safe_str(s)).rstrip('_')


def recursive_replace(str_, replace=' '):
    """
    Recursive replace of given sign to just one instance

    :param str_: given string
    :param replace: char to find and replace multiple instances

    Examples::
    >>> recursive_replace("Mighty---Mighty-Bo--sstones",'-')
    'Mighty-Mighty-Bo-sstones'
    """

    if str_.find(replace * 2) == -1:
        return str_
    else:
        str_ = str_.replace(replace * 2, replace)
        return recursive_replace(str_, replace)


def repo_name_slug(value):
    """
    Return slug of name of repository
    This function is called on each creation/modification
    of repository to prevent bad names in repo
    """

    slug = remove_formatting(value)
    slug = strip_tags(slug)

    for c in r"""`?=[]\;'"<>,/~!@#$%^&*()+{}|: """:
        slug = slug.replace(c, '-')
    slug = recursive_replace(slug, '-')
    slug = collapse(slug, '-')
    return slug


def ask_ok(prompt, retries=4, complaint='Yes or no please!'):
    while True:
        ok = raw_input(prompt)
        if ok in ('y', 'ye', 'yes'):
            return True
        if ok in ('n', 'no', 'nop', 'nope'):
            return False
        retries = retries - 1
        if retries < 0:
            raise IOError
        print(complaint)
