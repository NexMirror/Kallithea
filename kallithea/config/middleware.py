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
"""WSGI middleware initialization for the Kallithea application."""

from kallithea.config.app_cfg import base_config
from kallithea.config.environment import load_environment


__all__ = ['make_app']

# Use base_config to setup the necessary PasteDeploy application factory.
# make_base_app will wrap the TurboGears2 app with all the middleware it needs.
make_base_app = base_config.setup_tg_wsgi_app(load_environment)


def make_app_without_logging(global_conf, full_stack=True, **app_conf):
    """The core of make_app for use from gearbox commands (other than 'serve')"""
    return make_base_app(global_conf, full_stack=full_stack, **app_conf)


def make_app(global_conf, full_stack=True, **app_conf):
    """
    Set up Kallithea with the settings found in the PasteDeploy configuration
    file used.

    :param global_conf: The global settings for Kallithea (those
        defined under the ``[DEFAULT]`` section).
    :type global_conf: dict
    :param full_stack: Should the whole TurboGears2 stack be set up?
    :type full_stack: str or bool
    :return: The Kallithea application with all the relevant middleware
        loaded.

    This is the PasteDeploy factory for the Kallithea application.

    ``app_conf`` contains all the application-specific settings (those defined
    under ``[app:main]``.
    """
    return make_app_without_logging(global_conf, full_stack=full_stack, **app_conf)
