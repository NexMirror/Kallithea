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
kallithea.lib.middleware.sessionmiddleware
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

session management middleware

This file overrides Beaker's built-in SessionMiddleware
class to automagically use secure cookies over HTTPS.

Original Beaker SessionMiddleware class written by Ben Bangert
"""

from beaker.session import SessionObject
from beaker.middleware import SessionMiddleware

class SecureSessionMiddleware(SessionMiddleware):
    def __call__(self, environ, start_response):
        """
        This function's implementation is taken directly from Beaker,
        with HTTPS detection added. When accessed over HTTPS, force
        setting cookie's secure flag.

        The only difference from that original code is that we switch
        the secure option on and off depending on the URL scheme (first
        two lines). To avoid concurrency issues, we use a local options
        variable.
        """
        options = dict(self.options)
        options["secure"] = environ['wsgi.url_scheme'] == 'https'

        session = SessionObject(environ, **options)
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session

        if 'paste.testing_variables' in environ and 'webtest_varname' in options:
            environ['paste.testing_variables'][options['webtest_varname']] = session

        def session_start_response(status, headers, exc_info=None):
            if session.accessed():
                session.persist()
                if session.__dict__['_headers']['set_cookie']:
                    cookie = session.__dict__['_headers']['cookie_out']
                    if cookie:
                        headers.append(('Set-cookie', cookie))
            return start_response(status, headers, exc_info)
        return self.wrap_app(environ, session_start_response)
