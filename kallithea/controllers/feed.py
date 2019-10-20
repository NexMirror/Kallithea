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
kallithea.controllers.feed
~~~~~~~~~~~~~~~~~~~~~~~~~~

Feed controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 23, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging

from beaker.cache import cache_region
from tg import response
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webhelpers.feedgenerator import Atom1Feed, Rss201rev2Feed

from kallithea import CONFIG
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseRepoController
from kallithea.lib.diffs import DiffProcessor
from kallithea.lib.utils2 import safe_int, safe_unicode, str2bool


log = logging.getLogger(__name__)


language = 'en-us'
ttl = "5"


class FeedController(BaseRepoController):

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def _before(self, *args, **kwargs):
        super(FeedController, self)._before(*args, **kwargs)

    def _get_title(self, cs):
        return h.shorter(cs.message, 160)

    def __get_desc(self, cs):
        desc_msg = [(_('%s committed on %s')
                     % (h.person(cs.author), h.fmt_date(cs.date))) + '<br/>']
        # branches, tags, bookmarks
        for branch in cs.branches:
            desc_msg.append('branch: %s<br/>' % branch)
        for book in cs.bookmarks:
            desc_msg.append('bookmark: %s<br/>' % book)
        for tag in cs.tags:
            desc_msg.append('tag: %s<br/>' % tag)

        changes = []
        diff_limit = safe_int(CONFIG.get('rss_cut_off_limit', 32 * 1024))
        raw_diff = cs.diff()
        diff_processor = DiffProcessor(raw_diff,
                                       diff_limit=diff_limit,
                                       inline_diff=False)

        for st in diff_processor.parsed:
            st.update({'added': st['stats']['added'],
                       'removed': st['stats']['deleted']})
            changes.append('\n %(operation)s %(filename)s '
                           '(%(added)s lines added, %(removed)s lines removed)'
                            % st)
        if diff_processor.limited_diff:
            changes = changes + ['\n ' +
                                 _('Changeset was too big and was cut off...')]

        # rev link
        _url = h.canonical_url('changeset_home', repo_name=c.db_repo.repo_name,
                   revision=cs.raw_id)
        desc_msg.append('changeset: <a href="%s">%s</a>' % (_url, cs.raw_id[:8]))

        desc_msg.append('<pre>')
        desc_msg.append(h.urlify_text(cs.message))
        desc_msg.append('\n')
        desc_msg.extend(changes)
        if str2bool(CONFIG.get('rss_include_diff', False)):
            desc_msg.append('\n\n')
            desc_msg.append(raw_diff)
        desc_msg.append('</pre>')
        return map(safe_unicode, desc_msg)

    def atom(self, repo_name):
        """Produce an atom-1.0 feed via feedgenerator module"""

        @cache_region('long_term', '_get_feed_from_cache')
        def _get_feed_from_cache(*_cache_keys):  # parameters are not really used - only as caching key
            feed = Atom1Feed(
                title=_('%s %s feed') % (c.site_name, repo_name),
                link=h.canonical_url('summary_home', repo_name=repo_name),
                description=_('Changes on %s repository') % repo_name,
                language=language,
                ttl=ttl
            )

            rss_items_per_page = safe_int(CONFIG.get('rss_items_per_page', 20))
            for cs in reversed(list(c.db_repo_scm_instance[-rss_items_per_page:])):
                feed.add_item(title=self._get_title(cs),
                              link=h.canonical_url('changeset_home', repo_name=repo_name,
                                       revision=cs.raw_id),
                              author_name=cs.author,
                              description=''.join(self.__get_desc(cs)),
                              pubdate=cs.date,
                              )

            response.content_type = feed.mime_type
            return feed.writeString('utf-8')

        kind = 'ATOM'
        return _get_feed_from_cache(repo_name, kind, c.db_repo.changeset_cache.get('raw_id'))

    def rss(self, repo_name):
        """Produce an rss2 feed via feedgenerator module"""

        @cache_region('long_term', '_get_feed_from_cache')
        def _get_feed_from_cache(*_cache_keys):  # parameters are not really used - only as caching key
            feed = Rss201rev2Feed(
                title=_('%s %s feed') % (c.site_name, repo_name),
                link=h.canonical_url('summary_home', repo_name=repo_name),
                description=_('Changes on %s repository') % repo_name,
                language=language,
                ttl=ttl
            )

            rss_items_per_page = safe_int(CONFIG.get('rss_items_per_page', 20))
            for cs in reversed(list(c.db_repo_scm_instance[-rss_items_per_page:])):
                feed.add_item(title=self._get_title(cs),
                              link=h.canonical_url('changeset_home', repo_name=repo_name,
                                       revision=cs.raw_id),
                              author_name=cs.author,
                              description=''.join(self.__get_desc(cs)),
                              pubdate=cs.date,
                             )

            response.content_type = feed.mime_type
            return feed.writeString('utf-8')

        kind = 'RSS'
        return _get_feed_from_cache(repo_name, kind, c.db_repo.changeset_cache.get('raw_id'))
