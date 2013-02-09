# -*- coding: utf-8 -*-
"""
    rhodecode.lib.indexers.__init__
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Whoosh indexing module for RhodeCode

    :created_on: Aug 17, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
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
import os
import sys
import traceback
import logging
from os.path import dirname as dn, join as jn

#to get the rhodecode import
sys.path.append(dn(dn(dn(os.path.realpath(__file__)))))

from string import strip
from shutil import rmtree

from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter
from whoosh.fields import TEXT, ID, STORED, NUMERIC, BOOLEAN, Schema, FieldType, DATETIME
from whoosh.index import create_in, open_dir
from whoosh.formats import Characters
from whoosh.highlight import highlight, HtmlFormatter, ContextFragmenter

from webhelpers.html.builder import escape, literal
from sqlalchemy import engine_from_config

from rhodecode.model import init_model
from rhodecode.model.scm import ScmModel
from rhodecode.model.repo import RepoModel
from rhodecode.config.environment import load_environment
from rhodecode.lib.utils2 import LazyProperty
from rhodecode.lib.utils import BasePasterCommand, Command, add_cache,\
    load_rcextensions

log = logging.getLogger(__name__)

# CUSTOM ANALYZER wordsplit + lowercase filter
ANALYZER = RegexTokenizer(expression=r"\w+") | LowercaseFilter()

#INDEX SCHEMA DEFINITION
SCHEMA = Schema(
    fileid=ID(unique=True),
    owner=TEXT(),
    repository=TEXT(stored=True),
    path=TEXT(stored=True),
    content=FieldType(format=Characters(), analyzer=ANALYZER,
                      scorable=True, stored=True),
    modtime=STORED(),
    extension=TEXT(stored=True)
)

IDX_NAME = 'HG_INDEX'
FORMATTER = HtmlFormatter('span', between='\n<span class="break">...</span>\n')
FRAGMENTER = ContextFragmenter(200)

CHGSETS_SCHEMA = Schema(
    raw_id=ID(unique=True, stored=True),
    date=NUMERIC(stored=True),
    last=BOOLEAN(),
    owner=TEXT(),
    repository=ID(unique=True, stored=True),
    author=TEXT(stored=True),
    message=FieldType(format=Characters(), analyzer=ANALYZER,
                      scorable=True, stored=True),
    parents=TEXT(),
    added=TEXT(),
    removed=TEXT(),
    changed=TEXT(),
)

CHGSET_IDX_NAME = 'CHGSET_INDEX'

# used only to generate queries in journal
JOURNAL_SCHEMA = Schema(
    username=TEXT(),
    date=DATETIME(),
    action=TEXT(),
    repository=TEXT(),
    ip=TEXT(),
)


class MakeIndex(BasePasterCommand):

    max_args = 1
    min_args = 1

    usage = "CONFIG_FILE"
    summary = "Creates or update full text search index"
    group_name = "RhodeCode"
    takes_config_file = -1
    parser = Command.standard_parser(verbose=True)

    def command(self):
        logging.config.fileConfig(self.path_to_ini_file)
        from pylons import config
        add_cache(config)
        engine = engine_from_config(config, 'sqlalchemy.db1.')
        init_model(engine)
        index_location = config['index_dir']
        repo_location = self.options.repo_location \
            if self.options.repo_location else RepoModel().repos_path
        repo_list = map(strip, self.options.repo_list.split(',')) \
            if self.options.repo_list else None
        repo_update_list = map(strip, self.options.repo_update_list.split(',')) \
            if self.options.repo_update_list else None
        load_rcextensions(config['here'])
        #======================================================================
        # WHOOSH DAEMON
        #======================================================================
        from rhodecode.lib.pidlock import LockHeld, DaemonLock
        from rhodecode.lib.indexers.daemon import WhooshIndexingDaemon
        try:
            l = DaemonLock(file_=jn(dn(dn(index_location)), 'make_index.lock'))
            WhooshIndexingDaemon(index_location=index_location,
                                 repo_location=repo_location,
                                 repo_list=repo_list,
                                 repo_update_list=repo_update_list)\
                .run(full_index=self.options.full_index)
            l.release()
        except LockHeld:
            sys.exit(1)

    def update_parser(self):
        self.parser.add_option('--repo-location',
                          action='store',
                          dest='repo_location',
                          help="Specifies repositories location to index OPTIONAL",
                          )
        self.parser.add_option('--index-only',
                          action='store',
                          dest='repo_list',
                          help="Specifies a comma separated list of repositores "
                                "to build index on. If not given all repositories "
                                "are scanned for indexing. OPTIONAL",
                          )
        self.parser.add_option('--update-only',
                          action='store',
                          dest='repo_update_list',
                          help="Specifies a comma separated list of repositores "
                                "to re-build index on. OPTIONAL",
                          )
        self.parser.add_option('-f',
                          action='store_true',
                          dest='full_index',
                          help="Specifies that index should be made full i.e"
                                " destroy old and build from scratch",
                          default=False)


class WhooshResultWrapper(object):
    def __init__(self, search_type, searcher, matcher, highlight_items,
                 repo_location):
        self.search_type = search_type
        self.searcher = searcher
        self.matcher = matcher
        self.highlight_items = highlight_items
        self.fragment_size = 200
        self.repo_location = repo_location

    @LazyProperty
    def doc_ids(self):
        docs_id = []
        while self.matcher.is_active():
            docnum = self.matcher.id()
            chunks = [offsets for offsets in self.get_chunks()]
            docs_id.append([docnum, chunks])
            self.matcher.next()
        return docs_id

    def __str__(self):
        return '<%s at %s>' % (self.__class__.__name__, len(self.doc_ids))

    def __repr__(self):
        return self.__str__()

    def __len__(self):
        return len(self.doc_ids)

    def __iter__(self):
        """
        Allows Iteration over results,and lazy generate content

        *Requires* implementation of ``__getitem__`` method.
        """
        for docid in self.doc_ids:
            yield self.get_full_content(docid)

    def __getitem__(self, key):
        """
        Slicing of resultWrapper
        """
        i, j = key.start, key.stop

        slices = []
        for docid in self.doc_ids[i:j]:
            slices.append(self.get_full_content(docid))
        return slices

    def get_full_content(self, docid):
        res = self.searcher.stored_fields(docid[0])
        log.debug('result: %s' % res)
        if self.search_type == 'content':
            full_repo_path = jn(self.repo_location, res['repository'])
            f_path = res['path'].split(full_repo_path)[-1]
            f_path = f_path.lstrip(os.sep)
            content_short = self.get_short_content(res, docid[1])
            res.update({'content_short': content_short,
                        'content_short_hl': self.highlight(content_short),
                        'f_path': f_path
                      })
        elif self.search_type == 'path':
            full_repo_path = jn(self.repo_location, res['repository'])
            f_path = res['path'].split(full_repo_path)[-1]
            f_path = f_path.lstrip(os.sep)
            res.update({'f_path': f_path})
        elif self.search_type == 'message':
            res.update({'message_hl': self.highlight(res['message'])})

        log.debug('result: %s' % res)

        return res

    def get_short_content(self, res, chunks):

        return ''.join([res['content'][chunk[0]:chunk[1]] for chunk in chunks])

    def get_chunks(self):
        """
        Smart function that implements chunking the content
        but not overlap chunks so it doesn't highlight the same
        close occurrences twice.

        :param matcher:
        :param size:
        """
        memory = [(0, 0)]
        if self.matcher.supports('positions'):
            for span in self.matcher.spans():
                start = span.startchar or 0
                end = span.endchar or 0
                start_offseted = max(0, start - self.fragment_size)
                end_offseted = end + self.fragment_size

                if start_offseted < memory[-1][1]:
                    start_offseted = memory[-1][1]
                memory.append((start_offseted, end_offseted,))
                yield (start_offseted, end_offseted,)

    def highlight(self, content, top=5):
        if self.search_type not in ['content', 'message']:
            return ''
        hl = highlight(
            text=content,
            terms=self.highlight_items,
            analyzer=ANALYZER,
            fragmenter=FRAGMENTER,
            formatter=FORMATTER,
            top=top
        )
        return hl
