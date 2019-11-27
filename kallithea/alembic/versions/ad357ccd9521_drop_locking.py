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

"""Drop locking

Revision ID: ad357ccd9521
Revises: a020f7044fd6
Create Date: 2019-01-08

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = 'ad357ccd9521'
down_revision = 'a020f7044fd6'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

from kallithea.model.db import Ui


meta = MetaData()


def upgrade():
    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.drop_column('enable_locking')

    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.drop_column('locked')
        batch_op.drop_column('enable_locking')

    meta.bind = op.get_bind()
    ui = Table(Ui.__tablename__, meta, autoload=True)
    ui.delete().where(ui.c.ui_key == 'prechangegroup.push_lock_handling').execute()
    ui.delete().where(ui.c.ui_key == 'preoutgoing.pull_lock_handling').execute()


def downgrade():
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enable_locking', sa.BOOLEAN(), nullable=False, default=False))
        batch_op.add_column(sa.Column('locked', sa.VARCHAR(length=255), nullable=True, default=False))

    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enable_locking', sa.BOOLEAN(), nullable=False, default=False))

    # Note: not restoring hooks
