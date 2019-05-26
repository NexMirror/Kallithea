"""
Mercurial libs compatibility
"""

import mercurial
from mercurial import demandimport
# patch demandimport, due to bug in mercurial when it always triggers demandimport.enable()
demandimport.enable = lambda *args, **kwargs: 1
from mercurial import archival, merge as hg_merge, patch, ui
from mercurial import discovery
from mercurial import localrepo
from mercurial import unionrepo
from mercurial import scmutil
from mercurial import config
from mercurial.tags import tag
from mercurial import httppeer
from mercurial import sshpeer
from mercurial import obsutil
from mercurial.commands import clone, nullid, pull
from mercurial.context import memctx, memfilectx
from mercurial.error import RepoError, RepoLookupError, Abort
from mercurial.hgweb import hgweb_mod
from mercurial.hgweb.common import get_contact
from mercurial.match import match, exact as match_exact
from mercurial.mdiff import diffopts
from mercurial.node import hex
from mercurial.encoding import tolocal
from mercurial.discovery import findcommonoutgoing
from mercurial.hg import peer
from mercurial.util import url as hg_url
from mercurial.scmutil import revrange
from mercurial.node import nullrev
from mercurial.url import httpbasicauthhandler, httpdigestauthhandler


# workaround for 3.3 94ac64bcf6fe and not calling largefiles reposetup correctly
localrepo.localrepository._lfstatuswriters = [lambda *msg, **opts: None]
# 3.5 7699d3212994 added the invariant that repo.lfstatus must exist before hitting overridearchive
localrepo.localrepository.lfstatus = False

# Mercurial 5.0 550a172a603b renamed memfilectx argument `copied` to `copysource`
import inspect
if inspect.getargspec(memfilectx.__init__).args[7] != 'copysource':
    assert inspect.getargspec(memfilectx.__init__).args[7] == 'copied', inspect.getargspec(memfilectx.__init__).args
    __org_memfilectx_ = memfilectx
    memfilectx = lambda repo, changectx, path, data, islink=False, isexec=False, copysource=None: \
        __org_memfilectx_(repo, changectx, path, data, islink=islink, isexec=isexec, copied=copysource)

# Mercurial 5.0 dropped exact argument for match in 635a12c53ea6, and 0531dff73d0b made the exact function stable with a single parameter
if inspect.getargspec(match_exact).args[0] != 'files':
    match_exact = lambda path: match(None, '', [path], exact=True)
