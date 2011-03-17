# -*- coding: utf-8 -*-
"""
    rhodecode.controllers.admin.settings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    settings controller for rhodecode admin
        
    :created_on: Jul 14, 2010
    :author: marcink
    :copyright: (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>    
    :license: GPLv3, see COPYING for more details.
"""
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your opinion) any later version of the license.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

from formencode import htmlfill
from pylons import request, session, tmpl_context as c, url, app_globals as g, \
    config
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _
from rhodecode.lib import helpers as h
from rhodecode.lib.auth import LoginRequired, HasPermissionAllDecorator, \
    HasPermissionAnyDecorator, NotAnonymous
from rhodecode.lib.base import BaseController, render
from rhodecode.lib.celerylib import tasks, run_task
from rhodecode.lib.utils import repo2db_mapper, invalidate_cache, \
    set_rhodecode_config
from rhodecode.model.db import RhodeCodeUi, Repository
from rhodecode.model.forms import UserForm, ApplicationSettingsForm, \
    ApplicationUiSettingsForm
from rhodecode.model.scm import ScmModel
from rhodecode.model.settings import SettingsModel
from rhodecode.model.user import UserModel
from sqlalchemy import func
import formencode
import logging
import traceback

log = logging.getLogger(__name__)


class SettingsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('setting', 'settings', controller='admin/settings', 
    #         path_prefix='/admin', name_prefix='admin_')


    @LoginRequired()
    def __before__(self):
        c.admin_user = session.get('admin_user')
        c.admin_username = session.get('admin_username')
        super(SettingsController, self).__before__()


    @HasPermissionAllDecorator('hg.admin')
    def index(self, format='html'):
        """GET /admin/settings: All items in the collection"""
        # url('admin_settings')

        defaults = SettingsModel().get_app_settings()
        defaults.update(self.get_hg_ui_settings())
        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasPermissionAllDecorator('hg.admin')
    def create(self):
        """POST /admin/settings: Create a new item"""
        # url('admin_settings')

    @HasPermissionAllDecorator('hg.admin')
    def new(self, format='html'):
        """GET /admin/settings/new: Form to create a new item"""
        # url('admin_new_setting')

    @HasPermissionAllDecorator('hg.admin')
    def update(self, setting_id):
        """PUT /admin/settings/setting_id: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('admin_setting', setting_id=ID),
        #           method='put')
        # url('admin_setting', setting_id=ID)
        if setting_id == 'mapping':
            rm_obsolete = request.POST.get('destroy', False)
            log.debug('Rescanning directories with destroy=%s', rm_obsolete)

            initial = ScmModel().repo_scan(g.paths[0][1], g.baseui)
            for repo_name in initial.keys():
                invalidate_cache('get_repo_cached_%s' % repo_name)

            repo2db_mapper(initial, rm_obsolete)

            h.flash(_('Repositories successfully rescanned'), category='success')

        if setting_id == 'whoosh':
            repo_location = self.get_hg_ui_settings()['paths_root_path']
            full_index = request.POST.get('full_index', False)
            task = run_task(tasks.whoosh_index, repo_location, full_index)

            h.flash(_('Whoosh reindex task scheduled'), category='success')
        if setting_id == 'global':

            application_form = ApplicationSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
                settings_model = SettingsModel()
                try:
                    hgsettings1 = settings_model.get('title')
                    hgsettings1.app_settings_value = form_result['rhodecode_title']

                    hgsettings2 = settings_model.get('realm')
                    hgsettings2.app_settings_value = form_result['rhodecode_realm']


                    self.sa.add(hgsettings1)
                    self.sa.add(hgsettings2)
                    self.sa.commit()
                    set_rhodecode_config(config)
                    h.flash(_('Updated application settings'),
                            category='success')

                except:
                    log.error(traceback.format_exc())
                    h.flash(_('error occurred during updating'
                              ' application settings'), category='error')

                    self.sa.rollback()


            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8")

        if setting_id == 'mercurial':
            application_form = ApplicationUiSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))

                try:

                    hgsettings1 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == 'push_ssl').one()
                    hgsettings1.ui_value = form_result['web_push_ssl']

                    hgsettings2 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == '/').one()
                    hgsettings2.ui_value = form_result['paths_root_path']


                    #HOOKS
                    hgsettings3 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == 'changegroup.update').one()
                    hgsettings3.ui_active = bool(form_result['hooks_changegroup_update'])

                    hgsettings4 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == 'changegroup.repo_size').one()
                    hgsettings4.ui_active = bool(form_result['hooks_changegroup_repo_size'])

                    hgsettings5 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == 'pretxnchangegroup.push_logger').one()
                    hgsettings5.ui_active = bool(form_result['hooks_pretxnchangegroup_push_logger'])

                    hgsettings6 = self.sa.query(RhodeCodeUi)\
                    .filter(RhodeCodeUi.ui_key == 'preoutgoing.pull_logger').one()
                    hgsettings6.ui_active = bool(form_result['hooks_preoutgoing_pull_logger'])


                    self.sa.add(hgsettings1)
                    self.sa.add(hgsettings2)
                    self.sa.add(hgsettings3)
                    self.sa.add(hgsettings4)
                    self.sa.add(hgsettings5)
                    self.sa.add(hgsettings6)
                    self.sa.commit()

                    h.flash(_('Updated mercurial settings'),
                            category='success')

                except:
                    log.error(traceback.format_exc())
                    h.flash(_('error occurred during updating application settings'),
                            category='error')

                    self.sa.rollback()


            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8")



        return redirect(url('admin_settings'))

    @HasPermissionAllDecorator('hg.admin')
    def delete(self, setting_id):
        """DELETE /admin/settings/setting_id: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('admin_setting', setting_id=ID),
        #           method='delete')
        # url('admin_setting', setting_id=ID)

    @HasPermissionAllDecorator('hg.admin')
    def show(self, setting_id, format='html'):
        """GET /admin/settings/setting_id: Show a specific item"""
        # url('admin_setting', setting_id=ID)

    @HasPermissionAllDecorator('hg.admin')
    def edit(self, setting_id, format='html'):
        """GET /admin/settings/setting_id/edit: Form to edit an existing item"""
        # url('admin_edit_setting', setting_id=ID)

    @NotAnonymous()
    def my_account(self):
        """
        GET /_admin/my_account Displays info about my account 
        """
        # url('admin_settings_my_account')

        c.user = UserModel().get(c.rhodecode_user.user_id, cache=False)
        all_repos = self.sa.query(Repository)\
            .filter(Repository.user_id == c.user.user_id)\
            .order_by(func.lower(Repository.repo_name))\
            .all()

        c.user_repos = ScmModel().get_repos(all_repos)

        if c.user.username == 'default':
            h.flash(_("You can't edit this user since it's"
              " crucial for entire application"), category='warning')
            return redirect(url('users'))

        defaults = c.user.get_dict()
        return htmlfill.render(
            render('admin/users/user_edit_my_account.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    def my_account_update(self):
        """PUT /_admin/my_account_update: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('admin_settings_my_account_update'),
        #           method='put')
        # url('admin_settings_my_account_update', id=ID)
        user_model = UserModel()
        uid = c.rhodecode_user.user_id
        _form = UserForm(edit=True, old_data={'user_id':uid,
                                              'email':c.rhodecode_user.email})()
        form_result = {}
        try:
            form_result = _form.to_python(dict(request.POST))
            user_model.update_my_account(uid, form_result)
            h.flash(_('Your account was updated successfully'),
                    category='success')

        except formencode.Invalid, errors:
            c.user = user_model.get(c.rhodecode_user.user_id, cache=False)
            c.user = UserModel().get(c.rhodecode_user.user_id, cache=False)
            all_repos = self.sa.query(Repository)\
                .filter(Repository.user_id == c.user.user_id)\
                .order_by(func.lower(Repository.repo_name))\
                .all()
            c.user_repos = ScmModel().get_repos(all_repos)

            return htmlfill.render(
                render('admin/users/user_edit_my_account.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('error occurred during update of user %s') \
                    % form_result.get('username'), category='error')

        return redirect(url('my_account'))

    @NotAnonymous()
    @HasPermissionAnyDecorator('hg.admin', 'hg.create.repository')
    def create_repository(self):
        """GET /_admin/create_repository: Form to create a new item"""
        new_repo = request.GET.get('repo', '')
        c.new_repo = h.repo_name_slug(new_repo)

        return render('admin/repos/repo_add_create_repository.html')

    def get_hg_ui_settings(self):
        ret = self.sa.query(RhodeCodeUi).all()

        if not ret:
            raise Exception('Could not get application ui settings !')
        settings = {}
        for each in ret:
            k = each.ui_key
            v = each.ui_value
            if k == '/':
                k = 'root_path'

            if k.find('.') != -1:
                k = k.replace('.', '_')

            if each.ui_section == 'hooks':
                v = each.ui_active

            settings[each.ui_section + '_' + k] = v

        return settings
