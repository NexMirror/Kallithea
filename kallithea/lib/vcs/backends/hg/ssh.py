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

from mercurial import hg

from kallithea.lib.utils import make_ui
from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.lib.vcs.backends.ssh import BaseSshHandler


try:
    from mercurial.wireprotoserver import sshserver
except ImportError:
    from mercurial.sshserver import sshserver # moved in Mercurial 4.6 (1bf5263fe5cc)



log = logging.getLogger(__name__)


class MercurialSshHandler(BaseSshHandler):
    vcs_type = 'hg'

    @classmethod
    def make(cls, ssh_command_parts):
        r"""
        >>> import shlex

        >>> MercurialSshHandler.make(shlex.split('hg -R "foo bar" serve --stdio')).repo_name
        u'foo bar'
        >>> MercurialSshHandler.make(shlex.split(' hg -R blåbærgrød serve --stdio ')).repo_name
        u'bl\xe5b\xe6rgr\xf8d'
        >>> MercurialSshHandler.make(shlex.split('''hg -R 'foo"bar' serve --stdio''')).repo_name
        u'foo"bar'

        >>> MercurialSshHandler.make(shlex.split('/bin/hg -R "foo" serve --stdio'))
        >>> MercurialSshHandler.make(shlex.split('''hg -R "foo"bar" serve --stdio''')) # ssh-serve will report: Error parsing SSH command "...": invalid syntax
        Traceback (most recent call last):
        ValueError: No closing quotation
        >>> MercurialSshHandler.make(shlex.split('git-upload-pack "/foo"')) # not handled here
        """
        if ssh_command_parts[:2] == ['hg', '-R'] and ssh_command_parts[3:] == ['serve', '--stdio']:
            return cls(safe_unicode(ssh_command_parts[2]))

        return None

    def __init__(self, repo_name):
        self.repo_name = repo_name

    def _serve(self):
        # Note: we want a repo with config based on .hg/hgrc and can thus not use self.db_repo.scm_instance._repo.ui
        baseui = make_ui(repo_path=self.db_repo.repo_full_path)
        if not self.allow_push:
            baseui.setconfig('hooks', 'pretxnopen._ssh_reject', 'python:kallithea.lib.hooks.rejectpush')
            baseui.setconfig('hooks', 'prepushkey._ssh_reject', 'python:kallithea.lib.hooks.rejectpush')

        repo = hg.repository(baseui, safe_str(self.db_repo.repo_full_path))
        log.debug("Starting Mercurial sshserver for %s", self.db_repo.repo_full_path)
        sshserver(baseui, repo).serve_forever()
