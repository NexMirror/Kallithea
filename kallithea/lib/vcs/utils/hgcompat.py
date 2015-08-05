"""
Mercurial libs compatibility
"""

import mercurial
import mercurial.demandimport
## patch demandimport, due to bug in mercurial when it always triggers demandimport.enable()
mercurial.demandimport.enable = lambda *args, **kwargs: 1
from mercurial import archival, merge as hg_merge, patch, ui
from mercurial import discovery
from mercurial import localrepo
from mercurial import unionrepo
from mercurial import scmutil
from mercurial import config
from mercurial.commands import clone, nullid, pull
from mercurial.context import memctx, memfilectx
from mercurial.error import RepoError, RepoLookupError, Abort
from mercurial.hgweb import hgweb_mod
from mercurial.hgweb.common import get_contact
from mercurial.localrepo import localrepository
from mercurial.match import match
from mercurial.mdiff import diffopts
from mercurial.node import hex
from mercurial.encoding import tolocal
from mercurial.discovery import findcommonoutgoing
from mercurial.hg import peer
from mercurial.httppeer import httppeer
from mercurial.sshpeer import sshpeer
from mercurial.util import url as hg_url
from mercurial.scmutil import revrange
from mercurial.node import nullrev

# those authhandlers are patched for python 2.6.5 bug an
# infinite looping when given invalid resources
from mercurial.url import httpbasicauthhandler, httpdigestauthhandler

import inspect
# Mercurial 3.1 503bb3af70fe
if inspect.getargspec(memfilectx.__init__).args[1] != 'repo':
    _org__init__=memfilectx.__init__
    def _memfilectx__init__(self, repo, *a, **b):
        return _org__init__(self, *a, **b)
    memfilectx.__init__ = _memfilectx__init__

# workaround for 3.3 94ac64bcf6fe and not calling largefiles reposetup correctly
localrepository._lfstatuswriters = [lambda *msg, **opts: None]
# 3.5 7699d3212994 added the invariant that repo.lfstatus must exist before hitting overridearchive
localrepository.lfstatus = False
