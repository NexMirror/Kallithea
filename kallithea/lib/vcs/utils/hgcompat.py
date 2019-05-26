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
from mercurial.match import match
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
