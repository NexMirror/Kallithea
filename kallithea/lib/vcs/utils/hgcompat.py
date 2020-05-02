"""
Mercurial libs compatibility
"""

import mercurial.encoding
import mercurial.localrepo


def monkey_do():
    """Apply some Mercurial monkey patching"""
    # workaround for 3.3 94ac64bcf6fe and not calling largefiles reposetup correctly, and test_archival failing
    mercurial.localrepo.localrepository._lfstatuswriters = [lambda *msg, **opts: None]
    # 3.5 7699d3212994 added the invariant that repo.lfstatus must exist before hitting overridearchive
    mercurial.localrepo.localrepository.lfstatus = False

    # Minimize potential impact from custom configuration
    mercurial.encoding.environ[b'HGPLAIN'] = b'1'
