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

"""Create table for ssh keys

Revision ID: b74907136bc1
Revises: a020f7044fd6
Create Date: 2017-04-03 18:54:24.490346

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = 'b74907136bc1'
down_revision = 'ad357ccd9521'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op

from kallithea.model import db


def upgrade():
    op.create_table('user_ssh_keys',
        sa.Column('user_ssh_key_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('public_key', sa.UnicodeText(), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('fingerprint', sa.String(length=255), nullable=False),
        sa.Column('created_on', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name=op.f('fk_user_ssh_keys_user_id')),
        sa.PrimaryKeyConstraint('user_ssh_key_id', name=op.f('pk_user_ssh_keys')),
        sa.UniqueConstraint('fingerprint', name=op.f('uq_user_ssh_keys_fingerprint')),
    )
    with op.batch_alter_table('user_ssh_keys', schema=None) as batch_op:
        batch_op.create_index('usk_fingerprint_idx', ['fingerprint'], unique=False)

    session = sa.orm.session.Session(bind=op.get_bind())
    if not session.query(db.Setting).filter(db.Setting.app_settings_name == 'clone_ssh_tmpl').all():
        setting = db.Setting('clone_ssh_tmpl', db.Repository.DEFAULT_CLONE_SSH, 'unicode')
        session.add(setting)
    session.commit()


def downgrade():
    with op.batch_alter_table('user_ssh_keys', schema=None) as batch_op:
        batch_op.drop_index('usk_fingerprint_idx')
    op.drop_table('user_ssh_keys')
