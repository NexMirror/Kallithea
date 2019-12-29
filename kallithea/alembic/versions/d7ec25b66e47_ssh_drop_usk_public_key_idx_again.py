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

"""ssh: drop usk_public_key_idx again

Revision ID: d7ec25b66e47
Revises: 4851d15bc437
Create Date: 2019-12-29 15:33:10.982003

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = 'd7ec25b66e47'
down_revision = '4851d15bc437'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    meta = sa.MetaData()
    meta.reflect(bind=op.get_bind())

    if any(i.name == 'usk_public_key_idx' for i in meta.tables['user_ssh_keys'].indexes):
        with op.batch_alter_table('user_ssh_keys', schema=None) as batch_op:
            batch_op.drop_index('usk_public_key_idx')


def downgrade():
    pass
