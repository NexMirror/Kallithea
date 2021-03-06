"""
Utilities aimed to help achieve mostly basic tasks.
"""

import datetime
import os
import re
import time

from kallithea.lib.vcs.exceptions import RepositoryError, VCSError
from kallithea.lib.vcs.utils.paths import abspath


ALIASES = ['hg', 'git']


def get_scm(path, search_up=False, explicit_alias=None):
    """
    Returns one of alias from ``ALIASES`` (in order of precedence same as
    shortcuts given in ``ALIASES``) and top working dir path for the given
    argument. If no scm-specific directory is found or more than one scm is
    found at that directory, ``VCSError`` is raised.

    :param search_up: if set to ``True``, this function would try to
      move up to parent directory every time no scm is recognized for the
      currently checked path. Default: ``False``.
    :param explicit_alias: can be one of available backend aliases, when given
      it will return given explicit alias in repositories under more than one
      version control, if explicit_alias is different than found it will raise
      VCSError
    """
    if not os.path.isdir(path):
        raise VCSError("Given path %s is not a directory" % path)

    while True:
        found_scms = [(scm, path) for scm in get_scms_for_path(path)]
        if found_scms or not search_up:
            break
        newpath = abspath(path, '..')
        if newpath == path:
            break
        path = newpath

    if len(found_scms) > 1:
        for scm in found_scms:
            if scm[0] == explicit_alias:
                return scm
        raise VCSError('More than one [%s] scm found at given path %s'
                       % (', '.join((x[0] for x in found_scms)), path))

    if len(found_scms) == 0:
        raise VCSError('No scm found at given path %s' % path)

    return found_scms[0]


def get_scms_for_path(path):
    """
    Returns all scm's found at the given path. If no scm is recognized
    - empty list is returned.

    :param path: path to directory which should be checked. May be callable.

    :raises VCSError: if given ``path`` is not a directory
    """
    from kallithea.lib.vcs.backends import get_backend
    if hasattr(path, '__call__'):
        path = path()
    if not os.path.isdir(path):
        raise VCSError("Given path %r is not a directory" % path)

    result = []
    for key in ALIASES:
        # find .hg / .git
        dirname = os.path.join(path, '.' + key)
        if os.path.isdir(dirname):
            result.append(key)
            continue
        # find rm__.hg / rm__.git too - left overs from old method for deleting
        dirname = os.path.join(path, 'rm__.' + key)
        if os.path.isdir(dirname):
            return result
        # We still need to check if it's not bare repository as
        # bare repos don't have working directories
        try:
            get_backend(key)(path)
            result.append(key)
            continue
        except RepositoryError:
            # Wrong backend
            pass
        except VCSError:
            # No backend at all
            pass
    return result


def get_highlighted_code(name, code, type='terminal'):
    """
    If pygments are available on the system
    then returned output is colored. Otherwise
    unchanged content is returned.
    """
    import logging
    try:
        import pygments
        pygments
    except ImportError:
        return code
    from pygments import highlight
    from pygments.lexers import guess_lexer_for_filename, ClassNotFound
    from pygments.formatters import TerminalFormatter

    try:
        lexer = guess_lexer_for_filename(name, code)
        formatter = TerminalFormatter()
        content = highlight(code, lexer, formatter)
    except ClassNotFound:
        logging.debug("Couldn't guess Lexer, will not use pygments.")
        content = code
    return content


def parse_changesets(text):
    """
    Returns dictionary with *start*, *main* and *end* ids.

    Examples::

        >>> parse_changesets('aaabbb')
        {'start': None, 'main': 'aaabbb', 'end': None}
        >>> parse_changesets('aaabbb..cccddd')
        {'start': 'aaabbb', 'end': 'cccddd', 'main': None}

    """
    text = text.strip()
    CID_RE = r'[a-zA-Z0-9]+'
    if '..' not in text:
        m = re.match(r'^(?P<cid>%s)$' % CID_RE, text)
        if m:
            return {
                'start': None,
                'main': text,
                'end': None,
            }
    else:
        RE = r'^(?P<start>%s)?\.{2,3}(?P<end>%s)?$' % (CID_RE, CID_RE)
        m = re.match(RE, text)
        if m:
            result = m.groupdict()
            result['main'] = None
            return result
    raise ValueError("IDs not recognized")


def parse_datetime(text):
    """
    Parses given text and returns ``datetime.datetime`` instance or raises
    ``ValueError``.

    :param text: string of desired date/datetime or something more verbose,
      like *yesterday*, *2weeks 3days*, etc.
    """

    text = text.strip().lower()

    INPUT_FORMATS = (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y',
        '%m/%d/%y %H:%M:%S',
        '%m/%d/%y %H:%M',
        '%m/%d/%y',
    )
    for format in INPUT_FORMATS:
        try:
            return datetime.datetime(*time.strptime(text, format)[:6])
        except ValueError:
            pass

    # Try descriptive texts
    if text == 'tomorrow':
        future = datetime.datetime.now() + datetime.timedelta(days=1)
        args = future.timetuple()[:3] + (23, 59, 59)
        return datetime.datetime(*args)
    elif text == 'today':
        return datetime.datetime(*datetime.datetime.today().timetuple()[:3])
    elif text == 'now':
        return datetime.datetime.now()
    elif text == 'yesterday':
        past = datetime.datetime.now() - datetime.timedelta(days=1)
        return datetime.datetime(*past.timetuple()[:3])
    else:
        days = 0
        matched = re.match(
            r'^((?P<weeks>\d+) ?w(eeks?)?)? ?((?P<days>\d+) ?d(ays?)?)?$', text)
        if matched:
            groupdict = matched.groupdict()
            if groupdict['days']:
                days += int(matched.groupdict()['days'])
            if groupdict['weeks']:
                days += int(matched.groupdict()['weeks']) * 7
            past = datetime.datetime.now() - datetime.timedelta(days=days)
            return datetime.datetime(*past.timetuple()[:3])

    raise ValueError('Wrong date: "%s"' % text)


def get_dict_for_attrs(obj, attrs):
    """
    Returns dictionary for each attribute from given ``obj``.
    """
    data = {}
    for attr in attrs:
        data[attr] = getattr(obj, attr)
    return data
