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

import os
import re
import logging
import datetime
import traceback
import paste
import beaker
import tarfile
import shutil
import decorator
import warnings
from os.path import abspath
from os.path import dirname as dn, join as jn

from paste.script.command import Command, BadCommand

from webhelpers.text import collapse, remove_formatting, strip_tags
from beaker.cache import _cache_decorate

from kallithea import BRAND

from kallithea.lib.vcs.utils.hgcompat import ui, config
from kallithea.lib.vcs.utils.helpers import get_scm
from kallithea.lib.vcs.exceptions import VCSError

from kallithea.lib.caching_query import FromCache

from kallithea.model import meta
from kallithea.model.db import Repository, User, Ui, \
    UserLog, RepoGroup, Setting, CacheInvalidation, UserGroup
from kallithea.model.meta import Session
from kallithea.model.repo_group import RepoGroupModel
from kallithea.lib.utils2 import safe_str, safe_unicode, get_current_authuser
from kallithea.lib.vcs.utils.fakemod import create_module

log = logging.getLogger(__name__)

REMOVED_REPO_PAT = re.compile(r'rm__\d{8}_\d{6}_\d{6}_.*')


def recursive_replace(str_, replace=' '):
    """
    Recursive replace of given sign to just one instance

    :param str_: given string
    :param replace: char to find and replace multiple instances

    Examples::
    >>> recursive_replace("Mighty---Mighty-Bo--sstones",'-')
    'Mighty-Mighty-Bo-sstones'
    """

    if str_.find(replace * 2) == -1:
        return str_
    else:
        str_ = str_.replace(replace * 2, replace)
        return recursive_replace(str_, replace)


def repo_name_slug(value):
    """
    Return slug of name of repository
    This function is called on each creation/modification
    of repository to prevent bad names in repo
    """

    slug = remove_formatting(value)
    slug = strip_tags(slug)

    for c in """`?=[]\;'"<>,/~!@#$%^&*()+{}|: """:
        slug = slug.replace(c, '-')
    slug = recursive_replace(slug, '-')
    slug = collapse(slug, '-')
    return slug


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


def _extract_id_from_repo_name(repo_name):
    if repo_name.startswith('/'):
        repo_name = repo_name.lstrip('/')
    by_id_match = re.match(r'^_(\d{1,})', repo_name)
    if by_id_match:
        return by_id_match.groups()[0]


def get_repo_by_id(repo_name):
    """
    Extracts repo_name by id from special urls. Example url is _11/repo_name

    :param repo_name:
    :return: repo_name if matched else None
    """
    _repo_id = _extract_id_from_repo_name(repo_name)
    if _repo_id:
        from kallithea.model.db import Repository
        repo = Repository.get(_repo_id)
        if repo:
            # TODO: return repo instead of reponame? or would that be a layering violation?
            return repo.repo_name
    return None


def action_logger(user, action, repo, ipaddr='', sa=None, commit=False):
    """
    Action logger for various actions made by users

    :param user: user that made this action, can be a unique username string or
        object containing user_id attribute
    :param action: action to log, should be on of predefined unique actions for
        easy translations
    :param repo: string name of repository or object containing repo_id,
        that action was made on
    :param ipaddr: optional ip address from what the action was made
    :param sa: optional sqlalchemy session

    """

    if not sa:
        sa = meta.Session()
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
        repo_name = ''

    user_log = UserLog()
    user_log.user_id = user_obj.user_id
    user_log.username = user_obj.username
    user_log.action = safe_unicode(action)

    user_log.repository = repo_obj
    user_log.repository_name = repo_name

    user_log.action_date = datetime.datetime.now()
    user_log.user_ip = ipaddr
    sa.add(user_log)

    log.info('Logging action:%s on %s by user:%s ip:%s' %
             (action, safe_unicode(repo), user_obj, ipaddr))
    if commit:
        sa.commit()


def get_filesystem_repos(path, recursive=False, skip_removed_repos=True):
    """
    Scans given path for repos and return (name,(type,path)) tuple

    :param path: path to scan for repositories
    :param recursive: recursive search and return names with subdirs in front
    """

    # remove ending slash for better results
    path = path.rstrip(os.sep)
    log.debug('now scanning in %s location recursive:%s...' % (path, recursive))

    def _get_repos(p):
        if not os.access(p, os.R_OK) or not os.access(p, os.X_OK):
            log.warning('ignoring repo path without access: %s' % (p,))
            return
        if not os.access(p, os.W_OK):
            log.warning('repo path without write access: %s' % (p,))
        for dirpath in os.listdir(p):
            if os.path.isfile(os.path.join(p, dirpath)):
                continue
            cur_path = os.path.join(p, dirpath)

            # skip removed repos
            if skip_removed_repos and REMOVED_REPO_PAT.match(dirpath):
                continue

            #skip .<somethin> dirs
            if dirpath.startswith('.'):
                continue

            try:
                scm_info = get_scm(cur_path)
                yield scm_info[1].split(path, 1)[-1].lstrip(os.sep), scm_info
            except VCSError:
                if not recursive:
                    continue
                #check if this dir containts other repos for recursive scan
                rec_path = os.path.join(p, dirpath)
                if os.path.isdir(rec_path):
                    for inner_scm in _get_repos(rec_path):
                        yield inner_scm

    return _get_repos(path)


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


def ask_ok(prompt, retries=4, complaint='Yes or no please!'):
    while True:
        ok = raw_input(prompt)
        if ok in ('y', 'ye', 'yes'):
            return True
        if ok in ('n', 'no', 'nop', 'nope'):
            return False
        retries = retries - 1
        if retries < 0:
            raise IOError
        print complaint

#propagated from mercurial documentation
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


def make_ui(read_from='file', path=None, checkpaths=True, clear_session=True):
    """
    A function that will read python rc files or database
    and make an mercurial ui object from read options

    :param path: path to mercurial config file
    :param checkpaths: check the path
    :param read_from: read from 'file' or 'db'
    """

    baseui = ui.ui()

    # clean the baseui object
    baseui._ocfg = config.config()
    baseui._ucfg = config.config()
    baseui._tcfg = config.config()

    if read_from == 'file':
        if not os.path.isfile(path):
            log.debug('hgrc file is not present at %s, skipping...' % path)
            return False
        log.debug('reading hgrc from %s' % path)
        cfg = config.config()
        cfg.read(path)
        for section in ui_sections:
            for k, v in cfg.items(section):
                log.debug('settings ui from file: [%s] %s=%s' % (section, k, v))
                baseui.setconfig(safe_str(section), safe_str(k), safe_str(v))

    elif read_from == 'db':
        sa = meta.Session()
        ret = sa.query(Ui).all()

        hg_ui = ret
        for ui_ in hg_ui:
            if ui_.ui_active:
                ui_val = safe_str(ui_.ui_value)
                if ui_.ui_section == 'hooks' and BRAND != 'kallithea' and ui_val.startswith('python:' + BRAND + '.lib.hooks.'):
                    ui_val = ui_val.replace('python:' + BRAND + '.lib.hooks.', 'python:kallithea.lib.hooks.')
                log.debug('settings ui from db: [%s] %s=%s', ui_.ui_section,
                          ui_.ui_key, ui_val)
                baseui.setconfig(safe_str(ui_.ui_section), safe_str(ui_.ui_key),
                                 ui_val)
            if ui_.ui_key == 'push_ssl':
                # force set push_ssl requirement to False, kallithea
                # handles that
                baseui.setconfig(safe_str(ui_.ui_section), safe_str(ui_.ui_key),
                                 False)
        if clear_session:
            meta.Session.remove()

        # prevent interactive questions for ssh password / passphrase
        ssh = baseui.config('ui', 'ssh', default='ssh')
        baseui.setconfig('ui', 'ssh', '%s -oBatchMode=yes -oIdentitiesOnly=yes' % ssh)

    return baseui


def set_app_settings(config):
    """
    Updates pylons config with new settings from database

    :param config:
    """
    hgsettings = Setting.get_app_settings()

    for k, v in hgsettings.items():
        config[k] = v


def set_vcs_config(config):
    """
    Patch VCS config with some Kallithea specific stuff

    :param config: kallithea.CONFIG
    """
    import kallithea
    from kallithea.lib.vcs import conf
    from kallithea.lib.utils2 import aslist
    conf.settings.BACKENDS = {
        'hg': 'kallithea.lib.vcs.backends.hg.MercurialRepository',
        'git': 'kallithea.lib.vcs.backends.git.GitRepository',
    }

    conf.settings.GIT_EXECUTABLE_PATH = config.get('git_path', 'git')
    conf.settings.GIT_REV_FILTER = config.get('git_rev_filter', '--all').strip()
    conf.settings.DEFAULT_ENCODINGS = aslist(config.get('default_encoding',
                                                        'utf8'), sep=',')


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
    rgm = RepoGroupModel(sa)
    owner = User.get_first_admin()
    for lvl, group_name in enumerate(groups):
        group_name = '/'.join(groups[:lvl] + [group_name])
        group = RepoGroup.get_by_group_name(group_name)
        desc = '%s group' % group_name

        # skip folders that are now removed repos
        if REMOVED_REPO_PAT.match(group_name):
            break

        if group is None:
            log.debug('creating group level: %s group_name: %s'
                      % (lvl, group_name))
            group = RepoGroup(group_name, parent)
            group.group_description = desc
            group.user = owner
            sa.add(group)
            perm_obj = rgm._create_default_perms(group)
            sa.add(perm_obj)
            sa.flush()

        parent = group
    return group


def repo2db_mapper(initial_repo_list, remove_obsolete=False,
                   install_git_hook=False, user=None):
    """
    maps all repos given in initial_repo_list, non existing repositories
    are created, if remove_obsolete is True it also check for db entries
    that are not in initial_repo_list and removes them.

    :param initial_repo_list: list of repositories found by scanning methods
    :param remove_obsolete: check for obsolete entries in database
    :param install_git_hook: if this is True, also check and install githook
        for a repo if missing
    """
    from kallithea.model.repo import RepoModel
    from kallithea.model.scm import ScmModel
    sa = meta.Session()
    repo_model = RepoModel()
    if user is None:
        user = User.get_first_admin()
    added = []

    ##creation defaults
    defs = Setting.get_default_repo_settings(strip_prefix=True)
    enable_statistics = defs.get('repo_enable_statistics')
    enable_locking = defs.get('repo_enable_locking')
    enable_downloads = defs.get('repo_enable_downloads')
    private = defs.get('repo_private')

    for name, repo in initial_repo_list.items():
        group = map_groups(name)
        unicode_name = safe_unicode(name)
        db_repo = repo_model.get_by_repo_name(unicode_name)
        # found repo that is on filesystem not in Kallithea database
        if not db_repo:
            log.info('repository %s not found, creating now' % name)
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
                enable_locking=enable_locking,
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
                ScmModel().install_git_hook(git_repo)
                # update repository server-info
                log.debug('Running update server info')
                git_repo._update_server_info()
            new_repo.update_changeset_cache()
        elif install_git_hook:
            if db_repo.repo_type == 'git':
                ScmModel().install_git_hook(db_repo.scm_instance)

    removed = []
    # remove from database those repositories that are not in the filesystem
    for repo in sa.query(Repository).all():
        if repo.repo_name not in initial_repo_list.keys():
            if remove_obsolete:
                log.debug("Removing non-existing repository found in db `%s`" %
                          repo.repo_name)
                try:
                    RepoModel(sa).delete(repo, forks='detach', fs_remove=False)
                    sa.commit()
                except Exception:
                    #don't hold further removals on error
                    log.error(traceback.format_exc())
                    sa.rollback()
            removed.append(repo.repo_name)
    return added, removed


# set cache regions for beaker so celery can utilise it
def add_cache(settings):
    cache_settings = {'regions': None}
    for key in settings.keys():
        for prefix in ['beaker.cache.', 'cache.']:
            if key.startswith(prefix):
                name = key.split(prefix)[1].strip()
                cache_settings[name] = settings[key].strip()
    if cache_settings['regions']:
        for region in cache_settings['regions'].split(','):
            region = region.strip()
            region_settings = {}
            for key, value in cache_settings.items():
                if key.startswith(region):
                    region_settings[key.split('.')[1]] = value
            region_settings['expire'] = int(region_settings.get('expire',
                                                                60))
            region_settings.setdefault('lock_dir',
                                       cache_settings.get('lock_dir'))
            region_settings.setdefault('data_dir',
                                       cache_settings.get('data_dir'))

            if 'type' not in region_settings:
                region_settings['type'] = cache_settings.get('type',
                                                             'memory')
            beaker.cache.cache_regions[region] = region_settings


def load_rcextensions(root_path):
    import kallithea
    from kallithea.config import conf

    path = os.path.join(root_path, 'rcextensions', '__init__.py')
    if os.path.isfile(path):
        rcext = create_module('rc', path)
        EXT = kallithea.EXTENSIONS = rcext
        log.debug('Found rcextensions now loading %s...' % rcext)

        # Additional mappings that are not present in the pygments lexers
        conf.LANGUAGES_EXTENSIONS_MAP.update(getattr(EXT, 'EXTRA_MAPPINGS', {}))

        #OVERRIDE OUR EXTENSIONS FROM RC-EXTENSIONS (if present)

        if getattr(EXT, 'INDEX_EXTENSIONS', []):
            log.debug('settings custom INDEX_EXTENSIONS')
            conf.INDEX_EXTENSIONS = getattr(EXT, 'INDEX_EXTENSIONS', [])

        #ADDITIONAL MAPPINGS
        log.debug('adding extra into INDEX_EXTENSIONS')
        conf.INDEX_EXTENSIONS.extend(getattr(EXT, 'EXTRA_INDEX_EXTENSIONS', []))

        # auto check if the module is not missing any data, set to default if is
        # this will help autoupdate new feature of rcext module
        #from kallithea.config import rcextensions
        #for k in dir(rcextensions):
        #    if not k.startswith('_') and not hasattr(EXT, k):
        #        setattr(EXT, k, getattr(rcextensions, k))


def get_custom_lexer(extension):
    """
    returns a custom lexer if it's defined in rcextensions module, or None
    if there's no custom lexer defined
    """
    import kallithea
    from pygments import lexers
    #check if we didn't define this extension as other lexer
    if kallithea.EXTENSIONS and extension in kallithea.EXTENSIONS.EXTRA_LEXERS:
        _lexer_name = kallithea.EXTENSIONS.EXTRA_LEXERS[extension]
        return lexers.get_lexer_by_name(_lexer_name)


#==============================================================================
# TEST FUNCTIONS AND CREATORS
#==============================================================================
def create_test_index(repo_location, config, full_index):
    """
    Makes default test index

    :param config: test config
    :param full_index:
    """

    from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
    from kallithea.lib.pidlock import DaemonLock, LockHeld

    repo_location = repo_location

    index_location = os.path.join(config['app_conf']['index_dir'])
    if not os.path.exists(index_location):
        os.makedirs(index_location)

    try:
        l = DaemonLock(file_=jn(dn(index_location), 'make_index.lock'))
        WhooshIndexingDaemon(index_location=index_location,
                             repo_location=repo_location)\
            .run(full_index=full_index)
        l.release()
    except LockHeld:
        pass


def create_test_env(repos_test_path, config):
    """
    Makes a fresh database and
    install test repository into tmp dir
    """
    from kallithea.lib.db_manage import DbManage
    from kallithea.tests import HG_REPO, GIT_REPO, TESTS_TMP_PATH

    # PART ONE create db
    dbconf = config['sqlalchemy.db1.url']
    log.debug('making test db %s' % dbconf)

    # create test dir if it doesn't exist
    if not os.path.isdir(repos_test_path):
        log.debug('Creating testdir %s' % repos_test_path)
        os.makedirs(repos_test_path)

    dbmanage = DbManage(log_sql=True, dbconf=dbconf, root=config['here'],
                        tests=True)
    dbmanage.create_tables(override=True)
    # for tests dynamically set new root paths based on generated content
    dbmanage.create_settings(dbmanage.config_prompt(repos_test_path))
    dbmanage.create_default_user()
    dbmanage.admin_prompt()
    dbmanage.create_permissions()
    dbmanage.populate_default_permissions()
    Session().commit()
    # PART TWO make test repo
    log.debug('making test vcs repositories')

    idx_path = config['app_conf']['index_dir']
    data_path = config['app_conf']['cache_dir']

    #clean index and data
    if idx_path and os.path.exists(idx_path):
        log.debug('remove %s' % idx_path)
        shutil.rmtree(idx_path)

    if data_path and os.path.exists(data_path):
        log.debug('remove %s' % data_path)
        shutil.rmtree(data_path)

    #CREATE DEFAULT TEST REPOS
    cur_dir = dn(dn(abspath(__file__)))
    tar = tarfile.open(jn(cur_dir, 'tests', 'fixtures', "vcs_test_hg.tar.gz"))
    tar.extractall(jn(TESTS_TMP_PATH, HG_REPO))
    tar.close()

    cur_dir = dn(dn(abspath(__file__)))
    tar = tarfile.open(jn(cur_dir, 'tests', 'fixtures', "vcs_test_git.tar.gz"))
    tar.extractall(jn(TESTS_TMP_PATH, GIT_REPO))
    tar.close()

    #LOAD VCS test stuff
    from kallithea.tests.vcs import setup_package
    setup_package()


#==============================================================================
# PASTER COMMANDS
#==============================================================================
class BasePasterCommand(Command):
    """
    Abstract Base Class for paster commands.

    The celery commands are somewhat aggressive about loading
    celery.conf, and since our module sets the `CELERY_LOADER`
    environment variable to our loader, we have to bootstrap a bit and
    make sure we've had a chance to load the pylons config off of the
    command line, otherwise everything fails.
    """
    min_args = 1
    min_args_error = "Please provide a paster config file as an argument."
    takes_config_file = 1
    requires_config_file = True

    def notify_msg(self, msg, log=False):
        """Make a notification to user, additionally if logger is passed
        it logs this action using given logger

        :param msg: message that will be printed to user
        :param log: logging instance, to use to additionally log this message

        """
        if log and isinstance(log, logging):
            log(msg)

    def run(self, args):
        """
        Overrides Command.run

        Checks for a config file argument and loads it.
        """
        if len(args) < self.min_args:
            raise BadCommand(
                self.min_args_error % {'min_args': self.min_args,
                                       'actual_args': len(args)})

        # Decrement because we're going to lob off the first argument.
        # @@ This is hacky
        self.min_args -= 1
        self.bootstrap_config(args[0])
        self.update_parser()
        return super(BasePasterCommand, self).run(args[1:])

    def update_parser(self):
        """
        Abstract method.  Allows for the class's parser to be updated
        before the superclass's `run` method is called.  Necessary to
        allow options/arguments to be passed through to the underlying
        celery command.
        """
        raise NotImplementedError("Abstract Method.")

    def bootstrap_config(self, conf):
        """
        Loads the pylons configuration.
        """
        from pylons import config as pylonsconfig

        self.path_to_ini_file = os.path.realpath(conf)
        conf = paste.deploy.appconfig('config:' + self.path_to_ini_file)
        pylonsconfig.init_app(conf.global_conf, conf.local_conf)

    def _init_session(self):
        """
        Inits SqlAlchemy Session
        """
        logging.config.fileConfig(self.path_to_ini_file)
        from pylons import config
        from kallithea.model import init_model
        from kallithea.lib.utils2 import engine_from_config

        #get to remove repos !!
        add_cache(config)
        engine = engine_from_config(config, 'sqlalchemy.db1.')
        init_model(engine)


def check_git_version():
    """
    Checks what version of git is installed in system, and issues a warning
    if it's too old for Kallithea to work properly.
    """
    from kallithea import BACKENDS
    from kallithea.lib.vcs.backends.git.repository import GitRepository
    from kallithea.lib.vcs.conf import settings
    from distutils.version import StrictVersion

    if 'git' not in BACKENDS:
        return None

    stdout, stderr = GitRepository._run_git_command('--version', _bare=True,
                                                    _safe=True)

    m = re.search("\d+.\d+.\d+", stdout)
    if m:
        ver = StrictVersion(m.group(0))
    else:
        ver = StrictVersion('0.0.0')

    req_ver = StrictVersion('1.7.4')

    log.debug('Git executable: "%s" version %s detected: %s'
              % (settings.GIT_EXECUTABLE_PATH, ver, stdout))
    if stderr:
        log.warning('Error detecting git version: %r' % stderr)
    elif ver < req_ver:
        log.warning('Kallithea detected git version %s, which is too old '
                    'for the system to function properly. '
                    'Please upgrade to version %s or later.' % (ver, req_ver))
    return ver


@decorator.decorator
def jsonify(func, *args, **kwargs):
    """Action decorator that formats output for JSON

    Given a function that will return content, this decorator will turn
    the result into JSON, with a content-type of 'application/json' and
    output it.

    """
    from pylons.decorators.util import get_pylons
    from kallithea.lib.compat import json
    pylons = get_pylons(args)
    pylons.response.headers['Content-Type'] = 'application/json; charset=utf-8'
    data = func(*args, **kwargs)
    if isinstance(data, (list, tuple)):
        msg = "JSON responses with Array envelopes are susceptible to " \
              "cross-site data leak attacks, see " \
              "http://wiki.pylonshq.com/display/pylonsfaq/Warnings"
        warnings.warn(msg, Warning, 2)
        log.warning(msg)
    log.debug("Returning JSON wrapped action output")
    return json.dumps(data, encoding='utf-8')


def conditional_cache(region, prefix, condition, func):
    """

    Conditional caching function use like::
        def _c(arg):
            #heavy computation function
            return data

        # denpending from condition the compute is wrapped in cache or not
        compute = conditional_cache('short_term', 'cache_desc', codnition=True, func=func)
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
