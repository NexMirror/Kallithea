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
kallithea.lib.utils
~~~~~~~~~~~~~~~~~~~

Utilities library for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 18, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import datetime
import logging
import os
import re
import sys
import traceback
from distutils.version import StrictVersion

import beaker
from beaker.cache import _cache_decorate
from tg.i18n import ugettext as _

from kallithea.lib.exceptions import HgsubversionImportError
from kallithea.lib.utils2 import get_current_authuser, safe_str, safe_unicode
from kallithea.lib.vcs.exceptions import VCSError
from kallithea.lib.vcs.utils.fakemod import create_module
from kallithea.lib.vcs.utils.helpers import get_scm
from kallithea.lib.vcs.utils.hgcompat import config, ui
from kallithea.model import meta
from kallithea.model.db import RepoGroup, Repository, Setting, Ui, User, UserGroup, UserLog
from kallithea.model.repo_group import RepoGroupModel


log = logging.getLogger(__name__)

REMOVED_REPO_PAT = re.compile(r'rm__\d{8}_\d{6}_\d{6}_.*')


#==============================================================================
# PERM DECORATOR HELPERS FOR EXTRACTING NAMES FOR PERM CHECKS
#==============================================================================
def get_repo_slug(request):
    _repo = request.environ['pylons.routes_dict'].get('repo_name')
    if _repo:
        _repo = _repo.rstrip('/')
    return _repo


def get_repo_group_slug(request):
    _group = request.environ['pylons.routes_dict'].get('group_name')
    if _group:
        _group = _group.rstrip('/')
    return _group


def get_user_group_slug(request):
    _group = request.environ['pylons.routes_dict'].get('id')
    _group = UserGroup.get(_group)
    if _group:
        return _group.users_group_name
    return None


def _get_permanent_id(s):
    """Helper for decoding stable URLs with repo ID. For a string like '_123'
    return 123.
    """
    by_id_match = re.match(r'^_(\d+)$', s)
    if by_id_match is None:
        return None
    return int(by_id_match.group(1))


def fix_repo_id_name(path):
    """
    Rewrite repo_name for _<ID> permanent URLs.

    Given a path, if the first path element is like _<ID>, return the path with
    this part expanded to the corresponding full repo name, else return the
    provided path.
    """
    first, rest = path, ''
    if '/' in path:
        first, rest_ = path.split('/', 1)
        rest = '/' + rest_
    repo_id = _get_permanent_id(first)
    if repo_id is not None:
        from kallithea.model.db import Repository
        repo = Repository.get(repo_id)
        if repo is not None:
            return repo.repo_name + rest
    return path


def action_logger(user, action, repo, ipaddr='', commit=False):
    """
    Action logger for various actions made by users

    :param user: user that made this action, can be a unique username string or
        object containing user_id attribute
    :param action: action to log, should be on of predefined unique actions for
        easy translations
    :param repo: string name of repository or object containing repo_id,
        that action was made on
    :param ipaddr: optional IP address from what the action was made

    """

    # if we don't get explicit IP address try to get one from registered user
    # in tmpl context var
    if not ipaddr:
        ipaddr = getattr(get_current_authuser(), 'ip_addr', '')

    if getattr(user, 'user_id', None):
        user_obj = User.get(user.user_id)
    elif isinstance(user, basestring):
        user_obj = User.get_by_username(user)
    else:
        raise Exception('You have to provide a user object or a username')

    if getattr(repo, 'repo_id', None):
        repo_obj = Repository.get(repo.repo_id)
        repo_name = repo_obj.repo_name
    elif isinstance(repo, basestring):
        repo_name = repo.lstrip('/')
        repo_obj = Repository.get_by_repo_name(repo_name)
    else:
        repo_obj = None
        repo_name = u''

    user_log = UserLog()
    user_log.user_id = user_obj.user_id
    user_log.username = user_obj.username
    user_log.action = safe_unicode(action)

    user_log.repository = repo_obj
    user_log.repository_name = repo_name

    user_log.action_date = datetime.datetime.now()
    user_log.user_ip = ipaddr
    meta.Session().add(user_log)

    log.info('Logging action:%s on %s by user:%s ip:%s',
             action, safe_unicode(repo), user_obj, ipaddr)
    if commit:
        meta.Session().commit()


def get_filesystem_repos(path):
    """
    Scans given path for repos and return (name,(type,path)) tuple

    :param path: path to scan for repositories
    :param recursive: recursive search and return names with subdirs in front
    """

    # remove ending slash for better results
    path = safe_str(path.rstrip(os.sep))
    log.debug('now scanning in %s', path)

    def isdir(*n):
        return os.path.isdir(os.path.join(*n))

    for root, dirs, _files in os.walk(path):
        recurse_dirs = []
        for subdir in dirs:
            # skip removed repos
            if REMOVED_REPO_PAT.match(subdir):
                continue

            # skip .<something> dirs TODO: rly? then we should prevent creating them ...
            if subdir.startswith('.'):
                continue

            cur_path = os.path.join(root, subdir)
            if isdir(cur_path, '.git'):
                log.warning('ignoring non-bare Git repo: %s', cur_path)
                continue

            if (isdir(cur_path, '.hg') or
                isdir(cur_path, '.svn') or
                isdir(cur_path, 'objects') and (isdir(cur_path, 'refs') or
                                                os.path.isfile(os.path.join(cur_path, 'packed-refs')))):

                if not os.access(cur_path, os.R_OK) or not os.access(cur_path, os.X_OK):
                    log.warning('ignoring repo path without access: %s', cur_path)
                    continue

                if not os.access(cur_path, os.W_OK):
                    log.warning('repo path without write access: %s', cur_path)

                try:
                    scm_info = get_scm(cur_path)
                    assert cur_path.startswith(path)
                    repo_path = cur_path[len(path) + 1:]
                    yield repo_path, scm_info
                    continue # no recursion
                except VCSError:
                    # We should perhaps ignore such broken repos, but especially
                    # the bare git detection is unreliable so we dive into it
                    pass

            recurse_dirs.append(subdir)

        dirs[:] = recurse_dirs


def is_valid_repo_uri(repo_type, url, ui):
    """Check if the url seems like a valid remote repo location - raise an Exception if any problems"""
    if repo_type == 'hg':
        from kallithea.lib.vcs.backends.hg.repository import MercurialRepository
        if url.startswith('http') or url.startswith('ssh'):
            # initially check if it's at least the proper URL
            # or does it pass basic auth
            MercurialRepository._check_url(url, ui)
        elif url.startswith('svn+http'):
            try:
                from hgsubversion.svnrepo import svnremoterepo
            except ImportError:
                raise HgsubversionImportError(_('Unable to activate hgsubversion support. '
                                                'The "hgsubversion" library is missing'))
            svnremoterepo(ui, url).svn.uuid
        elif url.startswith('git+http'):
            raise NotImplementedError()
        else:
            raise Exception('URI %s not allowed' % (url,))

    elif repo_type == 'git':
        from kallithea.lib.vcs.backends.git.repository import GitRepository
        if url.startswith('http') or url.startswith('git'):
            # initially check if it's at least the proper URL
            # or does it pass basic auth
            GitRepository._check_url(url)
        elif url.startswith('svn+http'):
            raise NotImplementedError()
        elif url.startswith('hg+http'):
            raise NotImplementedError()
        else:
            raise Exception('URI %s not allowed' % (url))


def is_valid_repo(repo_name, base_path, scm=None):
    """
    Returns True if given path is a valid repository False otherwise.
    If scm param is given also compare if given scm is the same as expected
    from scm parameter

    :param repo_name:
    :param base_path:
    :param scm:

    :return True: if given path is a valid repository
    """
    # TODO: paranoid security checks?
    full_path = os.path.join(safe_str(base_path), safe_str(repo_name))

    try:
        scm_ = get_scm(full_path)
        if scm:
            return scm_[0] == scm
        return True
    except VCSError:
        return False


def is_valid_repo_group(repo_group_name, base_path, skip_path_check=False):
    """
    Returns True if given path is a repository group False otherwise

    :param repo_name:
    :param base_path:
    """
    full_path = os.path.join(safe_str(base_path), safe_str(repo_group_name))

    # check if it's not a repo
    if is_valid_repo(repo_group_name, base_path):
        return False

    try:
        # we need to check bare git repos at higher level
        # since we might match branches/hooks/info/objects or possible
        # other things inside bare git repo
        get_scm(os.path.dirname(full_path))
        return False
    except VCSError:
        pass

    # check if it's a valid path
    if skip_path_check or os.path.isdir(full_path):
        return True

    return False


# propagated from mercurial documentation
ui_sections = ['alias', 'auth',
                'decode/encode', 'defaults',
                'diff', 'email',
                'extensions', 'format',
                'merge-patterns', 'merge-tools',
                'hooks', 'http_proxy',
                'smtp', 'patch',
                'paths', 'profiling',
                'server', 'trusted',
                'ui', 'web', ]


def make_ui(repo_path=None, clear_session=True):
    """
    Create an Mercurial 'ui' object based on database Ui settings, possibly
    augmenting with content from a hgrc file.
    """
    baseui = ui.ui()

    # clean the baseui object
    baseui._ocfg = config.config()
    baseui._ucfg = config.config()
    baseui._tcfg = config.config()

    sa = meta.Session()
    for ui_ in sa.query(Ui).all():
        if ui_.ui_active:
            ui_val = '' if ui_.ui_value is None else safe_str(ui_.ui_value)
            log.debug('config from db: [%s] %s=%r', ui_.ui_section,
                      ui_.ui_key, ui_val)
            baseui.setconfig(safe_str(ui_.ui_section), safe_str(ui_.ui_key),
                             ui_val)
    if clear_session:
        meta.Session.remove()

    # force set push_ssl requirement to False, Kallithea handles that
    baseui.setconfig('web', 'push_ssl', False)
    baseui.setconfig('web', 'allow_push', '*')
    # prevent interactive questions for ssh password / passphrase
    ssh = baseui.config('ui', 'ssh', default='ssh')
    baseui.setconfig('ui', 'ssh', '%s -oBatchMode=yes -oIdentitiesOnly=yes' % ssh)
    # push / pull hooks
    baseui.setconfig('hooks', 'changegroup.kallithea_log_push_action', 'python:kallithea.lib.hooks.log_push_action')
    baseui.setconfig('hooks', 'outgoing.kallithea_log_pull_action', 'python:kallithea.lib.hooks.log_pull_action')

    if repo_path is not None:
        hgrc_path = os.path.join(repo_path, '.hg', 'hgrc')
        if os.path.isfile(hgrc_path):
            log.debug('reading hgrc from %s', hgrc_path)
            cfg = config.config()
            cfg.read(hgrc_path)
            for section in ui_sections:
                for k, v in cfg.items(section):
                    log.debug('config from file: [%s] %s=%s', section, k, v)
                    baseui.setconfig(safe_str(section), safe_str(k), safe_str(v))
        else:
            log.debug('hgrc file is not present at %s, skipping...', hgrc_path)

    return baseui


def set_app_settings(config):
    """
    Updates app config with new settings from database

    :param config:
    """
    try:
        hgsettings = Setting.get_app_settings()
        for k, v in hgsettings.items():
            config[k] = v
    finally:
        meta.Session.remove()


def set_vcs_config(config):
    """
    Patch VCS config with some Kallithea specific stuff

    :param config: kallithea.CONFIG
    """
    from kallithea.lib.vcs import conf
    from kallithea.lib.utils2 import aslist
    conf.settings.BACKENDS = {
        'hg': 'kallithea.lib.vcs.backends.hg.MercurialRepository',
        'git': 'kallithea.lib.vcs.backends.git.GitRepository',
    }

    conf.settings.GIT_EXECUTABLE_PATH = config.get('git_path', 'git')
    conf.settings.GIT_REV_FILTER = config.get('git_rev_filter', '--all').strip()
    conf.settings.DEFAULT_ENCODINGS = aslist(config.get('default_encoding',
                                                        'utf-8'), sep=',')


def set_indexer_config(config):
    """
    Update Whoosh index mapping

    :param config: kallithea.CONFIG
    """
    from kallithea.config import conf

    log.debug('adding extra into INDEX_EXTENSIONS')
    conf.INDEX_EXTENSIONS.extend(re.split(r'\s+', config.get('index.extensions', '')))

    log.debug('adding extra into INDEX_FILENAMES')
    conf.INDEX_FILENAMES.extend(re.split(r'\s+', config.get('index.filenames', '')))


def map_groups(path):
    """
    Given a full path to a repository, create all nested groups that this
    repo is inside. This function creates parent-child relationships between
    groups and creates default perms for all new groups.

    :param paths: full path to repository
    """
    sa = meta.Session()
    groups = path.split(Repository.url_sep())
    parent = None
    group = None

    # last element is repo in nested groups structure
    groups = groups[:-1]
    rgm = RepoGroupModel()
    owner = User.get_first_admin()
    for lvl, group_name in enumerate(groups):
        group_name = u'/'.join(groups[:lvl] + [group_name])
        group = RepoGroup.get_by_group_name(group_name)
        desc = '%s group' % group_name

        # skip folders that are now removed repos
        if REMOVED_REPO_PAT.match(group_name):
            break

        if group is None:
            log.debug('creating group level: %s group_name: %s',
                      lvl, group_name)
            group = RepoGroup(group_name, parent)
            group.group_description = desc
            group.owner = owner
            sa.add(group)
            rgm._create_default_perms(group)
            sa.flush()

        parent = group
    return group


def repo2db_mapper(initial_repo_list, remove_obsolete=False,
                   install_git_hooks=False, user=None, overwrite_git_hooks=False):
    """
    maps all repos given in initial_repo_list, non existing repositories
    are created, if remove_obsolete is True it also check for db entries
    that are not in initial_repo_list and removes them.

    :param initial_repo_list: list of repositories found by scanning methods
    :param remove_obsolete: check for obsolete entries in database
    :param install_git_hooks: if this is True, also check and install git hook
        for a repo if missing
    :param overwrite_git_hooks: if this is True, overwrite any existing git hooks
        that may be encountered (even if user-deployed)
    """
    from kallithea.model.repo import RepoModel
    from kallithea.model.scm import ScmModel
    sa = meta.Session()
    repo_model = RepoModel()
    if user is None:
        user = User.get_first_admin()
    added = []

    # creation defaults
    defs = Setting.get_default_repo_settings(strip_prefix=True)
    enable_statistics = defs.get('repo_enable_statistics')
    enable_downloads = defs.get('repo_enable_downloads')
    private = defs.get('repo_private')

    for name, repo in initial_repo_list.items():
        group = map_groups(name)
        unicode_name = safe_unicode(name)
        db_repo = repo_model.get_by_repo_name(unicode_name)
        # found repo that is on filesystem not in Kallithea database
        if not db_repo:
            log.info('repository %s not found, creating now', name)
            added.append(name)
            desc = (repo.description
                    if repo.description != 'unknown'
                    else '%s repository' % name)

            new_repo = repo_model._create_repo(
                repo_name=name,
                repo_type=repo.alias,
                description=desc,
                repo_group=getattr(group, 'group_id', None),
                owner=user,
                enable_downloads=enable_downloads,
                enable_statistics=enable_statistics,
                private=private,
                state=Repository.STATE_CREATED
            )
            sa.commit()
            # we added that repo just now, and make sure it has githook
            # installed, and updated server info
            if new_repo.repo_type == 'git':
                git_repo = new_repo.scm_instance
                ScmModel().install_git_hooks(git_repo)
                # update repository server-info
                log.debug('Running update server info')
                git_repo._update_server_info()
            new_repo.update_changeset_cache()
        elif install_git_hooks:
            if db_repo.repo_type == 'git':
                ScmModel().install_git_hooks(db_repo.scm_instance, force_create=overwrite_git_hooks)

    removed = []
    # remove from database those repositories that are not in the filesystem
    unicode_initial_repo_list = set(safe_unicode(name) for name in initial_repo_list)
    for repo in sa.query(Repository).all():
        if repo.repo_name not in unicode_initial_repo_list:
            if remove_obsolete:
                log.debug("Removing non-existing repository found in db `%s`",
                          repo.repo_name)
                try:
                    RepoModel().delete(repo, forks='detach', fs_remove=False)
                    sa.commit()
                except Exception:
                    #don't hold further removals on error
                    log.error(traceback.format_exc())
                    sa.rollback()
            removed.append(repo.repo_name)
    return added, removed


def load_rcextensions(root_path):
    import kallithea
    from kallithea.config import conf

    path = os.path.join(root_path, 'rcextensions', '__init__.py')
    if os.path.isfile(path):
        rcext = create_module('rc', path)
        EXT = kallithea.EXTENSIONS = rcext
        log.debug('Found rcextensions now loading %s...', rcext)

        # Additional mappings that are not present in the pygments lexers
        conf.LANGUAGES_EXTENSIONS_MAP.update(getattr(EXT, 'EXTRA_MAPPINGS', {}))

        # OVERRIDE OUR EXTENSIONS FROM RC-EXTENSIONS (if present)

        if getattr(EXT, 'INDEX_EXTENSIONS', []):
            log.debug('settings custom INDEX_EXTENSIONS')
            conf.INDEX_EXTENSIONS = getattr(EXT, 'INDEX_EXTENSIONS', [])

        # ADDITIONAL MAPPINGS
        log.debug('adding extra into INDEX_EXTENSIONS')
        conf.INDEX_EXTENSIONS.extend(getattr(EXT, 'EXTRA_INDEX_EXTENSIONS', []))

        # auto check if the module is not missing any data, set to default if is
        # this will help autoupdate new feature of rcext module
        #from kallithea.config import rcextensions
        #for k in dir(rcextensions):
        #    if not k.startswith('_') and not hasattr(EXT, k):
        #        setattr(EXT, k, getattr(rcextensions, k))


#==============================================================================
# MISC
#==============================================================================

git_req_ver = StrictVersion('1.7.4')

def check_git_version():
    """
    Checks what version of git is installed on the system, and raise a system exit
    if it's too old for Kallithea to work properly.
    """
    from kallithea import BACKENDS
    from kallithea.lib.vcs.backends.git.repository import GitRepository
    from kallithea.lib.vcs.conf import settings

    if 'git' not in BACKENDS:
        return None

    if not settings.GIT_EXECUTABLE_PATH:
        log.warning('No git executable configured - check "git_path" in the ini file.')
        return None

    stdout, stderr = GitRepository._run_git_command(['--version'], _bare=True,
                                                    _safe=True)

    if stderr:
        log.warning('Error/stderr from "%s --version": %r', settings.GIT_EXECUTABLE_PATH, stderr)

    m = re.search(r"\d+.\d+.\d+", stdout)
    if m:
        ver = StrictVersion(m.group(0))
        log.debug('Git executable: "%s", version %s (parsed from: "%s")',
                  settings.GIT_EXECUTABLE_PATH, ver, stdout.strip())
        if ver < git_req_ver:
            log.error('Kallithea detected %s version %s, which is too old '
                      'for the system to function properly. '
                      'Please upgrade to version %s or later. '
                      'If you strictly need Mercurial repositories, you can '
                      'clear the "git_path" setting in the ini file.',
                      settings.GIT_EXECUTABLE_PATH, ver, git_req_ver)
            log.error("Terminating ...")
            sys.exit(1)
    else:
        ver = StrictVersion('0.0.0')
        log.warning('Error finding version number in "%s --version" stdout: %r',
                    settings.GIT_EXECUTABLE_PATH, stdout.strip())

    return ver


#===============================================================================
# CACHE RELATED METHODS
#===============================================================================

# set cache regions for beaker so celery can utilise it
def setup_cache_regions(settings):
    # Create dict with just beaker cache configs with prefix stripped
    cache_settings = {'regions': None}
    prefix = 'beaker.cache.'
    for key in settings:
        if key.startswith(prefix):
            name = key[len(prefix):]
            cache_settings[name] = settings[key]
    # Find all regions, apply defaults, and apply to beaker
    if cache_settings['regions']:
        for region in cache_settings['regions'].split(','):
            region = region.strip()
            prefix = region + '.'
            region_settings = {}
            for key in cache_settings:
                if key.startswith(prefix):
                    name = key[len(prefix):]
                    region_settings[name] = cache_settings[key]
            region_settings.setdefault('expire',
                                       cache_settings.get('expire', '60'))
            region_settings.setdefault('lock_dir',
                                       cache_settings.get('lock_dir'))
            region_settings.setdefault('data_dir',
                                       cache_settings.get('data_dir'))
            region_settings.setdefault('type',
                                       cache_settings.get('type', 'memory'))
            beaker.cache.cache_regions[region] = region_settings


def conditional_cache(region, prefix, condition, func):
    """

    Conditional caching function use like::
        def _c(arg):
            #heavy computation function
            return data

        # depending from condition the compute is wrapped in cache or not
        compute = conditional_cache('short_term', 'cache_desc', condition=True, func=func)
        return compute(arg)

    :param region: name of cache region
    :param prefix: cache region prefix
    :param condition: condition for cache to be triggered, and return data cached
    :param func: wrapped heavy function to compute

    """
    wrapped = func
    if condition:
        log.debug('conditional_cache: True, wrapping call of '
                  'func: %s into %s region cache' % (region, func))
        wrapped = _cache_decorate((prefix,), None, None, region)(func)

    return wrapped
