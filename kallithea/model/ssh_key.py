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
kallithea.model.ssh_key
~~~~~~~~~~~~~~~~~~~~~~~

SSH key model for Kallithea

"""

import logging

from kallithea.model.db import UserSshKeys, User
from kallithea.model.meta import Session

log = logging.getLogger(__name__)

class SshKeyModel(object):

    def create(self, user, description, public_key):
        """
        :param user: user or user_id
        :param description: description of SshKey
        :param publickey: public key text
        """
        user = User.guess_instance(user)

        new_ssh_key = UserSshKeys()
        new_ssh_key.user_id = user.user_id
        new_ssh_key.description = description
        new_ssh_key.public_key = public_key
        Session().add(new_ssh_key)

        return new_ssh_key

    def delete(self, public_key, user=None):
        """
        Deletes given public_key, if user is set it also filters the object for
        deletion by given user.
        """
        ssh_key = UserSshKeys.query().filter(UserSshKeys._public_key == public_key)

        if user:
            user = User.guess_instance(user)
            ssh_key = ssh_key.filter(UserSshKeys.user_id == user.user_id)

        ssh_key = ssh_key.scalar()
        Session().delete(ssh_key)

    def get_ssh_keys(self, user):
        user = User.guess_instance(user)
        user_ssh_keys = UserSshKeys.query() \
            .filter(UserSshKeys.user_id == user.user_id).all()
        return user_ssh_keys
