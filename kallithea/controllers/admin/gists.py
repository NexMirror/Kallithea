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
kallithea.controllers.admin.gists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

gist controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 9, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

import formencode.htmlfill
from sqlalchemy.sql.expression import or_
from tg import request, response
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPForbidden, HTTPFound, HTTPNotFound

from kallithea.config.routing import url
from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired
from kallithea.lib.base import BaseController, jsonify, render
from kallithea.lib.page import Page
from kallithea.lib.utils2 import safe_int, safe_unicode, time_to_datetime
from kallithea.lib.vcs.exceptions import NodeNotChangedError, VCSError
from kallithea.model.db import Gist
from kallithea.model.forms import GistForm
from kallithea.model.gist import GistModel
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class GistsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""

    def __load_defaults(self, extra_values=None):
        c.lifetime_values = [
            (str(-1), _('Forever')),
            (str(5), _('5 minutes')),
            (str(60), _('1 hour')),
            (str(60 * 24), _('1 day')),
            (str(60 * 24 * 30), _('1 month')),
        ]
        if extra_values:
            c.lifetime_values.append(extra_values)
        c.lifetime_options = [(c.lifetime_values, _("Lifetime"))]

    @LoginRequired(allow_default_user=True)
    def index(self):
        not_default_user = not request.authuser.is_default_user
        c.show_private = request.GET.get('private') and not_default_user
        c.show_public = request.GET.get('public') and not_default_user

        gists = Gist().query() \
            .filter_by(is_expired=False) \
            .order_by(Gist.created_on.desc())

        # MY private
        if c.show_private and not c.show_public:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PRIVATE) \
                             .filter(Gist.owner_id == request.authuser.user_id)
        # MY public
        elif c.show_public and not c.show_private:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PUBLIC) \
                             .filter(Gist.owner_id == request.authuser.user_id)

        # MY public+private
        elif c.show_private and c.show_public:
            gists = gists.filter(or_(Gist.gist_type == Gist.GIST_PUBLIC,
                                     Gist.gist_type == Gist.GIST_PRIVATE)) \
                             .filter(Gist.owner_id == request.authuser.user_id)

        # default show ALL public gists
        if not c.show_public and not c.show_private:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PUBLIC)

        c.gists = gists
        p = safe_int(request.GET.get('page'), 1)
        c.gists_pager = Page(c.gists, page=p, items_per_page=10)
        return render('admin/gists/index.html')

    @LoginRequired()
    def create(self):
        self.__load_defaults()
        gist_form = GistForm([x[0] for x in c.lifetime_values])()
        try:
            form_result = gist_form.to_python(dict(request.POST))
            # TODO: multiple files support, from the form
            filename = form_result['filename'] or Gist.DEFAULT_FILENAME
            nodes = {
                filename: {
                    'content': form_result['content'],
                    'lexer': form_result['mimetype']  # None is autodetect
                }
            }
            _public = form_result['public']
            gist_type = Gist.GIST_PUBLIC if _public else Gist.GIST_PRIVATE
            gist = GistModel().create(
                description=form_result['description'],
                owner=request.authuser.user_id,
                ip_addr=request.ip_addr,
                gist_mapping=nodes,
                gist_type=gist_type,
                lifetime=form_result['lifetime']
            )
            Session().commit()
            new_gist_id = gist.gist_access_id
        except formencode.Invalid as errors:
            defaults = errors.value

            return formencode.htmlfill.render(
                render('admin/gists/new.html'),
                defaults=defaults,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8",
                force_defaults=False)

        except Exception as e:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during gist creation'), category='error')
            raise HTTPFound(location=url('new_gist'))
        raise HTTPFound(location=url('gist', gist_id=new_gist_id))

    @LoginRequired()
    def new(self, format='html'):
        self.__load_defaults()
        return render('admin/gists/new.html')

    @LoginRequired()
    def delete(self, gist_id):
        gist = GistModel().get_gist(gist_id)
        owner = gist.owner_id == request.authuser.user_id
        if h.HasPermissionAny('hg.admin')() or owner:
            GistModel().delete(gist)
            Session().commit()
            h.flash(_('Deleted gist %s') % gist.gist_access_id, category='success')
        else:
            raise HTTPForbidden()

        raise HTTPFound(location=url('gists'))

    @LoginRequired(allow_default_user=True)
    def show(self, gist_id, revision='tip', format='html', f_path=None):
        c.gist = Gist.get_or_404(gist_id)

        if c.gist.is_expired:
            log.error('Gist expired at %s',
                      time_to_datetime(c.gist.gist_expires))
            raise HTTPNotFound()
        try:
            c.file_changeset, c.files = GistModel().get_gist_files(gist_id,
                                                            revision=revision)
        except VCSError:
            log.error(traceback.format_exc())
            raise HTTPNotFound()
        if format == 'raw':
            content = '\n\n'.join([f.content for f in c.files if (f_path is None or safe_unicode(f.path) == f_path)])
            response.content_type = 'text/plain'
            return content
        return render('admin/gists/show.html')

    @LoginRequired()
    def edit(self, gist_id, format='html'):
        c.gist = Gist.get_or_404(gist_id)

        if c.gist.is_expired:
            log.error('Gist expired at %s',
                      time_to_datetime(c.gist.gist_expires))
            raise HTTPNotFound()
        try:
            c.file_changeset, c.files = GistModel().get_gist_files(gist_id)
        except VCSError:
            log.error(traceback.format_exc())
            raise HTTPNotFound()

        self.__load_defaults(extra_values=('0', _('Unmodified')))
        rendered = render('admin/gists/edit.html')

        if request.POST:
            rpost = request.POST
            nodes = {}
            for org_filename, filename, mimetype, content in zip(
                                                    rpost.getall('org_files'),
                                                    rpost.getall('files'),
                                                    rpost.getall('mimetypes'),
                                                    rpost.getall('contents')):

                nodes[org_filename] = {
                    'org_filename': org_filename,
                    'filename': filename,
                    'content': content,
                    'lexer': mimetype,
                }
            try:
                GistModel().update(
                    gist=c.gist,
                    description=rpost['description'],
                    owner=c.gist.owner, # FIXME: request.authuser.user_id ?
                    ip_addr=request.ip_addr,
                    gist_mapping=nodes,
                    gist_type=c.gist.gist_type,
                    lifetime=rpost['lifetime']
                )

                Session().commit()
                h.flash(_('Successfully updated gist content'), category='success')
            except NodeNotChangedError:
                # raised if nothing was changed in repo itself. We anyway then
                # store only DB stuff for gist
                Session().commit()
                h.flash(_('Successfully updated gist data'), category='success')
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during update of gist %s') % gist_id,
                        category='error')

            raise HTTPFound(location=url('gist', gist_id=gist_id))

        return rendered

    @LoginRequired()
    @jsonify
    def check_revision(self, gist_id):
        c.gist = Gist.get_or_404(gist_id)
        last_rev = c.gist.scm_instance.get_changeset()
        success = True
        revision = request.POST.get('revision')

        # TODO: maybe move this to model ?
        if revision != last_rev.raw_id:
            log.error('Last revision %s is different than submitted %s',
                      revision, last_rev)
            # our gist has newer version than we
            success = False

        return {'success': success}
