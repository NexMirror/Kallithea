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

"""db: migration step after 95c01895c006 failed to add usk_public_key_idx in alembic step b74907136bc1

Revision ID: 4851d15bc437
Revises: 151b4a4e8c48
Create Date: 2019-11-24 02:51:14.029583

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = '4851d15bc437'
down_revision = '151b4a4e8c48'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    pass
    # The following upgrade step turned out to be a bad idea. A later step
    # "d7ec25b66e47_ssh_drop_usk_public_key_idx_again" will remove the index
    # again if it exists ... but we shouldn't even try to create it.

    #meta = sa.MetaData()
    #meta.reflect(bind=op.get_bind())

    #if not any(i.name == 'usk_public_key_idx' for i in meta.tables['user_ssh_keys'].indexes):
    #    with op.batch_alter_table('user_ssh_keys', schema=None) as batch_op:
    #        batch_op.create_index('usk_public_key_idx', ['public_key'], unique=False)


def downgrade():
    meta = sa.MetaData()
    if any(i.name == 'usk_public_key_idx' for i in meta.tables['user_ssh_keys'].indexes):
        with op.batch_alter_table('user_ssh_keys', schema=None) as batch_op:
            batch_op.drop_index('usk_public_key_idx')
