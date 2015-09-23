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
kallithea.controllers.login
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Login controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 22, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import re
import formencode

from formencode import htmlfill
from webob.exc import HTTPFound, HTTPBadRequest
from pylons.i18n.translation import _
from pylons.controllers.util import redirect
from pylons import request, session, tmpl_context as c, url

import kallithea.lib.helpers as h
from kallithea.lib.auth import AuthUser, HasPermissionAnyDecorator
from kallithea.lib.base import BaseController, log_in_user, render
from kallithea.lib.exceptions import UserCreationError
from kallithea.lib.utils2 import safe_str
from kallithea.model.db import User, Setting
from kallithea.model.forms import \
    LoginForm, RegisterForm, PasswordResetRequestForm, PasswordResetConfirmationForm
from kallithea.model.user import UserModel
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class LoginController(BaseController):

    def __before__(self):
        super(LoginController, self).__before__()

    def _validate_came_from(self, came_from,
            _re=re.compile(r"/(?!/)[-!#$%&'()*+,./:;=?@_~0-9A-Za-z]*$")):
        """Return True if came_from is valid and can and should be used.

        Determines if a URI reference is valid and relative to the origin;
        or in RFC 3986 terms, whether it matches this production:

          origin-relative-ref = path-absolute [ "?" query ] [ "#" fragment ]

        with the exception that '%' escapes are not validated and '#' is
        allowed inside the fragment part.
        """
        return _re.match(came_from) is not None

    def index(self):
        c.came_from = safe_str(request.GET.get('came_from', ''))
        if c.came_from:
            if not self._validate_came_from(c.came_from):
                log.error('Invalid came_from (not server-relative): %r', c.came_from)
                raise HTTPBadRequest()
        else:
            c.came_from = url('home')

        not_default = self.authuser.username != User.DEFAULT_USER
        ip_allowed = AuthUser.check_ip_allowed(self.authuser, self.ip_addr)

        # redirect if already logged in
        if self.authuser.is_authenticated and not_default and ip_allowed:
            raise HTTPFound(location=c.came_from)

        if request.POST:
            # import Login Form validator class
            login_form = LoginForm()
            try:
                c.form_result = login_form.to_python(dict(request.POST))
                # form checks for username/password, now we're authenticated
                username = c.form_result['username']
                user = User.get_by_username(username, case_insensitive=True)
            except formencode.Invalid as errors:
                defaults = errors.value
                # remove password from filling in form again
                del defaults['password']
                return htmlfill.render(
                    render('/login.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8",
                    force_defaults=False)
            except UserCreationError as e:
                # container auth or other auth functions that create users on
                # the fly can throw this exception signaling that there's issue
                # with user creation, explanation should be provided in
                # Exception itself
                h.flash(e, 'error')
            else:
                log_in_user(user, c.form_result['remember'],
                    is_external_auth=False)
                raise HTTPFound(location=c.came_from)

        return render('/login.html')

    @HasPermissionAnyDecorator('hg.admin', 'hg.register.auto_activate',
                               'hg.register.manual_activate')
    def register(self):
        c.auto_active = 'hg.register.auto_activate' in User.get_default_user()\
            .AuthUser.permissions['global']

        settings = Setting.get_app_settings()
        captcha_private_key = settings.get('captcha_private_key')
        c.captcha_active = bool(captcha_private_key)
        c.captcha_public_key = settings.get('captcha_public_key')

        if request.POST:
            register_form = RegisterForm()()
            try:
                form_result = register_form.to_python(dict(request.POST))
                form_result['active'] = c.auto_active

                if c.captcha_active:
                    from kallithea.lib.recaptcha import submit
                    response = submit(request.POST.get('recaptcha_challenge_field'),
                                      request.POST.get('recaptcha_response_field'),
                                      private_key=captcha_private_key,
                                      remoteip=self.ip_addr)
                    if c.captcha_active and not response.is_valid:
                        _value = form_result
                        _msg = _('Bad captcha')
                        error_dict = {'recaptcha_field': _msg}
                        raise formencode.Invalid(_msg, _value, None,
                                                 error_dict=error_dict)

                UserModel().create_registration(form_result)
                h.flash(_('You have successfully registered into Kallithea'),
                        category='success')
                Session().commit()
                return redirect(url('login_home'))

            except formencode.Invalid as errors:
                return htmlfill.render(
                    render('/register.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8",
                    force_defaults=False)
            except UserCreationError as e:
                # container auth or other auth functions that create users on
                # the fly can throw this exception signaling that there's issue
                # with user creation, explanation should be provided in
                # Exception itself
                h.flash(e, 'error')

        return render('/register.html')

    def password_reset(self):
        settings = Setting.get_app_settings()
        captcha_private_key = settings.get('captcha_private_key')
        c.captcha_active = bool(captcha_private_key)
        c.captcha_public_key = settings.get('captcha_public_key')

        if request.POST:
            password_reset_form = PasswordResetRequestForm()()
            try:
                form_result = password_reset_form.to_python(dict(request.POST))
                if c.captcha_active:
                    from kallithea.lib.recaptcha import submit
                    response = submit(request.POST.get('recaptcha_challenge_field'),
                                      request.POST.get('recaptcha_response_field'),
                                      private_key=captcha_private_key,
                                      remoteip=self.ip_addr)
                    if c.captcha_active and not response.is_valid:
                        _value = form_result
                        _msg = _('Bad captcha')
                        error_dict = {'recaptcha_field': _msg}
                        raise formencode.Invalid(_msg, _value, None,
                                                 error_dict=error_dict)
                redirect_link = UserModel().send_reset_password_email(form_result)
                h.flash(_('A password reset confirmation code has been sent'),
                            category='success')
                return redirect(redirect_link)

            except formencode.Invalid as errors:
                return htmlfill.render(
                    render('/password_reset.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8",
                    force_defaults=False)

        return render('/password_reset.html')

    def password_reset_confirmation(self):
        # This controller handles both GET and POST requests, though we
        # only ever perform the actual password change on POST (since
        # GET requests are not allowed to have side effects, and do not
        # receive automatic CSRF protection).

        # The template needs the email address outside of the form.
        c.email = request.params.get('email')

        if not request.POST:
            return htmlfill.render(
                render('/password_reset_confirmation.html'),
                defaults=dict(request.params),
                encoding='UTF-8')

        form = PasswordResetConfirmationForm()()
        try:
            form_result = form.to_python(dict(request.POST))
        except formencode.Invalid as errors:
            return htmlfill.render(
                render('/password_reset_confirmation.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding='UTF-8')

        if not UserModel().verify_reset_password_token(
            form_result['email'],
            form_result['timestamp'],
            form_result['token'],
        ):
            return htmlfill.render(
                render('/password_reset_confirmation.html'),
                defaults=form_result,
                errors={'token': _('Invalid password reset token')},
                prefix_error=False,
                encoding='UTF-8')

        UserModel().reset_password(form_result['email'], form_result['password'])
        h.flash(_('Successfully updated password'), category='success')
        return redirect(url('login_home'))

    def logout(self):
        session.delete()
        log.info('Logging out and deleting session for user')
        redirect(url('home'))

    def authentication_token(self):
        """Return the CSRF protection token for the session - just like it
        could have been screen scraped from a page with a form.
        Only intended for testing but might also be useful for other kinds
        of automation.
        """
        return h.authentication_token()
