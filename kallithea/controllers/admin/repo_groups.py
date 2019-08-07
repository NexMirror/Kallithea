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
kallithea.controllers.admin.repo_groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository groups controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Mar 23, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import itertools
import logging
import traceback

import formencode
from formencode import htmlfill
from tg import app_globals, request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from tg.i18n import ungettext
from webob.exc import HTTPForbidden, HTTPFound, HTTPInternalServerError, HTTPNotFound

import kallithea
from kallithea.config.routing import url
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasPermissionAny, HasRepoGroupPermissionLevel, HasRepoGroupPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseController, render
from kallithea.lib.utils2 import safe_int
from kallithea.model.db import RepoGroup, Repository
from kallithea.model.forms import RepoGroupForm, RepoGroupPermsForm
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.scm import AvailableRepoGroupChoices, RepoGroupList


log = logging.getLogger(__name__)


class RepoGroupsController(BaseController):

    @LoginRequired(allow_default_user=True)
    def _before(self, *args, **kwargs):
        super(RepoGroupsController, self)._before(*args, **kwargs)

    def __load_defaults(self, extras=(), exclude=()):
        """extras is used for keeping current parent ignoring permissions
        exclude is used for not moving group to itself TODO: also exclude descendants
        Note: only admin can create top level groups
        """
        repo_groups = AvailableRepoGroupChoices([], 'admin', extras)
        exclude_group_ids = set(rg.group_id for rg in exclude)
        c.repo_groups = [rg for rg in repo_groups
                         if rg[0] not in exclude_group_ids]

    def __load_data(self, group_id):
        """
        Load defaults settings for edit, and update

        :param group_id:
        """
        repo_group = RepoGroup.get_or_404(group_id)
        data = repo_group.get_dict()
        data['group_name'] = repo_group.name

        # fill repository group users
        for p in repo_group.repo_group_to_perm:
            data.update({'u_perm_%s' % p.user.username:
                             p.permission.permission_name})

        # fill repository group groups
        for p in repo_group.users_group_to_perm:
            data.update({'g_perm_%s' % p.users_group.users_group_name:
                             p.permission.permission_name})

        return data

    def _revoke_perms_on_yourself(self, form_result):
        _up = filter(lambda u: request.authuser.username == u[0],
                     form_result['perms_updates'])
        _new = filter(lambda u: request.authuser.username == u[0],
                      form_result['perms_new'])
        if _new and _new[0][1] != 'group.admin' or _up and _up[0][1] != 'group.admin':
            return True
        return False

    def index(self, format='html'):
        _list = RepoGroup.query(sorted=True).all()
        group_iter = RepoGroupList(_list, perm_level='admin')
        repo_groups_data = []
        total_records = len(group_iter)
        _tmpl_lookup = app_globals.mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        repo_group_name = lambda repo_group_name, children_groups: (
            template.get_def("repo_group_name")
            .render(repo_group_name, children_groups, _=_, h=h, c=c)
        )
        repo_group_actions = lambda repo_group_id, repo_group_name, gr_count: (
            template.get_def("repo_group_actions")
            .render(repo_group_id, repo_group_name, gr_count, _=_, h=h, c=c,
                    ungettext=ungettext)
        )

        for repo_gr in group_iter:
            children_groups = map(h.safe_unicode,
                itertools.chain((g.name for g in repo_gr.parents),
                                (x.name for x in [repo_gr])))
            repo_count = repo_gr.repositories.count()
            repo_groups_data.append({
                "raw_name": repo_gr.group_name,
                "group_name": repo_group_name(repo_gr.group_name, children_groups),
                "desc": h.escape(repo_gr.group_description),
                "repos": repo_count,
                "owner": h.person(repo_gr.owner),
                "action": repo_group_actions(repo_gr.group_id, repo_gr.group_name,
                                             repo_count)
            })

        c.data = {
            "sort": None,
            "dir": "asc",
            "records": repo_groups_data
        }

        return render('admin/repo_groups/repo_groups.html')

    def create(self):
        self.__load_defaults()

        # permissions for can create group based on parent_id are checked
        # here in the Form
        repo_group_form = RepoGroupForm(repo_groups=c.repo_groups)
        try:
            form_result = repo_group_form.to_python(dict(request.POST))
            gr = RepoGroupModel().create(
                group_name=form_result['group_name'],
                group_description=form_result['group_description'],
                parent=form_result['parent_group_id'],
                owner=request.authuser.user_id, # TODO: make editable
                copy_permissions=form_result['group_copy_permissions']
            )
            Session().commit()
            # TODO: in future action_logger(, '', '', '')
        except formencode.Invalid as errors:
            return htmlfill.render(
                render('admin/repo_groups/repo_group_add.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8",
                force_defaults=False)
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during creation of repository group %s')
                    % request.POST.get('group_name'), category='error')
            parent_group_id = form_result['parent_group_id']
            # TODO: maybe we should get back to the main view, not the admin one
            raise HTTPFound(location=url('repos_groups', parent_group=parent_group_id))
        h.flash(_('Created repository group %s') % gr.group_name,
                category='success')
        raise HTTPFound(location=url('repos_group_home', group_name=gr.group_name))

    def new(self):
        if HasPermissionAny('hg.admin')('group create'):
            # we're global admin, we're ok and we can create TOP level groups
            pass
        else:
            # we pass in parent group into creation form, thus we know
            # what would be the group, we can check perms here !
            group_id = safe_int(request.GET.get('parent_group'))
            group = RepoGroup.get(group_id) if group_id else None
            group_name = group.group_name if group else None
            if HasRepoGroupPermissionLevel('admin')(group_name, 'group create'):
                pass
            else:
                raise HTTPForbidden()

        self.__load_defaults()
        return render('admin/repo_groups/repo_group_add.html')

    @HasRepoGroupPermissionLevelDecorator('admin')
    def update(self, group_name):
        c.repo_group = RepoGroup.guess_instance(group_name)
        self.__load_defaults(extras=[c.repo_group.parent_group],
                             exclude=[c.repo_group])

        # TODO: kill allow_empty_group - it is only used for redundant form validation!
        if HasPermissionAny('hg.admin')('group edit'):
            # we're global admin, we're ok and we can create TOP level groups
            allow_empty_group = True
        elif not c.repo_group.parent_group:
            allow_empty_group = True
        else:
            allow_empty_group = False
        repo_group_form = RepoGroupForm(
            edit=True,
            old_data=c.repo_group.get_dict(),
            repo_groups=c.repo_groups,
            can_create_in_root=allow_empty_group,
        )()
        try:
            form_result = repo_group_form.to_python(dict(request.POST))

            new_gr = RepoGroupModel().update(group_name, form_result)
            Session().commit()
            h.flash(_('Updated repository group %s')
                    % form_result['group_name'], category='success')
            # we now have new name !
            group_name = new_gr.group_name
            # TODO: in future action_logger(, '', '', '')
        except formencode.Invalid as errors:
            c.active = 'settings'
            return htmlfill.render(
                render('admin/repo_groups/repo_group_edit.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8",
                force_defaults=False)
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of repository group %s')
                    % request.POST.get('group_name'), category='error')

        raise HTTPFound(location=url('edit_repo_group', group_name=group_name))

    @HasRepoGroupPermissionLevelDecorator('admin')
    def delete(self, group_name):
        gr = c.repo_group = RepoGroup.guess_instance(group_name)
        repos = gr.repositories.all()
        if repos:
            h.flash(_('This group contains %s repositories and cannot be '
                      'deleted') % len(repos), category='warning')
            raise HTTPFound(location=url('repos_groups'))

        children = gr.children.all()
        if children:
            h.flash(_('This group contains %s subgroups and cannot be deleted'
                      % (len(children))), category='warning')
            raise HTTPFound(location=url('repos_groups'))

        try:
            RepoGroupModel().delete(group_name)
            Session().commit()
            h.flash(_('Removed repository group %s') % group_name,
                    category='success')
            # TODO: in future action_logger(, '', '', '')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during deletion of repository group %s')
                    % group_name, category='error')

        if gr.parent_group:
            raise HTTPFound(location=url('repos_group_home', group_name=gr.parent_group.group_name))
        raise HTTPFound(location=url('repos_groups'))

    def show_by_name(self, group_name):
        """
        This is a proxy that does a lookup group_name -> id, and shows
        the group by id view instead
        """
        group_name = group_name.rstrip('/')
        id_ = RepoGroup.get_by_group_name(group_name)
        if id_:
            return self.show(group_name)
        raise HTTPNotFound

    @HasRepoGroupPermissionLevelDecorator('read')
    def show(self, group_name):
        c.active = 'settings'

        c.group = c.repo_group = RepoGroup.guess_instance(group_name)

        groups = RepoGroup.query(sorted=True).filter_by(parent_group=c.group).all()
        repo_groups_list = self.scm_model.get_repo_groups(groups)

        repos_list = Repository.query(sorted=True).filter_by(group=c.group).all()
        c.data = RepoModel().get_repos_as_dict(repos_list,
                                               repo_groups_list=repo_groups_list,
                                               short_name=True)

        return render('admin/repo_groups/repo_group_show.html')

    @HasRepoGroupPermissionLevelDecorator('admin')
    def edit(self, group_name):
        c.active = 'settings'

        c.repo_group = RepoGroup.guess_instance(group_name)
        self.__load_defaults(extras=[c.repo_group.parent_group],
                             exclude=[c.repo_group])
        defaults = self.__load_data(c.repo_group.group_id)

        return htmlfill.render(
            render('admin/repo_groups/repo_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasRepoGroupPermissionLevelDecorator('admin')
    def edit_repo_group_advanced(self, group_name):
        c.active = 'advanced'
        c.repo_group = RepoGroup.guess_instance(group_name)

        return render('admin/repo_groups/repo_group_edit.html')

    @HasRepoGroupPermissionLevelDecorator('admin')
    def edit_repo_group_perms(self, group_name):
        c.active = 'perms'
        c.repo_group = RepoGroup.guess_instance(group_name)
        self.__load_defaults()
        defaults = self.__load_data(c.repo_group.group_id)

        return htmlfill.render(
            render('admin/repo_groups/repo_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasRepoGroupPermissionLevelDecorator('admin')
    def update_perms(self, group_name):
        """
        Update permissions for given repository group

        :param group_name:
        """

        c.repo_group = RepoGroup.guess_instance(group_name)
        valid_recursive_choices = ['none', 'repos', 'groups', 'all']
        form_result = RepoGroupPermsForm(valid_recursive_choices)().to_python(request.POST)
        if not request.authuser.is_admin:
            if self._revoke_perms_on_yourself(form_result):
                msg = _('Cannot revoke permission for yourself as admin')
                h.flash(msg, category='warning')
                raise HTTPFound(location=url('edit_repo_group_perms', group_name=group_name))
        recursive = form_result['recursive']
        # iterate over all members(if in recursive mode) of this groups and
        # set the permissions !
        # this can be potentially heavy operation
        RepoGroupModel()._update_permissions(c.repo_group,
                                             form_result['perms_new'],
                                             form_result['perms_updates'],
                                             recursive)
        # TODO: implement this
        #action_logger(request.authuser, 'admin_changed_repo_permissions',
        #              repo_name, request.ip_addr)
        Session().commit()
        h.flash(_('Repository group permissions updated'), category='success')
        raise HTTPFound(location=url('edit_repo_group_perms', group_name=group_name))

    @HasRepoGroupPermissionLevelDecorator('admin')
    def delete_perms(self, group_name):
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
            recursive = request.POST.get('recursive', 'none')
            if obj_type == 'user':
                RepoGroupModel().delete_permission(repo_group=group_name,
                                                   obj=obj_id, obj_type='user',
                                                   recursive=recursive)
            elif obj_type == 'user_group':
                RepoGroupModel().delete_permission(repo_group=group_name,
                                                   obj=obj_id,
                                                   obj_type='user_group',
                                                   recursive=recursive)

            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during revoking of permission'),
                    category='error')
            raise HTTPInternalServerError()
