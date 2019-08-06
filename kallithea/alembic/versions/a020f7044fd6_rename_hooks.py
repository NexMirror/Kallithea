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

"""rename hooks

Revision ID: a020f7044fd6
Revises: 9358dc3d6828
Create Date: 2017-11-24 13:35:14.374000

"""

# The following opaque hexadecimal identifiers ("revisions") are used
# by Alembic to track this migration script and its relations to others.
revision = 'a020f7044fd6'
down_revision = '9358dc3d6828'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import MetaData, Table

from kallithea.model.db import Ui


meta = MetaData()


def upgrade():
    meta.bind = op.get_bind()
    ui = Table(Ui.__tablename__, meta, autoload=True)

    ui.update(values={
        'ui_key': 'prechangegroup.push_lock_handling',
        'ui_value': 'python:kallithea.lib.hooks.push_lock_handling',
    }).where(ui.c.ui_key == 'prechangegroup.pre_push').execute()
    ui.update(values={
        'ui_key': 'preoutgoing.pull_lock_handling',
        'ui_value': 'python:kallithea.lib.hooks.pull_lock_handling',
    }).where(ui.c.ui_key == 'preoutgoing.pre_pull').execute()


def downgrade():
    meta.bind = op.get_bind()
    ui = Table(Ui.__tablename__, meta, autoload=True)

    ui.update(values={
        'ui_key': 'prechangegroup.pre_push',
        'ui_value': 'python:kallithea.lib.hooks.pre_push',
    }).where(ui.c.ui_key == 'prechangegroup.push_lock_handling').execute()
    ui.update(values={
        'ui_key': 'preoutgoing.pre_pull',
        'ui_value': 'python:kallithea.lib.hooks.pre_pull',
    }).where(ui.c.ui_key == 'preoutgoing.pull_lock_handling').execute()
