# -*- coding: utf-8 -*-
"""
    kallithea.lib.ssh
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :created_on: Dec 10, 2012
    :author: ir4y
    :copyright: (C) 2012 Ilya Beda <ir4y.ix@gmail.com>
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

import binascii
import logging
import re

from tg.i18n import ugettext as _


log = logging.getLogger(__name__)


class SshKeyParseError(Exception):
    """Exception raised by parse_pub_key"""


def parse_pub_key(ssh_key):
    r"""Parse SSH public key string, raise SshKeyParseError or return decoded keytype, data and comment

    >>> getfixture('doctest_mock_ugettext')
    >>> parse_pub_key('')
    Traceback (most recent call last):
    ...
    SshKeyParseError: SSH key is missing
    >>> parse_pub_key('''AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ''')
    Traceback (most recent call last):
    ...
    SshKeyParseError: Incorrect SSH key - it must have both a key type and a base64 part, like 'ssh-rsa ASRNeaZu4FA...xlJp='
    >>> parse_pub_key('''abc AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ''')
    Traceback (most recent call last):
    ...
    SshKeyParseError: Incorrect SSH key - it must start with 'ssh-(rsa|dss|ed25519)'
    >>> parse_pub_key('''ssh-rsa  AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ''')
    Traceback (most recent call last):
    ...
    SshKeyParseError: Incorrect SSH key - failed to decode base64 part 'AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ'
    >>> parse_pub_key('''ssh-rsa  AAAAB2NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ==''')
    Traceback (most recent call last):
    ...
    SshKeyParseError: Incorrect SSH key - base64 part is not 'ssh-rsa' as claimed but 'csh-rsa'
    >>> parse_pub_key('''ssh-rsa  AAAAB3NzaC1yc2EAAAA'LVGhpcyBpcyBmYWtlIQ''')
    Traceback (most recent call last):
    ...
    SshKeyParseError: Incorrect SSH key - unexpected characters in base64 part "AAAAB3NzaC1yc2EAAAA'LVGhpcyBpcyBmYWtlIQ"
    >>> parse_pub_key(''' ssh-rsa  AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ== and a comment
    ... ''')
    ('ssh-rsa', '\x00\x00\x00\x07ssh-rsa\x00\x00\x00\x0bThis is fake!', 'and a comment\n')
    >>> parse_pub_key('''ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP1NA2kBQIKe74afUXmIWD9ByDYQJqUwW44Y4gJOBRuo''')
    ('ssh-ed25519', '\x00\x00\x00\x0bssh-ed25519\x00\x00\x00 \xfdM\x03i\x01@\x82\x9e\xef\x86\x9fQy\x88X?A\xc86\x10&\xa50[\x8e\x18\xe2\x02N\x05\x1b\xa8', '')
    """
    if not ssh_key:
        raise SshKeyParseError(_("SSH key is missing"))

    parts = ssh_key.split(None, 2)
    if len(parts) < 2:
        raise SshKeyParseError(_("Incorrect SSH key - it must have both a key type and a base64 part, like 'ssh-rsa ASRNeaZu4FA...xlJp='"))

    keytype, keyvalue, comment = (parts + [''])[:3]
    if keytype not in ('ssh-rsa', 'ssh-dss', 'ssh-ed25519'):
        raise SshKeyParseError(_("Incorrect SSH key - it must start with 'ssh-(rsa|dss|ed25519)'"))

    if re.search(r'[^a-zA-Z0-9+/=]', keyvalue):
        raise SshKeyParseError(_("Incorrect SSH key - unexpected characters in base64 part %r") % keyvalue)

    try:
        decoded = keyvalue.decode('base64')
    except binascii.Error:
        raise SshKeyParseError(_("Incorrect SSH key - failed to decode base64 part %r") % keyvalue)

    if not decoded.startswith('\x00\x00\x00' + chr(len(keytype)) + str(keytype) + '\x00'):
        raise SshKeyParseError(_("Incorrect SSH key - base64 part is not %r as claimed but %r") % (str(keytype), str(decoded[4:].split('\0', 1)[0])))

    return keytype, decoded, comment


SSH_OPTIONS = 'no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding'


def _safe_check(s, rec = re.compile('^[a-zA-Z0-9+/]+={0,2}$')):
    """Return true if s really has the right content for base64 encoding and only contains safe characters
    >>> _safe_check('asdf')
    True
    >>> _safe_check('as df')
    False
    >>> _safe_check('AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ==')
    True
    """
    return rec.match(s) is not None


def authorized_keys_line(kallithea_cli_path, config_file, key):
    """
    Return a line as it would appear in .authorized_keys

    >>> from kallithea.model.db import UserSshKeys, User
    >>> user = User(user_id=7, username='uu')
    >>> key = UserSshKeys(user_ssh_key_id=17, user=user, description='test key')
    >>> key.public_key='''ssh-rsa  AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ== and a comment'''
    >>> authorized_keys_line('/srv/kallithea/venv/bin/kallithea-cli', '/srv/kallithea/my.ini', key)
    'no-pty,no-port-forwarding,no-X11-forwarding,no-agent-forwarding,command="/srv/kallithea/venv/bin/kallithea-cli ssh-serve -c /srv/kallithea/my.ini 7 17" ssh-rsa AAAAB3NzaC1yc2EAAAALVGhpcyBpcyBmYWtlIQ==\\n'
    """
    try:
        keytype, decoded, comment = parse_pub_key(key.public_key)
    except SshKeyParseError:
        return '# Invalid Kallithea SSH key: %s %s\n' % (key.user.user_id, key.user_ssh_key_id)
    mimekey = decoded.encode('base64').replace('\n', '')
    if not _safe_check(mimekey):
        return '# Invalid Kallithea SSH key - bad base64 encoding: %s %s\n' % (key.user.user_id, key.user_ssh_key_id)
    return '%s,command="%s ssh-serve -c %s %s %s" %s %s\n' % (
        SSH_OPTIONS, kallithea_cli_path, config_file,
        key.user.user_id, key.user_ssh_key_id,
        keytype, mimekey)
