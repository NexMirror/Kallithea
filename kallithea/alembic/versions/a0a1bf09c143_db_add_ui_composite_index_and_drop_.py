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

"""db: add Ui composite index and drop UniqueConstraint on Ui.ui_key

Revision ID: a0a1bf09c143
Revises: d7ec25b66e47
Create Date: 2020-03-12 22:41:14.421837

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = 'a0a1bf09c143'
down_revision = 'd7ec25b66e47'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    with op.batch_alter_table('ui', schema=None) as batch_op:
        batch_op.create_index('ui_ui_section_ui_key_idx', ['ui_section', 'ui_key'], unique=False)
        batch_op.drop_constraint('uq_ui_ui_key', type_='unique')


def downgrade():
    with op.batch_alter_table('ui', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_ui_ui_key', ['ui_key'])
        batch_op.drop_index('ui_ui_section_ui_key_idx')
