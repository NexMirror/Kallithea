import re

from kallithea.lib.utils2 import ascii_str, safe_str
from kallithea.lib.vcs.backends.base import BaseWorkdir
from kallithea.lib.vcs.exceptions import BranchDoesNotExistError, RepositoryError


class GitWorkdir(BaseWorkdir):

    def get_branch(self):
        headpath = self.repository._repo.refs.refpath(b'HEAD')
        try:
            content = safe_str(open(headpath, 'rb').read())
            match = re.match(r'^ref: refs/heads/(?P<branch>.+)\n$', content)
            if match:
                return match.groupdict()['branch']
            else:
                raise RepositoryError("Couldn't compute workdir's branch")
        except IOError:
            # Try naive way...
            raise RepositoryError("Couldn't compute workdir's branch")

    def get_changeset(self):
        wk_dir_id = ascii_str(self.repository._repo.refs.as_dict().get(b'HEAD'))
        return self.repository.get_changeset(wk_dir_id)

    def checkout_branch(self, branch=None):
        if branch is None:
            branch = self.repository.DEFAULT_BRANCH_NAME
        if branch not in self.repository.branches:
            raise BranchDoesNotExistError
        self.repository.run_git_command(['checkout', branch])
