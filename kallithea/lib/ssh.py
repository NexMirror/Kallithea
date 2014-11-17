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

import logging
import binascii
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
    SshKeyParseError: Incorrect SSH key - it must have both a key type and a base64 part
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
    """
    if not ssh_key:
        raise SshKeyParseError(_("SSH key is missing"))

    parts = ssh_key.split(None, 2)
    if len(parts) < 2:
        raise SshKeyParseError(_("Incorrect SSH key - it must have both a key type and a base64 part"))

    keytype, keyvalue, comment = (parts + [''])[:3]
    if keytype not in ('ssh-rsa', 'ssh-dss', 'ssh-ed25519'):
        raise SshKeyParseError(_("Incorrect SSH key - it must start with 'ssh-(rsa|dss|ed25519)'"))

    if re.search(r'[^a-zA-Z0-9+/=]', keyvalue):
        raise SshKeyParseError(_("Incorrect SSH key - unexpected characters in base64 part %r") % keyvalue)

    try:
        decoded = keyvalue.decode('base64')
    except binascii.Error:
        raise SshKeyParseError(_("Incorrect SSH key - failed to decode base64 part %r") % keyvalue)

    if not decoded.startswith('\x00\x00\x00\x07' + str(keytype) + '\x00'):
        raise SshKeyParseError(_("Incorrect SSH key - base64 part is not %r as claimed but %r") % (str(keytype), str(decoded[4:].split('\0', 1)[0])))

    return keytype, decoded, comment
