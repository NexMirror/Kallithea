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

"""db: migration step after 93834966ae01 dropped non-nullable inherit_default_permissions

Revision ID: 151b4a4e8c48
Revises: b74907136bc1
Create Date: 2019-11-23 01:37:42.963119

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = '151b4a4e8c48'
down_revision = 'b74907136bc1'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    meta = sa.MetaData()
    meta.reflect(bind=op.get_bind())

    if 'inherit_default_permissions' in meta.tables['users'].columns:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('inherit_default_permissions')

    if 'users_group_inherit_default_permissions' in meta.tables['users_groups'].columns:
        with op.batch_alter_table('users_groups', schema=None) as batch_op:
            batch_op.drop_column('users_group_inherit_default_permissions')


def downgrade():
    with op.batch_alter_table('users_groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('users_group_inherit_default_permissions', sa.BOOLEAN(), nullable=False, default=True))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('inherit_default_permissions', sa.BOOLEAN(), nullable=False, default=True))
