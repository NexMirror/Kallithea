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
kallithea.model.ssh_key
~~~~~~~~~~~~~~~~~~~~~~~

SSH key model for Kallithea

"""

import errno
import logging
import os
import stat
import tempfile

from tg import config
from tg.i18n import ugettext as _

from kallithea.lib import ssh
from kallithea.lib.utils2 import safe_str, str2bool
from kallithea.lib.vcs.exceptions import RepositoryError
from kallithea.model.db import User, UserSshKeys
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class SshKeyModelException(RepositoryError):
    """Exception raised by SshKeyModel methods to report errors"""


class SshKeyModel(object):

    def create(self, user, description, public_key):
        """
        :param user: user or user_id
        :param description: description of SshKey
        :param publickey: public key text
        Will raise SshKeyModelException on errors
        """
        try:
            keytype, pub, comment = ssh.parse_pub_key(public_key)
        except ssh.SshKeyParseError as e:
            raise SshKeyModelException(_('SSH key %r is invalid: %s') % (safe_str(public_key), e.message))
        if not description.strip():
            description = comment.strip()

        user = User.guess_instance(user)

        new_ssh_key = UserSshKeys()
        new_ssh_key.user_id = user.user_id
        new_ssh_key.description = description
        new_ssh_key.public_key = public_key

        for ssh_key in UserSshKeys.query().filter(UserSshKeys.fingerprint == new_ssh_key.fingerprint).all():
            raise SshKeyModelException(_('SSH key %s is already used by %s') %
                                       (new_ssh_key.fingerprint, ssh_key.user.username))

        Session().add(new_ssh_key)

        return new_ssh_key

    def delete(self, fingerprint, user):
        """
        Deletes ssh key with given fingerprint for the given user.
        Will raise SshKeyModelException on errors
        """
        ssh_key = UserSshKeys.query().filter(UserSshKeys.fingerprint == fingerprint)

        user = User.guess_instance(user)
        ssh_key = ssh_key.filter(UserSshKeys.user_id == user.user_id)

        ssh_key = ssh_key.scalar()
        if ssh_key is None:
            raise SshKeyModelException(_('SSH key with fingerprint %r found') % safe_str(fingerprint))
        Session().delete(ssh_key)

    def get_ssh_keys(self, user):
        user = User.guess_instance(user)
        user_ssh_keys = UserSshKeys.query() \
            .filter(UserSshKeys.user_id == user.user_id).all()
        return user_ssh_keys

    def write_authorized_keys(self):
        if not str2bool(config.get('ssh_enabled', False)):
            log.error("Will not write SSH authorized_keys file - ssh_enabled is not configured")
            return
        authorized_keys = config.get('ssh_authorized_keys')
        kallithea_cli_path = config.get('kallithea_cli_path', 'kallithea-cli')
        if not authorized_keys:
            log.error('Cannot write SSH authorized_keys file - ssh_authorized_keys is not configured')
            return
        log.info('Writing %s', authorized_keys)

        authorized_keys_dir = os.path.dirname(authorized_keys)
        try:
            os.makedirs(authorized_keys_dir)
            os.chmod(authorized_keys_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR) # ~/.ssh/ must be 0700
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
        # Now, test that the directory is or was created in a readable way by previous.
        if not (os.path.isdir(authorized_keys_dir) and
                os.access(authorized_keys_dir, os.W_OK)):
            raise SshKeyModelException("Directory of authorized_keys cannot be written to so authorized_keys file %s cannot be written" % (authorized_keys))

        # Make sure we don't overwrite a key file with important content
        if os.path.exists(authorized_keys):
            with open(authorized_keys) as f:
                for l in f:
                    if not l.strip() or l.startswith('#'):
                        pass # accept empty lines and comments
                    elif ssh.SSH_OPTIONS in l and ' ssh-serve ' in l:
                        pass # Kallithea entries are ok to overwrite
                    else:
                        raise SshKeyModelException("Safety check failed, found %r line in %s - please remove it if Kallithea should manage the file" % (l.strip(), authorized_keys))

        fh, tmp_authorized_keys = tempfile.mkstemp('.authorized_keys', dir=os.path.dirname(authorized_keys))
        with os.fdopen(fh, 'w') as f:
            f.write("# WARNING: This .ssh/authorized_keys file is managed by Kallithea. Manual editing or adding new entries will make Kallithea back off.\n")
            for key in UserSshKeys.query().join(UserSshKeys.user).filter(User.active == True):
                f.write(ssh.authorized_keys_line(kallithea_cli_path, config['__file__'], key))
        os.chmod(tmp_authorized_keys, stat.S_IRUSR | stat.S_IWUSR)
        # This preliminary remove is needed for Windows, not for Unix.
        # TODO In Python 3, the remove+rename sequence below should become os.replace.
        if os.path.exists(authorized_keys):
            os.remove(authorized_keys)
        os.rename(tmp_authorized_keys, authorized_keys)
