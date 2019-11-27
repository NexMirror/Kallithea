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
kallithea.controllers.changelog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

changelog controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 21, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

from tg import request, session
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPBadRequest, HTTPFound, HTTPNotFound

import kallithea.lib.helpers as h
from kallithea.config.routing import url
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.graphmod import graph_data
from kallithea.lib.page import RepoPage
from kallithea.lib.utils2 import safe_int, safe_str
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError, ChangesetError, EmptyRepositoryError, NodeDoesNotExistError, RepositoryError


log = logging.getLogger(__name__)


class ChangelogController(BaseRepoController):

    def _before(self, *args, **kwargs):
        super(ChangelogController, self)._before(*args, **kwargs)
        c.affected_files_cut_off = 60

    @staticmethod
    def __get_cs(rev, repo):
        """
        Safe way to get changeset. If error occur fail with error message.

        :param rev: revision to fetch
        :param repo: repo instance
        """

        try:
            return c.db_repo_scm_instance.get_changeset(rev)
        except EmptyRepositoryError as e:
            h.flash(_('There are no changesets yet'), category='error')
        except RepositoryError as e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='error')
        raise HTTPBadRequest()

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def index(self, repo_name, revision=None, f_path=None):
        limit = 2000
        default = 100
        if request.GET.get('size'):
            c.size = max(min(safe_int(request.GET.get('size')), limit), 1)
            session['changelog_size'] = c.size
            session.save()
        else:
            c.size = int(session.get('changelog_size', default))
        # min size must be 1
        c.size = max(c.size, 1)
        p = safe_int(request.GET.get('page'), 1)
        branch_name = request.GET.get('branch', None)
        if (branch_name and
            branch_name not in c.db_repo_scm_instance.branches and
            branch_name not in c.db_repo_scm_instance.closed_branches and
            not revision
        ):
            raise HTTPFound(location=url('changelog_file_home', repo_name=c.repo_name,
                                    revision=branch_name, f_path=f_path or ''))

        if revision == 'tip':
            revision = None

        c.changelog_for_path = f_path
        try:

            if f_path:
                log.debug('generating changelog for path %s', f_path)
                # get the history for the file !
                tip_cs = c.db_repo_scm_instance.get_changeset()
                try:
                    collection = tip_cs.get_file_history(f_path)
                except (NodeDoesNotExistError, ChangesetError):
                    # this node is not present at tip !
                    try:
                        cs = self.__get_cs(revision, repo_name)
                        collection = cs.get_file_history(f_path)
                    except RepositoryError as e:
                        h.flash(safe_str(e), category='warning')
                        raise HTTPFound(location=h.url('changelog_home', repo_name=repo_name))
                collection = list(reversed(collection))
            else:
                collection = c.db_repo_scm_instance.get_changesets(start=0, end=revision,
                                                        branch_name=branch_name)
            c.total_cs = len(collection)

            c.cs_pagination = RepoPage(collection, page=p, item_count=c.total_cs,
                                    items_per_page=c.size, branch=branch_name,)

            page_revisions = [x.raw_id for x in c.cs_pagination]
            c.cs_comments = c.db_repo.get_comments(page_revisions)
            c.cs_statuses = c.db_repo.statuses(page_revisions)
        except EmptyRepositoryError as e:
            h.flash(safe_str(e), category='warning')
            raise HTTPFound(location=url('summary_home', repo_name=c.repo_name))
        except (RepositoryError, ChangesetDoesNotExistError, Exception) as e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='error')
            raise HTTPFound(location=url('changelog_home', repo_name=c.repo_name))

        c.branch_name = branch_name
        c.branch_filters = [('', _('None'))] + \
            [(k, k) for k in c.db_repo_scm_instance.branches.keys()]
        if c.db_repo_scm_instance.closed_branches:
            prefix = _('(closed)') + ' '
            c.branch_filters += [('-', '-')] + \
                [(k, prefix + k) for k in c.db_repo_scm_instance.closed_branches.keys()]
        revs = []
        if not f_path:
            revs = [x.revision for x in c.cs_pagination]
        c.jsdata = graph_data(c.db_repo_scm_instance, revs)

        c.revision = revision # requested revision ref
        c.first_revision = c.cs_pagination[0] # pagination is never empty here!
        return render('changelog/changelog.html')

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def changelog_details(self, cs):
        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            c.cs = c.db_repo_scm_instance.get_changeset(cs)
            return render('changelog/changelog_details.html')
        raise HTTPNotFound()
