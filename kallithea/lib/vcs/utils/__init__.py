# -*- coding: utf-8 -*-

"""
This module provides some useful tools for ``vcs`` like annotate/diff html
output. It also includes some internal helpers.
"""

import datetime
import re
import time


def makedate():
    lt = time.localtime()
    if lt[8] == 1 and time.daylight:
        tz = time.altzone
    else:
        tz = time.timezone
    return time.mktime(lt), tz


def aslist(obj, sep=None, strip=True):
    """
    Returns given string separated by sep as list

    :param obj:
    :param sep:
    :param strip:
    """
    if isinstance(obj, str):
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


def date_fromtimestamp(unixts, tzoffset=0):
    """
    Makes a local datetime object out of unix timestamp

    :param unixts:
    :param tzoffset:
    """

    return datetime.datetime.fromtimestamp(float(unixts))


def safe_int(val, default=None):
    """
    Returns int() of val if val is not convertible to int use default
    instead

    :param val:
    :param default:
    """

    try:
        val = int(val)
    except (ValueError, TypeError):
        val = default

    return val


def safe_str(s):
    """
    Safe unicode str function. Use a few tricks to turn s into str:
    In case of UnicodeDecodeError with configured default encodings, try to
    detect encoding with chardet library, then fall back to first encoding with
    errors replaced.
    """
    if isinstance(s, str):
        return s

    if not isinstance(s, bytes):  # use __str__ and don't expect UnicodeDecodeError
        return str(s)

    from kallithea.lib.vcs.conf import settings
    for enc in settings.DEFAULT_ENCODINGS:
        try:
            return str(s, enc)
        except UnicodeDecodeError:
            pass

    try:
        import chardet
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)
    except (ImportError, UnicodeDecodeError):
        pass

    return str(s, settings.DEFAULT_ENCODINGS[0], 'replace')


def safe_bytes(s):
    """
    Safe bytes function. Use a few tricks to turn s into bytes string:
    In case of UnicodeEncodeError with configured default encodings, fall back
    to first configured encoding with errors replaced.
    """
    if isinstance(s, bytes):
        return s

    assert isinstance(s, str), repr(s)  # bytes cannot coerse with __str__ or handle None or int

    from kallithea.lib.vcs.conf import settings
    for enc in settings.DEFAULT_ENCODINGS:
        try:
            return s.encode(enc)
        except UnicodeEncodeError:
            pass

    return s.encode(settings.DEFAULT_ENCODINGS[0], 'replace')


def ascii_bytes(s):
    """
    Simple conversion from str to bytes, *assuming* all codepoints are
    7-bit and it thus is pure ASCII.
    Will fail badly with UnicodeError on invalid input.
    This should be used where enocding and "safe" ambiguity should be avoided.
    Where strings already have been encoded in other ways but still are unicode
    string - for example to hex, base64, json, urlencoding, or are known to be
    identifiers.

    >>> ascii_bytes('a')
    b'a'
    >>> ascii_bytes(u'a')
    b'a'
    >>> ascii_bytes('å')
    Traceback (most recent call last):
    UnicodeEncodeError: 'ascii' codec can't encode character '\xe5' in position 0: ordinal not in range(128)
    >>> ascii_bytes('å'.encode('utf8'))
    Traceback (most recent call last):
    AssertionError: b'\xc3\xa5'
    """
    assert isinstance(s, str), repr(s)
    return s.encode('ascii')


def ascii_str(s):
    r"""
    Simple conversion from bytes to str, *assuming* all codepoints are
    7-bit and it thus is pure ASCII.
    Will fail badly with UnicodeError on invalid input.
    This should be used where enocding and "safe" ambiguity should be avoided.
    Where strings are encoded but also in other ways are known to be ASCII, and
    where a unicode string is wanted without caring about encoding. For example
    to hex, base64, urlencoding, or are known to be identifiers.

    >>> ascii_str(b'a')
    'a'
    >>> ascii_str(u'a')
    Traceback (most recent call last):
    AssertionError: 'a'
    >>> ascii_str('å'.encode('utf8'))
    Traceback (most recent call last):
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 0: ordinal not in range(128)
    >>> ascii_str(u'å')
    Traceback (most recent call last):
    AssertionError: 'å'
    """
    assert isinstance(s, bytes), repr(s)
    return s.decode('ascii')


# Regex taken from http://www.regular-expressions.info/email.html
email_re = re.compile(
    r"""[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"""
    r"""(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?""",
    re.IGNORECASE)


def author_email(author):
    """
    Returns email address of given author string.
    If author contains <> brackets, only look inside that.
    If any RFC valid email address is found, return that.
    Else, return empty string.

    """
    if not author:
        return ''

    l = author.find('<') + 1
    if l != 0:
        r = author.find('>', l)
        if r != -1:
            author = author[l:r]

    m = email_re.search(author)
    if m is None:
        return ''
    return m.group(0)


def author_name(author):
    """
    get name of author, or else username.
    It'll try to find an email in the author string and just cut it off
    to get the username
    """
    if not author:
        return ''
    if '@' not in author:
        return author
    return author.replace(author_email(author), '').replace('<', '') \
        .replace('>', '').strip()
