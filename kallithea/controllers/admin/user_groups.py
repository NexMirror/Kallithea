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
kallithea.controllers.admin.user_groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

User Groups crud controller

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jan 25, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

import formencode
from formencode import htmlfill
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from tg import app_globals, config, request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPFound, HTTPInternalServerError

import kallithea
from kallithea.config.routing import url
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasPermissionAnyDecorator, HasUserGroupPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseController, render
from kallithea.lib.exceptions import RepoGroupAssignmentError, UserGroupsAssignedException
from kallithea.lib.utils import action_logger
from kallithea.lib.utils2 import safe_int, safe_unicode
from kallithea.model.db import User, UserGroup, UserGroupRepoGroupToPerm, UserGroupRepoToPerm, UserGroupToPerm
from kallithea.model.forms import CustomDefaultPermissionsForm, UserGroupForm, UserGroupPermsForm
from kallithea.model.meta import Session
from kallithea.model.scm import UserGroupList
from kallithea.model.user_group import UserGroupModel


log = logging.getLogger(__name__)


class UserGroupsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""

    @LoginRequired(allow_default_user=True)
    def _before(self, *args, **kwargs):
        super(UserGroupsController, self)._before(*args, **kwargs)
        c.available_permissions = config['available_permissions']

    def __load_data(self, user_group_id):
        c.group_members_obj = sorted((x.user for x in c.user_group.members),
                                     key=lambda u: u.username.lower())

        c.group_members = [(x.user_id, x.username) for x in c.group_members_obj]
        c.available_members = sorted(((x.user_id, x.username) for x in
                                      User.query().all()),
                                     key=lambda u: u[1].lower())

    def __load_defaults(self, user_group_id):
        """
        Load defaults settings for edit, and update

        :param user_group_id:
        """
        user_group = UserGroup.get_or_404(user_group_id)
        data = user_group.get_dict()
        return data

    def index(self, format='html'):
        _list = UserGroup.query() \
                        .order_by(func.lower(UserGroup.users_group_name)) \
                        .all()
        group_iter = UserGroupList(_list, perm_level='admin')
        user_groups_data = []
        total_records = len(group_iter)
        _tmpl_lookup = app_globals.mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        user_group_name = lambda user_group_id, user_group_name: (
            template.get_def("user_group_name")
            .render(user_group_id, user_group_name, _=_, h=h, c=c)
        )
        user_group_actions = lambda user_group_id, user_group_name: (
            template.get_def("user_group_actions")
            .render(user_group_id, user_group_name, _=_, h=h, c=c)
        )
        for user_gr in group_iter:

            user_groups_data.append({
                "raw_name": user_gr.users_group_name,
                "group_name": user_group_name(user_gr.users_group_id,
                                              user_gr.users_group_name),
                "desc": h.escape(user_gr.user_group_description),
                "members": len(user_gr.members),
                "active": h.boolicon(user_gr.users_group_active),
                "owner": h.person(user_gr.owner.username),
                "action": user_group_actions(user_gr.users_group_id, user_gr.users_group_name)
            })

        c.data = {
            "sort": None,
            "dir": "asc",
            "records": user_groups_data
        }

        return render('admin/user_groups/user_groups.html')

    @HasPermissionAnyDecorator('hg.admin', 'hg.usergroup.create.true')
    def create(self):
        users_group_form = UserGroupForm()()
        try:
            form_result = users_group_form.to_python(dict(request.POST))
            ug = UserGroupModel().create(name=form_result['users_group_name'],
                                         description=form_result['user_group_description'],
                                         owner=request.authuser.user_id,
                                         active=form_result['users_group_active'])

            gr = form_result['users_group_name']
            action_logger(request.authuser,
                          'admin_created_users_group:%s' % gr,
                          None, request.ip_addr)
            h.flash(h.HTML(_('Created user group %s')) % h.link_to(gr, url('edit_users_group', id=ug.users_group_id)),
                category='success')
            Session().commit()
        except formencode.Invalid as errors:
            return htmlfill.render(
                render('admin/user_groups/user_group_add.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8",
                force_defaults=False)
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during creation of user group %s')
                    % request.POST.get('users_group_name'), category='error')

        raise HTTPFound(location=url('users_groups'))

    @HasPermissionAnyDecorator('hg.admin', 'hg.usergroup.create.true')
    def new(self, format='html'):
        return render('admin/user_groups/user_group_add.html')

    @HasUserGroupPermissionLevelDecorator('admin')
    def update(self, id):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'settings'
        self.__load_data(id)

        available_members = [safe_unicode(x[0]) for x in c.available_members]

        users_group_form = UserGroupForm(edit=True,
                                         old_data=c.user_group.get_dict(),
                                         available_members=available_members)()

        try:
            form_result = users_group_form.to_python(request.POST)
            UserGroupModel().update(c.user_group, form_result)
            gr = form_result['users_group_name']
            action_logger(request.authuser,
                          'admin_updated_users_group:%s' % gr,
                          None, request.ip_addr)
            h.flash(_('Updated user group %s') % gr, category='success')
            Session().commit()
        except formencode.Invalid as errors:
            ug_model = UserGroupModel()
            defaults = errors.value
            e = errors.error_dict or {}
            defaults.update({
                'create_repo_perm': ug_model.has_perm(id,
                                                      'hg.create.repository'),
                'fork_repo_perm': ug_model.has_perm(id,
                                                    'hg.fork.repository'),
            })

            return htmlfill.render(
                render('admin/user_groups/user_group_edit.html'),
                defaults=defaults,
                errors=e,
                prefix_error=False,
                encoding="UTF-8",
                force_defaults=False)
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of user group %s')
                    % request.POST.get('users_group_name'), category='error')

        raise HTTPFound(location=url('edit_users_group', id=id))

    @HasUserGroupPermissionLevelDecorator('admin')
    def delete(self, id):
        usr_gr = UserGroup.get_or_404(id)
        try:
            UserGroupModel().delete(usr_gr)
            Session().commit()
            h.flash(_('Successfully deleted user group'), category='success')
        except UserGroupsAssignedException as e:
            h.flash(e, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during deletion of user group'),
                    category='error')
        raise HTTPFound(location=url('users_groups'))

    @HasUserGroupPermissionLevelDecorator('admin')
    def edit(self, id, format='html'):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'settings'
        self.__load_data(id)

        defaults = self.__load_defaults(id)

        return htmlfill.render(
            render('admin/user_groups/user_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasUserGroupPermissionLevelDecorator('admin')
    def edit_perms(self, id):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'perms'

        defaults = {}
        # fill user group users
        for p in c.user_group.user_user_group_to_perm:
            defaults.update({'u_perm_%s' % p.user.username:
                             p.permission.permission_name})

        for p in c.user_group.user_group_user_group_to_perm:
            defaults.update({'g_perm_%s' % p.user_group.users_group_name:
                             p.permission.permission_name})

        return htmlfill.render(
            render('admin/user_groups/user_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasUserGroupPermissionLevelDecorator('admin')
    def update_perms(self, id):
        """
        grant permission for given usergroup

        :param id:
        """
        user_group = UserGroup.get_or_404(id)
        form = UserGroupPermsForm()().to_python(request.POST)

        # set the permissions !
        try:
            UserGroupModel()._update_permissions(user_group, form['perms_new'],
                                                 form['perms_updates'])
        except RepoGroupAssignmentError:
            h.flash(_('Target group cannot be the same'), category='error')
            raise HTTPFound(location=url('edit_user_group_perms', id=id))
        # TODO: implement this
        #action_logger(request.authuser, 'admin_changed_repo_permissions',
        #              repo_name, request.ip_addr)
        Session().commit()
        h.flash(_('User group permissions updated'), category='success')
        raise HTTPFound(location=url('edit_user_group_perms', id=id))

    @HasUserGroupPermissionLevelDecorator('admin')
    def delete_perms(self, id):
        try:
            obj_type = request.POST.get('obj_type')
            obj_id = None
            if obj_type == 'user':
                obj_id = safe_int(request.POST.get('user_id'))
            elif obj_type == 'user_group':
                obj_id = safe_int(request.POST.get('user_group_id'))

            if not request.authuser.is_admin:
                if obj_type == 'user' and request.authuser.user_id == obj_id:
                    msg = _('Cannot revoke permission for yourself as admin')
                    h.flash(msg, category='warning')
                    raise Exception('revoke admin permission on self')
            if obj_type == 'user':
                UserGroupModel().revoke_user_permission(user_group=id,
                                                        user=obj_id)
            elif obj_type == 'user_group':
                UserGroupModel().revoke_user_group_permission(target_user_group=id,
                                                              user_group=obj_id)
            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during revoking of permission'),
                    category='error')
            raise HTTPInternalServerError()

    @HasUserGroupPermissionLevelDecorator('admin')
    def edit_default_perms(self, id):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'default_perms'

        permissions = {
            'repositories': {},
            'repositories_groups': {}
        }
        ugroup_repo_perms = UserGroupRepoToPerm.query() \
            .options(joinedload(UserGroupRepoToPerm.permission)) \
            .options(joinedload(UserGroupRepoToPerm.repository)) \
            .filter(UserGroupRepoToPerm.users_group_id == id) \
            .all()

        for gr in ugroup_repo_perms:
            permissions['repositories'][gr.repository.repo_name]  \
                = gr.permission.permission_name

        ugroup_group_perms = UserGroupRepoGroupToPerm.query() \
            .options(joinedload(UserGroupRepoGroupToPerm.permission)) \
            .options(joinedload(UserGroupRepoGroupToPerm.group)) \
            .filter(UserGroupRepoGroupToPerm.users_group_id == id) \
            .all()

        for gr in ugroup_group_perms:
            permissions['repositories_groups'][gr.group.group_name] \
                = gr.permission.permission_name
        c.permissions = permissions

        ug_model = UserGroupModel()

        defaults = c.user_group.get_dict()
        defaults.update({
            'create_repo_perm': ug_model.has_perm(c.user_group,
                                                  'hg.create.repository'),
            'create_user_group_perm': ug_model.has_perm(c.user_group,
                                                        'hg.usergroup.create.true'),
            'fork_repo_perm': ug_model.has_perm(c.user_group,
                                                'hg.fork.repository'),
        })

        return htmlfill.render(
            render('admin/user_groups/user_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasUserGroupPermissionLevelDecorator('admin')
    def update_default_perms(self, id):
        user_group = UserGroup.get_or_404(id)

        try:
            form = CustomDefaultPermissionsForm()()
            form_result = form.to_python(request.POST)

            usergroup_model = UserGroupModel()

            defs = UserGroupToPerm.query() \
                .filter(UserGroupToPerm.users_group == user_group) \
                .all()
            for ug in defs:
                Session().delete(ug)

            if form_result['create_repo_perm']:
                usergroup_model.grant_perm(id, 'hg.create.repository')
            else:
                usergroup_model.grant_perm(id, 'hg.create.none')
            if form_result['create_user_group_perm']:
                usergroup_model.grant_perm(id, 'hg.usergroup.create.true')
            else:
                usergroup_model.grant_perm(id, 'hg.usergroup.create.false')
            if form_result['fork_repo_perm']:
                usergroup_model.grant_perm(id, 'hg.fork.repository')
            else:
                usergroup_model.grant_perm(id, 'hg.fork.none')

            h.flash(_("Updated permissions"), category='success')
            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during permissions saving'),
                    category='error')

        raise HTTPFound(location=url('edit_user_group_default_perms', id=id))

    @HasUserGroupPermissionLevelDecorator('admin')
    def edit_advanced(self, id):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'advanced'
        c.group_members_obj = sorted((x.user for x in c.user_group.members),
                                     key=lambda u: u.username.lower())
        return render('admin/user_groups/user_group_edit.html')

    @HasUserGroupPermissionLevelDecorator('admin')
    def edit_members(self, id):
        c.user_group = UserGroup.get_or_404(id)
        c.active = 'members'
        c.group_members_obj = sorted((x.user for x in c.user_group.members),
                                     key=lambda u: u.username.lower())

        c.group_members = [(x.user_id, x.username) for x in c.group_members_obj]
        return render('admin/user_groups/user_group_edit.html')
