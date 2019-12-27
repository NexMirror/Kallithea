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
    if isinstance(obj, basestring):
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


def safe_unicode(s):
    """
    Safe unicode function. Use a few tricks to turn s into unicode string:
    In case of UnicodeDecodeError with configured default encodings, try to
    detect encoding with chardet library, then fall back to first encoding with
    errors replaced.
    """
    if isinstance(s, unicode):
        return s

    if not isinstance(s, str):  # use __str__ / __unicode__ and don't expect UnicodeDecodeError
        return unicode(s)

    from kallithea.lib.vcs.conf import settings
    for enc in settings.DEFAULT_ENCODINGS:
        try:
            return unicode(s, enc)
        except UnicodeDecodeError:
            pass

    try:
        import chardet
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)
    except (ImportError, UnicodeDecodeError):
        pass

    return unicode(s, settings.DEFAULT_ENCODINGS[0], 'replace')


def safe_str(s):
    """
    Safe str function. Use a few tricks to turn s into bytes string:
    In case of UnicodeEncodeError with configured default encodings, fall back
    to first configured encoding with errors replaced.
    """
    if isinstance(s, str):
        return s

    assert isinstance(s, unicode), s  # don't use safe_str to coerce non-strings

    from kallithea.lib.vcs.conf import settings
    for enc in settings.DEFAULT_ENCODINGS:
        try:
            return s.encode(enc)
        except UnicodeEncodeError:
            pass

    return s.encode(settings.DEFAULT_ENCODINGS[0], 'replace')


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
    return safe_str(m.group(0))


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
