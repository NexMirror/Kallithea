# -*- coding: utf-8 -*-
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
"""
kallithea.model.repo_permission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

repository permission model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 1, 2011
:author: nvinot, marcink
"""

import logging
from kallithea.model import BaseModel
from kallithea.model.db import UserRepoToPerm, UserGroupRepoToPerm, \
    Permission

log = logging.getLogger(__name__)


class RepositoryPermissionModel(BaseModel):

    cls = UserRepoToPerm

    def get_user_permission(self, repository, user):
        repository = self._get_repo(repository)
        user = self._get_user(user)

        return UserRepoToPerm.query() \
                .filter(UserRepoToPerm.user == user) \
                .filter(UserRepoToPerm.repository == repository) \
                .scalar()

    def update_user_permission(self, repository, user, permission):
        permission = Permission.get_by_key(permission)
        current = self.get_user_permission(repository, user)
        if current:
            if not current.permission is permission:
                current.permission = permission
        else:
            p = UserRepoToPerm()
            p.user = user
            p.repository = repository
            p.permission = permission
            self.sa.add(p)

    def delete_user_permission(self, repository, user):
        current = self.get_user_permission(repository, user)
        if current:
            self.sa.delete(current)

    def get_users_group_permission(self, repository, users_group):
        return UserGroupRepoToPerm.query() \
                .filter(UserGroupRepoToPerm.users_group == users_group) \
                .filter(UserGroupRepoToPerm.repository == repository) \
                .scalar()

    def update_users_group_permission(self, repository, users_group,
                                      permission):
        permission = Permission.get_by_key(permission)
        current = self.get_users_group_permission(repository, users_group)
        if current:
            if not current.permission is permission:
                current.permission = permission
        else:
            p = UserGroupRepoToPerm()
            p.users_group = users_group
            p.repository = repository
            p.permission = permission
            self.sa.add(p)

    def delete_users_group_permission(self, repository, users_group):
        current = self.get_users_group_permission(repository, users_group)
        if current:
            self.sa.delete(current)

    def update_or_delete_user_permission(self, repository, user, permission):
        if permission:
            self.update_user_permission(repository, user, permission)
        else:
            self.delete_user_permission(repository, user)

    def update_or_delete_users_group_permission(self, repository, user_group,
                                              permission):
        if permission:
            self.update_users_group_permission(repository, user_group,
                                               permission)
        else:
            self.delete_users_group_permission(repository, user_group)
