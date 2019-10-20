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
kallithea.model.scm
~~~~~~~~~~~~~~~~~~~

Scm model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 9, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import cStringIO
import logging
import os
import posixpath
import re
import sys
import traceback

import pkg_resources
from tg.i18n import ugettext as _

import kallithea
from kallithea import BACKENDS
from kallithea.lib.auth import HasPermissionAny, HasRepoGroupPermissionLevel, HasRepoPermissionLevel, HasUserGroupPermissionLevel
from kallithea.lib.exceptions import IMCCommitError, NonRelativePathError
from kallithea.lib.hooks import process_pushed_raw_ids
from kallithea.lib.utils import action_logger, get_filesystem_repos, make_ui
from kallithea.lib.utils2 import safe_str, safe_unicode, set_hook_environment
from kallithea.lib.vcs import get_backend
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.exceptions import RepositoryError
from kallithea.lib.vcs.nodes import FileNode
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.model.db import PullRequest, RepoGroup, Repository, Session, Ui, User, UserFollowing, UserLog


log = logging.getLogger(__name__)


class UserTemp(object):
    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<%s('id:%s')>" % (self.__class__.__name__, self.user_id)


class RepoTemp(object):
    def __init__(self, repo_id):
        self.repo_id = repo_id

    def __repr__(self):
        return "<%s('id:%s')>" % (self.__class__.__name__, self.repo_id)


class _PermCheckIterator(object):
    def __init__(self, obj_list, obj_attr, perm_set, perm_checker, extra_kwargs=None):
        """
        Creates iterator from given list of objects, additionally
        checking permission for them from perm_set var

        :param obj_list: list of db objects
        :param obj_attr: attribute of object to pass into perm_checker
        :param perm_set: list of permissions to check
        :param perm_checker: callable to check permissions against
        """
        self.obj_list = obj_list
        self.obj_attr = obj_attr
        self.perm_set = perm_set
        self.perm_checker = perm_checker
        self.extra_kwargs = extra_kwargs or {}

    def __len__(self):
        return len(self.obj_list)

    def __repr__(self):
        return '<%s (%s)>' % (self.__class__.__name__, self.__len__())

    def __iter__(self):
        for db_obj in self.obj_list:
            # check permission at this level
            name = getattr(db_obj, self.obj_attr, None)
            if not self.perm_checker(*self.perm_set)(
                    name, self.__class__.__name__, **self.extra_kwargs):
                continue

            yield db_obj


class RepoList(_PermCheckIterator):

    def __init__(self, db_repo_list, perm_level, extra_kwargs=None):
        super(RepoList, self).__init__(obj_list=db_repo_list,
                    obj_attr='repo_name', perm_set=[perm_level],
                    perm_checker=HasRepoPermissionLevel,
                    extra_kwargs=extra_kwargs)


class RepoGroupList(_PermCheckIterator):

    def __init__(self, db_repo_group_list, perm_level, extra_kwargs=None):
        super(RepoGroupList, self).__init__(obj_list=db_repo_group_list,
                    obj_attr='group_name', perm_set=[perm_level],
                    perm_checker=HasRepoGroupPermissionLevel,
                    extra_kwargs=extra_kwargs)


class UserGroupList(_PermCheckIterator):

    def __init__(self, db_user_group_list, perm_level, extra_kwargs=None):
        super(UserGroupList, self).__init__(obj_list=db_user_group_list,
                    obj_attr='users_group_name', perm_set=[perm_level],
                    perm_checker=HasUserGroupPermissionLevel,
                    extra_kwargs=extra_kwargs)


class ScmModel(object):
    """
    Generic Scm Model
    """

    def __get_repo(self, instance):
        cls = Repository
        if isinstance(instance, cls):
            return instance
        elif isinstance(instance, int) or safe_str(instance).isdigit():
            return cls.get(instance)
        elif isinstance(instance, basestring):
            return cls.get_by_repo_name(instance)
        elif instance is not None:
            raise Exception('given object must be int, basestr or Instance'
                            ' of %s got %s' % (type(cls), type(instance)))

    @LazyProperty
    def repos_path(self):
        """
        Gets the repositories root path from database
        """

        q = Ui.query().filter(Ui.ui_key == '/').one()

        return q.ui_value

    def repo_scan(self, repos_path=None):
        """
        Listing of repositories in given path. This path should not be a
        repository itself. Return a dictionary of repository objects

        :param repos_path: path to directory containing repositories
        """

        if repos_path is None:
            repos_path = self.repos_path

        log.info('scanning for repositories in %s', repos_path)

        baseui = make_ui()
        repos = {}

        for name, path in get_filesystem_repos(repos_path):
            # name need to be decomposed and put back together using the /
            # since this is internal storage separator for kallithea
            name = Repository.normalize_repo_name(name)

            try:
                if name in repos:
                    raise RepositoryError('Duplicate repository name %s '
                                          'found in %s' % (name, path))
                else:

                    klass = get_backend(path[0])

                    if path[0] == 'hg' and path[0] in BACKENDS.keys():
                        repos[name] = klass(safe_str(path[1]), baseui=baseui)

                    if path[0] == 'git' and path[0] in BACKENDS.keys():
                        repos[name] = klass(path[1])
            except OSError:
                continue
        log.debug('found %s paths with repositories', len(repos))
        return repos

    def get_repos(self, repos):
        """Return the repos the user has access to"""
        return RepoList(repos, perm_level='read')

    def get_repo_groups(self, groups=None):
        """Return the repo groups the user has access to
        If no groups are specified, use top level groups.
        """
        if groups is None:
            groups = RepoGroup.query() \
                .filter(RepoGroup.parent_group_id == None).all()
        return RepoGroupList(groups, perm_level='read')

    def mark_for_invalidation(self, repo_name):
        """
        Mark caches of this repo invalid in the database.

        :param repo_name: the repo for which caches should be marked invalid
        """
        log.debug("Marking %s as invalidated and update cache", repo_name)
        repo = Repository.get_by_repo_name(repo_name)
        if repo is not None:
            repo.set_invalidate()
            repo.update_changeset_cache()

    def toggle_following_repo(self, follow_repo_id, user_id):

        f = UserFollowing.query() \
            .filter(UserFollowing.follows_repository_id == follow_repo_id) \
            .filter(UserFollowing.user_id == user_id).scalar()

        if f is not None:
            try:
                Session().delete(f)
                action_logger(UserTemp(user_id),
                              'stopped_following_repo',
                              RepoTemp(follow_repo_id))
                return
            except Exception:
                log.error(traceback.format_exc())
                raise

        try:
            f = UserFollowing()
            f.user_id = user_id
            f.follows_repository_id = follow_repo_id
            Session().add(f)

            action_logger(UserTemp(user_id),
                          'started_following_repo',
                          RepoTemp(follow_repo_id))
        except Exception:
            log.error(traceback.format_exc())
            raise

    def toggle_following_user(self, follow_user_id, user_id):
        f = UserFollowing.query() \
            .filter(UserFollowing.follows_user_id == follow_user_id) \
            .filter(UserFollowing.user_id == user_id).scalar()

        if f is not None:
            try:
                Session().delete(f)
                return
            except Exception:
                log.error(traceback.format_exc())
                raise

        try:
            f = UserFollowing()
            f.user_id = user_id
            f.follows_user_id = follow_user_id
            Session().add(f)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def is_following_repo(self, repo_name, user_id):
        r = Repository.query() \
            .filter(Repository.repo_name == repo_name).scalar()

        f = UserFollowing.query() \
            .filter(UserFollowing.follows_repository == r) \
            .filter(UserFollowing.user_id == user_id).scalar()

        return f is not None

    def is_following_user(self, username, user_id):
        u = User.get_by_username(username)

        f = UserFollowing.query() \
            .filter(UserFollowing.follows_user == u) \
            .filter(UserFollowing.user_id == user_id).scalar()

        return f is not None

    def get_followers(self, repo):
        repo = Repository.guess_instance(repo)

        return UserFollowing.query() \
                .filter(UserFollowing.follows_repository == repo).count()

    def get_forks(self, repo):
        repo = Repository.guess_instance(repo)
        return Repository.query() \
                .filter(Repository.fork == repo).count()

    def get_pull_requests(self, repo):
        repo = Repository.guess_instance(repo)
        return PullRequest.query() \
                .filter(PullRequest.other_repo == repo) \
                .filter(PullRequest.status != PullRequest.STATUS_CLOSED).count()

    def mark_as_fork(self, repo, fork, user):
        repo = self.__get_repo(repo)
        fork = self.__get_repo(fork)
        if fork and repo.repo_id == fork.repo_id:
            raise Exception("Cannot set repository as fork of itself")

        if fork and repo.repo_type != fork.repo_type:
            raise RepositoryError("Cannot set repository as fork of repository with other type")

        repo.fork = fork
        return repo

    def _handle_push(self, repo, username, ip_addr, action, repo_name, revisions):
        """
        Handle that the repository has changed.
        Adds an action log entry with the new revisions, and the head revision
        cache and in-memory caches are invalidated/updated.

        :param username: username who pushes
        :param action: push/push_local/push_remote
        :param repo_name: name of repo
        :param revisions: list of revisions that we pushed
        """
        set_hook_environment(username, ip_addr, repo_name, repo_alias=repo.alias, action=action)
        process_pushed_raw_ids(revisions) # also calls mark_for_invalidation

    def _get_IMC_module(self, scm_type):
        """
        Returns InMemoryCommit class based on scm_type

        :param scm_type:
        """
        if scm_type == 'hg':
            from kallithea.lib.vcs.backends.hg import MercurialInMemoryChangeset
            return MercurialInMemoryChangeset

        if scm_type == 'git':
            from kallithea.lib.vcs.backends.git import GitInMemoryChangeset
            return GitInMemoryChangeset

        raise Exception('Invalid scm_type, must be one of hg,git got %s'
                        % (scm_type,))

    def pull_changes(self, repo, username, ip_addr, clone_uri=None):
        """
        Pull from "clone URL" or fork origin.
        """
        dbrepo = self.__get_repo(repo)
        if clone_uri is None:
            clone_uri = dbrepo.clone_uri or dbrepo.fork and dbrepo.fork.repo_full_path
        if not clone_uri:
            raise Exception("This repository doesn't have a clone uri")

        repo = dbrepo.scm_instance
        repo_name = dbrepo.repo_name
        try:
            if repo.alias == 'git':
                repo.fetch(clone_uri)
                # git doesn't really have something like post-fetch action
                # we fake that now.
                # TODO: extract fetched revisions ... somehow ...
                self._handle_push(repo,
                                  username=username,
                                  ip_addr=ip_addr,
                                  action='push_remote',
                                  repo_name=repo_name,
                                  revisions=[])
            else:
                set_hook_environment(username, ip_addr, dbrepo.repo_name,
                                           repo.alias, action='push_remote')
                repo.pull(clone_uri)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def commit_change(self, repo, repo_name, cs, user, ip_addr, author, message,
                      content, f_path):
        """
        Commit a change to a single file

        :param repo: a db_repo.scm_instance
        """
        user = User.guess_instance(user)
        IMC = self._get_IMC_module(repo.alias)

        # decoding here will force that we have proper encoded values
        # in any other case this will throw exceptions and deny commit
        content = safe_str(content)
        path = safe_str(f_path)
        # message and author needs to be unicode
        # proper backend should then translate that into required type
        message = safe_unicode(message)
        author = safe_unicode(author)
        imc = IMC(repo)
        imc.change(FileNode(path, content, mode=cs.get_file_mode(f_path)))
        try:
            tip = imc.commit(message=message, author=author,
                             parents=[cs], branch=cs.branch)
        except Exception as e:
            log.error(traceback.format_exc())
            # clear caches - we also want a fresh object if commit fails
            self.mark_for_invalidation(repo_name)
            raise IMCCommitError(str(e))
        self._handle_push(repo,
                          username=user.username,
                          ip_addr=ip_addr,
                          action='push_local',
                          repo_name=repo_name,
                          revisions=[tip.raw_id])
        return tip

    def _sanitize_path(self, f_path):
        if f_path.startswith('/') or f_path.startswith('.') or '../' in f_path:
            raise NonRelativePathError('%s is not an relative path' % f_path)
        if f_path:
            f_path = posixpath.normpath(f_path)
        return f_path

    def get_nodes(self, repo_name, revision, root_path='/', flat=True):
        """
        Recursively walk root dir and return a set of all paths found.

        :param repo_name: name of repository
        :param revision: revision for which to list nodes
        :param root_path: root path to list
        :param flat: return as a list, if False returns a dict with description

        """
        _files = list()
        _dirs = list()
        try:
            _repo = self.__get_repo(repo_name)
            changeset = _repo.scm_instance.get_changeset(revision)
            root_path = root_path.lstrip('/')
            for topnode, dirs, files in changeset.walk(root_path):
                for f in files:
                    _files.append(f.path if flat else {"name": f.path,
                                                       "type": "file"})
                for d in dirs:
                    _dirs.append(d.path if flat else {"name": d.path,
                                                      "type": "dir"})
        except RepositoryError:
            log.debug(traceback.format_exc())
            raise

        return _dirs, _files

    def create_nodes(self, user, ip_addr, repo, message, nodes, parent_cs=None,
                     author=None, trigger_push_hook=True):
        """
        Commits specified nodes to repo.

        :param user: Kallithea User object or user_id, the committer
        :param repo: Kallithea Repository object
        :param message: commit message
        :param nodes: mapping {filename:{'content':content},...}
        :param parent_cs: parent changeset, can be empty than it's initial commit
        :param author: author of commit, cna be different that committer only for git
        :param trigger_push_hook: trigger push hooks

        :returns: new committed changeset
        """

        user = User.guess_instance(user)
        scm_instance = repo.scm_instance_no_cache()

        processed_nodes = []
        for f_path in nodes:
            content = nodes[f_path]['content']
            f_path = self._sanitize_path(f_path)
            f_path = safe_str(f_path)
            # decoding here will force that we have proper encoded values
            # in any other case this will throw exceptions and deny commit
            if isinstance(content, (basestring,)):
                content = safe_str(content)
            elif isinstance(content, (file, cStringIO.OutputType,)):
                content = content.read()
            else:
                raise Exception('Content is of unrecognized type %s' % (
                    type(content)
                ))
            processed_nodes.append((f_path, content))

        message = safe_unicode(message)
        committer = user.full_contact
        author = safe_unicode(author) if author else committer

        IMC = self._get_IMC_module(scm_instance.alias)
        imc = IMC(scm_instance)

        if not parent_cs:
            parent_cs = EmptyChangeset(alias=scm_instance.alias)

        if isinstance(parent_cs, EmptyChangeset):
            # EmptyChangeset means we we're editing empty repository
            parents = None
        else:
            parents = [parent_cs]
        # add multiple nodes
        for path, content in processed_nodes:
            imc.add(FileNode(path, content=content))

        tip = imc.commit(message=message,
                         author=author,
                         parents=parents,
                         branch=parent_cs.branch)

        if trigger_push_hook:
            self._handle_push(scm_instance,
                              username=user.username,
                              ip_addr=ip_addr,
                              action='push_local',
                              repo_name=repo.repo_name,
                              revisions=[tip.raw_id])
        else:
            self.mark_for_invalidation(repo.repo_name)
        return tip

    def update_nodes(self, user, ip_addr, repo, message, nodes, parent_cs=None,
                     author=None, trigger_push_hook=True):
        """
        Commits specified nodes to repo. Again.
        """
        user = User.guess_instance(user)
        scm_instance = repo.scm_instance_no_cache()

        message = safe_unicode(message)
        committer = user.full_contact
        author = safe_unicode(author) if author else committer

        imc_class = self._get_IMC_module(scm_instance.alias)
        imc = imc_class(scm_instance)

        if not parent_cs:
            parent_cs = EmptyChangeset(alias=scm_instance.alias)

        if isinstance(parent_cs, EmptyChangeset):
            # EmptyChangeset means we we're editing empty repository
            parents = None
        else:
            parents = [parent_cs]

        # add multiple nodes
        for _filename, data in nodes.items():
            # new filename, can be renamed from the old one
            filename = self._sanitize_path(data['filename'])
            old_filename = self._sanitize_path(_filename)
            content = data['content']

            filenode = FileNode(old_filename, content=content)
            op = data['op']
            if op == 'add':
                imc.add(filenode)
            elif op == 'del':
                imc.remove(filenode)
            elif op == 'mod':
                if filename != old_filename:
                    # TODO: handle renames, needs vcs lib changes
                    imc.remove(filenode)
                    imc.add(FileNode(filename, content=content))
                else:
                    imc.change(filenode)

        # commit changes
        tip = imc.commit(message=message,
                         author=author,
                         parents=parents,
                         branch=parent_cs.branch)

        if trigger_push_hook:
            self._handle_push(scm_instance,
                              username=user.username,
                              ip_addr=ip_addr,
                              action='push_local',
                              repo_name=repo.repo_name,
                              revisions=[tip.raw_id])
        else:
            self.mark_for_invalidation(repo.repo_name)

    def delete_nodes(self, user, ip_addr, repo, message, nodes, parent_cs=None,
                     author=None, trigger_push_hook=True):
        """
        Deletes specified nodes from repo.

        :param user: Kallithea User object or user_id, the committer
        :param repo: Kallithea Repository object
        :param message: commit message
        :param nodes: mapping {filename:{'content':content},...}
        :param parent_cs: parent changeset, can be empty than it's initial commit
        :param author: author of commit, cna be different that committer only for git
        :param trigger_push_hook: trigger push hooks

        :returns: new committed changeset after deletion
        """

        user = User.guess_instance(user)
        scm_instance = repo.scm_instance_no_cache()

        processed_nodes = []
        for f_path in nodes:
            f_path = self._sanitize_path(f_path)
            # content can be empty but for compatibility it allows same dicts
            # structure as add_nodes
            content = nodes[f_path].get('content')
            processed_nodes.append((f_path, content))

        message = safe_unicode(message)
        committer = user.full_contact
        author = safe_unicode(author) if author else committer

        IMC = self._get_IMC_module(scm_instance.alias)
        imc = IMC(scm_instance)

        if not parent_cs:
            parent_cs = EmptyChangeset(alias=scm_instance.alias)

        if isinstance(parent_cs, EmptyChangeset):
            # EmptyChangeset means we we're editing empty repository
            parents = None
        else:
            parents = [parent_cs]
        # add multiple nodes
        for path, content in processed_nodes:
            imc.remove(FileNode(path, content=content))

        tip = imc.commit(message=message,
                         author=author,
                         parents=parents,
                         branch=parent_cs.branch)

        if trigger_push_hook:
            self._handle_push(scm_instance,
                              username=user.username,
                              ip_addr=ip_addr,
                              action='push_local',
                              repo_name=repo.repo_name,
                              revisions=[tip.raw_id])
        else:
            self.mark_for_invalidation(repo.repo_name)
        return tip

    def get_unread_journal(self):
        return UserLog.query().count()

    def get_repo_landing_revs(self, repo=None):
        """
        Generates select option with tags branches and bookmarks (for hg only)
        grouped by type

        :param repo:
        """

        hist_l = []
        choices = []
        repo = self.__get_repo(repo)
        hist_l.append(('rev:tip', _('latest tip')))
        choices.append('rev:tip')
        if repo is None:
            return choices, hist_l

        repo = repo.scm_instance

        branches_group = ([(u'branch:%s' % k, k) for k, v in
                           repo.branches.iteritems()], _("Branches"))
        hist_l.append(branches_group)
        choices.extend([x[0] for x in branches_group[0]])

        if repo.alias == 'hg':
            bookmarks_group = ([(u'book:%s' % k, k) for k, v in
                                repo.bookmarks.iteritems()], _("Bookmarks"))
            hist_l.append(bookmarks_group)
            choices.extend([x[0] for x in bookmarks_group[0]])

        tags_group = ([(u'tag:%s' % k, k) for k, v in
                       repo.tags.iteritems()], _("Tags"))
        hist_l.append(tags_group)
        choices.extend([x[0] for x in tags_group[0]])

        return choices, hist_l

    def _get_git_hook_interpreter(self):
        """Return a suitable interpreter for Git hooks.

        Return a suitable string to be written in the POSIX #! shebang line for
        Git hook scripts so they invoke Kallithea code with the right Python
        interpreter and in the right environment.
        """
        # Note: sys.executable might not point at a usable Python interpreter. For
        # example, when using uwsgi, it will point at the uwsgi program itself.
        # FIXME This may not work on Windows and may need a shell wrapper script.
        return (kallithea.CONFIG.get('git_hook_interpreter')
                or sys.executable
                or '/usr/bin/env python2')

    def install_git_hooks(self, repo, force_create=False):
        """
        Creates a kallithea hook inside a git repository

        :param repo: Instance of VCS repo
        :param force_create: Create even if same name hook exists
        """

        loc = os.path.join(repo.path, 'hooks')
        if not repo.bare:
            loc = os.path.join(repo.path, '.git', 'hooks')
        if not os.path.isdir(loc):
            os.makedirs(loc)

        tmpl_post = "#!%s\n" % self._get_git_hook_interpreter()
        tmpl_post += pkg_resources.resource_string(
            'kallithea', os.path.join('config', 'post_receive_tmpl.py')
        )
        tmpl_pre = "#!%s\n" % self._get_git_hook_interpreter()
        tmpl_pre += pkg_resources.resource_string(
            'kallithea', os.path.join('config', 'pre_receive_tmpl.py')
        )

        for h_type, tmpl in [('pre', tmpl_pre), ('post', tmpl_post)]:
            _hook_file = os.path.join(loc, '%s-receive' % h_type)
            has_hook = False
            log.debug('Installing git hook in repo %s', repo)
            if os.path.exists(_hook_file):
                # let's take a look at this hook, maybe it's kallithea ?
                log.debug('hook exists, checking if it is from kallithea')
                with open(_hook_file, 'rb') as f:
                    data = f.read()
                    matches = re.compile(r'(?:%s)\s*=\s*(.*)'
                                         % 'KALLITHEA_HOOK_VER').search(data)
                    if matches:
                        try:
                            ver = matches.groups()[0]
                            log.debug('got %s it is kallithea', ver)
                            has_hook = True
                        except Exception:
                            log.error(traceback.format_exc())
            else:
                # there is no hook in this dir, so we want to create one
                has_hook = True

            if has_hook or force_create:
                log.debug('writing %s hook file !', h_type)
                try:
                    with open(_hook_file, 'wb') as f:
                        tmpl = tmpl.replace('_TMPL_', kallithea.__version__)
                        f.write(tmpl)
                    os.chmod(_hook_file, 0755)
                except IOError as e:
                    log.error('error writing %s: %s', _hook_file, e)
            else:
                log.debug('skipping writing hook file')


def AvailableRepoGroupChoices(top_perms, repo_group_perm_level, extras=()):
    """Return group_id,string tuples with choices for all the repo groups where
    the user has the necessary permissions.

    Top level is -1.
    """
    groups = RepoGroup.query().all()
    if HasPermissionAny('hg.admin')('available repo groups'):
        groups.append(None)
    else:
        groups = list(RepoGroupList(groups, perm_level=repo_group_perm_level))
        if top_perms and HasPermissionAny(*top_perms)('available repo groups'):
            groups.append(None)
        for extra in extras:
            if not any(rg == extra for rg in groups):
                groups.append(extra)
    return RepoGroup.groups_choices(groups=groups)
