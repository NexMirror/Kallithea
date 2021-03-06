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
kallithea.model.repo
~~~~~~~~~~~~~~~~~~~~

Repository model for kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jun 5, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

import logging
import os
import shutil
import traceback
from datetime import datetime

import kallithea.lib.utils2
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionLevel, HasUserGroupPermissionLevel
from kallithea.lib.exceptions import AttachedForksError
from kallithea.lib.hooks import log_delete_repository
from kallithea.lib.utils import is_valid_repo_uri, make_ui
from kallithea.lib.utils2 import LazyProperty, get_current_authuser, obfuscate_url_pw, remove_prefix
from kallithea.lib.vcs.backends import get_backend
from kallithea.model.db import (URL_SEP, Permission, RepoGroup, Repository, RepositoryField, Session, Statistics, Ui, User, UserGroup, UserGroupRepoGroupToPerm,
                                UserGroupRepoToPerm, UserRepoGroupToPerm, UserRepoToPerm)


log = logging.getLogger(__name__)


class RepoModel(object):

    URL_SEPARATOR = URL_SEP

    def _create_default_perms(self, repository, private):
        # create default permission
        default = 'repository.read'
        def_user = User.get_default_user()
        for p in def_user.user_perms:
            if p.permission.permission_name.startswith('repository.'):
                default = p.permission.permission_name
                break

        default_perm = 'repository.none' if private else default

        repo_to_perm = UserRepoToPerm()
        repo_to_perm.permission = Permission.get_by_key(default_perm)

        repo_to_perm.repository = repository
        repo_to_perm.user_id = def_user.user_id
        Session().add(repo_to_perm)

        return repo_to_perm

    @LazyProperty
    def repos_path(self):
        """
        Gets the repositories root path from database
        """

        q = Ui.query().filter(Ui.ui_key == '/').one()
        return q.ui_value

    def get(self, repo_id):
        repo = Repository.query() \
            .filter(Repository.repo_id == repo_id)
        return repo.scalar()

    def get_repo(self, repository):
        return Repository.guess_instance(repository)

    def get_by_repo_name(self, repo_name):
        repo = Repository.query() \
            .filter(Repository.repo_name == repo_name)
        return repo.scalar()

    def get_all_user_repos(self, user):
        """
        Gets all repositories that user have at least read access

        :param user:
        """
        from kallithea.lib.auth import AuthUser
        auth_user = AuthUser(dbuser=User.guess_instance(user))
        repos = [repo_name
            for repo_name, perm in auth_user.permissions['repositories'].items()
            if perm in ['repository.read', 'repository.write', 'repository.admin']
            ]
        return Repository.query().filter(Repository.repo_name.in_(repos))

    @classmethod
    def _render_datatable(cls, tmpl, *args, **kwargs):
        from tg import tmpl_context as c, request, app_globals
        from tg.i18n import ugettext as _

        _tmpl_lookup = app_globals.mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        tmpl = template.get_def(tmpl)
        kwargs.update(dict(_=_, h=h, c=c, request=request))
        return tmpl.render_unicode(*args, **kwargs)

    def get_repos_as_dict(self, repos_list, repo_groups_list=None,
                          admin=False,
                          short_name=False):
        """Return repository list for use by DataTable.
        repos_list: list of repositories - but will be filtered for read permission.
        repo_groups_list: added at top of list without permission check.
        admin: return data for action column.
        """
        _render = self._render_datatable
        from tg import tmpl_context as c, request
        from kallithea.model.scm import ScmModel

        def repo_lnk(name, rtype, rstate, private, fork_of):
            return _render('repo_name', name, rtype, rstate, private, fork_of,
                           short_name=short_name)

        def following(repo_id, is_following):
            return _render('following', repo_id, is_following)

        def last_change(last_change):
            return _render("last_change", last_change)

        def rss_lnk(repo_name):
            return _render("rss", repo_name)

        def atom_lnk(repo_name):
            return _render("atom", repo_name)

        def last_rev(repo_name, cs_cache):
            return _render('revision', repo_name, cs_cache.get('revision'),
                           cs_cache.get('raw_id'), cs_cache.get('author'),
                           cs_cache.get('message'))

        def desc(desc):
            return h.urlify_text(desc, truncate=80, stylize=c.visual.stylify_metalabels)

        def state(repo_state):
            return _render("repo_state", repo_state)

        def repo_actions(repo_name):
            return _render('repo_actions', repo_name)

        def owner_actions(owner_id, username):
            return _render('user_name', owner_id, username)

        repos_data = []

        for gr in repo_groups_list or []:
            repos_data.append(dict(
                raw_name='\0' + gr.name, # sort before repositories
                just_name=gr.name,
                name=_render('group_name_html', group_name=gr.group_name, name=gr.name),
                desc=gr.group_description))

        for repo in repos_list:
            if not HasRepoPermissionLevel('read')(repo.repo_name, 'get_repos_as_dict check'):
                continue
            cs_cache = repo.changeset_cache
            row = {
                "raw_name": repo.repo_name,
                "just_name": repo.just_name,
                "name": repo_lnk(repo.repo_name, repo.repo_type,
                                 repo.repo_state, repo.private, repo.fork),
                "following": following(
                    repo.repo_id,
                    ScmModel().is_following_repo(repo.repo_name, request.authuser.user_id),
                ),
                "last_change_iso": repo.last_db_change.isoformat(),
                "last_change": last_change(repo.last_db_change),
                "last_changeset": last_rev(repo.repo_name, cs_cache),
                "last_rev_raw": cs_cache.get('revision'),
                "desc": desc(repo.description),
                "owner": h.person(repo.owner),
                "state": state(repo.repo_state),
                "rss": rss_lnk(repo.repo_name),
                "atom": atom_lnk(repo.repo_name),
            }
            if admin:
                row.update({
                    "action": repo_actions(repo.repo_name),
                    "owner": owner_actions(repo.owner_id,
                                           h.person(repo.owner))
                })
            repos_data.append(row)

        return {
            "sort": "name",
            "dir": "asc",
            "records": repos_data
        }

    def _get_defaults(self, repo_name):
        """
        Gets information about repository, and returns a dict for
        usage in forms

        :param repo_name:
        """

        repo_info = Repository.get_by_repo_name(repo_name)

        if repo_info is None:
            return None

        defaults = repo_info.get_dict()
        defaults['repo_name'] = repo_info.just_name
        defaults['repo_group'] = repo_info.group_id

        for strip, k in [(0, 'repo_type'), (1, 'repo_enable_downloads'),
                         (1, 'repo_description'),
                         (1, 'repo_landing_rev'), (0, 'clone_uri'),
                         (1, 'repo_private'), (1, 'repo_enable_statistics')]:
            attr = k
            if strip:
                attr = remove_prefix(k, 'repo_')

            val = defaults[attr]
            if k == 'repo_landing_rev':
                val = ':'.join(defaults[attr])
            defaults[k] = val
            if k == 'clone_uri':
                defaults['clone_uri_hidden'] = repo_info.clone_uri_hidden

        # fill owner
        if repo_info.owner:
            defaults.update({'owner': repo_info.owner.username})
        else:
            replacement_user = User.query().filter(User.admin ==
                                                   True).first().username
            defaults.update({'owner': replacement_user})

        # fill repository users
        for p in repo_info.repo_to_perm:
            defaults.update({'u_perm_%s' % p.user.username:
                                 p.permission.permission_name})

        # fill repository groups
        for p in repo_info.users_group_to_perm:
            defaults.update({'g_perm_%s' % p.users_group.users_group_name:
                                 p.permission.permission_name})

        return defaults

    def update(self, repo, **kwargs):
        try:
            cur_repo = Repository.guess_instance(repo)
            org_repo_name = cur_repo.repo_name
            if 'owner' in kwargs:
                cur_repo.owner = User.get_by_username(kwargs['owner'])

            if 'repo_group' in kwargs:
                assert kwargs['repo_group'] != '-1', kwargs # RepoForm should have converted to None
                cur_repo.group = RepoGroup.get(kwargs['repo_group'])
                cur_repo.repo_name = cur_repo.get_new_name(cur_repo.just_name)
            log.debug('Updating repo %s with params:%s', cur_repo, kwargs)
            for k in ['repo_enable_downloads',
                      'repo_description',
                      'repo_landing_rev',
                      'repo_private',
                      'repo_enable_statistics',
                      ]:
                if k in kwargs:
                    setattr(cur_repo, remove_prefix(k, 'repo_'), kwargs[k])
            clone_uri = kwargs.get('clone_uri')
            if clone_uri is not None and clone_uri != cur_repo.clone_uri_hidden:
                # clone_uri is modified - if given a value, check it is valid
                if clone_uri != '':
                    # will raise exception on error
                    is_valid_repo_uri(cur_repo.repo_type, clone_uri, make_ui())
                cur_repo.clone_uri = clone_uri

            if 'repo_name' in kwargs:
                repo_name = kwargs['repo_name']
                if kallithea.lib.utils2.repo_name_slug(repo_name) != repo_name:
                    raise Exception('invalid repo name %s' % repo_name)
                cur_repo.repo_name = cur_repo.get_new_name(repo_name)

            # if private flag is set, reset default permission to NONE
            if kwargs.get('repo_private'):
                EMPTY_PERM = 'repository.none'
                RepoModel().grant_user_permission(
                    repo=cur_repo, user='default', perm=EMPTY_PERM
                )
                # handle extra fields
            for field in [k for k in kwargs if k.startswith(RepositoryField.PREFIX)]:
                k = RepositoryField.un_prefix_key(field)
                ex_field = RepositoryField.get_by_key_name(key=k, repo=cur_repo)
                if ex_field:
                    ex_field.field_value = kwargs[field]

            if org_repo_name != cur_repo.repo_name:
                # rename repository
                self._rename_filesystem_repo(old=org_repo_name, new=cur_repo.repo_name)

            return cur_repo
        except Exception:
            log.error(traceback.format_exc())
            raise

    def _create_repo(self, repo_name, repo_type, description, owner,
                     private=False, clone_uri=None, repo_group=None,
                     landing_rev='rev:tip', fork_of=None,
                     copy_fork_permissions=False, enable_statistics=False,
                     enable_downloads=False,
                     copy_group_permissions=False, state=Repository.STATE_PENDING):
        """
        Create repository inside database with PENDING state. This should only be
        executed by create() repo, with exception of importing existing repos.

        """
        from kallithea.model.scm import ScmModel

        owner = User.guess_instance(owner)
        fork_of = Repository.guess_instance(fork_of)
        repo_group = RepoGroup.guess_instance(repo_group)
        try:
            repo_name = repo_name
            description = description
            # repo name is just a name of repository
            # while repo_name_full is a full qualified name that is combined
            # with name and path of group
            repo_name_full = repo_name
            repo_name = repo_name.split(URL_SEP)[-1]
            if kallithea.lib.utils2.repo_name_slug(repo_name) != repo_name:
                raise Exception('invalid repo name %s' % repo_name)

            new_repo = Repository()
            new_repo.repo_state = state
            new_repo.enable_statistics = False
            new_repo.repo_name = repo_name_full
            new_repo.repo_type = repo_type
            new_repo.owner = owner
            new_repo.group = repo_group
            new_repo.description = description or repo_name
            new_repo.private = private
            if clone_uri:
                # will raise exception on error
                is_valid_repo_uri(repo_type, clone_uri, make_ui())
            new_repo.clone_uri = clone_uri
            new_repo.landing_rev = landing_rev

            new_repo.enable_statistics = enable_statistics
            new_repo.enable_downloads = enable_downloads

            if fork_of:
                parent_repo = fork_of
                new_repo.fork = parent_repo

            Session().add(new_repo)

            if fork_of and copy_fork_permissions:
                repo = fork_of
                user_perms = UserRepoToPerm.query() \
                    .filter(UserRepoToPerm.repository == repo).all()
                group_perms = UserGroupRepoToPerm.query() \
                    .filter(UserGroupRepoToPerm.repository == repo).all()

                for perm in user_perms:
                    UserRepoToPerm.create(perm.user, new_repo, perm.permission)

                for perm in group_perms:
                    UserGroupRepoToPerm.create(perm.users_group, new_repo,
                                               perm.permission)

            elif repo_group and copy_group_permissions:

                user_perms = UserRepoGroupToPerm.query() \
                    .filter(UserRepoGroupToPerm.group == repo_group).all()

                group_perms = UserGroupRepoGroupToPerm.query() \
                    .filter(UserGroupRepoGroupToPerm.group == repo_group).all()

                for perm in user_perms:
                    perm_name = perm.permission.permission_name.replace('group.', 'repository.')
                    perm_obj = Permission.get_by_key(perm_name)
                    UserRepoToPerm.create(perm.user, new_repo, perm_obj)

                for perm in group_perms:
                    perm_name = perm.permission.permission_name.replace('group.', 'repository.')
                    perm_obj = Permission.get_by_key(perm_name)
                    UserGroupRepoToPerm.create(perm.users_group, new_repo, perm_obj)

            else:
                self._create_default_perms(new_repo, private)

            # now automatically start following this repository as owner
            ScmModel().toggle_following_repo(new_repo.repo_id, owner.user_id)
            # we need to flush here, in order to check if database won't
            # throw any exceptions, create filesystem dirs at the very end
            Session().flush()
            return new_repo
        except Exception:
            log.error(traceback.format_exc())
            raise

    def create(self, form_data, cur_user):
        """
        Create repository using celery tasks

        :param form_data:
        :param cur_user:
        """
        from kallithea.lib.celerylib import tasks
        return tasks.create_repo(form_data, cur_user)

    def _update_permissions(self, repo, perms_new=None, perms_updates=None,
                            check_perms=True):
        if not perms_new:
            perms_new = []
        if not perms_updates:
            perms_updates = []

        # update permissions
        for member, perm, member_type in perms_updates:
            if member_type == 'user':
                # this updates existing one
                self.grant_user_permission(
                    repo=repo, user=member, perm=perm
                )
            else:
                # check if we have permissions to alter this usergroup's access
                if not check_perms or HasUserGroupPermissionLevel('read')(member):
                    self.grant_user_group_permission(
                        repo=repo, group_name=member, perm=perm
                    )
            # set new permissions
        for member, perm, member_type in perms_new:
            if member_type == 'user':
                self.grant_user_permission(
                    repo=repo, user=member, perm=perm
                )
            else:
                # check if we have permissions to alter this usergroup's access
                if not check_perms or HasUserGroupPermissionLevel('read')(member):
                    self.grant_user_group_permission(
                        repo=repo, group_name=member, perm=perm
                    )

    def create_fork(self, form_data, cur_user):
        """
        Simple wrapper into executing celery task for fork creation

        :param form_data:
        :param cur_user:
        """
        from kallithea.lib.celerylib import tasks
        return tasks.create_repo_fork(form_data, cur_user)

    def delete(self, repo, forks=None, fs_remove=True, cur_user=None):
        """
        Delete given repository, forks parameter defines what do do with
        attached forks. Throws AttachedForksError if deleted repo has attached
        forks

        :param repo:
        :param forks: str 'delete' or 'detach'
        :param fs_remove: remove(archive) repo from filesystem
        """
        if not cur_user:
            cur_user = getattr(get_current_authuser(), 'username', None)
        repo = Repository.guess_instance(repo)
        if repo is not None:
            if forks == 'detach':
                for r in repo.forks:
                    r.fork = None
            elif forks == 'delete':
                for r in repo.forks:
                    self.delete(r, forks='delete')
            elif [f for f in repo.forks]:
                raise AttachedForksError()

            old_repo_dict = repo.get_dict()
            try:
                Session().delete(repo)
                if fs_remove:
                    self._delete_filesystem_repo(repo)
                else:
                    log.debug('skipping removal from filesystem')
                log_delete_repository(old_repo_dict,
                                      deleted_by=cur_user)
            except Exception:
                log.error(traceback.format_exc())
                raise

    def grant_user_permission(self, repo, user, perm):
        """
        Grant permission for user on given repository, or update existing one
        if found

        :param repo: Instance of Repository, repository_id, or repository name
        :param user: Instance of User, user_id or username
        :param perm: Instance of Permission, or permission_name
        """
        user = User.guess_instance(user)
        repo = Repository.guess_instance(repo)
        permission = Permission.guess_instance(perm)

        # check if we have that permission already
        obj = UserRepoToPerm.query() \
            .filter(UserRepoToPerm.user == user) \
            .filter(UserRepoToPerm.repository == repo) \
            .scalar()
        if obj is None:
            # create new !
            obj = UserRepoToPerm()
            Session().add(obj)
        obj.repository = repo
        obj.user = user
        obj.permission = permission
        log.debug('Granted perm %s to %s on %s', perm, user, repo)
        return obj

    def revoke_user_permission(self, repo, user):
        """
        Revoke permission for user on given repository

        :param repo: Instance of Repository, repository_id, or repository name
        :param user: Instance of User, user_id or username
        """

        user = User.guess_instance(user)
        repo = Repository.guess_instance(repo)

        obj = UserRepoToPerm.query() \
            .filter(UserRepoToPerm.repository == repo) \
            .filter(UserRepoToPerm.user == user) \
            .scalar()
        if obj is not None:
            Session().delete(obj)
            log.debug('Revoked perm on %s on %s', repo, user)

    def grant_user_group_permission(self, repo, group_name, perm):
        """
        Grant permission for user group on given repository, or update
        existing one if found

        :param repo: Instance of Repository, repository_id, or repository name
        :param group_name: Instance of UserGroup, users_group_id,
            or user group name
        :param perm: Instance of Permission, or permission_name
        """
        repo = Repository.guess_instance(repo)
        group_name = UserGroup.guess_instance(group_name)
        permission = Permission.guess_instance(perm)

        # check if we have that permission already
        obj = UserGroupRepoToPerm.query() \
            .filter(UserGroupRepoToPerm.users_group == group_name) \
            .filter(UserGroupRepoToPerm.repository == repo) \
            .scalar()

        if obj is None:
            # create new
            obj = UserGroupRepoToPerm()
            Session().add(obj)

        obj.repository = repo
        obj.users_group = group_name
        obj.permission = permission
        log.debug('Granted perm %s to %s on %s', perm, group_name, repo)
        return obj

    def revoke_user_group_permission(self, repo, group_name):
        """
        Revoke permission for user group on given repository

        :param repo: Instance of Repository, repository_id, or repository name
        :param group_name: Instance of UserGroup, users_group_id,
            or user group name
        """
        repo = Repository.guess_instance(repo)
        group_name = UserGroup.guess_instance(group_name)

        obj = UserGroupRepoToPerm.query() \
            .filter(UserGroupRepoToPerm.repository == repo) \
            .filter(UserGroupRepoToPerm.users_group == group_name) \
            .scalar()
        if obj is not None:
            Session().delete(obj)
            log.debug('Revoked perm to %s on %s', repo, group_name)

    def delete_stats(self, repo_name):
        """
        removes stats for given repo

        :param repo_name:
        """
        repo = Repository.guess_instance(repo_name)
        try:
            obj = Statistics.query() \
                .filter(Statistics.repository == repo).scalar()
            if obj is not None:
                Session().delete(obj)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def _create_filesystem_repo(self, repo_name, repo_type, repo_group,
                                clone_uri=None, repo_store_location=None):
        """
        Makes repository on filesystem. Operation is group aware, meaning that it will create
        a repository within a group, and alter the paths accordingly to the group location.

        Note: clone_uri is low level and not validated - it might be a file system path used for validated cloning
        """
        from kallithea.lib.utils import is_valid_repo, is_valid_repo_group
        from kallithea.model.scm import ScmModel

        if '/' in repo_name:
            raise ValueError('repo_name must not contain groups got `%s`' % repo_name)

        if isinstance(repo_group, RepoGroup):
            new_parent_path = os.sep.join(repo_group.full_path_splitted)
        else:
            new_parent_path = repo_group or ''

        if repo_store_location:
            _paths = [repo_store_location]
        else:
            _paths = [self.repos_path, new_parent_path, repo_name]
        repo_path = os.path.join(*_paths)

        # check if this path is not a repository
        if is_valid_repo(repo_path, self.repos_path):
            raise Exception('This path %s is a valid repository' % repo_path)

        # check if this path is a group
        if is_valid_repo_group(repo_path, self.repos_path):
            raise Exception('This path %s is a valid group' % repo_path)

        log.info('creating repo %s in %s from url: `%s`',
            repo_name, repo_path,
            obfuscate_url_pw(clone_uri))

        backend = get_backend(repo_type)

        if repo_type == 'hg':
            baseui = make_ui()
            # patch and reset hooks section of UI config to not run any
            # hooks on creating remote repo
            for k, v in baseui.configitems('hooks'):
                baseui.setconfig('hooks', k, None)

            repo = backend(repo_path, create=True, src_url=clone_uri, baseui=baseui)
        elif repo_type == 'git':
            repo = backend(repo_path, create=True, src_url=clone_uri, bare=True)
            # add kallithea hook into this repo
            ScmModel().install_git_hooks(repo=repo)
        else:
            raise Exception('Not supported repo_type %s expected hg/git' % repo_type)

        log.debug('Created repo %s with %s backend',
                  repo_name, repo_type)
        return repo

    def _rename_filesystem_repo(self, old, new):
        """
        renames repository on filesystem

        :param old: old name
        :param new: new name
        """
        log.info('renaming repo from %s to %s', old, new)

        old_path = os.path.join(self.repos_path, old)
        new_path = os.path.join(self.repos_path, new)
        if os.path.isdir(new_path):
            raise Exception(
                'Was trying to rename to already existing dir %s' % new_path
            )
        shutil.move(old_path, new_path)

    def _delete_filesystem_repo(self, repo):
        """
        removes repo from filesystem, the removal is actually done by
        renaming dir to a 'rm__*' prefix which Kallithea will skip.
        It can be undeleted later by reverting the rename.

        :param repo: repo object
        """
        rm_path = os.path.join(self.repos_path, repo.repo_name)
        log.info("Removing %s", rm_path)

        _now = datetime.now()
        _ms = str(_now.microsecond).rjust(6, '0')
        _d = 'rm__%s__%s' % (_now.strftime('%Y%m%d_%H%M%S_' + _ms),
                             repo.just_name)
        if repo.group:
            args = repo.group.full_path_splitted + [_d]
            _d = os.path.join(*args)
        if os.path.exists(rm_path):
            shutil.move(rm_path, os.path.join(self.repos_path, _d))
        else:
            log.error("Can't find repo to delete in %r", rm_path)
