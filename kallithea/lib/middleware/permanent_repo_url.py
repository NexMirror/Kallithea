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
kallithea.lib.middleware.permanent_repo_url
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

middleware to handle permanent repo URLs, replacing PATH_INFO '/_123/yada' with
'/name/of/repo/yada' after looking 123 up in the database.
"""


from kallithea.lib.utils import fix_repo_id_name, safe_str


class PermanentRepoUrl(object):

    def __init__(self, app, config):
        self.application = app
        self.config = config

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        if path_info.startswith('/'): # it must
            path_info = '/' + safe_str(fix_repo_id_name(path_info[1:]))
            environ['PATH_INFO'] = path_info

        return self.application(environ, start_response)
