#!/usr/bin/env python
# encoding: utf-8
# summary controller for pylons
# Copyright (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your opinion) any later version of the license.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.
"""
Created on April 18, 2010
summary controller for pylons
@author: marcink
"""
from pylons import tmpl_context as c, request, url
from pylons_app.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from pylons_app.lib.base import BaseController, render
from pylons_app.lib.utils import OrderedDict
from pylons_app.model.hg_model import HgModel
from webhelpers.paginate import Page
from pylons_app.lib.celerylib import run_task
from pylons_app.lib.celerylib.tasks import get_commits_stats
import logging

log = logging.getLogger(__name__)

class SummaryController(BaseController):
    
    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')           
    def __before__(self):
        super(SummaryController, self).__before__()
                
    def index(self):
        hg_model = HgModel()
        c.repo_info = hg_model.get_repo(c.repo_name)
        c.repo_changesets = Page(list(c.repo_info[:10]), page=1, items_per_page=20)
        e = request.environ
        uri = u'%(protocol)s://%(user)s@%(host)s/%(repo_name)s' % {
                                        'protocol': e.get('wsgi.url_scheme'),
                                        'user':str(c.hg_app_user.username),
                                        'host':e.get('HTTP_HOST'),
                                        'repo_name':c.repo_name, }
        c.clone_repo_url = uri
        c.repo_tags = OrderedDict()
        for name, hash in c.repo_info.tags.items()[:10]:
            c.repo_tags[name] = c.repo_info.get_changeset(hash)
        
        c.repo_branches = OrderedDict()
        for name, hash in c.repo_info.branches.items()[:10]:
            c.repo_branches[name] = c.repo_info.get_changeset(hash)
        
        task = run_task(get_commits_stats, c.repo_info.name)
        c.ts_min = task.result[0]
        c.ts_max = task.result[1]
        c.commit_data = task.result[2]
        c.overview_data = task.result[3]
        
        return render('summary/summary.html')

