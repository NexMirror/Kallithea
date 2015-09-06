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
kallithea.controllers.error
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea error controller

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 8, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import os
import cgi
import logging
import paste.fileapp

from pylons import tmpl_context as c, request, config
from pylons.i18n.translation import _
from pylons.middleware import media_path

from kallithea.lib.base import BaseController, render

log = logging.getLogger(__name__)


class ErrorController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behavior can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.
    """

    def __before__(self):
        # disable all base actions since we don't need them here
        pass

    def document(self):
        resp = request.environ.get('pylons.original_response')
        c.site_name = config.get('title')

        log.debug('### %s ###', resp and resp.status or 'no response')

        e = request.environ
        c.serv_p = r'%(protocol)s://%(host)s/' % {
            'protocol': e.get('wsgi.url_scheme'),
            'host': e.get('HTTP_HOST'), }
        if resp:
            c.error_message = cgi.escape(request.GET.get('code',
                                                         str(resp.status)))
            c.error_explanation = self.get_error_explanation(resp.status_int)
        else:
            c.error_message = _('No response')
            c.error_explanation = _('Unknown error')

        return render('/errors/error_document.html')

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file(os.path.join(media_path, 'img', id))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file(os.path.join(media_path, 'style', id))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        fapp = paste.fileapp.FileApp(path)
        return fapp(request.environ, self.start_response)

    def get_error_explanation(self, code):
        """ get the error explanations of int codes
            [400, 401, 403, 404, 500]"""
        try:
            code = int(code)
        except ValueError:
            code = 500

        if code == 400:
            return _('The request could not be understood by the server'
                     ' due to malformed syntax.')
        if code == 401:
            return _('Unauthorized access to resource')
        if code == 403:
            return _("You don't have permission to view this page")
        if code == 404:
            return _('The resource could not be found')
        if code == 500:
            return _('The server encountered an unexpected condition'
                     ' which prevented it from fulfilling the request.')
