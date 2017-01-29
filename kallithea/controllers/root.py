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
from tgext.routes import RoutedController
from kallithea.lib.base import BaseController
from kallithea.controllers.error import ErrorController


# With TurboGears, the RootController is the controller from which all routing
# starts from. It is 'magically' found based on the fact that a controller
# 'foo' is expected to have a class name FooController, located in a file
# foo.py, inside config['paths']['controllers']. The name 'root' for the root
# controller is the default name. The dictionary config['paths'] determines the
# directories where templates, static files and controllers are found. It is
# set up in tg.AppConfig based on AppConfig['package'] ('kallithea') and the
# respective defaults 'templates', 'public' and 'controllers'.
# Inherit from RoutedController to allow Kallithea to use regex-based routing.
class RootController(RoutedController, BaseController):

    # the following assignment hooks in error handling
    error = ErrorController()
