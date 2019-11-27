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
from tg import config
from tgext.routes import RoutedController

from kallithea.config.routing import make_map
from kallithea.controllers.error import ErrorController
from kallithea.lib.base import BaseController


# This is the main Kallithea entry point; TurboGears will forward all requests
# to an instance of 'controller.root.RootController' in the configured
# 'application' module (set by app_cfg.py).  Requests are forwarded to
# controllers based on the routing mapper that lives in this root instance.
# The mapper is configured using routes defined in routing.py.  This use of the
# 'mapper' attribute is a feature of tgext.routes, which is activated by
# inheriting from its RoutedController class.
class RootController(RoutedController, BaseController):

    def __init__(self):
        self.mapper = make_map(config)

        # the following assignment hooks in error handling
        self.error = ErrorController()
