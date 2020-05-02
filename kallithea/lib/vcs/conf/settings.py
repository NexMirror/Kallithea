from kallithea.lib.vcs.utils import aslist


# list of default encoding used in safe_str/safe_bytes methods
DEFAULT_ENCODINGS = aslist('utf-8')

# path to git executable run by run_git_command function
GIT_EXECUTABLE_PATH = 'git'
# can be also --branches --tags
GIT_REV_FILTER = '--all'

BACKENDS = {
    'hg': 'kallithea.lib.vcs.backends.hg.MercurialRepository',
    'git': 'kallithea.lib.vcs.backends.git.GitRepository',
}

ARCHIVE_SPECS = {
    'tar': ('application/x-tar', '.tar'),
    'tbz2': ('application/x-bzip2', '.tar.bz2'),
    'tgz': ('application/x-gzip', '.tar.gz'),
    'zip': ('application/zip', '.zip'),
}
