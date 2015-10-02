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
kallithea.lib.auth
~~~~~~~~~~~~~~~~~~

authentication and permission libraries

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
import time
import os
import logging
import traceback
import hashlib
import itertools
import collections

from decorator import decorator

from pylons import url, request, session
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _
from webhelpers.pylonslib import secure_form
from sqlalchemy import or_
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import joinedload

from kallithea import __platform__, is_windows, is_unix
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.model import meta
from kallithea.model.meta import Session
from kallithea.model.user import UserModel
from kallithea.model.db import User, Repository, Permission, \
    UserToPerm, UserGroupRepoToPerm, UserGroupToPerm, UserGroupMember, \
    RepoGroup, UserGroupRepoGroupToPerm, UserIpMap, UserGroupUserGroupToPerm, \
    UserGroup, UserApiKeys

from kallithea.lib.utils2 import safe_unicode, aslist
from kallithea.lib.utils import get_repo_slug, get_repo_group_slug, \
    get_user_group_slug, conditional_cache
from kallithea.lib.caching_query import FromCache


log = logging.getLogger(__name__)


class PasswordGenerator(object):
    """
    This is a simple class for generating password from different sets of
    characters
    usage::

        passwd_gen = PasswordGenerator()
        #print 8-letter password containing only big and small letters
            of alphabet
        passwd_gen.gen_password(8, passwd_gen.ALPHABETS_BIG_SMALL)
    """
    ALPHABETS_NUM = r'''1234567890'''
    ALPHABETS_SMALL = r'''qwertyuiopasdfghjklzxcvbnm'''
    ALPHABETS_BIG = r'''QWERTYUIOPASDFGHJKLZXCVBNM'''
    ALPHABETS_SPECIAL = r'''`-=[]\;',./~!@#$%^&*()_+{}|:"<>?'''
    ALPHABETS_FULL = ALPHABETS_BIG + ALPHABETS_SMALL \
        + ALPHABETS_NUM + ALPHABETS_SPECIAL
    ALPHABETS_ALPHANUM = ALPHABETS_BIG + ALPHABETS_SMALL + ALPHABETS_NUM
    ALPHABETS_BIG_SMALL = ALPHABETS_BIG + ALPHABETS_SMALL
    ALPHABETS_ALPHANUM_BIG = ALPHABETS_BIG + ALPHABETS_NUM
    ALPHABETS_ALPHANUM_SMALL = ALPHABETS_SMALL + ALPHABETS_NUM

    def gen_password(self, length, alphabet=ALPHABETS_FULL):
        assert len(alphabet) <= 256, alphabet
        l = []
        while len(l) < length:
            i = ord(os.urandom(1))
            if i < len(alphabet):
                l.append(alphabet[i])
        return ''.join(l)


class KallitheaCrypto(object):

    @classmethod
    def hash_string(cls, str_):
        """
        Cryptographic function used for password hashing based on pybcrypt
        or Python's own OpenSSL wrapper on windows

        :param password: password to hash
        """
        if is_windows:
            return hashlib.sha256(str_).hexdigest()
        elif is_unix:
            import bcrypt
            return bcrypt.hashpw(str_, bcrypt.gensalt(10))
        else:
            raise Exception('Unknown or unsupported platform %s' \
                            % __platform__)

    @classmethod
    def hash_check(cls, password, hashed):
        """
        Checks matching password with it's hashed value, runs different
        implementation based on platform it runs on

        :param password: password
        :param hashed: password in hashed form
        """

        if is_windows:
            return hashlib.sha256(password).hexdigest() == hashed
        elif is_unix:
            import bcrypt
            return bcrypt.hashpw(password, hashed) == hashed
        else:
            raise Exception('Unknown or unsupported platform %s' \
                            % __platform__)


def get_crypt_password(password):
    return KallitheaCrypto.hash_string(password)


def check_password(password, hashed):
    return KallitheaCrypto.hash_check(password, hashed)



def _cached_perms_data(user_id, user_is_admin, user_inherit_default_permissions,
                       explicit, algo):
    RK = 'repositories'
    GK = 'repositories_groups'
    UK = 'user_groups'
    GLOBAL = 'global'
    PERM_WEIGHTS = Permission.PERM_WEIGHTS
    permissions = {RK: {}, GK: {}, UK: {}, GLOBAL: set()}

    def _choose_perm(new_perm, cur_perm):
        new_perm_val = PERM_WEIGHTS[new_perm]
        cur_perm_val = PERM_WEIGHTS[cur_perm]
        if algo == 'higherwin':
            if new_perm_val > cur_perm_val:
                return new_perm
            return cur_perm
        elif algo == 'lowerwin':
            if new_perm_val < cur_perm_val:
                return new_perm
            return cur_perm

    #======================================================================
    # fetch default permissions
    #======================================================================
    default_user = User.get_by_username('default', cache=True)
    default_user_id = default_user.user_id

    default_repo_perms = Permission.get_default_perms(default_user_id)
    default_repo_groups_perms = Permission.get_default_group_perms(default_user_id)
    default_user_group_perms = Permission.get_default_user_group_perms(default_user_id)

    if user_is_admin:
        #==================================================================
        # admin users have all rights;
        # based on default permissions, just set everything to admin
        #==================================================================
        permissions[GLOBAL].add('hg.admin')
        permissions[GLOBAL].add('hg.create.write_on_repogroup.true')

        # repositories
        for perm in default_repo_perms:
            r_k = perm.UserRepoToPerm.repository.repo_name
            p = 'repository.admin'
            permissions[RK][r_k] = p

        # repository groups
        for perm in default_repo_groups_perms:
            rg_k = perm.UserRepoGroupToPerm.group.group_name
            p = 'group.admin'
            permissions[GK][rg_k] = p

        # user groups
        for perm in default_user_group_perms:
            u_k = perm.UserUserGroupToPerm.user_group.users_group_name
            p = 'usergroup.admin'
            permissions[UK][u_k] = p
        return permissions

    #==================================================================
    # SET DEFAULTS GLOBAL, REPOS, REPOSITORY GROUPS
    #==================================================================

    # default global permissions taken from the default user
    default_global_perms = UserToPerm.query()\
        .filter(UserToPerm.user_id == default_user_id)\
        .options(joinedload(UserToPerm.permission))

    for perm in default_global_perms:
        permissions[GLOBAL].add(perm.permission.permission_name)

    # defaults for repositories, taken from default user
    for perm in default_repo_perms:
        r_k = perm.UserRepoToPerm.repository.repo_name
        if perm.Repository.private and not (perm.Repository.user_id == user_id):
            # disable defaults for private repos,
            p = 'repository.none'
        elif perm.Repository.user_id == user_id:
            # set admin if owner
            p = 'repository.admin'
        else:
            p = perm.Permission.permission_name

        permissions[RK][r_k] = p

    # defaults for repository groups taken from default user permission
    # on given group
    for perm in default_repo_groups_perms:
        rg_k = perm.UserRepoGroupToPerm.group.group_name
        p = perm.Permission.permission_name
        permissions[GK][rg_k] = p

    # defaults for user groups taken from default user permission
    # on given user group
    for perm in default_user_group_perms:
        u_k = perm.UserUserGroupToPerm.user_group.users_group_name
        p = perm.Permission.permission_name
        permissions[UK][u_k] = p

    #======================================================================
    # !! OVERRIDE GLOBALS !! with user permissions if any found
    #======================================================================
    # those can be configured from groups or users explicitly
    _configurable = set([
        'hg.fork.none', 'hg.fork.repository',
        'hg.create.none', 'hg.create.repository',
        'hg.usergroup.create.false', 'hg.usergroup.create.true'
    ])

    # USER GROUPS comes first
    # user group global permissions
    user_perms_from_users_groups = Session().query(UserGroupToPerm)\
        .options(joinedload(UserGroupToPerm.permission))\
        .join((UserGroupMember, UserGroupToPerm.users_group_id ==
               UserGroupMember.users_group_id))\
        .filter(UserGroupMember.user_id == user_id)\
        .join((UserGroup, UserGroupMember.users_group_id ==
               UserGroup.users_group_id))\
        .filter(UserGroup.users_group_active == True)\
        .order_by(UserGroupToPerm.users_group_id)\
        .all()
    # need to group here by groups since user can be in more than
    # one group
    _grouped = [[x, list(y)] for x, y in
                itertools.groupby(user_perms_from_users_groups,
                                  lambda x:x.users_group)]
    for gr, perms in _grouped:
        # since user can be in multiple groups iterate over them and
        # select the lowest permissions first (more explicit)
        ##TODO: do this^^
        if not gr.inherit_default_permissions:
            # NEED TO IGNORE all configurable permissions and
            # replace them with explicitly set
            permissions[GLOBAL] = permissions[GLOBAL]\
                                            .difference(_configurable)
        for perm in perms:
            permissions[GLOBAL].add(perm.permission.permission_name)

    # user specific global permissions
    user_perms = Session().query(UserToPerm)\
            .options(joinedload(UserToPerm.permission))\
            .filter(UserToPerm.user_id == user_id).all()

    if not user_inherit_default_permissions:
        # NEED TO IGNORE all configurable permissions and
        # replace them with explicitly set
        permissions[GLOBAL] = permissions[GLOBAL]\
                                        .difference(_configurable)

        for perm in user_perms:
            permissions[GLOBAL].add(perm.permission.permission_name)
    ## END GLOBAL PERMISSIONS

    #======================================================================
    # !! PERMISSIONS FOR REPOSITORIES !!
    #======================================================================
    #======================================================================
    # check if user is part of user groups for this repository and
    # fill in his permission from it. _choose_perm decides of which
    # permission should be selected based on selected method
    #======================================================================

    # user group for repositories permissions
    user_repo_perms_from_users_groups = \
     Session().query(UserGroupRepoToPerm, Permission, Repository,)\
        .join((Repository, UserGroupRepoToPerm.repository_id ==
               Repository.repo_id))\
        .join((Permission, UserGroupRepoToPerm.permission_id ==
               Permission.permission_id))\
        .join((UserGroup, UserGroupRepoToPerm.users_group_id ==
               UserGroup.users_group_id))\
        .filter(UserGroup.users_group_active == True)\
        .join((UserGroupMember, UserGroupRepoToPerm.users_group_id ==
               UserGroupMember.users_group_id))\
        .filter(UserGroupMember.user_id == user_id)\
        .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_repo_perms_from_users_groups:
        r_k = perm.UserGroupRepoToPerm.repository.repo_name
        multiple_counter[r_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[RK][r_k]

        if perm.Repository.user_id == user_id:
            # set admin if owner
            p = 'repository.admin'
        else:
            if multiple_counter[r_k] > 1:
                p = _choose_perm(p, cur_perm)
        permissions[RK][r_k] = p

    # user explicit permissions for repositories, overrides any specified
    # by the group permission
    user_repo_perms = Permission.get_default_perms(user_id)
    for perm in user_repo_perms:
        r_k = perm.UserRepoToPerm.repository.repo_name
        cur_perm = permissions[RK][r_k]
        # set admin if owner
        if perm.Repository.user_id == user_id:
            p = 'repository.admin'
        else:
            p = perm.Permission.permission_name
            if not explicit:
                p = _choose_perm(p, cur_perm)
        permissions[RK][r_k] = p

    #======================================================================
    # !! PERMISSIONS FOR REPOSITORY GROUPS !!
    #======================================================================
    #======================================================================
    # check if user is part of user groups for this repository groups and
    # fill in his permission from it. _choose_perm decides of which
    # permission should be selected based on selected method
    #======================================================================
    # user group for repo groups permissions
    user_repo_group_perms_from_users_groups = \
     Session().query(UserGroupRepoGroupToPerm, Permission, RepoGroup)\
     .join((RepoGroup, UserGroupRepoGroupToPerm.group_id == RepoGroup.group_id))\
     .join((Permission, UserGroupRepoGroupToPerm.permission_id
            == Permission.permission_id))\
     .join((UserGroup, UserGroupRepoGroupToPerm.users_group_id ==
            UserGroup.users_group_id))\
     .filter(UserGroup.users_group_active == True)\
     .join((UserGroupMember, UserGroupRepoGroupToPerm.users_group_id
            == UserGroupMember.users_group_id))\
     .filter(UserGroupMember.user_id == user_id)\
     .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_repo_group_perms_from_users_groups:
        g_k = perm.UserGroupRepoGroupToPerm.group.group_name
        multiple_counter[g_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[GK][g_k]
        if multiple_counter[g_k] > 1:
            p = _choose_perm(p, cur_perm)
        permissions[GK][g_k] = p

    # user explicit permissions for repository groups
    user_repo_groups_perms = Permission.get_default_group_perms(user_id)
    for perm in user_repo_groups_perms:
        rg_k = perm.UserRepoGroupToPerm.group.group_name
        p = perm.Permission.permission_name
        cur_perm = permissions[GK][rg_k]
        if not explicit:
            p = _choose_perm(p, cur_perm)
        permissions[GK][rg_k] = p

    #======================================================================
    # !! PERMISSIONS FOR USER GROUPS !!
    #======================================================================
    # user group for user group permissions
    user_group_user_groups_perms = \
     Session().query(UserGroupUserGroupToPerm, Permission, UserGroup)\
     .join((UserGroup, UserGroupUserGroupToPerm.target_user_group_id
            == UserGroup.users_group_id))\
     .join((Permission, UserGroupUserGroupToPerm.permission_id
            == Permission.permission_id))\
     .join((UserGroupMember, UserGroupUserGroupToPerm.user_group_id
            == UserGroupMember.users_group_id))\
     .filter(UserGroupMember.user_id == user_id)\
     .join((UserGroup, UserGroupMember.users_group_id ==
            UserGroup.users_group_id), aliased=True, from_joinpoint=True)\
     .filter(UserGroup.users_group_active == True)\
     .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_group_user_groups_perms:
        g_k = perm.UserGroupUserGroupToPerm.target_user_group.users_group_name
        multiple_counter[g_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[UK][g_k]
        if multiple_counter[g_k] > 1:
            p = _choose_perm(p, cur_perm)
        permissions[UK][g_k] = p

    #user explicit permission for user groups
    user_user_groups_perms = Permission.get_default_user_group_perms(user_id)
    for perm in user_user_groups_perms:
        u_k = perm.UserUserGroupToPerm.user_group.users_group_name
        p = perm.Permission.permission_name
        cur_perm = permissions[UK][u_k]
        if not explicit:
            p = _choose_perm(p, cur_perm)
        permissions[UK][u_k] = p

    return permissions


def allowed_api_access(controller_name, whitelist=None, api_key=None):
    """
    Check if given controller_name is in whitelist API access
    """
    if not whitelist:
        from kallithea import CONFIG
        whitelist = aslist(CONFIG.get('api_access_controllers_whitelist'),
                           sep=',')
        log.debug('whitelist of API access is: %s', whitelist)
    api_access_valid = controller_name in whitelist
    if api_access_valid:
        log.debug('controller:%s is in API whitelist', controller_name)
    else:
        msg = 'controller: %s is *NOT* in API whitelist' % (controller_name)
        if api_key:
            #if we use API key and don't have access it's a warning
            log.warning(msg)
        else:
            log.debug(msg)
    return api_access_valid


class AuthUser(object):
    """
    Represents a Kallithea user, including various authentication and
    authorization information. Typically used to store the current user,
    but is also used as a generic user information data structure in
    parts of the code, e.g. user management.

    Constructed from a database `User` object, a user ID or cookie dict,
    it looks up the user (if needed) and copies all attributes to itself,
    adding various non-persistent data. If lookup fails but anonymous
    access to Kallithea is enabled, the default user is loaded instead.

    `AuthUser` does not by itself authenticate users and the constructor
    sets the `is_authenticated` field to False, except when falling back
    to the default anonymous user (if enabled). It's up to other parts
    of the code to check e.g. if a supplied password is correct, and if
    so, set `is_authenticated` to True.

    However, `AuthUser` does refuse to load a user that is not `active`.
    """

    def __init__(self, user_id=None, dbuser=None,
            is_external_auth=False):

        self.is_authenticated = False
        self.is_external_auth = is_external_auth

        user_model = UserModel()
        self.anonymous_user = User.get_default_user(cache=True)

        # These attributes will be overriden by fill_data, below, unless the
        # requested user cannot be found and the default anonymous user is
        # not enabled.
        self.user_id = None
        self.username = None
        self.api_key = None
        self.name = ''
        self.lastname = ''
        self.email = ''
        self.admin = False
        self.inherit_default_permissions = False

        # Look up database user, if necessary.
        if user_id is not None:
            log.debug('Auth User lookup by USER ID %s', user_id)
            dbuser = user_model.get(user_id)
        else:
            # Note: dbuser is allowed to be None.
            log.debug('Auth User lookup by database user %s', dbuser)

        is_user_loaded = self._fill_data(dbuser)

        # If user cannot be found, try falling back to anonymous.
        if not is_user_loaded:
            is_user_loaded =  self._fill_data(self.anonymous_user)

        # The anonymous user is always "logged in".
        if self.user_id == self.anonymous_user.user_id:
            self.is_authenticated = True

        if not self.username:
            self.username = 'None'

        log.debug('Auth User is now %s', self)

    def _fill_data(self, dbuser):
        """
        Copies database fields from a `db.User` to this `AuthUser`. Does
        not copy `api_keys` and `permissions` attributes.

        Checks that `dbuser` is `active` (and not None) before copying;
        returns True on success.
        """
        if dbuser is not None and dbuser.active:
            log.debug('filling %s data', dbuser)
            for k, v in dbuser.get_dict().iteritems():
                assert k not in ['api_keys', 'permissions']
                setattr(self, k, v)
            return True
        return False

    @LazyProperty
    def permissions(self):
        return self.__get_perms(user=self, cache=False)

    @property
    def api_keys(self):
        return self._get_api_keys()

    def __get_perms(self, user, explicit=True, algo='higherwin', cache=False):
        """
        Fills user permission attribute with permissions taken from database
        works for permissions given for repositories, and for permissions that
        are granted to groups

        :param user: `AuthUser` instance
        :param explicit: In case there are permissions both for user and a group
            that user is part of, explicit flag will define if user will
            explicitly override permissions from group, if it's False it will
            make decision based on the algo
        :param algo: algorithm to decide what permission should be choose if
            it's multiple defined, eg user in two different groups. It also
            decides if explicit flag is turned off how to specify the permission
            for case when user is in a group + have defined separate permission
        """
        user_id = user.user_id
        user_is_admin = user.is_admin
        user_inherit_default_permissions = user.inherit_default_permissions

        log.debug('Getting PERMISSION tree')
        compute = conditional_cache('short_term', 'cache_desc',
                                    condition=cache, func=_cached_perms_data)
        return compute(user_id, user_is_admin,
                       user_inherit_default_permissions, explicit, algo)

    def _get_api_keys(self):
        api_keys = [self.api_key]
        for api_key in UserApiKeys.query()\
                .filter(UserApiKeys.user_id == self.user_id)\
                .filter(or_(UserApiKeys.expires == -1,
                            UserApiKeys.expires >= time.time())).all():
            api_keys.append(api_key.api_key)

        return api_keys

    @property
    def is_admin(self):
        return self.admin

    @property
    def repositories_admin(self):
        """
        Returns list of repositories you're an admin of
        """
        return [x[0] for x in self.permissions['repositories'].iteritems()
                if x[1] == 'repository.admin']

    @property
    def repository_groups_admin(self):
        """
        Returns list of repository groups you're an admin of
        """
        return [x[0] for x in self.permissions['repositories_groups'].iteritems()
                if x[1] == 'group.admin']

    @property
    def user_groups_admin(self):
        """
        Returns list of user groups you're an admin of
        """
        return [x[0] for x in self.permissions['user_groups'].iteritems()
                if x[1] == 'usergroup.admin']

    @staticmethod
    def check_ip_allowed(user, ip_addr):
        """
        Check if the given IP address (a `str`) is allowed for the given
        user (an `AuthUser` or `db.User`).
        """
        allowed_ips = AuthUser.get_allowed_ips(user.user_id, cache=True,
            inherit_from_default=user.inherit_default_permissions)
        if check_ip_access(source_ip=ip_addr, allowed_ips=allowed_ips):
            log.debug('IP:%s is in range of %s', ip_addr, allowed_ips)
            return True
        else:
            log.info('Access for IP:%s forbidden, '
                     'not in %s' % (ip_addr, allowed_ips))
            return False

    def __repr__(self):
        return "<AuthUser('id:%s[%s] auth:%s')>"\
            % (self.user_id, self.username, self.is_authenticated)

    def set_authenticated(self, authenticated=True):
        if self.user_id != self.anonymous_user.user_id:
            self.is_authenticated = authenticated

    def to_cookie(self):
        """ Serializes this login session to a cookie `dict`. """
        return {
            'user_id': self.user_id,
            'is_authenticated': self.is_authenticated,
            'is_external_auth': self.is_external_auth,
        }

    @staticmethod
    def from_cookie(cookie):
        """
        Deserializes an `AuthUser` from a cookie `dict`.
        """

        au = AuthUser(
            user_id=cookie.get('user_id'),
            is_external_auth=cookie.get('is_external_auth', False),
        )
        if not au.is_authenticated and au.user_id is not None:
            # user is not authenticated and not empty
            au.set_authenticated(cookie.get('is_authenticated'))
        return au

    @classmethod
    def get_allowed_ips(cls, user_id, cache=False, inherit_from_default=False):
        _set = set()

        if inherit_from_default:
            default_ips = UserIpMap.query().filter(UserIpMap.user ==
                                            User.get_default_user(cache=True))
            if cache:
                default_ips = default_ips.options(FromCache("sql_cache_short",
                                                  "get_user_ips_default"))

            # populate from default user
            for ip in default_ips:
                try:
                    _set.add(ip.ip_addr)
                except ObjectDeletedError:
                    # since we use heavy caching sometimes it happens that we get
                    # deleted objects here, we just skip them
                    pass

        user_ips = UserIpMap.query().filter(UserIpMap.user_id == user_id)
        if cache:
            user_ips = user_ips.options(FromCache("sql_cache_short",
                                                  "get_user_ips_%s" % user_id))

        for ip in user_ips:
            try:
                _set.add(ip.ip_addr)
            except ObjectDeletedError:
                # since we use heavy caching sometimes it happens that we get
                # deleted objects here, we just skip them
                pass
        return _set or set(['0.0.0.0/0', '::/0'])


def set_available_permissions(config):
    """
    This function will propagate pylons globals with all available defined
    permission given in db. We don't want to check each time from db for new
    permissions since adding a new permission also requires application restart
    ie. to decorate new views with the newly created permission

    :param config: current pylons config instance

    """
    log.info('getting information about all available permissions')
    try:
        sa = meta.Session
        all_perms = sa.query(Permission).all()
        config['available_permissions'] = [x.permission_name for x in all_perms]
    finally:
        meta.Session.remove()


#==============================================================================
# CHECK DECORATORS
#==============================================================================

def redirect_to_login(message=None):
    from kallithea.lib import helpers as h
    p = request.path_qs
    if message:
        h.flash(h.literal(message), category='warning')
    log.debug('Redirecting to login page, origin: %s', p)
    return redirect(url('login_home', came_from=p))


class LoginRequired(object):
    """
    Must be logged in to execute this function else
    redirect to login page

    :param api_access: if enabled this checks only for valid auth token
        and grants access based on valid token
    """

    def __init__(self, api_access=False):
        self.api_access = api_access

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        controller = fargs[0]
        user = controller.authuser
        loc = "%s:%s" % (controller.__class__.__name__, func.__name__)
        log.debug('Checking access for user %s @ %s', user, loc)

        if not AuthUser.check_ip_allowed(user, controller.ip_addr):
            return redirect_to_login(_('IP %s not allowed') % controller.ip_addr)

        # check if we used an API key and it's a valid one
        api_key = request.GET.get('api_key')
        if api_key is not None:
            # explicit controller is enabled or API is in our whitelist
            if self.api_access or allowed_api_access(loc, api_key=api_key):
                if api_key in user.api_keys:
                    log.info('user %s authenticated with API key ****%s @ %s',
                             user, api_key[-4:], loc)
                    return func(*fargs, **fkwargs)
                else:
                    log.warning('API key ****%s is NOT valid', api_key[-4:])
                    return redirect_to_login(_('Invalid API key'))
            else:
                # controller does not allow API access
                log.warning('API access to %s is not allowed', loc)
                return abort(403)

        # Only allow the following HTTP request methods. (We sometimes use POST
        # requests with a '_method' set to 'PUT' or 'DELETE'; but that is only
        # used for the route lookup, and does not affect request.method.)
        if request.method not in ['GET', 'HEAD', 'POST', 'PUT']:
            return abort(405)

        # Make sure CSRF token never appears in the URL. If so, invalidate it.
        if secure_form.token_key in request.GET:
            log.error('CSRF key leak detected')
            session.pop(secure_form.token_key, None)
            session.save()
            from kallithea.lib import helpers as h
            h.flash(_("CSRF token leak has been detected - all form tokens have been expired"),
                    category='error')

        # CSRF protection: Whenever a request has ambient authority (whether
        # through a session cookie or its origin IP address), it must include
        # the correct token, unless the HTTP method is GET or HEAD (and thus
        # guaranteed to be side effect free. In practice, the only situation
        # where we allow side effects without ambient authority is when the
        # authority comes from an API key; and that is handled above.
        if request.method not in ['GET', 'HEAD']:
            token = request.POST.get(secure_form.token_key)
            if not token or token != secure_form.authentication_token():
                log.error('CSRF check failed')
                return abort(403)

        # WebOb already ignores request payload parameters for anything other
        # than POST/PUT, but double-check since other Kallithea code relies on
        # this assumption.
        if request.method not in ['POST', 'PUT'] and request.POST:
            log.error('%r request with payload parameters; WebOb should have stopped this', request.method)
            return abort(400)

        # regular user authentication
        if user.is_authenticated:
            log.info('user %s authenticated with regular auth @ %s', user, loc)
            return func(*fargs, **fkwargs)
        else:
            log.warning('user %s NOT authenticated with regular auth @ %s', user, loc)
            return redirect_to_login()

class NotAnonymous(object):
    """
    Must be logged in to execute this function else
    redirect to login page"""

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.authuser

        log.debug('Checking if user is not anonymous @%s', cls)

        anonymous = self.user.username == User.DEFAULT_USER

        if anonymous:
            return redirect_to_login(_('You need to be a registered user to '
                    'perform this action'))
        else:
            return func(*fargs, **fkwargs)


class PermsDecorator(object):
    """Base class for controller decorators"""

    def __init__(self, *required_perms):
        self.required_perms = set(required_perms)
        self.user_perms = None

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.authuser
        self.user_perms = self.user.permissions
        log.debug('checking %s permissions %s for %s %s',
          self.__class__.__name__, self.required_perms, cls, self.user)

        if self.check_permissions():
            log.debug('Permission granted for %s %s', cls, self.user)
            return func(*fargs, **fkwargs)

        else:
            log.debug('Permission denied for %s %s', cls, self.user)
            anonymous = self.user.username == User.DEFAULT_USER

            if anonymous:
                return redirect_to_login(_('You need to be signed in to view this page'))
            else:
                # redirect with forbidden ret code
                return abort(403)

    def check_permissions(self):
        """Dummy function for overriding"""
        raise Exception('You have to write this function in child class')


class HasPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates. All of them
    have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        if self.required_perms.issubset(self.user_perms.get('global')):
            return True
        return False


class HasPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates. In order to
    fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        if self.required_perms.intersection(self.user_perms.get('global')):
            return True
        return False


class HasRepoPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    repository. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        repo_name = get_repo_slug(request)
        try:
            user_perms = set([self.user_perms['repositories'][repo_name]])
        except KeyError:
            return False
        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasRepoPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    repository. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        repo_name = get_repo_slug(request)
        try:
            user_perms = set([self.user_perms['repositories'][repo_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


class HasRepoGroupPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    repository group. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        group_name = get_repo_group_slug(request)
        try:
            user_perms = set([self.user_perms['repositories_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasRepoGroupPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    repository group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        group_name = get_repo_group_slug(request)
        try:
            user_perms = set([self.user_perms['repositories_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


class HasUserGroupPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    user group. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        group_name = get_user_group_slug(request)
        try:
            user_perms = set([self.user_perms['user_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasUserGroupPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    user group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        group_name = get_user_group_slug(request)
        try:
            user_perms = set([self.user_perms['user_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


#==============================================================================
# CHECK FUNCTIONS
#==============================================================================
class PermsFunction(object):
    """Base function for other check functions"""

    def __init__(self, *perms):
        self.required_perms = set(perms)
        self.user_perms = None
        self.repo_name = None
        self.group_name = None

    def __call__(self, check_location='', user=None):
        if not user:
            #TODO: remove this someday,put as user as attribute here
            user = request.user

        # init auth user if not already given
        if not isinstance(user, AuthUser):
            user = AuthUser(user.user_id)

        cls_name = self.__class__.__name__
        check_scope = {
            'HasPermissionAll': '',
            'HasPermissionAny': '',
            'HasRepoPermissionAll': 'repo:%s' % self.repo_name,
            'HasRepoPermissionAny': 'repo:%s' % self.repo_name,
            'HasRepoGroupPermissionAll': 'group:%s' % self.group_name,
            'HasRepoGroupPermissionAny': 'group:%s' % self.group_name,
        }.get(cls_name, '?')
        log.debug('checking cls:%s %s usr:%s %s @ %s', cls_name,
                  self.required_perms, user, check_scope,
                  check_location or 'unspecified location')
        if not user:
            log.debug('Empty request user')
            return False
        self.user_perms = user.permissions
        if self.check_permissions():
            log.debug('Permission to %s granted for user: %s @ %s',
                      check_scope, user,
                         check_location or 'unspecified location')
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s',
                      check_scope, user,
                         check_location or 'unspecified location')
            return False

    def check_permissions(self):
        """Dummy function for overriding"""
        raise Exception('You have to write this function in child class')


class HasPermissionAll(PermsFunction):
    def check_permissions(self):
        if self.required_perms.issubset(self.user_perms.get('global')):
            return True
        return False


class HasPermissionAny(PermsFunction):
    def check_permissions(self):
        if self.required_perms.intersection(self.user_perms.get('global')):
            return True
        return False


class HasRepoPermissionAll(PermsFunction):
    def __call__(self, repo_name=None, check_location='', user=None):
        self.repo_name = repo_name
        return super(HasRepoPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self._user_perms = set(
                [self.user_perms['repositories'][self.repo_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


class HasRepoPermissionAny(PermsFunction):
    def __call__(self, repo_name=None, check_location='', user=None):
        self.repo_name = repo_name
        return super(HasRepoPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self._user_perms = set(
                [self.user_perms['repositories'][self.repo_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasRepoGroupPermissionAny(PermsFunction):
    def __call__(self, group_name=None, check_location='', user=None):
        self.group_name = group_name
        return super(HasRepoGroupPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['repositories_groups'][self.group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasRepoGroupPermissionAll(PermsFunction):
    def __call__(self, group_name=None, check_location='', user=None):
        self.group_name = group_name
        return super(HasRepoGroupPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['repositories_groups'][self.group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


class HasUserGroupPermissionAny(PermsFunction):
    def __call__(self, user_group_name=None, check_location='', user=None):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['user_groups'][self.user_group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasUserGroupPermissionAll(PermsFunction):
    def __call__(self, user_group_name=None, check_location='', user=None):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['user_groups'][self.user_group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


#==============================================================================
# SPECIAL VERSION TO HANDLE MIDDLEWARE AUTH
#==============================================================================
class HasPermissionAnyMiddleware(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, user, repo_name):
        # repo_name MUST be unicode, since we handle keys in permission
        # dict by unicode
        repo_name = safe_unicode(repo_name)
        usr = AuthUser(user.user_id)
        self.user_perms = set([usr.permissions['repositories'][repo_name]])
        self.username = user.username
        self.repo_name = repo_name
        return self.check_permissions()

    def check_permissions(self):
        log.debug('checking VCS protocol '
                  'permissions %s for user:%s repository:%s', self.user_perms,
                                                self.username, self.repo_name)
        if self.required_perms.intersection(self.user_perms):
            log.debug('Permission to repo: %s granted for user: %s @ %s',
                      self.repo_name, self.username, 'PermissionMiddleware')
            return True
        log.debug('Permission to repo: %s denied for user: %s @ %s',
                  self.repo_name, self.username, 'PermissionMiddleware')
        return False


#==============================================================================
# SPECIAL VERSION TO HANDLE API AUTH
#==============================================================================
class _BaseApiPerm(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, check_location=None, user=None, repo_name=None,
                 group_name=None):
        cls_name = self.__class__.__name__
        check_scope = 'user:%s' % (user)
        if repo_name:
            check_scope += ', repo:%s' % (repo_name)

        if group_name:
            check_scope += ', repo group:%s' % (group_name)

        log.debug('checking cls:%s %s %s @ %s',
                  cls_name, self.required_perms, check_scope, check_location)
        if not user:
            log.debug('Empty User passed into arguments')
            return False

        ## process user
        if not isinstance(user, AuthUser):
            user = AuthUser(user.user_id)
        if not check_location:
            check_location = 'unspecified'
        if self.check_permissions(user.permissions, repo_name, group_name):
            log.debug('Permission to %s granted for user: %s @ %s',
                      check_scope, user, check_location)
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s',
                      check_scope, user, check_location)
            return False

    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        """
        implement in child class should return True if permissions are ok,
        False otherwise

        :param perm_defs: dict with permission definitions
        :param repo_name: repo name
        """
        raise NotImplementedError()


class HasPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        if self.required_perms.issubset(perm_defs.get('global')):
            return True
        return False


class HasPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        if self.required_perms.intersection(perm_defs.get('global')):
            return True
        return False


class HasRepoPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories'][repo_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.issubset(_user_perms):
            return True
        return False


class HasRepoPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories'][repo_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.intersection(_user_perms):
            return True
        return False


class HasRepoGroupPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories_groups'][group_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.intersection(_user_perms):
            return True
        return False

class HasRepoGroupPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories_groups'][group_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.issubset(_user_perms):
            return True
        return False

def check_ip_access(source_ip, allowed_ips=None):
    """
    Checks if source_ip is a subnet of any of allowed_ips.

    :param source_ip:
    :param allowed_ips: list of allowed ips together with mask
    """
    from kallithea.lib import ipaddr
    log.debug('checking if ip:%s is subnet of %s', source_ip, allowed_ips)
    if isinstance(allowed_ips, (tuple, list, set)):
        for ip in allowed_ips:
            if ipaddr.IPAddress(source_ip) in ipaddr.IPNetwork(ip):
                log.debug('IP %s is network %s',
                          ipaddr.IPAddress(source_ip), ipaddr.IPNetwork(ip))
                return True
    return False
