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

"""Drop SQLAlchemy Migrate support

Revision ID: 9358dc3d6828
Revises:
Create Date: 2016-03-01 15:21:30.896585

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = '9358dc3d6828'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.drop_table('db_migrate_version')


def downgrade():
    raise NotImplementedError('cannot revert to SQLAlchemy Migrate')
