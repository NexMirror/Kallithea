# -*- coding: utf-8 -*-
"""
    rhodecode.controllers.admin.settings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    settings controller for rhodecode admin

    :created_on: Jul 14, 2010
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
import formencode
import pkg_resources
import platform

from sqlalchemy import func
from formencode import htmlfill
from pylons import request, session, tmpl_context as c, url, config
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _

from rhodecode.lib import helpers as h
from rhodecode.lib.auth import LoginRequired, HasPermissionAllDecorator, \
    HasPermissionAnyDecorator, NotAnonymous, HasPermissionAny,\
    HasReposGroupPermissionAll, HasReposGroupPermissionAny, AuthUser
from rhodecode.lib.base import BaseController, render
from rhodecode.lib.celerylib import tasks, run_task
from rhodecode.lib.utils import repo2db_mapper, invalidate_cache, \
    set_rhodecode_config, repo_name_slug, check_git_version
from rhodecode.model.db import RhodeCodeUi, Repository, RepoGroup, \
    RhodeCodeSetting, PullRequest, PullRequestReviewers
from rhodecode.model.forms import UserForm, ApplicationSettingsForm, \
    ApplicationUiSettingsForm, ApplicationVisualisationForm
from rhodecode.model.scm import ScmModel, GroupList
from rhodecode.model.user import UserModel
from rhodecode.model.repo import RepoModel
from rhodecode.model.db import User
from rhodecode.model.notification import EmailNotificationModel
from rhodecode.model.meta import Session
from rhodecode.lib.utils2 import str2bool, safe_unicode
from rhodecode.lib.compat import json
from webob.exc import HTTPForbidden
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
        c.modules = sorted([(p.project_name, p.version)
                            for p in pkg_resources.working_set]
                           + [('git', check_git_version())],
                           key=lambda k: k[0].lower())
        c.py_version = platform.python_version()
        c.platform = platform.platform()
        super(SettingsController, self).__before__()

    @HasPermissionAllDecorator('hg.admin')
    def index(self, format='html'):
        """GET /admin/settings: All items in the collection"""
        # url('admin_settings')

        defaults = RhodeCodeSetting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

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
            log.debug('Rescanning directories with destroy=%s' % rm_obsolete)
            initial = ScmModel().repo_scan()
            log.debug('invalidating all repositories')
            for repo_name in initial.keys():
                invalidate_cache('get_repo_cached_%s' % repo_name)

            added, removed = repo2db_mapper(initial, rm_obsolete)
            _repr = lambda l: ', '.join(map(safe_unicode, l)) or '-'
            h.flash(_('Repositories successfully '
                      'rescanned added: %s ; removed: %s') %
                    (_repr(added), _repr(removed)),
                    category='success')

        if setting_id == 'whoosh':
            repo_location = self._get_hg_ui_settings()['paths_root_path']
            full_index = request.POST.get('full_index', False)
            run_task(tasks.whoosh_index, repo_location, full_index)
            h.flash(_('Whoosh reindex task scheduled'), category='success')

        if setting_id == 'global':

            application_form = ApplicationSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8"
                )

            try:
                sett1 = RhodeCodeSetting.get_by_name_or_create('title')
                sett1.app_settings_value = form_result['rhodecode_title']
                Session().add(sett1)

                sett2 = RhodeCodeSetting.get_by_name_or_create('realm')
                sett2.app_settings_value = form_result['rhodecode_realm']
                Session().add(sett2)

                sett3 = RhodeCodeSetting.get_by_name_or_create('ga_code')
                sett3.app_settings_value = form_result['rhodecode_ga_code']
                Session().add(sett3)

                Session().commit()
                set_rhodecode_config(config)
                h.flash(_('Updated application settings'), category='success')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'application settings'),
                          category='error')

        if setting_id == 'visual':

            application_form = ApplicationVisualisationForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8"
                )

            try:
                sett1 = RhodeCodeSetting.get_by_name_or_create('show_public_icon')
                sett1.app_settings_value = \
                    form_result['rhodecode_show_public_icon']
                Session().add(sett1)

                sett2 = RhodeCodeSetting.get_by_name_or_create('show_private_icon')
                sett2.app_settings_value = \
                    form_result['rhodecode_show_private_icon']
                Session().add(sett2)

                sett3 = RhodeCodeSetting.get_by_name_or_create('stylify_metatags')
                sett3.app_settings_value = \
                    form_result['rhodecode_stylify_metatags']
                Session().add(sett3)

                sett4 = RhodeCodeSetting.get_by_name_or_create('lightweight_dashboard')
                sett4.app_settings_value = \
                    form_result['rhodecode_lightweight_dashboard']
                Session().add(sett4)

                sett4 = RhodeCodeSetting.get_by_name_or_create('repository_fields')
                sett4.app_settings_value = \
                    form_result['rhodecode_repository_fields']
                Session().add(sett4)

                Session().commit()
                set_rhodecode_config(config)
                h.flash(_('Updated visualisation settings'),
                        category='success')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'visualisation settings'),
                        category='error')

        if setting_id == 'vcs':
            application_form = ApplicationUiSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8"
                )

            try:
                sett = RhodeCodeUi.get_by_key('push_ssl')
                sett.ui_value = form_result['web_push_ssl']
                Session().add(sett)

                sett = RhodeCodeUi.get_by_key('/')
                sett.ui_value = form_result['paths_root_path']
                Session().add(sett)

                #HOOKS
                sett = RhodeCodeUi.get_by_key(RhodeCodeUi.HOOK_UPDATE)
                sett.ui_active = form_result['hooks_changegroup_update']
                Session().add(sett)

                sett = RhodeCodeUi.get_by_key(RhodeCodeUi.HOOK_REPO_SIZE)
                sett.ui_active = form_result['hooks_changegroup_repo_size']
                Session().add(sett)

                sett = RhodeCodeUi.get_by_key(RhodeCodeUi.HOOK_PUSH)
                sett.ui_active = form_result['hooks_changegroup_push_logger']
                Session().add(sett)

                sett = RhodeCodeUi.get_by_key(RhodeCodeUi.HOOK_PULL)
                sett.ui_active = form_result['hooks_outgoing_pull_logger']

                Session().add(sett)

                ## EXTENSIONS
                sett = RhodeCodeUi.get_by_key('largefiles')
                if not sett:
                    #make one if it's not there !
                    sett = RhodeCodeUi()
                    sett.ui_key = 'largefiles'
                    sett.ui_section = 'extensions'
                sett.ui_active = form_result['extensions_largefiles']
                Session().add(sett)

                sett = RhodeCodeUi.get_by_key('hgsubversion')
                if not sett:
                    #make one if it's not there !
                    sett = RhodeCodeUi()
                    sett.ui_key = 'hgsubversion'
                    sett.ui_section = 'extensions'

                sett.ui_active = form_result['extensions_hgsubversion']
                Session().add(sett)

#                sett = RhodeCodeUi.get_by_key('hggit')
#                if not sett:
#                    #make one if it's not there !
#                    sett = RhodeCodeUi()
#                    sett.ui_key = 'hggit'
#                    sett.ui_section = 'extensions'
#
#                sett.ui_active = form_result['extensions_hggit']
#                Session().add(sett)

                Session().commit()

                h.flash(_('Updated VCS settings'), category='success')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'application settings'), category='error')

        if setting_id == 'hooks':
            ui_key = request.POST.get('new_hook_ui_key')
            ui_value = request.POST.get('new_hook_ui_value')
            try:

                if ui_value and ui_key:
                    RhodeCodeUi.create_or_update_hook(ui_key, ui_value)
                    h.flash(_('Added new hook'),
                            category='success')

                # check for edits
                update = False
                _d = request.POST.dict_of_lists()
                for k, v in zip(_d.get('hook_ui_key', []),
                                _d.get('hook_ui_value_new', [])):
                    RhodeCodeUi.create_or_update_hook(k, v)
                    update = True

                if update:
                    h.flash(_('Updated hooks'), category='success')
                Session().commit()
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during hook creation'),
                        category='error')

            return redirect(url('admin_edit_setting', setting_id='hooks'))

        if setting_id == 'email':
            test_email = request.POST.get('test_email')
            test_email_subj = 'RhodeCode TestEmail'
            test_email_body = 'RhodeCode Email test'

            test_email_html_body = EmailNotificationModel()\
                .get_email_tmpl(EmailNotificationModel.TYPE_DEFAULT,
                                body=test_email_body)

            recipients = [test_email] if test_email else None

            run_task(tasks.send_email, recipients, test_email_subj,
                     test_email_body, test_email_html_body)

            h.flash(_('Email task created'), category='success')
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
        if setting_id == 'hooks':
            hook_id = request.POST.get('hook_id')
            RhodeCodeUi.delete(hook_id)
            Session().commit()

    @HasPermissionAllDecorator('hg.admin')
    def show(self, setting_id, format='html'):
        """
        GET /admin/settings/setting_id: Show a specific item"""
        # url('admin_setting', setting_id=ID)

    @HasPermissionAllDecorator('hg.admin')
    def edit(self, setting_id, format='html'):
        """
        GET /admin/settings/setting_id/edit: Form to
        edit an existing item"""
        # url('admin_edit_setting', setting_id=ID)

        c.hooks = RhodeCodeUi.get_builtin_hooks()
        c.custom_hooks = RhodeCodeUi.get_custom_hooks()

        return htmlfill.render(
            render('admin/settings/hooks.html'),
            defaults={},
            encoding="UTF-8",
            force_defaults=False
        )

    def _load_my_repos_data(self):
        repos_list = Session().query(Repository)\
                     .filter(Repository.user_id ==
                             self.rhodecode_user.user_id)\
                     .order_by(func.lower(Repository.repo_name)).all()

        repos_data = RepoModel().get_repos_as_dict(repos_list=repos_list,
                                                   admin=True)
        #json used to render the grid
        return json.dumps(repos_data)

    @NotAnonymous()
    def my_account(self):
        """
        GET /_admin/my_account Displays info about my account
        """
        # url('admin_settings_my_account')

        c.user = User.get(self.rhodecode_user.user_id)
        c.perm_user = AuthUser(user_id=self.rhodecode_user.user_id,
                               ip_addr=self.ip_addr)
        c.ldap_dn = c.user.ldap_dn

        if c.user.username == 'default':
            h.flash(_("You can't edit this user since it's"
              " crucial for entire application"), category='warning')
            return redirect(url('users'))

        #json used to render the grid
        c.data = self._load_my_repos_data()

        defaults = c.user.get_dict()

        c.form = htmlfill.render(
            render('admin/users/user_edit_my_account_form.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )
        return render('admin/users/user_edit_my_account.html')

    @NotAnonymous()
    def my_account_update(self):
        """PUT /_admin/my_account_update: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('admin_settings_my_account_update'),
        #           method='put')
        # url('admin_settings_my_account_update', id=ID)
        uid = self.rhodecode_user.user_id
        c.user = User.get(self.rhodecode_user.user_id)
        c.perm_user = AuthUser(user_id=self.rhodecode_user.user_id,
                               ip_addr=self.ip_addr)
        c.ldap_dn = c.user.ldap_dn
        email = self.rhodecode_user.email
        _form = UserForm(edit=True,
                         old_data={'user_id': uid, 'email': email})()
        form_result = {}
        try:
            form_result = _form.to_python(dict(request.POST))
            skip_attrs = ['admin', 'active']  # skip attr for my account
            if c.ldap_dn:
                #forbid updating username for ldap accounts
                skip_attrs.append('username')
            UserModel().update(uid, form_result, skip_attrs=skip_attrs)
            h.flash(_('Your account was updated successfully'),
                    category='success')
            Session().commit()
        except formencode.Invalid, errors:
            #json used to render the grid
            c.data = self._load_my_repos_data()
            c.form = htmlfill.render(
                render('admin/users/user_edit_my_account_form.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
            return render('admin/users/user_edit_my_account.html')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of user %s') \
                    % form_result.get('username'), category='error')

        return redirect(url('my_account'))

    @NotAnonymous()
    def my_account_my_pullrequests(self):
        c.show_closed = request.GET.get('pr_show_closed')

        def _filter(pr):
            s = sorted(pr, key=lambda o: o.created_on, reverse=True)
            if not c.show_closed:
                s = filter(lambda p: p.status != PullRequest.STATUS_CLOSED, s)
            return s

        c.my_pull_requests = _filter(PullRequest.query()\
                                .filter(PullRequest.user_id ==
                                        self.rhodecode_user.user_id)\
                                .all())

        c.participate_in_pull_requests = _filter([
                    x.pull_request for x in PullRequestReviewers.query()\
                    .filter(PullRequestReviewers.user_id ==
                            self.rhodecode_user.user_id).all()])

        return render('admin/users/user_edit_my_account_pullrequests.html')

    def _get_hg_ui_settings(self):
        ret = RhodeCodeUi.query().all()

        if not ret:
            raise Exception('Could not get application ui settings !')
        settings = {}
        for each in ret:
            k = each.ui_key
            v = each.ui_value
            if k == '/':
                k = 'root_path'

            if k == 'push_ssl':
                v = str2bool(v)

            if k.find('.') != -1:
                k = k.replace('.', '_')

            if each.ui_section in ['hooks', 'extensions']:
                v = each.ui_active

            settings[each.ui_section + '_' + k] = v
        return settings
