# -*- coding: utf-8 -*-
"""
    rhodecode.lib.utils
    ~~~~~~~~~~~~~~~~~~~

    Utilities library for RhodeCode

    :created_on: Apr 18, 2010
    :author: marcink
    :copyright: (C) 2009-2011 Marcin Kuzminski <marcin@python-works.com>
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
import logging
import datetime
import traceback
import paste
import beaker

from paste.script.command import Command, BadCommand

from UserDict import DictMixin

from mercurial import ui, config, hg
from mercurial.error import RepoError

from webhelpers.text import collapse, remove_formatting, strip_tags

from vcs.backends.base import BaseChangeset
from vcs.utils.lazy import LazyProperty

from rhodecode.model import meta
from rhodecode.model.caching_query import FromCache
from rhodecode.model.db import Repository, User, RhodeCodeUi, UserLog
from rhodecode.model.repo import RepoModel
from rhodecode.model.user import UserModel

log = logging.getLogger(__name__)


def recursive_replace(str, replace=' '):
    """Recursive replace of given sign to just one instance

    :param str: given string
    :param replace: char to find and replace multiple instances

    Examples::
    >>> recursive_replace("Mighty---Mighty-Bo--sstones",'-')
    'Mighty-Mighty-Bo-sstones'
    """

    if str.find(replace * 2) == -1:
        return str
    else:
        str = str.replace(replace * 2, replace)
        return recursive_replace(str, replace)


def repo_name_slug(value):
    """Return slug of name of repository
    This function is called on each creation/modification
    of repository to prevent bad names in repo
    """

    slug = remove_formatting(value)
    slug = strip_tags(slug)

    for c in """=[]\;'"<>,/~!@#$%^&*()+{}|: """:
        slug = slug.replace(c, '-')
    slug = recursive_replace(slug, '-')
    slug = collapse(slug, '-')
    return slug


def get_repo_slug(request):
    return request.environ['pylons.routes_dict'].get('repo_name')


def action_logger(user, action, repo, ipaddr='', sa=None):
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

    try:
        um = UserModel()
        if hasattr(user, 'user_id'):
            user_obj = user
        elif isinstance(user, basestring):
            user_obj = um.get_by_username(user, cache=False)
        else:
            raise Exception('You have to provide user object or username')

        rm = RepoModel()
        if hasattr(repo, 'repo_id'):
            repo_obj = rm.get(repo.repo_id, cache=False)
            repo_name = repo_obj.repo_name
        elif  isinstance(repo, basestring):
            repo_name = repo.lstrip('/')
            repo_obj = rm.get_by_repo_name(repo_name, cache=False)
        else:
            raise Exception('You have to provide repository to action logger')

        user_log = UserLog()
        user_log.user_id = user_obj.user_id
        user_log.action = action

        user_log.repository_id = repo_obj.repo_id
        user_log.repository_name = repo_name

        user_log.action_date = datetime.datetime.now()
        user_log.user_ip = ipaddr
        sa.add(user_log)
        sa.commit()

        log.info('Adding user %s, action %s on %s', user_obj, action, repo)
    except:
        log.error(traceback.format_exc())
        sa.rollback()


def get_repos(path, recursive=False, initial=False):
    """
    Scans given path for repos and return (name,(type,path)) tuple 
    
    :param prefix:
    :param path:
    :param recursive:
    :param initial:
    """
    from vcs.utils.helpers import get_scm
    from vcs.exceptions import VCSError

    try:
        scm = get_scm(path)
    except:
        pass
    else:
        raise Exception('The given path %s should not be a repository got %s',
                        path, scm)

    for dirpath in os.listdir(path):
        try:
            yield dirpath, get_scm(os.path.join(path, dirpath))
        except VCSError:
            pass

def check_repo_fast(repo_name, base_path):
    """
    Check given path for existence of directory
    :param repo_name:
    :param base_path:

    :return False: if this directory is present
    """
    if os.path.isdir(os.path.join(base_path, repo_name)):
        return False
    return True


def check_repo(repo_name, base_path, verify=True):

    repo_path = os.path.join(base_path, repo_name)

    try:
        if not check_repo_fast(repo_name, base_path):
            return False
        r = hg.repository(ui.ui(), repo_path)
        if verify:
            hg.verify(r)
        #here we hnow that repo exists it was verified
        log.info('%s repo is already created', repo_name)
        return False
    except RepoError:
        #it means that there is no valid repo there...
        log.info('%s repo is free for creation', repo_name)
        return True


def ask_ok(prompt, retries=4, complaint='Yes or no, please!'):
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


def make_ui(read_from='file', path=None, checkpaths=True):
    """A function that will read python rc files or database
    and make an mercurial ui object from read options

    :param path: path to mercurial config file
    :param checkpaths: check the path
    :param read_from: read from 'file' or 'db'
    """

    baseui = ui.ui()

    #clean the baseui object
    baseui._ocfg = config.config()
    baseui._ucfg = config.config()
    baseui._tcfg = config.config()

    if read_from == 'file':
        if not os.path.isfile(path):
            log.warning('Unable to read config file %s' % path)
            return False
        log.debug('reading hgrc from %s', path)
        cfg = config.config()
        cfg.read(path)
        for section in ui_sections:
            for k, v in cfg.items(section):
                log.debug('settings ui from file[%s]%s:%s', section, k, v)
                baseui.setconfig(section, k, v)

    elif read_from == 'db':
        sa = meta.Session()
        ret = sa.query(RhodeCodeUi)\
            .options(FromCache("sql_cache_short",
                               "get_hg_ui_settings")).all()

        hg_ui = ret
        for ui_ in hg_ui:
            if ui_.ui_active:
                log.debug('settings ui from db[%s]%s:%s', ui_.ui_section,
                          ui_.ui_key, ui_.ui_value)
                baseui.setconfig(ui_.ui_section, ui_.ui_key, ui_.ui_value)

        meta.Session.remove()
    return baseui


def set_rhodecode_config(config):
    """Updates pylons config with new settings from database

    :param config:
    """
    from rhodecode.model.settings import SettingsModel
    hgsettings = SettingsModel().get_app_settings()

    for k, v in hgsettings.items():
        config[k] = v


def invalidate_cache(cache_key, *args):
    """Puts cache invalidation task into db for
    further global cache invalidation
    """

    from rhodecode.model.scm import ScmModel

    if cache_key.startswith('get_repo_cached_'):
        name = cache_key.split('get_repo_cached_')[-1]
        ScmModel().mark_for_invalidation(name)


class EmptyChangeset(BaseChangeset):
    """
    An dummy empty changeset. It's possible to pass hash when creating
    an EmptyChangeset
    """

    def __init__(self, cs='0' * 40, repo=None):
        self._empty_cs = cs
        self.revision = -1
        self.message = ''
        self.author = ''
        self.date = ''
        self.repository = repo

    @LazyProperty
    def raw_id(self):
        """Returns raw string identifying this changeset, useful for web
        representation.
        """

        return self._empty_cs

    @LazyProperty
    def short_id(self):
        return self.raw_id[:12]

    def get_file_changeset(self, path):
        return self

    def get_file_content(self, path):
        return u''

    def get_file_size(self, path):
        return 0

def repo2db_mapper(initial_repo_list, remove_obsolete=False):
    """maps all found repositories into db
    """

    sa = meta.Session()
    rm = RepoModel()
    user = sa.query(User).filter(User.admin == True).first()

    for name, repo in initial_repo_list.items():
        if not rm.get_by_repo_name(name, cache=False):
            log.info('repository %s not found creating default', name)

            form_data = {
                         'repo_name':name,
                         'repo_type':repo.alias,
                         'description':repo.description \
                            if repo.description != 'unknown' else \
                                        '%s repository' % name,
                         'private':False
                         }
            rm.create(form_data, user, just_db=True)

    if remove_obsolete:
        #remove from database those repositories that are not in the filesystem
        for repo in sa.query(Repository).all():
            if repo.repo_name not in initial_repo_list.keys():
                sa.delete(repo)
                sa.commit()


class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self) == len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other


#set cache regions for beaker so celery can utilise it
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


def get_current_revision():
    """Returns tuple of (number, id) from repository containing this package
    or None if repository could not be found.
    """

    try:
        from vcs import get_repo
        from vcs.utils.helpers import get_scm
        from vcs.exceptions import RepositoryError, VCSError
        repopath = os.path.join(os.path.dirname(__file__), '..', '..')
        scm = get_scm(repopath)[0]
        repo = get_repo(path=repopath, alias=scm)
        tip = repo.get_changeset()
        return (tip.revision, tip.short_id)
    except (ImportError, RepositoryError, VCSError), err:
        logging.debug("Cannot retrieve rhodecode's revision. Original error "
                      "was: %s" % err)
        return None


#==============================================================================
# TEST FUNCTIONS AND CREATORS
#==============================================================================
def create_test_index(repo_location, full_index):
    """Makes default test index
    :param repo_location:
    :param full_index:
    """
    from rhodecode.lib.indexers.daemon import WhooshIndexingDaemon
    from rhodecode.lib.pidlock import DaemonLock, LockHeld
    import shutil

    index_location = os.path.join(repo_location, 'index')
    if os.path.exists(index_location):
        shutil.rmtree(index_location)

    try:
        l = DaemonLock()
        WhooshIndexingDaemon(index_location=index_location,
                             repo_location=repo_location)\
            .run(full_index=full_index)
        l.release()
    except LockHeld:
        pass


def create_test_env(repos_test_path, config):
    """Makes a fresh database and
    install test repository into tmp dir
    """
    from rhodecode.lib.db_manage import DbManage
    from rhodecode.tests import HG_REPO, GIT_REPO, NEW_HG_REPO, NEW_GIT_REPO, \
        HG_FORK, GIT_FORK, TESTS_TMP_PATH
    import tarfile
    import shutil
    from os.path import dirname as dn, join as jn, abspath

    log = logging.getLogger('TestEnvCreator')
    # create logger
    log.setLevel(logging.DEBUG)
    log.propagate = True
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s -"
                                  " %(levelname)s - %(message)s")

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    log.addHandler(ch)

    #PART ONE create db
    dbconf = config['sqlalchemy.db1.url']
    log.debug('making test db %s', dbconf)

    dbmanage = DbManage(log_sql=True, dbconf=dbconf, root=config['here'],
                        tests=True)
    dbmanage.create_tables(override=True)
    dbmanage.create_settings(dbmanage.config_prompt(repos_test_path))
    dbmanage.create_default_user()
    dbmanage.admin_prompt()
    dbmanage.create_permissions()
    dbmanage.populate_default_permissions()

    #PART TWO make test repo
    log.debug('making test vcs repositories')

    #remove old one from previos tests
    for r in [HG_REPO, GIT_REPO, NEW_HG_REPO, NEW_GIT_REPO, HG_FORK, GIT_FORK]:

        if os.path.isdir(jn(TESTS_TMP_PATH, r)):
            log.debug('removing %s', r)
            shutil.rmtree(jn(TESTS_TMP_PATH, r))

    #CREATE DEFAULT HG REPOSITORY
    cur_dir = dn(dn(abspath(__file__)))
    tar = tarfile.open(jn(cur_dir, 'tests', "vcs_test_hg.tar.gz"))
    tar.extractall(jn(TESTS_TMP_PATH, HG_REPO))
    tar.close()


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

        path_to_ini_file = os.path.realpath(conf)
        conf = paste.deploy.appconfig('config:' + path_to_ini_file)
        pylonsconfig.init_app(conf.global_conf, conf.local_conf)
