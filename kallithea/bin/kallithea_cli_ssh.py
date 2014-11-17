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

import click
import kallithea.bin.kallithea_cli_base as cli_base

import os
import sys
import re
import logging
import shlex

import kallithea
from kallithea.lib.utils2 import str2bool
from kallithea.lib.vcs.backends.git.ssh import GitSshHandler
from kallithea.lib.vcs.backends.hg.ssh import MercurialSshHandler
from kallithea.model.ssh_key import SshKeyModel

log = logging.getLogger(__name__)


@cli_base.register_command(config_file_initialize_app=True, hidden=True)
@click.argument('user-id', type=click.INT, required=True)
@click.argument('key-id', type=click.INT, required=True)
def ssh_serve(user_id, key_id):
    """Serve SSH repository protocol access.

    The trusted command that is invoked from .ssh/authorized_keys to serve SSH
    protocol access. The access will be granted as the specified user ID, and
    logged as using the specified key ID.
    """
    ssh_enabled = kallithea.CONFIG.get('ssh_enabled', False)
    if not str2bool(ssh_enabled):
        sys.stderr.write("SSH access is disabled.\n")
        return sys.exit(1)

    ssh_original_command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    connection = re.search('^([\d\.]+)', os.environ.get('SSH_CONNECTION', ''))
    client_ip = connection.group(1) if connection else '0.0.0.0'
    log.debug('ssh-serve was invoked for SSH command %r from %s', ssh_original_command, client_ip)

    if not ssh_original_command:
        if os.environ.get('SSH_CONNECTION'):
            sys.stderr.write("'kallithea-cli ssh-serve' can only provide protocol access over SSH. Interactive SSH login for this user is disabled.\n")
        else:
            sys.stderr.write("'kallithea-cli ssh-serve' cannot be called directly. It must be specified as command in an SSH authorized_keys file.\n")
        return sys.exit(1)

    try:
        ssh_command_parts = shlex.split(ssh_original_command)
    except ValueError as e:
        sys.stderr.write('Error parsing SSH command %r: %s\n' % (ssh_original_command, e))
        sys.exit(1)
    for VcsHandler in [MercurialSshHandler, GitSshHandler]:
        vcs_handler = VcsHandler.make(ssh_command_parts)
        if vcs_handler is not None:
            vcs_handler.serve(user_id, key_id, client_ip)
            assert False # serve is written so it never will terminate

    sys.stderr.write("This account can only be used for repository access. SSH command %r is not supported.\n" % ssh_original_command)
    sys.exit(1)


@cli_base.register_command(config_file_initialize_app=True)
def ssh_update_authorized_keys():
    """Update .ssh/authorized_keys file.

    The file is usually maintained automatically, but this command will also re-write it.
    """

    SshKeyModel().write_authorized_keys()
