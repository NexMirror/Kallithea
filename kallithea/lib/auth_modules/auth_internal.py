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
kallithea.lib.auth_modules.auth_internal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea authentication plugin for built in internal auth

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Created on Nov 17, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging

from kallithea.lib import auth_modules
from kallithea.lib.compat import formatted_json, hybrid_property
from kallithea.model.db import User


log = logging.getLogger(__name__)


class KallitheaAuthPlugin(auth_modules.KallitheaAuthPluginBase):
    def __init__(self):
        pass

    @hybrid_property
    def name(self):
        # Also found as kallithea.lib.model.db.User.DEFAULT_AUTH_TYPE
        return 'internal'

    def settings(self):
        return []

    def accepts(self, user, accepts_empty=True):
        """
        Custom accepts for this auth that doesn't accept empty users. We
        know that user exists in database.
        """
        return super(KallitheaAuthPlugin, self).accepts(user,
                                                        accepts_empty=False)

    def auth(self, userobj, username, password, settings, **kwargs):
        if not userobj:
            log.debug('userobj was:%s skipping', userobj)
            return None
        if userobj.extern_type != self.name:
            log.warning("userobj:%s extern_type mismatch got:`%s` expected:`%s`",
                     userobj, userobj.extern_type, self.name)
            return None
        if not username:
            log.debug('Empty username - skipping...')
            return None

        user_data = {
            "username": userobj.username,
            "firstname": userobj.firstname,
            "lastname": userobj.lastname,
            "groups": [],
            "email": userobj.email,
            "admin": userobj.admin,
            "extern_name": userobj.user_id,
        }
        log.debug(formatted_json(user_data))

        from kallithea.lib import auth
        password_match = auth.check_password(password, userobj.password)
        if userobj.is_default_user:
            log.info('user %s authenticated correctly as anonymous user',
                     username)
            return user_data

        elif userobj.username == username and password_match:
            log.info('user %s authenticated correctly', user_data['username'])
            return user_data

        log.error("user %s had a bad password", username)
        return None

    def get_managed_fields(self):
        # Note: 'username' should only be editable (at least for user) if self registration is enabled
        return []
