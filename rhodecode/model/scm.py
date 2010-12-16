# -*- coding: utf-8 -*-
"""
    rhodecode.model.scm
    ~~~~~~~~~~~~~~~~~~~

    Scm model for RhodeCode

    :created_on: Apr 9, 2010
    :author: marcink
    :copyright: (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>    
    :license: GPLv3, see COPYING for more details.
"""
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
import os
import time
import traceback
import logging

from vcs import get_backend
from vcs.utils.helpers import get_scm
from vcs.exceptions import RepositoryError, VCSError
from vcs.utils.lazy import LazyProperty

from mercurial import ui

from beaker.cache import cache_region, region_invalidate

from rhodecode import BACKENDS
from rhodecode.lib import helpers as h
from rhodecode.lib.auth import HasRepoPermissionAny
from rhodecode.lib.utils import get_repos, make_ui, action_logger
from rhodecode.model import BaseModel
from rhodecode.model.user import UserModel

from rhodecode.model.db import Repository, RhodeCodeUi, CacheInvalidation, \
    UserFollowing, UserLog
from rhodecode.model.caching_query import FromCache

from sqlalchemy.orm import joinedload
from sqlalchemy.orm.session import make_transient
from sqlalchemy.exc import DatabaseError

log = logging.getLogger(__name__)


class UserTemp(object):
    def __init__(self, user_id):
        self.user_id = user_id
class RepoTemp(object):
    def __init__(self, repo_id):
        self.repo_id = repo_id

class ScmModel(BaseModel):
    """Generic Scm Model
    """

    @LazyProperty
    def repos_path(self):
        """Get's the repositories root path from database
        """

        q = self.sa.query(RhodeCodeUi).filter(RhodeCodeUi.ui_key == '/').one()

        return q.ui_value

    def repo_scan(self, repos_path, baseui):
        """Listing of repositories in given path. This path should not be a 
        repository itself. Return a dictionary of repository objects
        
        :param repos_path: path to directory containing repositories
        :param baseui: baseui instance to instantiate MercurialRepostitory with
        """

        log.info('scanning for repositories in %s', repos_path)

        if not isinstance(baseui, ui.ui):
            baseui = make_ui('db')
        repos_list = {}

        for name, path in get_repos(repos_path):
            try:
                if repos_list.has_key(name):
                    raise RepositoryError('Duplicate repository name %s '
                                    'found in %s' % (name, path))
                else:

                    klass = get_backend(path[0])

                    if path[0] == 'hg' and path[0] in BACKENDS.keys():
                        repos_list[name] = klass(path[1], baseui=baseui)

                    if path[0] == 'git' and path[0] in BACKENDS.keys():
                        repos_list[name] = klass(path[1])
            except OSError:
                continue

        return repos_list

    def get_repos(self, all_repos=None):
        """Get all repos from db and for each repo create it's backend instance.
        and fill that backed with information from database
        
        :param all_repos: give specific repositories list, good for filtering
        """

        if all_repos is None:
            all_repos = self.sa.query(Repository)\
                .order_by(Repository.repo_name).all()

        #get the repositories that should be invalidated
        invalidation_list = [str(x.cache_key) for x in \
                             self.sa.query(CacheInvalidation.cache_key)\
                             .filter(CacheInvalidation.cache_active == False)\
                             .all()]

        for r in all_repos:

            repo = self.get(r.repo_name, invalidation_list)

            if repo is not None:
                last_change = repo.last_change
                tip = h.get_changeset_safe(repo, 'tip')

                tmp_d = {}
                tmp_d['name'] = repo.name
                tmp_d['name_sort'] = tmp_d['name'].lower()
                tmp_d['description'] = repo.dbrepo.description
                tmp_d['description_sort'] = tmp_d['description']
                tmp_d['last_change'] = last_change
                tmp_d['last_change_sort'] = time.mktime(last_change.timetuple())
                tmp_d['tip'] = tip.raw_id
                tmp_d['tip_sort'] = tip.revision
                tmp_d['rev'] = tip.revision
                tmp_d['contact'] = repo.dbrepo.user.full_contact
                tmp_d['contact_sort'] = tmp_d['contact']
                tmp_d['repo_archives'] = list(repo._get_archives())
                tmp_d['last_msg'] = tip.message
                tmp_d['repo'] = repo
                yield tmp_d

    def get_repo(self, repo_name):
        return self.get(repo_name)

    def get(self, repo_name, invalidation_list=None):
        """Get's repository from given name, creates BackendInstance and
        propagates it's data from database with all additional information
        
        :param repo_name:
        :param invalidation_list: if a invalidation list is given the get
            method should not manually check if this repository needs 
            invalidation and just invalidate the repositories in list
            
        """
        if not HasRepoPermissionAny('repository.read', 'repository.write',
                            'repository.admin')(repo_name, 'get repo check'):
            return

        #======================================================================
        # CACHE FUNCTION
        #======================================================================
        @cache_region('long_term')
        def _get_repo(repo_name):

            repo_path = os.path.join(self.repos_path, repo_name)

            try:
                alias = get_scm(repo_path)[0]

                log.debug('Creating instance of %s repository', alias)
                backend = get_backend(alias)
            except VCSError:
                log.error(traceback.format_exc())
                return

            if alias == 'hg':
                from pylons import app_globals as g
                repo = backend(repo_path, create=False, baseui=g.baseui)
                #skip hidden web repository
                if repo._get_hidden():
                    return
            else:
                repo = backend(repo_path, create=False)

            dbrepo = self.sa.query(Repository)\
                .options(joinedload(Repository.fork))\
                .options(joinedload(Repository.user))\
                .filter(Repository.repo_name == repo_name)\
                .scalar()

            make_transient(dbrepo)
            if dbrepo.user:
                make_transient(dbrepo.user)
            if dbrepo.fork:
                make_transient(dbrepo.fork)

            repo.dbrepo = dbrepo
            return repo

        pre_invalidate = True
        if invalidation_list is not None:
            pre_invalidate = repo_name in invalidation_list

        if pre_invalidate:
            invalidate = self._should_invalidate(repo_name)

            if invalidate:
                log.info('invalidating cache for repository %s', repo_name)
                region_invalidate(_get_repo, None, repo_name)
                self._mark_invalidated(invalidate)

        return _get_repo(repo_name)



    def mark_for_invalidation(self, repo_name):
        """Puts cache invalidation task into db for 
        further global cache invalidation
        
        :param repo_name: this repo that should invalidation take place
        """

        log.debug('marking %s for invalidation', repo_name)
        cache = self.sa.query(CacheInvalidation)\
            .filter(CacheInvalidation.cache_key == repo_name).scalar()

        if cache:
            #mark this cache as inactive
            cache.cache_active = False
        else:
            log.debug('cache key not found in invalidation db -> creating one')
            cache = CacheInvalidation(repo_name)

        try:
            self.sa.add(cache)
            self.sa.commit()
        except (DatabaseError,):
            log.error(traceback.format_exc())
            self.sa.rollback()


    def toggle_following_repo(self, follow_repo_id, user_id):

        f = self.sa.query(UserFollowing)\
            .filter(UserFollowing.follows_repo_id == follow_repo_id)\
            .filter(UserFollowing.user_id == user_id).scalar()

        if f is not None:

            try:
                self.sa.delete(f)
                self.sa.commit()
                action_logger(UserTemp(user_id),
                              'stopped_following_repo',
                              RepoTemp(follow_repo_id))
                return
            except:
                log.error(traceback.format_exc())
                self.sa.rollback()
                raise


        try:
            f = UserFollowing()
            f.user_id = user_id
            f.follows_repo_id = follow_repo_id
            self.sa.add(f)
            self.sa.commit()
            action_logger(UserTemp(user_id),
                          'started_following_repo',
                          RepoTemp(follow_repo_id))
        except:
            log.error(traceback.format_exc())
            self.sa.rollback()
            raise

    def toggle_following_user(self, follow_user_id , user_id):
        f = self.sa.query(UserFollowing)\
            .filter(UserFollowing.follows_user_id == follow_user_id)\
            .filter(UserFollowing.user_id == user_id).scalar()

        if f is not None:
            try:
                self.sa.delete(f)
                self.sa.commit()
                return
            except:
                log.error(traceback.format_exc())
                self.sa.rollback()
                raise

        try:
            f = UserFollowing()
            f.user_id = user_id
            f.follows_user_id = follow_user_id
            self.sa.add(f)
            self.sa.commit()
        except:
            log.error(traceback.format_exc())
            self.sa.rollback()
            raise

    def is_following_repo(self, repo_name, user_id):
        r = self.sa.query(Repository)\
            .filter(Repository.repo_name == repo_name).scalar()

        f = self.sa.query(UserFollowing)\
            .filter(UserFollowing.follows_repository == r)\
            .filter(UserFollowing.user_id == user_id).scalar()

        return f is not None

    def is_following_user(self, username, user_id):
        u = UserModel(self.sa).get_by_username(username)

        f = self.sa.query(UserFollowing)\
            .filter(UserFollowing.follows_user == u)\
            .filter(UserFollowing.user_id == user_id).scalar()

        return f is not None

    def get_followers(self, repo_id):
        return self.sa.query(UserFollowing)\
                .filter(UserFollowing.follows_repo_id == repo_id).count()

    def get_forks(self, repo_id):
        return self.sa.query(Repository)\
                .filter(Repository.fork_id == repo_id).count()


    def get_unread_journal(self):
        return self.sa.query(UserLog).count()


    def _should_invalidate(self, repo_name):
        """Looks up database for invalidation signals for this repo_name
        
        :param repo_name:
        """

        ret = self.sa.query(CacheInvalidation)\
            .options(FromCache('sql_cache_short',
                           'get_invalidation_%s' % repo_name))\
            .filter(CacheInvalidation.cache_key == repo_name)\
            .filter(CacheInvalidation.cache_active == False)\
            .scalar()

        return ret

    def _mark_invalidated(self, cache_key):
        """ Marks all occurences of cache to invaldation as already invalidated
        
        :param cache_key:
        """

        if cache_key:
            log.debug('marking %s as already invalidated', cache_key)
        try:
            cache_key.cache_active = True
            self.sa.add(cache_key)
            self.sa.commit()
        except (DatabaseError,):
            log.error(traceback.format_exc())
            self.sa.rollback()

