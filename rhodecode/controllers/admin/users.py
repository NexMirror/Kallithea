# -*- coding: utf-8 -*-
"""
    rhodecode.controllers.admin.users
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Users crud controller for pylons

    :created_on: Apr 4, 2010
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
from pylons import response

from formencode import htmlfill
from pylons import request, session, tmpl_context as c, url, config
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

import rhodecode
from rhodecode.lib.exceptions import DefaultUserException, \
    UserOwnsReposException, UserCreationError
from rhodecode.lib import helpers as h
from rhodecode.lib.auth import LoginRequired, HasPermissionAllDecorator, \
    AuthUser
from rhodecode.lib.base import BaseController, render

from rhodecode.model.db import User, UserEmailMap, UserIpMap, UserToPerm
from rhodecode.model.forms import UserForm, CustomDefaultPermissionsForm
from rhodecode.model.user import UserModel
from rhodecode.model.meta import Session
from rhodecode.lib.utils import action_logger
from rhodecode.lib.compat import json
from rhodecode.lib.utils2 import datetime_to_time, str2bool

log = logging.getLogger(__name__)


class UsersController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('user', 'users')

    @LoginRequired()
    @HasPermissionAllDecorator('hg.admin')
    def __before__(self):
        super(UsersController, self).__before__()
        c.available_permissions = config['available_permissions']

    def index(self, format='html'):
        """GET /users: All items in the collection"""
        # url('users')

        c.users_list = User.query().order_by(User.username)\
                        .filter(User.username != User.DEFAULT_USER)\
                        .all()

        users_data = []
        total_records = len(c.users_list)
        _tmpl_lookup = rhodecode.CONFIG['pylons.app_globals'].mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        grav_tmpl = lambda user_email, size: (
                template.get_def("user_gravatar")
                .render(user_email, size, _=_, h=h, c=c))

        user_lnk = lambda user_id, username: (
                template.get_def("user_name")
                .render(user_id, username, _=_, h=h, c=c))

        user_actions = lambda user_id, username: (
                template.get_def("user_actions")
                .render(user_id, username, _=_, h=h, c=c))

        for user in c.users_list:

            users_data.append({
                "gravatar": grav_tmpl(user. email, 24),
                "raw_username": user.username,
                "username": user_lnk(user.user_id, user.username),
                "firstname": user.name,
                "lastname": user.lastname,
                "last_login": h.fmt_date(user.last_login),
                "last_login_raw": datetime_to_time(user.last_login),
                "active": h.boolicon(user.active),
                "admin": h.boolicon(user.admin),
                "ldap": h.boolicon(bool(user.ldap_dn)),
                "action": user_actions(user.user_id, user.username),
            })

        c.data = json.dumps({
            "totalRecords": total_records,
            "startIndex": 0,
            "sort": None,
            "dir": "asc",
            "records": users_data
        })

        return render('admin/users/users.html')

    def create(self):
        """POST /users: Create a new item"""
        # url('users')

        user_model = UserModel()
        user_form = UserForm()()
        try:
            form_result = user_form.to_python(dict(request.POST))
            user_model.create(form_result)
            usr = form_result['username']
            action_logger(self.rhodecode_user, 'admin_created_user:%s' % usr,
                          None, self.ip_addr, self.sa)
            h.flash(_('Created user %s') % usr,
                    category='success')
            Session().commit()
        except formencode.Invalid, errors:
            return htmlfill.render(
                render('admin/users/user_add.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
        except UserCreationError, e:
            h.flash(e, 'error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during creation of user %s') \
                    % request.POST.get('username'), category='error')
        return redirect(url('users'))

    def new(self, format='html'):
        """GET /users/new: Form to create a new item"""
        # url('new_user')
        return render('admin/users/user_add.html')

    def update(self, id):
        """PUT /users/id: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('update_user', id=ID),
        #           method='put')
        # url('user', id=ID)
        user_model = UserModel()
        c.user = user_model.get(id)
        c.ldap_dn = c.user.ldap_dn
        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)
        _form = UserForm(edit=True, old_data={'user_id': id,
                                              'email': c.user.email})()
        form_result = {}
        try:
            form_result = _form.to_python(dict(request.POST))
            skip_attrs = []
            if c.ldap_dn:
                #forbid updating username for ldap accounts
                skip_attrs = ['username']
            user_model.update(id, form_result, skip_attrs=skip_attrs)
            usr = form_result['username']
            action_logger(self.rhodecode_user, 'admin_updated_user:%s' % usr,
                          None, self.ip_addr, self.sa)
            h.flash(_('User updated successfully'), category='success')
            Session().commit()
        except formencode.Invalid, errors:
            c.user_email_map = UserEmailMap.query()\
                            .filter(UserEmailMap.user == c.user).all()
            c.user_ip_map = UserIpMap.query()\
                            .filter(UserIpMap.user == c.user).all()
            defaults = errors.value
            e = errors.error_dict or {}
            defaults.update({
                'create_repo_perm': user_model.has_perm(id, 'hg.create.repository'),
                'fork_repo_perm': user_model.has_perm(id, 'hg.fork.repository'),
                '_method': 'put'
            })
            return htmlfill.render(
                render('admin/users/user_edit.html'),
                defaults=defaults,
                errors=e,
                prefix_error=False,
                encoding="UTF-8")
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of user %s') \
                    % form_result.get('username'), category='error')
        return redirect(url('edit_user', id=id))

    def delete(self, id):
        """DELETE /users/id: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('delete_user', id=ID),
        #           method='delete')
        # url('user', id=ID)
        usr = User.get_or_404(id)
        try:
            UserModel().delete(usr)
            Session().commit()
            h.flash(_('Successfully deleted user'), category='success')
        except (UserOwnsReposException, DefaultUserException), e:
            h.flash(e, category='warning')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during deletion of user'),
                    category='error')
        return redirect(url('users'))

    def show(self, id, format='html'):
        """GET /users/id: Show a specific item"""
        # url('user', id=ID)
        User.get_or_404(-1)

    def edit(self, id, format='html'):
        """GET /users/id/edit: Form to edit an existing item"""
        # url('edit_user', id=ID)
        c.user = User.get_or_404(id)

        if c.user.username == 'default':
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)
        c.user.permissions = {}
        c.granted_permissions = UserModel().fill_perms(c.user)\
            .permissions['global']
        c.user_email_map = UserEmailMap.query()\
                        .filter(UserEmailMap.user == c.user).all()
        c.user_ip_map = UserIpMap.query()\
                        .filter(UserIpMap.user == c.user).all()
        umodel = UserModel()
        c.ldap_dn = c.user.ldap_dn
        defaults = c.user.get_dict()
        defaults.update({
         'create_repo_perm': umodel.has_perm(c.user, 'hg.create.repository'),
         'create_user_group_perm': umodel.has_perm(c.user, 'hg.usergroup.create.true'),
         'fork_repo_perm': umodel.has_perm(c.user, 'hg.fork.repository'),
        })

        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    def update_perm(self, id):
        """PUT /users_perm/id: Update an existing item"""
        # url('user_perm', id=ID, method='put')
        user = User.get_or_404(id)

        try:
            form = CustomDefaultPermissionsForm()()
            form_result = form.to_python(request.POST)

            inherit_perms = form_result['inherit_default_permissions']
            user.inherit_default_permissions = inherit_perms
            Session().add(user)
            user_model = UserModel()

            defs = UserToPerm.query()\
                .filter(UserToPerm.user == user)\
                .all()
            for ug in defs:
                Session().delete(ug)

            if form_result['create_repo_perm']:
                user_model.grant_perm(id, 'hg.create.repository')
            else:
                user_model.grant_perm(id, 'hg.create.none')
            if form_result['create_user_group_perm']:
                user_model.grant_perm(id, 'hg.usergroup.create.true')
            else:
                user_model.grant_perm(id, 'hg.usergroup.create.false')
            if form_result['fork_repo_perm']:
                user_model.grant_perm(id, 'hg.fork.repository')
            else:
                user_model.grant_perm(id, 'hg.fork.none')
            h.flash(_("Updated permissions"), category='success')
            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during permissions saving'),
                    category='error')
        return redirect(url('edit_user', id=id))

    def add_email(self, id):
        """POST /user_emails:Add an existing item"""
        # url('user_emails', id=ID, method='put')

        email = request.POST.get('new_email')
        user_model = UserModel()

        try:
            user_model.add_extra_email(id, email)
            Session().commit()
            h.flash(_("Added email %s to user") % email, category='success')
        except formencode.Invalid, error:
            msg = error.error_dict['email']
            h.flash(msg, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during email saving'),
                    category='error')
        return redirect(url('edit_user', id=id))

    def delete_email(self, id):
        """DELETE /user_emails_delete/id: Delete an existing item"""
        # url('user_emails_delete', id=ID, method='delete')
        user_model = UserModel()
        user_model.delete_extra_email(id, request.POST.get('del_email'))
        Session().commit()
        h.flash(_("Removed email from user"), category='success')
        return redirect(url('edit_user', id=id))

    def add_ip(self, id):
        """POST /user_ips:Add an existing item"""
        # url('user_ips', id=ID, method='put')

        ip = request.POST.get('new_ip')
        user_model = UserModel()

        try:
            user_model.add_extra_ip(id, ip)
            Session().commit()
            h.flash(_("Added ip %s to user") % ip, category='success')
        except formencode.Invalid, error:
            msg = error.error_dict['ip']
            h.flash(msg, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during ip saving'),
                    category='error')
        if 'default_user' in request.POST:
            return redirect(url('edit_permission', id='default'))
        return redirect(url('edit_user', id=id))

    def delete_ip(self, id):
        """DELETE /user_ips_delete/id: Delete an existing item"""
        # url('user_ips_delete', id=ID, method='delete')
        user_model = UserModel()
        user_model.delete_extra_ip(id, request.POST.get('del_ip'))
        Session().commit()
        h.flash(_("Removed ip from user"), category='success')
        if 'default_user' in request.POST:
            return redirect(url('edit_permission', id='default'))
        return redirect(url('edit_user', id=id))
