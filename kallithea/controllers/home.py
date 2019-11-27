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
kallithea.controllers.home
~~~~~~~~~~~~~~~~~~~~~~~~~~

Home controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Feb 18, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

import logging

from sqlalchemy import or_
from tg import request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPBadRequest

from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseController, jsonify, render
from kallithea.lib.utils import conditional_cache
from kallithea.model.db import RepoGroup, Repository, User, UserGroup
from kallithea.model.repo import RepoModel
from kallithea.model.scm import UserGroupList


log = logging.getLogger(__name__)


class HomeController(BaseController):

    def about(self):
        return render('/about.html')

    @LoginRequired(allow_default_user=True)
    def index(self):
        c.group = None

        repo_groups_list = self.scm_model.get_repo_groups()
        repos_list = Repository.query(sorted=True).filter_by(group=None).all()

        c.data = RepoModel().get_repos_as_dict(repos_list,
                                               repo_groups_list=repo_groups_list,
                                               short_name=True)

        return render('/index.html')

    @LoginRequired(allow_default_user=True)
    @jsonify
    def repo_switcher_data(self):
        # wrapper for conditional cache
        def _c():
            log.debug('generating switcher repo/groups list')
            all_repos = Repository.query(sorted=True).all()
            repo_iter = self.scm_model.get_repos(all_repos)
            all_groups = RepoGroup.query(sorted=True).all()
            repo_groups_iter = self.scm_model.get_repo_groups(all_groups)

            res = [{
                    'text': _('Groups'),
                    'children': [
                       {'id': obj.group_name,
                        'text': obj.group_name,
                        'type': 'group',
                        'obj': {}}
                       for obj in repo_groups_iter
                    ],
                   },
                   {
                    'text': _('Repositories'),
                    'children': [
                       {'id': obj.repo_name,
                        'text': obj.repo_name,
                        'type': 'repo',
                        'obj': obj.get_dict()}
                       for obj in repo_iter
                    ],
                   }]

            data = {
                'more': False,
                'results': res,
            }
            return data

        if request.is_xhr:
            condition = False
            compute = conditional_cache('short_term', 'cache_desc',
                                        condition=condition, func=_c)
            return compute()
        else:
            raise HTTPBadRequest()

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def repo_refs_data(self, repo_name):
        repo = Repository.get_by_repo_name(repo_name).scm_instance
        res = []
        _branches = repo.branches.items()
        if _branches:
            res.append({
                'text': _('Branch'),
                'children': [{'id': rev, 'text': name, 'type': 'branch'} for name, rev in _branches]
            })
        _closed_branches = repo.closed_branches.items()
        if _closed_branches:
            res.append({
                'text': _('Closed Branches'),
                'children': [{'id': rev, 'text': name, 'type': 'closed-branch'} for name, rev in _closed_branches]
            })
        _tags = repo.tags.items()
        if _tags:
            res.append({
                'text': _('Tag'),
                'children': [{'id': rev, 'text': name, 'type': 'tag'} for name, rev in _tags]
            })
        _bookmarks = repo.bookmarks.items()
        if _bookmarks:
            res.append({
                'text': _('Bookmark'),
                'children': [{'id': rev, 'text': name, 'type': 'book'} for name, rev in _bookmarks]
            })
        data = {
            'more': False,
            'results': res
        }
        return data

    @LoginRequired()
    @jsonify
    def users_and_groups_data(self):
        """
        Returns 'results' with a list of users and user groups.

        You can either use the 'key' GET parameter to get a user by providing
        the exact user key or you can use the 'query' parameter to
        search for users by user key, first name and last name.
        'types' defaults to just 'users' but can be set to 'users,groups' to
        get both users and groups.
        No more than 500 results (of each kind) will be returned.
        """
        types = request.GET.get('types', 'users').split(',')
        key = request.GET.get('key', '')
        query = request.GET.get('query', '')
        results = []
        if 'users' in types:
            user_list = []
            if key:
                u = User.get_by_username(key)
                if u:
                    user_list = [u]
            elif query:
                user_list = User.query() \
                    .filter(User.is_default_user == False) \
                    .filter(User.active == True) \
                    .filter(or_(
                        User.username.ilike("%%" + query + "%%"),
                        User.name.ilike("%%" + query + "%%"),
                        User.lastname.ilike("%%" + query + "%%"),
                    )) \
                    .order_by(User.username) \
                    .limit(500) \
                    .all()
            for u in user_list:
                results.append({
                    'type': 'user',
                    'id': u.user_id,
                    'nname': u.username,
                    'fname': u.name,
                    'lname': u.lastname,
                    'gravatar_lnk': h.gravatar_url(u.email, size=28, default='default'),
                    'gravatar_size': 14,
                })
        if 'groups' in types:
            grp_list = []
            if key:
                grp = UserGroup.get_by_group_name(key)
                if grp:
                    grp_list = [grp]
            elif query:
                grp_list = UserGroup.query() \
                    .filter(UserGroup.users_group_name.ilike("%%" + query + "%%")) \
                    .filter(UserGroup.users_group_active == True) \
                    .order_by(UserGroup.users_group_name) \
                    .limit(500) \
                    .all()
            for g in UserGroupList(grp_list, perm_level='read'):
                results.append({
                    'type': 'group',
                    'id': g.users_group_id,
                    'grname': g.users_group_name,
                })
        return dict(results=results)
