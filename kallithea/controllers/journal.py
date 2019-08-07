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
kallithea.controllers.journal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Journal controller

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 21, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

import logging
import traceback
from itertools import groupby

from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from tg import request, response
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webhelpers.feedgenerator import Atom1Feed, Rss201rev2Feed
from webob.exc import HTTPBadRequest

import kallithea.lib.helpers as h
from kallithea.config.routing import url
from kallithea.controllers.admin.admin import _journal_filter
from kallithea.lib.auth import LoginRequired
from kallithea.lib.base import BaseController, render
from kallithea.lib.page import Page
from kallithea.lib.utils2 import AttributeDict, safe_int
from kallithea.model.db import Repository, User, UserFollowing, UserLog
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel


log = logging.getLogger(__name__)


language = 'en-us'
ttl = "5"
feed_nr = 20


class JournalController(BaseController):

    def _before(self, *args, **kwargs):
        super(JournalController, self)._before(*args, **kwargs)
        c.search_term = request.GET.get('filter')

    def _get_daily_aggregate(self, journal):
        groups = []
        for k, g in groupby(journal, lambda x: x.action_as_day):
            user_group = []
            # groupby username if it's a present value, else fallback to journal username
            for _unused, g2 in groupby(list(g), lambda x: x.user.username if x.user else x.username):
                l = list(g2)
                user_group.append((l[0].user, l))

            groups.append((k, user_group,))

        return groups

    def _get_journal_data(self, following_repos):
        repo_ids = [x.follows_repository_id for x in following_repos
                    if x.follows_repository_id is not None]
        user_ids = [x.follows_user_id for x in following_repos
                    if x.follows_user_id is not None]

        filtering_criterion = None

        if repo_ids and user_ids:
            filtering_criterion = or_(UserLog.repository_id.in_(repo_ids),
                        UserLog.user_id.in_(user_ids))
        if repo_ids and not user_ids:
            filtering_criterion = UserLog.repository_id.in_(repo_ids)
        if not repo_ids and user_ids:
            filtering_criterion = UserLog.user_id.in_(user_ids)
        if filtering_criterion is not None:
            journal = UserLog.query() \
                .options(joinedload(UserLog.user)) \
                .options(joinedload(UserLog.repository))
            # filter
            journal = _journal_filter(journal, c.search_term)
            journal = journal.filter(filtering_criterion) \
                        .order_by(UserLog.action_date.desc())
        else:
            journal = []

        return journal

    def _atom_feed(self, repos, public=True):
        journal = self._get_journal_data(repos)
        if public:
            _link = h.canonical_url('public_journal_atom')
            _desc = '%s %s %s' % (c.site_name, _('Public Journal'),
                                  'atom feed')
        else:
            _link = h.canonical_url('journal_atom')
            _desc = '%s %s %s' % (c.site_name, _('Journal'), 'atom feed')

        feed = Atom1Feed(title=_desc,
                         link=_link,
                         description=_desc,
                         language=language,
                         ttl=ttl)

        for entry in journal[:feed_nr]:
            user = entry.user
            if user is None:
                # fix deleted users
                user = AttributeDict({'short_contact': entry.username,
                                      'email': '',
                                      'full_contact': ''})
            action, action_extra, ico = h.action_parser(entry, feed=True)
            title = "%s - %s %s" % (user.short_contact, action(),
                                    entry.repository.repo_name)
            desc = action_extra()
            _url = None
            if entry.repository is not None:
                _url = h.canonical_url('changelog_home',
                           repo_name=entry.repository.repo_name)

            feed.add_item(title=title,
                          pubdate=entry.action_date,
                          link=_url or h.canonical_url(''),
                          author_email=user.email,
                          author_name=user.full_contact,
                          description=desc)

        response.content_type = feed.mime_type
        return feed.writeString('utf-8')

    def _rss_feed(self, repos, public=True):
        journal = self._get_journal_data(repos)
        if public:
            _link = h.canonical_url('public_journal_atom')
            _desc = '%s %s %s' % (c.site_name, _('Public Journal'),
                                  'rss feed')
        else:
            _link = h.canonical_url('journal_atom')
            _desc = '%s %s %s' % (c.site_name, _('Journal'), 'rss feed')

        feed = Rss201rev2Feed(title=_desc,
                         link=_link,
                         description=_desc,
                         language=language,
                         ttl=ttl)

        for entry in journal[:feed_nr]:
            user = entry.user
            if user is None:
                # fix deleted users
                user = AttributeDict({'short_contact': entry.username,
                                      'email': '',
                                      'full_contact': ''})
            action, action_extra, ico = h.action_parser(entry, feed=True)
            title = "%s - %s %s" % (user.short_contact, action(),
                                    entry.repository.repo_name)
            desc = action_extra()
            _url = None
            if entry.repository is not None:
                _url = h.canonical_url('changelog_home',
                           repo_name=entry.repository.repo_name)

            feed.add_item(title=title,
                          pubdate=entry.action_date,
                          link=_url or h.canonical_url(''),
                          author_email=user.email,
                          author_name=user.full_contact,
                          description=desc)

        response.content_type = feed.mime_type
        return feed.writeString('utf-8')

    @LoginRequired()
    def index(self):
        # Return a rendered template
        p = safe_int(request.GET.get('page'), 1)
        c.user = User.get(request.authuser.user_id)
        c.following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()

        journal = self._get_journal_data(c.following)

        def url_generator(**kw):
            return url.current(filter=c.search_term, **kw)

        c.journal_pager = Page(journal, page=p, items_per_page=20, url=url_generator)
        c.journal_day_aggregate = self._get_daily_aggregate(c.journal_pager)

        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            return render('journal/journal_data.html')

        repos_list = Repository.query(sorted=True) \
            .filter_by(owner_id=request.authuser.user_id).all()

        repos_data = RepoModel().get_repos_as_dict(repos_list, admin=True)
        # data used to render the grid
        c.data = repos_data

        return render('journal/journal.html')

    @LoginRequired()
    def journal_atom(self):
        """
        Produce an atom-1.0 feed via feedgenerator module
        """
        following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()
        return self._atom_feed(following, public=False)

    @LoginRequired()
    def journal_rss(self):
        """
        Produce an rss feed via feedgenerator module
        """
        following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()
        return self._rss_feed(following, public=False)

    @LoginRequired()
    def toggle_following(self):
        user_id = request.POST.get('follows_user_id')
        if user_id:
            try:
                self.scm_model.toggle_following_user(user_id,
                                            request.authuser.user_id)
                Session().commit()
                return 'ok'
            except Exception:
                log.error(traceback.format_exc())
                raise HTTPBadRequest()

        repo_id = request.POST.get('follows_repository_id')
        if repo_id:
            try:
                self.scm_model.toggle_following_repo(repo_id,
                                            request.authuser.user_id)
                Session().commit()
                return 'ok'
            except Exception:
                log.error(traceback.format_exc())
                raise HTTPBadRequest()

        raise HTTPBadRequest()

    @LoginRequired(allow_default_user=True)
    def public_journal(self):
        # Return a rendered template
        p = safe_int(request.GET.get('page'), 1)

        c.following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()

        journal = self._get_journal_data(c.following)

        c.journal_pager = Page(journal, page=p, items_per_page=20)

        c.journal_day_aggregate = self._get_daily_aggregate(c.journal_pager)

        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            return render('journal/journal_data.html')

        return render('journal/public_journal.html')

    @LoginRequired(allow_default_user=True)
    def public_journal_atom(self):
        """
        Produce an atom-1.0 feed via feedgenerator module
        """
        c.following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()

        return self._atom_feed(c.following)

    @LoginRequired(allow_default_user=True)
    def public_journal_rss(self):
        """
        Produce an rss2 feed via feedgenerator module
        """
        c.following = UserFollowing.query() \
            .filter(UserFollowing.user_id == request.authuser.user_id) \
            .options(joinedload(UserFollowing.follows_repository)) \
            .all()

        return self._rss_feed(c.following)
