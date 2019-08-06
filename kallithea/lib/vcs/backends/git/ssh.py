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

import logging
import os

from kallithea.lib.hooks import log_pull_action
from kallithea.lib.utils import make_ui
from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.lib.vcs.backends.ssh import BaseSshHandler


log = logging.getLogger(__name__)


class GitSshHandler(BaseSshHandler):
    vcs_type = 'git'

    @classmethod
    def make(cls, ssh_command_parts):
        r"""
        >>> import shlex

        >>> GitSshHandler.make(shlex.split("git-upload-pack '/foo bar'")).repo_name
        u'foo bar'
        >>> GitSshHandler.make(shlex.split("git-upload-pack '/foo bar'")).verb
        'git-upload-pack'
        >>> GitSshHandler.make(shlex.split(" git-upload-pack /blåbærgrød ")).repo_name # might not be necessary to support no quoting ... but we can
        u'bl\xe5b\xe6rgr\xf8d'
        >>> GitSshHandler.make(shlex.split('''git-upload-pack "/foo'bar"''')).repo_name
        u"foo'bar"
        >>> GitSshHandler.make(shlex.split("git-receive-pack '/foo'")).repo_name
        u'foo'
        >>> GitSshHandler.make(shlex.split("git-receive-pack '/foo'")).verb
        'git-receive-pack'

        >>> GitSshHandler.make(shlex.split("/bin/git-upload-pack '/foo'")) # ssh-serve will report 'SSH command %r is not supported'
        >>> GitSshHandler.make(shlex.split('''git-upload-pack /foo bar''')) # ssh-serve will report 'SSH command %r is not supported'
        >>> shlex.split("git-upload-pack '/foo'bar' x") # ssh-serve will report: Error parsing SSH command "...": No closing quotation
        Traceback (most recent call last):
        ValueError: No closing quotation
        >>> GitSshHandler.make(shlex.split('hg -R foo serve --stdio')) # not handled here
        """
        if (len(ssh_command_parts) == 2 and
            ssh_command_parts[0] in ['git-upload-pack', 'git-receive-pack'] and
            ssh_command_parts[1].startswith('/')
        ):
            return cls(safe_unicode(ssh_command_parts[1][1:]), ssh_command_parts[0])

        return None

    def __init__(self, repo_name, verb):
        self.repo_name = repo_name
        self.verb = verb

    def _serve(self):
        if self.verb == 'git-upload-pack': # action 'pull'
            # base class called set_hook_environment - action is hardcoded to 'pull'
            log_pull_action(ui=make_ui(), repo=self.db_repo.scm_instance._repo)
        else: # probably verb 'git-receive-pack', action 'push'
            if not self.allow_push:
                self.exit('Push access to %r denied' % safe_str(self.repo_name))
            # Note: push logging is handled by Git post-receive hook

        # git shell is not a real shell but use shell inspired quoting *inside* the argument.
        # Per https://github.com/git/git/blob/v2.22.0/quote.c#L12 :
        # The path must be "'" quoted, but "'" and "!" must exit the quoting and be "\" escaped
        quoted_abspath = "'%s'" % self.db_repo.repo_full_path.replace("'", r"'\''").replace("!", r"'\!'")
        newcmd = ['git', 'shell', '-c', "%s %s" % (self.verb, quoted_abspath)]
        log.debug('Serving: %s', newcmd)
        os.execvp(newcmd[0], newcmd)
        self.exit("Failed to exec 'git' as %s" % newcmd)
