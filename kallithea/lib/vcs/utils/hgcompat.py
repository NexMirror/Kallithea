"""
Mercurial libs compatibility
"""

import mercurial
from mercurial import archival, config, demandimport, discovery, httppeer, localrepo
from mercurial import merge as hg_merge
from mercurial import obsutil, patch, scmutil, sshpeer, ui, unionrepo
from mercurial.commands import clone, nullid, pull
from mercurial.context import memctx, memfilectx
from mercurial.discovery import findcommonoutgoing
from mercurial.encoding import tolocal
from mercurial.error import Abort, RepoError, RepoLookupError
from mercurial.hg import peer
from mercurial.hgweb import hgweb_mod
from mercurial.hgweb.common import get_contact
from mercurial.match import exact as match_exact
from mercurial.match import match
from mercurial.mdiff import diffopts
from mercurial.node import hex, nullrev
from mercurial.scmutil import revrange
from mercurial.tags import tag
from mercurial.url import httpbasicauthhandler, httpdigestauthhandler
from mercurial.util import url as hg_url


# workaround for 3.3 94ac64bcf6fe and not calling largefiles reposetup correctly, and test_archival failing
localrepo.localrepository._lfstatuswriters = [lambda *msg, **opts: None]
# 3.5 7699d3212994 added the invariant that repo.lfstatus must exist before hitting overridearchive
localrepo.localrepository.lfstatus = False
