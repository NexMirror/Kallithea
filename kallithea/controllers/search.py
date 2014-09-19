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
import urllib
from pylons.i18n.translation import _
from pylons import request, config, tmpl_context as c

from whoosh.index import open_dir, EmptyIndexError
from whoosh.qparser import QueryParser, QueryParserError
from whoosh.query import Phrase, Prefix
from webhelpers.util import update_params

from kallithea.lib.auth import LoginRequired
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.indexers import CHGSETS_SCHEMA, SCHEMA, CHGSET_IDX_NAME, \
    IDX_NAME, WhooshResultWrapper
from kallithea.model.repo import RepoModel
from kallithea.lib.utils2 import safe_str, safe_int
from kallithea.lib.helpers import Page

log = logging.getLogger(__name__)


class SearchController(BaseRepoController):

    def __before__(self):
        super(SearchController, self).__before__()

    @LoginRequired()
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

        log.debug('IDX: %s' % index_name)
        log.debug('SCHEMA: %s' % schema_defn)

        if c.cur_query:
            cur_query = c.cur_query.lower()
            log.debug(cur_query)

        if c.cur_query:
            p = safe_int(request.GET.get('page', 1), 1)
            highlight_items = set()
            try:
                idx = open_dir(config['app_conf']['index_dir'],
                               indexname=index_name)
                searcher = idx.searcher()

                qp = QueryParser(search_type, schema=schema_defn)
                if c.repo_name:
                    cur_query = u'repository:%s %s' % (c.repo_name, cur_query)
                try:
                    query = qp.parse(unicode(cur_query))
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

                    log.debug('query: %s' % query)
                    log.debug('hl terms: %s' % highlight_items)
                    results = searcher.search(query)
                    res_ln = len(results)
                    c.runtime = '%s results (%.3f seconds)' % (
                        res_ln, results.runtime
                    )

                    def url_generator(**kw):
                        q = urllib.quote(safe_str(c.cur_query))
                        return update_params("?q=%s&type=%s" \
                        % (q, safe_str(c.cur_type)), **kw)
                    repo_location = RepoModel().repos_path
                    c.formated_results = Page(
                        WhooshResultWrapper(search_type, searcher, matcher,
                                            highlight_items, repo_location),
                        page=p,
                        item_count=res_ln,
                        items_per_page=10,
                        url=url_generator
                    )

                except QueryParserError:
                    c.runtime = _('Invalid search query. Try quoting it.')
                searcher.close()
            except (EmptyIndexError, IOError):
                log.error(traceback.format_exc())
                log.error('Empty Index data')
                c.runtime = _('There is no index to search in. '
                              'Please run whoosh indexer')
            except (Exception):
                log.error(traceback.format_exc())
                c.runtime = _('An error occurred during search operation.')

        # Return a rendered template
        return render('/search/search.html')
