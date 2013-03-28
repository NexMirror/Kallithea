# -*- coding: utf-8 -*-
"""
    rhodecode.model.permission
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    permissions model for RhodeCode

    :created_on: Aug 20, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
    :license: GPLv3, see COPYING for more details.
"""
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

import logging
import traceback

from sqlalchemy.exc import DatabaseError

from rhodecode.lib.caching_query import FromCache

from rhodecode.model import BaseModel
from rhodecode.model.db import User, Permission, UserToPerm, UserRepoToPerm,\
    UserRepoGroupToPerm

log = logging.getLogger(__name__)


class PermissionModel(BaseModel):
    """
    Permissions model for RhodeCode
    """

    cls = Permission

    def get_permission(self, permission_id, cache=False):
        """
        Get's permissions by id

        :param permission_id: id of permission to get from database
        :param cache: use Cache for this query
        """
        perm = self.sa.query(Permission)
        if cache:
            perm = perm.options(FromCache("sql_cache_short",
                                          "get_permission_%s" % permission_id))
        return perm.get(permission_id)

    def get_permission_by_name(self, name, cache=False):
        """
        Get's permissions by given name

        :param name: name to fetch
        :param cache: Use cache for this query
        """
        perm = self.sa.query(Permission)\
            .filter(Permission.permission_name == name)
        if cache:
            perm = perm.options(FromCache("sql_cache_short",
                                          "get_permission_%s" % name))
        return perm.scalar()

    def update(self, form_result):
        perm_user = self.sa.query(User)\
                        .filter(User.username ==
                                form_result['perm_user_name']).scalar()
        u2p = self.sa.query(UserToPerm).filter(UserToPerm.user ==
                                               perm_user).all()
        if len(u2p) != len(User.DEFAULT_PERMISSIONS):
            raise Exception('Defined: %s should be %s  permissions for default'
                            ' user. This should not happen please verify'
                            ' your database' % (len(u2p), len(User.DEFAULT_PERMISSIONS)))

        try:
            # stage 1 change defaults
            for p in u2p:
                if p.permission.permission_name.startswith('repository.'):
                    p.permission = self.get_permission_by_name(
                                       form_result['default_repo_perm'])
                    self.sa.add(p)

                elif p.permission.permission_name.startswith('group.'):
                    p.permission = self.get_permission_by_name(
                                       form_result['default_group_perm'])
                    self.sa.add(p)

                elif p.permission.permission_name.startswith('hg.register.'):
                    p.permission = self.get_permission_by_name(
                                       form_result['default_register'])
                    self.sa.add(p)

                elif p.permission.permission_name.startswith('hg.create.'):
                    p.permission = self.get_permission_by_name(
                                        form_result['default_create'])
                    self.sa.add(p)

                elif p.permission.permission_name.startswith('hg.fork.'):
                    p.permission = self.get_permission_by_name(
                                        form_result['default_fork'])
                    self.sa.add(p)

            #stage 2 update all default permissions for repos if checked
            if form_result['overwrite_default_repo'] == True:
                _def_name = form_result['default_repo_perm'].split('repository.')[-1]
                _def = self.get_permission_by_name('repository.' + _def_name)
                # repos
                for r2p in self.sa.query(UserRepoToPerm)\
                               .filter(UserRepoToPerm.user == perm_user)\
                               .all():

                    #don't reset PRIVATE repositories
                    if not r2p.repository.private:
                        r2p.permission = _def
                        self.sa.add(r2p)

            if form_result['overwrite_default_group'] == True:
                _def_name = form_result['default_group_perm'].split('group.')[-1]
                # groups
                _def = self.get_permission_by_name('group.' + _def_name)
                for g2p in self.sa.query(UserRepoGroupToPerm)\
                               .filter(UserRepoGroupToPerm.user == perm_user)\
                               .all():
                    g2p.permission = _def
                    self.sa.add(g2p)

            # stage 3 set anonymous access
            if perm_user.username == 'default':
                perm_user.active = bool(form_result['anonymous'])
                self.sa.add(perm_user)

        except (DatabaseError,):
            log.error(traceback.format_exc())
            raise
