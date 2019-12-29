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
kallithea.lib.hooks
~~~~~~~~~~~~~~~~~~~

Hooks run by Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 6, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import binascii
import os
import sys
import time

from kallithea.lib import helpers as h
from kallithea.lib.exceptions import UserCreationError
from kallithea.lib.utils import action_logger, make_ui, setup_cache_regions
from kallithea.lib.utils2 import HookEnvironmentError, get_hook_environment, safe_str, safe_unicode
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.utils.hgcompat import revrange
from kallithea.model.db import Repository, User


def _get_scm_size(alias, root_path):
    if not alias.startswith('.'):
        alias += '.'

    size_scm, size_root = 0, 0
    for path, dirs, files in os.walk(safe_str(root_path)):
        if path.find(alias) != -1:
            for f in files:
                try:
                    size_scm += os.path.getsize(os.path.join(path, f))
                except OSError:
                    pass
        else:
            for f in files:
                try:
                    size_root += os.path.getsize(os.path.join(path, f))
                except OSError:
                    pass

    size_scm_f = h.format_byte_size(size_scm)
    size_root_f = h.format_byte_size(size_root)
    size_total_f = h.format_byte_size(size_root + size_scm)

    return size_scm_f, size_root_f, size_total_f


def repo_size(ui, repo, hooktype=None, **kwargs):
    """Presents size of repository after push"""
    size_hg_f, size_root_f, size_total_f = _get_scm_size('.hg', repo.root)

    last_cs = repo[len(repo) - 1]

    msg = ('Repository size .hg: %s Checkout: %s Total: %s\n'
           'Last revision is now r%s:%s\n') % (
        size_hg_f, size_root_f, size_total_f, last_cs.rev(), last_cs.hex()[:12]
    )
    ui.status(msg)


def log_pull_action(ui, repo, **kwargs):
    """Logs user last pull action

    Called as Mercurial hook outgoing.pull_logger or from Kallithea before invoking Git.

    Does *not* use the action from the hook environment but is always 'pull'.
    """
    ex = get_hook_environment()

    user = User.get_by_username(ex.username)
    action = 'pull'
    action_logger(user, action, ex.repository, ex.ip, commit=True)
    # extension hook call
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'PULL_HOOK', None)
    if callable(callback):
        kw = {}
        kw.update(ex)
        callback(**kw)

    return 0


def log_push_action(ui, repo, node, node_last, **kwargs):
    """
    Entry point for Mercurial hook changegroup.push_logger.

    The pushed changesets is given by the revset 'node:node_last'.

    Note: This hook is not only logging, but also the side effect invalidating
    cahes! The function should perhaps be renamed.
    """
    _h = binascii.hexlify
    revs = [_h(repo[r].node()) for r in revrange(repo, [node + ':' + node_last])]
    process_pushed_raw_ids(revs)
    return 0


def process_pushed_raw_ids(revs):
    """
    Register that changes have been added to the repo - log the action *and* invalidate caches.

    Called from  Mercurial changegroup.push_logger calling hook log_push_action,
    or from the Git post-receive hook calling handle_git_post_receive ...
    or from scm _handle_push.
    """
    ex = get_hook_environment()

    action = '%s:%s' % (ex.action, ','.join(revs))
    action_logger(ex.username, action, ex.repository, ex.ip, commit=True)

    from kallithea.model.scm import ScmModel
    ScmModel().mark_for_invalidation(ex.repository)

    # extension hook call
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'PUSH_HOOK', None)
    if callable(callback):
        kw = {'pushed_revs': revs}
        kw.update(ex)
        callback(**kw)


def log_create_repository(repository_dict, created_by, **kwargs):
    """
    Post create repository Hook.

    :param repository: dict dump of repository object
    :param created_by: username who created repository

    available keys of repository_dict:

     'repo_type',
     'description',
     'private',
     'created_on',
     'enable_downloads',
     'repo_id',
     'owner_id',
     'enable_statistics',
     'clone_uri',
     'fork_id',
     'group_id',
     'repo_name'

    """
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'CREATE_REPO_HOOK', None)
    if callable(callback):
        kw = {}
        kw.update(repository_dict)
        kw.update({'created_by': created_by})
        kw.update(kwargs)
        return callback(**kw)

    return 0


def check_allowed_create_user(user_dict, created_by, **kwargs):
    # pre create hooks
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'PRE_CREATE_USER_HOOK', None)
    if callable(callback):
        allowed, reason = callback(created_by=created_by, **user_dict)
        if not allowed:
            raise UserCreationError(reason)


def log_create_user(user_dict, created_by, **kwargs):
    """
    Post create user Hook.

    :param user_dict: dict dump of user object

    available keys for user_dict:

     'username',
     'full_name_or_username',
     'full_contact',
     'user_id',
     'name',
     'firstname',
     'short_contact',
     'admin',
     'lastname',
     'ip_addresses',
     'ldap_dn',
     'email',
     'api_key',
     'last_login',
     'full_name',
     'active',
     'password',
     'emails',

    """
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'CREATE_USER_HOOK', None)
    if callable(callback):
        return callback(created_by=created_by, **user_dict)

    return 0


def log_delete_repository(repository_dict, deleted_by, **kwargs):
    """
    Post delete repository Hook.

    :param repository: dict dump of repository object
    :param deleted_by: username who deleted the repository

    available keys of repository_dict:

     'repo_type',
     'description',
     'private',
     'created_on',
     'enable_downloads',
     'repo_id',
     'owner_id',
     'enable_statistics',
     'clone_uri',
     'fork_id',
     'group_id',
     'repo_name'

    """
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'DELETE_REPO_HOOK', None)
    if callable(callback):
        kw = {}
        kw.update(repository_dict)
        kw.update({'deleted_by': deleted_by,
                   'deleted_on': time.time()})
        kw.update(kwargs)
        return callback(**kw)

    return 0


def log_delete_user(user_dict, deleted_by, **kwargs):
    """
    Post delete user Hook.

    :param user_dict: dict dump of user object

    available keys for user_dict:

     'username',
     'full_name_or_username',
     'full_contact',
     'user_id',
     'name',
     'firstname',
     'short_contact',
     'admin',
     'lastname',
     'ip_addresses',
     'ldap_dn',
     'email',
     'api_key',
     'last_login',
     'full_name',
     'active',
     'password',
     'emails',

    """
    from kallithea import EXTENSIONS
    callback = getattr(EXTENSIONS, 'DELETE_USER_HOOK', None)
    if callable(callback):
        return callback(deleted_by=deleted_by, **user_dict)

    return 0


def _hook_environment(repo_path):
    """
    Create a light-weight environment for stand-alone scripts and return an UI and the
    db repository.

    Git hooks are executed as subprocess of Git while Kallithea is waiting, and
    they thus need enough info to be able to create an app environment and
    connect to the database.
    """
    from paste.deploy import appconfig
    from sqlalchemy import engine_from_config
    from kallithea.config.environment import load_environment
    from kallithea.model.base import init_model

    extras = get_hook_environment()
    ini_file_path = extras['config']
    #logging.config.fileConfig(ini_file_path) # Note: we are in a different process - don't use configured logging
    app_conf = appconfig('config:%s' % ini_file_path)
    conf = load_environment(app_conf.global_conf, app_conf.local_conf)

    setup_cache_regions(conf)

    engine = engine_from_config(conf, 'sqlalchemy.')
    init_model(engine)

    repo_path = safe_unicode(repo_path)
    # fix if it's not a bare repo
    if repo_path.endswith(os.sep + '.git'):
        repo_path = repo_path[:-5]

    repo = Repository.get_by_full_path(repo_path)
    if not repo:
        raise OSError('Repository %s not found in database'
                      % (safe_str(repo_path)))

    baseui = make_ui()
    return baseui, repo


def handle_git_pre_receive(repo_path, git_stdin_lines):
    """Called from Git pre-receive hook"""
    # Currently unused. TODO: remove?
    return 0


def handle_git_post_receive(repo_path, git_stdin_lines):
    """Called from Git post-receive hook"""
    try:
        baseui, repo = _hook_environment(repo_path)
    except HookEnvironmentError as e:
        sys.stderr.write("Skipping Kallithea Git post-recieve hook %r.\nGit was apparently not invoked by Kallithea: %s\n" % (sys.argv[0], e))
        return 0

    # the post push hook should never use the cached instance
    scm_repo = repo.scm_instance_no_cache()

    rev_data = []
    for l in git_stdin_lines:
        old_rev, new_rev, ref = l.strip().split(' ')
        _ref_data = ref.split('/')
        if _ref_data[1] in ['tags', 'heads']:
            rev_data.append({'old_rev': old_rev,
                             'new_rev': new_rev,
                             'ref': ref,
                             'type': _ref_data[1],
                             'name': '/'.join(_ref_data[2:])})

    git_revs = []
    for push_ref in rev_data:
        _type = push_ref['type']
        if _type == 'heads':
            if push_ref['old_rev'] == EmptyChangeset().raw_id:
                # update the symbolic ref if we push new repo
                if scm_repo.is_empty():
                    scm_repo._repo.refs.set_symbolic_ref('HEAD',
                                        'refs/heads/%s' % push_ref['name'])

                # build exclude list without the ref
                cmd = ['for-each-ref', '--format=%(refname)', 'refs/heads/*']
                stdout, stderr = scm_repo.run_git_command(cmd)
                ref = push_ref['ref']
                heads = [head for head in stdout.splitlines() if head != ref]
                # now list the git revs while excluding from the list
                cmd = ['log', push_ref['new_rev'], '--reverse', '--pretty=format:%H']
                cmd.append('--not')
                cmd.extend(heads) # empty list is ok
                stdout, stderr = scm_repo.run_git_command(cmd)
                git_revs += stdout.splitlines()

            elif push_ref['new_rev'] == EmptyChangeset().raw_id:
                # delete branch case
                git_revs += ['delete_branch=>%s' % push_ref['name']]
            else:
                cmd = ['log', '%(old_rev)s..%(new_rev)s' % push_ref,
                       '--reverse', '--pretty=format:%H']
                stdout, stderr = scm_repo.run_git_command(cmd)
                git_revs += stdout.splitlines()

        elif _type == 'tags':
            git_revs += ['tag=>%s' % push_ref['name']]

    process_pushed_raw_ids(git_revs)

    return 0


# Almost exactly like Mercurial contrib/hg-ssh:
def rejectpush(ui, **kwargs):
    """Mercurial hook to be installed as pretxnopen and prepushkey for read-only repos"""
    ex = get_hook_environment()
    ui.warn((b"Push access to %r denied\n") % safe_str(ex.repository))
    return 1
