# -*- coding: utf-8 -*-
"""
    rhodecode.controllers.summary
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Summary controller for Rhodecode

    :created_on: Apr 18, 2010
    :author: marcink
    :copyright: (C) 2009-2011 Marcin Kuzminski <marcin@python-works.com>    
    :license: GPLv3, see COPYING for more details.
"""
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

import calendar
import logging
from time import mktime
from datetime import datetime, timedelta, date

from vcs.exceptions import ChangesetError

from pylons import tmpl_context as c, request, url
from pylons.i18n.translation import _

from rhodecode.model.scm import ScmModel
from rhodecode.model.db import Statistics

from rhodecode.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from rhodecode.lib.base import BaseController, render
from rhodecode.lib.utils import OrderedDict, EmptyChangeset

from rhodecode.lib.celerylib import run_task
from rhodecode.lib.celerylib.tasks import get_commits_stats

from webhelpers.paginate import Page

try:
    import json
except ImportError:
    #python 2.5 compatibility
    import simplejson as json
log = logging.getLogger(__name__)

class SummaryController(BaseController):

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def __before__(self):
        super(SummaryController, self).__before__()

    def index(self, repo_name):
        scm_model = ScmModel()
        c.repo_info = scm_model.get_repo(c.repo_name)
        c.following = scm_model.is_following_repo(c.repo_name,
                                             c.rhodecode_user.user_id)
        def url_generator(**kw):
            return url('shortlog_home', repo_name=repo_name, size=10, **kw)

        c.repo_changesets = Page(c.repo_info, page=1,
                                                items_per_page=10, url=url_generator)

        e = request.environ

        if self.rhodecode_user.username == 'default':
            password = ':default'
        else:
            password = ''

        uri = u'%(protocol)s://%(user)s%(password)s@%(host)s%(prefix)s/%(repo_name)s' % {
                                        'protocol': e.get('wsgi.url_scheme'),
                                        'user':str(c.rhodecode_user.username),
                                        'password':password,
                                        'host':e.get('HTTP_HOST'),
                                        'prefix':e.get('SCRIPT_NAME'),
                                        'repo_name':c.repo_name, }
        c.clone_repo_url = uri
        c.repo_tags = OrderedDict()
        for name, hash in c.repo_info.tags.items()[:10]:
            try:
                c.repo_tags[name] = c.repo_info.get_changeset(hash)
            except ChangesetError:
                c.repo_tags[name] = EmptyChangeset(hash)

        c.repo_branches = OrderedDict()
        for name, hash in c.repo_info.branches.items()[:10]:
            try:
                c.repo_branches[name] = c.repo_info.get_changeset(hash)
            except ChangesetError:
                c.repo_branches[name] = EmptyChangeset(hash)

        td = date.today() + timedelta(days=1)
        td_1m = td - timedelta(days=calendar.mdays[td.month])
        td_1y = td - timedelta(days=365)

        ts_min_m = mktime(td_1m.timetuple())
        ts_min_y = mktime(td_1y.timetuple())
        ts_max_y = mktime(td.timetuple())

        if c.repo_info.dbrepo.enable_statistics:
            c.no_data_msg = _('No data loaded yet')
            run_task(get_commits_stats, c.repo_info.name, ts_min_y, ts_max_y)
        else:
            c.no_data_msg = _('Statistics update are disabled for this repository')
        c.ts_min = ts_min_m
        c.ts_max = ts_max_y

        stats = self.sa.query(Statistics)\
            .filter(Statistics.repository == c.repo_info.dbrepo)\
            .scalar()


        if stats and stats.languages:
            c.no_data = False is c.repo_info.dbrepo.enable_statistics
            lang_stats = json.loads(stats.languages)
            c.commit_data = stats.commit_activity
            c.overview_data = stats.commit_activity_combined
            c.trending_languages = json.dumps(OrderedDict(
                                       sorted(lang_stats.items(), reverse=True,
                                            key=lambda k: k[1])[:10]
                                        )
                                    )
        else:
            c.commit_data = json.dumps({})
            c.overview_data = json.dumps([[ts_min_y, 0], [ts_max_y, 10] ])
            c.trending_languages = json.dumps({})
            c.no_data = True

        return render('summary/summary.html')

