import logging

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.model import meta
from kallithea.lib.dbmigrate.versions import _reset_base, notify

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """
    Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """
    _reset_base(migrate_engine)
    from kallithea.lib.dbmigrate.schema import db_2_0_2

    # issue fixups
    fixups(db_2_0_2, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('fixing new schema for landing_rev')

    for repo in models.Repository.get_all():
        print u'repo %s old landing rev is: %s' % (repo, repo.landing_rev)
        _rev = repo.landing_rev[1]
        _rev_type = 'rev'  # default

        if _rev in ['default', 'master']:
            _rev_type = 'branch'
        elif _rev in ['tip']:
            _rev_type = 'rev'
        else:
            try:
                scm = repo.scm_instance
                if scm:
                    known_branches = scm.branches.keys()
                    known_bookmarks = scm.bookmarks.keys()
                    if _rev in known_branches:
                        _rev_type = 'branch'
                    elif _rev in known_bookmarks:
                        _rev_type = 'book'
            except Exception, e:
                print e
                print 'continue...'
                #we don't want any error to break the process
                pass

        _new_landing_rev = '%s:%s' % (_rev_type, _rev)
        print u'setting to %s' % _new_landing_rev
        repo.landing_rev = _new_landing_rev
        _SESSION().add(repo)
        _SESSION().commit()
