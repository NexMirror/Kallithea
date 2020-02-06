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
kallithea.controllers.search
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 7, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

from tg import config, request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from whoosh.index import EmptyIndexError, exists_in, open_dir
from whoosh.qparser import QueryParser, QueryParserError
from whoosh.query import Phrase, Prefix

from kallithea.lib.auth import LoginRequired
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.indexers import CHGSET_IDX_NAME, CHGSETS_SCHEMA, IDX_NAME, SCHEMA, WhooshResultWrapper
from kallithea.lib.page import Page
from kallithea.lib.utils2 import safe_int
from kallithea.model.repo import RepoModel


log = logging.getLogger(__name__)


class SearchController(BaseRepoController):

    @LoginRequired(allow_default_user=True)
    def index(self, repo_name=None):
        c.repo_name = repo_name
        c.formated_results = []
        c.runtime = ''
        c.cur_query = request.GET.get('q', None)
        c.cur_type = request.GET.get('type', 'content')
        c.cur_search = search_type = {'content': 'content',
                                      'commit': 'message',
                                      'path': 'path',
                                      'repository': 'repository'
                                      }.get(c.cur_type, 'content')

        index_name = {
            'content': IDX_NAME,
            'commit': CHGSET_IDX_NAME,
            'path': IDX_NAME
        }.get(c.cur_type, IDX_NAME)

        schema_defn = {
            'content': SCHEMA,
            'commit': CHGSETS_SCHEMA,
            'path': SCHEMA
        }.get(c.cur_type, SCHEMA)

        log.debug('IDX: %s', index_name)
        log.debug('SCHEMA: %s', schema_defn)

        if c.cur_query:
            cur_query = c.cur_query.lower()
            log.debug(cur_query)

        if c.cur_query:
            p = safe_int(request.GET.get('page'), 1)
            highlight_items = set()
            index_dir = config['index_dir']
            try:
                if not exists_in(index_dir, index_name):
                    raise EmptyIndexError
                idx = open_dir(index_dir, indexname=index_name)
                searcher = idx.searcher()

                qp = QueryParser(search_type, schema=schema_defn)
                if c.repo_name:
                    # use "repository_rawname:" instead of "repository:"
                    # for case-sensitive matching
                    cur_query = 'repository_rawname:%s %s' % (c.repo_name, cur_query)
                try:
                    query = qp.parse(cur_query)
                    # extract words for highlight
                    if isinstance(query, Phrase):
                        highlight_items.update(query.words)
                    elif isinstance(query, Prefix):
                        highlight_items.add(query.text)
                    else:
                        for i in query.all_terms():
                            if i[0] in ['content', 'message']:
                                highlight_items.add(i[1])

                    matcher = query.matcher(searcher)

                    log.debug('query: %s', query)
                    log.debug('hl terms: %s', highlight_items)
                    results = searcher.search(query)
                    res_ln = len(results)
                    c.runtime = '%s results (%.3f seconds)' % (
                        res_ln, results.runtime
                    )

                    repo_location = RepoModel().repos_path
                    c.formated_results = Page(
                        WhooshResultWrapper(search_type, searcher, matcher,
                                            highlight_items, repo_location),
                        page=p,
                        item_count=res_ln,
                        items_per_page=10,
                        type=c.cur_type,
                        q=c.cur_query,
                    )

                except QueryParserError:
                    c.runtime = _('Invalid search query. Try quoting it.')
                searcher.close()
            except EmptyIndexError:
                log.error("Empty search index - run 'kallithea-cli index-create' regularly")
                c.runtime = _('The server has no search index.')
            except Exception:
                log.error(traceback.format_exc())
                c.runtime = _('An error occurred during search operation.')

        # Return a rendered template
        return render('/search/search.html')
