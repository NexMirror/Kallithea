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
vcs.backends.ssh
~~~~~~~~~~~~~~~~~

SSH backend for all available SCMs
"""

import datetime
import logging
import sys

from kallithea.lib.auth import AuthUser, HasPermissionAnyMiddleware
from kallithea.lib.utils2 import safe_str, set_hook_environment
from kallithea.model.db import Repository, User, UserSshKeys
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class BaseSshHandler(object):
    # Protocol for setting properties:
    # Set by sub class:
    #   vcs_type: 'hg' or 'git'
    # Set by make() / __init__():
    #   repo_name: requested repo name - only validated by serve()
    # Set by serve() - must not be accessed before:
    #   db_repo: repository db object
    #   authuser: user that has been authenticated - like request.authuser ... which isn't used here
    #   allow_push: false for read-only access to the repo

    # Set defaults, in case .exit should be called early
    vcs_type = None
    repo_name = None

    @staticmethod
    def make(ssh_command):
        """Factory function. Given a command as invoked over SSH (and preserved
        in SSH_ORIGINAL_COMMAND when run as authorized_keys command), return a
        handler if the command looks ok, else return None.
        """
        raise NotImplementedError

    def serve(self, user_id, key_id, client_ip):
        """Verify basic sanity of the repository, and that the user is
        valid and has access - then serve the native VCS protocol for
        repository access."""
        dbuser = User.get(user_id)
        if dbuser is None:
            self.exit('User %r not found' % user_id)
        self.authuser = AuthUser.make(dbuser=dbuser, ip_addr=client_ip)
        log.info('Authorized user %s from SSH %s trusting user id %s and key id %s for %r', dbuser, client_ip, user_id, key_id, self.repo_name)
        if self.authuser is None: # not ok ... but already kind of authenticated by SSH ... but not really not authorized ...
            self.exit('User %s from %s cannot be authorized' % (dbuser.username, client_ip))

        ssh_key = UserSshKeys.get(key_id)
        if ssh_key is None:
            self.exit('SSH key %r not found' % key_id)
        ssh_key.last_seen = datetime.datetime.now()
        Session().commit()

        if HasPermissionAnyMiddleware('repository.write',
                                      'repository.admin')(self.authuser, self.repo_name):
            self.allow_push = True
        elif HasPermissionAnyMiddleware('repository.read')(self.authuser, self.repo_name):
            self.allow_push = False
        else:
            self.exit('Access to %r denied' % safe_str(self.repo_name))

        self.db_repo = Repository.get_by_repo_name(self.repo_name)
        if self.db_repo is None:
            self.exit("Repository '%s' not found" % self.repo_name)
        assert self.db_repo.repo_name == self.repo_name

        # Set global hook environment up for 'push' actions.
        # If pull actions should be served, the actual hook invocation will be
        # hardcoded to 'pull' when log_pull_action is invoked (directly on Git,
        # or through the Mercurial 'outgoing' hook).
        # For push actions, the action in global hook environment is used (in
        # handle_git_post_receive when it is called as Git post-receive hook,
        # or in log_push_action through the Mercurial 'changegroup' hook).
        set_hook_environment(self.authuser.username, client_ip, self.repo_name, self.vcs_type, 'push')
        return self._serve()

    def _serve(self):
        """Serve the native protocol for repository access."""
        raise NotImplementedError

    def exit(self, error):
        log.info('abort serving %s %s: %s', self.vcs_type, self.repo_name, error)
        sys.stderr.write('abort: %s\n' % error)
        sys.exit(1)
