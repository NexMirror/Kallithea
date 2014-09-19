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
kallithea.model.permission
~~~~~~~~~~~~~~~~~~~~~~~~~~

permissions model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 20, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import traceback

from sqlalchemy.exc import DatabaseError

from kallithea.model import BaseModel
from kallithea.model.db import User, Permission, UserToPerm, UserRepoToPerm,\
    UserRepoGroupToPerm, UserUserGroupToPerm
from kallithea.lib.utils2 import str2bool

log = logging.getLogger(__name__)


class PermissionModel(BaseModel):
    """
    Permissions model for Kallithea
    """

    cls = Permission

    def create_permissions(self):
        """
        Create permissions for whole system
        """
        for p in Permission.PERMS:
            if not Permission.get_by_key(p[0]):
                new_perm = Permission()
                new_perm.permission_name = p[0]
                new_perm.permission_longname = p[0]  #translation err with p[1]
                self.sa.add(new_perm)

    def create_default_permissions(self, user, force=False):
        """
        Create missing default permissions for user. If force is set, the default
        permissions for the user are reset, otherwise only missing permissions are
        created.

        :param user:
        """
        user = self._get_user(user)

        def _make_perm(perm):
            new_perm = UserToPerm()
            new_perm.user = user
            new_perm.permission = Permission.get_by_key(perm)
            return new_perm

        def _get_group(perm_name):
            return '.'.join(perm_name.split('.')[:1])

        perms = UserToPerm.query().filter(UserToPerm.user == user).all()
        defined_perms_groups = map(_get_group,
                                (x.permission.permission_name for x in perms))
        log.debug('GOT ALREADY DEFINED:%s' % perms)
        DEFAULT_PERMS = Permission.DEFAULT_USER_PERMISSIONS

        if force:
            for perm in perms:
                self.sa.delete(perm)
            self.sa.commit()
            defined_perms_groups = []
        # For every default permission that needs to be created, we check if
        # its group is already defined. If it's not, we create default permission.
        for perm_name in DEFAULT_PERMS:
            gr = _get_group(perm_name)
            if gr not in defined_perms_groups:
                log.debug('GR:%s not found, creating permission %s'
                          % (gr, perm_name))
                new_perm = _make_perm(perm_name)
                self.sa.add(new_perm)

    def update(self, form_result):
        perm_user = User.get_by_username(username=form_result['perm_user_name'])

        try:
            # stage 1 set anonymous access
            if perm_user.username == User.DEFAULT_USER:
                perm_user.active = str2bool(form_result['anonymous'])
                self.sa.add(perm_user)

            # stage 2 reset defaults and set them from form data
            def _make_new(usr, perm_name):
                log.debug('Creating new permission:%s' % (perm_name))
                new = UserToPerm()
                new.user = usr
                new.permission = Permission.get_by_key(perm_name)
                return new
            # clear current entries, to make this function idempotent
            # it will fix even if we define more permissions or permissions
            # are somehow missing
            u2p = self.sa.query(UserToPerm)\
                .filter(UserToPerm.user == perm_user)\
                .all()
            for p in u2p:
                self.sa.delete(p)
            #create fresh set of permissions
            for def_perm_key in ['default_repo_perm',
                                 'default_group_perm',
                                 'default_user_group_perm',
                                 'default_repo_create',
                                 'create_on_write', # special case for create repos on write access to group
                                 #'default_repo_group_create', #not implemented yet
                                 'default_user_group_create',
                                 'default_fork',
                                 'default_register',
                                 'default_extern_activate']:
                p = _make_new(perm_user, form_result[def_perm_key])
                self.sa.add(p)

            #stage 3 update all default permissions for repos if checked
            if form_result['overwrite_default_repo']:
                _def_name = form_result['default_repo_perm'].split('repository.')[-1]
                _def = Permission.get_by_key('repository.' + _def_name)
                # repos
                for r2p in self.sa.query(UserRepoToPerm)\
                               .filter(UserRepoToPerm.user == perm_user)\
                               .all():

                    #don't reset PRIVATE repositories
                    if not r2p.repository.private:
                        r2p.permission = _def
                        self.sa.add(r2p)

            if form_result['overwrite_default_group']:
                _def_name = form_result['default_group_perm'].split('group.')[-1]
                # groups
                _def = Permission.get_by_key('group.' + _def_name)
                for g2p in self.sa.query(UserRepoGroupToPerm)\
                               .filter(UserRepoGroupToPerm.user == perm_user)\
                               .all():
                    g2p.permission = _def
                    self.sa.add(g2p)

            if form_result['overwrite_default_user_group']:
                _def_name = form_result['default_user_group_perm'].split('usergroup.')[-1]
                # groups
                _def = Permission.get_by_key('usergroup.' + _def_name)
                for g2p in self.sa.query(UserUserGroupToPerm)\
                               .filter(UserUserGroupToPerm.user == perm_user)\
                               .all():
                    g2p.permission = _def
                    self.sa.add(g2p)

            self.sa.commit()
        except (DatabaseError,):
            log.error(traceback.format_exc())
            self.sa.rollback()
            raise
