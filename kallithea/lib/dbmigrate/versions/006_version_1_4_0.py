import logging
import datetime

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.lib.dbmigrate.versions import _reset_base

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """
    Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """

    #==========================================================================
    # USEREMAILMAP
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_4_0 import UserEmailMap
    tbl = UserEmailMap.__table__
    tbl.create()
    #==========================================================================
    # PULL REQUEST
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_4_0 import PullRequest
    tbl = PullRequest.__table__
    tbl.create()

    #==========================================================================
    # PULL REQUEST REVIEWERS
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_4_0 import PullRequestReviewers
    tbl = PullRequestReviewers.__table__
    tbl.create()

    #==========================================================================
    # CHANGESET STATUS
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_4_0 import ChangesetStatus
    tbl = ChangesetStatus.__table__
    tbl.create()

    _reset_base(migrate_engine)

    #==========================================================================
    # USERS TABLE
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import User
    tbl = User.__table__

    # change column name -> firstname
    col = User.__table__.columns.name
    col.alter(index=Index('u_username_idx', 'username'))
    col.alter(index=Index('u_email_idx', 'email'))
    col.alter(name="firstname", table=tbl)

    # add inherit_default_permission column
    inherit_default_permissions = Column("inherit_default_permissions",
                                         Boolean(), nullable=True, unique=None,
                                         default=True)
    inherit_default_permissions.create(table=tbl)
    inherit_default_permissions.alter(nullable=False, default=True, table=tbl)

    #==========================================================================
    # USERS GROUP TABLE
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import UserGroup
    tbl = UserGroup.__table__
    # add inherit_default_permission column
    gr_inherit_default_permissions = Column(
                                    "users_group_inherit_default_permissions",
                                    Boolean(), nullable=True, unique=None,
                                    default=True)
    gr_inherit_default_permissions.create(table=tbl)
    gr_inherit_default_permissions.alter(nullable=False, default=True, table=tbl)

    #==========================================================================
    # REPOSITORIES
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import Repository
    tbl = Repository.__table__

    # add enable locking column
    enable_locking = Column("enable_locking", Boolean(), nullable=True,
                            unique=None, default=False)
    enable_locking.create(table=tbl)
    enable_locking.alter(nullable=False, default=False, table=tbl)

    # add locked column
    _locked = Column("locked", String(255), nullable=True, unique=False,
                     default=None)
    _locked.create(table=tbl)

    #add langing revision column
    landing_rev = Column("landing_revision", String(255), nullable=True,
                         unique=False, default='tip')
    landing_rev.create(table=tbl)
    landing_rev.alter(nullable=False, default='tip', table=tbl)

    #==========================================================================
    # GROUPS
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import RepoGroup
    tbl = RepoGroup.__table__

    # add enable locking column
    enable_locking = Column("enable_locking", Boolean(), nullable=True,
                            unique=None, default=False)
    enable_locking.create(table=tbl)
    enable_locking.alter(nullable=False, default=False)

    #==========================================================================
    # CACHE INVALIDATION
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import CacheInvalidation
    tbl = CacheInvalidation.__table__

    # add INDEX for cache keys
    col = CacheInvalidation.__table__.columns.cache_key
    col.alter(index=Index('key_idx', 'cache_key'))

    #==========================================================================
    # NOTIFICATION
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import Notification
    tbl = Notification.__table__

    # add index for notification type
    col = Notification.__table__.columns.type
    col.alter(index=Index('notification_type_idx', 'type'),)

    #==========================================================================
    # CHANGESET_COMMENTS
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import ChangesetComment

    tbl = ChangesetComment.__table__
    col = ChangesetComment.__table__.columns.revision

    # add index for revisions
    col.alter(index=Index('cc_revision_idx', 'revision'),)

    # add hl_lines column
    hl_lines = Column('hl_lines', Unicode(512), nullable=True)
    hl_lines.create(table=tbl)

    # add created_on column
    created_on = Column('created_on', DateTime(timezone=False), nullable=True,
                        default=datetime.datetime.now)
    created_on.create(table=tbl)
    created_on.alter(nullable=False, default=datetime.datetime.now)

    modified_at = Column('modified_at', DateTime(timezone=False), nullable=False,
                         default=datetime.datetime.now)
    modified_at.alter(type=DateTime(timezone=False), table=tbl)

    # add FK to pull_request
    pull_request_id = Column("pull_request_id", Integer(),
                             ForeignKey('pull_requests.pull_request_id'),
                             nullable=True)
    pull_request_id.create(table=tbl)
    _reset_base(migrate_engine)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
