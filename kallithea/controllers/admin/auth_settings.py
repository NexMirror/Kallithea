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
kallithea.controllers.admin.auth_settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pluggable authentication controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 26, 2010
:author: akesterson
"""

import logging
import formencode.htmlfill
import traceback

from pylons import request, tmpl_context as c, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea.lib import helpers as h
from kallithea.lib.compat import formatted_json
from kallithea.lib.base import BaseController, render
from kallithea.lib.auth import LoginRequired, HasPermissionAllDecorator
from kallithea.lib import auth_modules
from kallithea.model.forms import AuthSettingsForm
from kallithea.model.db import Setting
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class AuthSettingsController(BaseController):

    @LoginRequired()
    @HasPermissionAllDecorator('hg.admin')
    def __before__(self):
        super(AuthSettingsController, self).__before__()

    def __load_defaults(self):
        c.available_plugins = [
            'kallithea.lib.auth_modules.auth_internal',
            'kallithea.lib.auth_modules.auth_container',
            'kallithea.lib.auth_modules.auth_ldap',
            'kallithea.lib.auth_modules.auth_crowd',
            'kallithea.lib.auth_modules.auth_pam'
        ]
        c.enabled_plugins = Setting.get_auth_plugins()

    def __render(self, defaults, errors):
        c.defaults = {}
        c.plugin_settings = {}
        c.plugin_shortnames = {}

        for module in c.enabled_plugins:
            plugin = auth_modules.loadplugin(module)
            plugin_name = plugin.name
            c.plugin_shortnames[module] = plugin_name
            c.plugin_settings[module] = plugin.plugin_settings()
            for v in c.plugin_settings[module]:
                fullname = ("auth_" + plugin_name + "_" + v["name"])
                if "default" in v:
                    c.defaults[fullname] = v["default"]
                # Current values will be the default on the form, if there are any
                setting = Setting.get_by_name(fullname)
                if setting is not None:
                    c.defaults[fullname] = setting.app_settings_value
        # we want to show , separated list of enabled plugins
        c.defaults['auth_plugins'] = ','.join(c.enabled_plugins)

        if defaults:
            c.defaults.update(defaults)

        log.debug(formatted_json(defaults))
        return formencode.htmlfill.render(
            render('admin/auth/auth_settings.html'),
            defaults=c.defaults,
            errors=errors,
            prefix_error=False,
            encoding="UTF-8",
            force_defaults=False)

    def index(self):
        self.__load_defaults()
        return self.__render(defaults=None, errors=None)

    def auth_settings(self):
        """POST create and store auth settings"""
        self.__load_defaults()
        log.debug("POST Result: %s", formatted_json(dict(request.POST)))

        # First, parse only the plugin list (not the plugin settings).
        _auth_plugins_validator = AuthSettingsForm([]).fields['auth_plugins']
        try:
            new_enabled_plugins = _auth_plugins_validator.to_python(request.POST.get('auth_plugins'))
        except formencode.Invalid:
            # User provided an invalid plugin list. Just fall back to
            # the list of currently enabled plugins. (We'll re-validate
            # and show an error message to the user, below.)
            pass
        else:
            # Hide plugins that the user has asked to be disabled, but
            # do not show plugins that the user has asked to be enabled
            # (yet), since that'll cause validation errors and/or wrong
            # settings being applied (e.g. checkboxes being cleared),
            # since the plugin settings will not be in the POST data.
            c.enabled_plugins = [ p for p in c.enabled_plugins if p in new_enabled_plugins ]

        # Next, parse everything including plugin settings.
        _form = AuthSettingsForm(c.enabled_plugins)()

        try:
            form_result = _form.to_python(dict(request.POST))
            for k, v in form_result.items():
                if k == 'auth_plugins':
                    # we want to store it comma separated inside our settings
                    v = ','.join(v)
                log.debug("%s = %s", k, str(v))
                setting = Setting.create_or_update(k, v)
                Session().add(setting)
            Session().commit()
            h.flash(_('Auth settings updated successfully'),
                       category='success')
        except formencode.Invalid as errors:
            log.error(traceback.format_exc())
            e = errors.error_dict or {}
            return self.__render(
                defaults=errors.value,
                errors=e,
            )
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('error occurred during update of auth settings'),
                    category='error')

        return redirect(url('auth_home'))
