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
import os
import logging
import traceback
import hashlib
import itertools
import collections

from decorator import decorator

from tg import request, session
from tg.i18n import ugettext as _
from webhelpers.pylonslib import secure_form
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import joinedload
from webob.exc import HTTPFound, HTTPBadRequest, HTTPForbidden, HTTPMethodNotAllowed

from kallithea import __platform__, is_windows, is_unix
from kallithea.config.routing import url
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.model.meta import Session
from kallithea.model.user import UserModel
from kallithea.model.db import User, Repository, Permission, \
    UserToPerm, UserGroupRepoToPerm, UserGroupToPerm, UserGroupMember, \
    RepoGroup, UserGroupRepoGroupToPerm, UserIpMap, UserGroupUserGroupToPerm, \
    UserGroup, UserApiKeys

from kallithea.lib.utils2 import safe_str, safe_unicode, aslist
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


def get_crypt_password(password):
    """
    Cryptographic function used for password hashing based on pybcrypt
    or Python's own OpenSSL wrapper on windows

    :param password: password to hash
    """
    if is_windows:
        return hashlib.sha256(password).hexdigest()
    elif is_unix:
        import bcrypt
        return bcrypt.hashpw(safe_str(password), bcrypt.gensalt(10))
    else:
        raise Exception('Unknown or unsupported platform %s'
                        % __platform__)


def check_password(password, hashed):
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
        try:
            return bcrypt.checkpw(safe_str(password), safe_str(hashed))
        except ValueError as e:
            # bcrypt will throw ValueError 'Invalid hashed_password salt' on all password errors
            log.error('error from bcrypt checking password: %s', e)
            return False
    else:
        raise Exception('Unknown or unsupported platform %s'
                        % __platform__)


def _cached_perms_data(user_id, user_is_admin, user_inherit_default_permissions,
                       explicit):
    RK = 'repositories'
    GK = 'repositories_groups'
    UK = 'user_groups'
    GLOBAL = 'global'
    PERM_WEIGHTS = Permission.PERM_WEIGHTS
    permissions = {RK: {}, GK: {}, UK: {}, GLOBAL: set()}

    def _choose_perm(new_perm, cur_perm):
        new_perm_val = PERM_WEIGHTS[new_perm]
        cur_perm_val = PERM_WEIGHTS[cur_perm]
        if new_perm_val > cur_perm_val:
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
    default_global_perms = UserToPerm.query() \
        .filter(UserToPerm.user_id == default_user_id) \
        .options(joinedload(UserToPerm.permission))

    for perm in default_global_perms:
        permissions[GLOBAL].add(perm.permission.permission_name)

    # defaults for repositories, taken from default user
    for perm in default_repo_perms:
        r_k = perm.UserRepoToPerm.repository.repo_name
        if perm.Repository.private and not (perm.Repository.owner_id == user_id):
            # disable defaults for private repos,
            p = 'repository.none'
        elif perm.Repository.owner_id == user_id:
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
    user_perms_from_users_groups = Session().query(UserGroupToPerm) \
        .options(joinedload(UserGroupToPerm.permission)) \
        .join((UserGroupMember, UserGroupToPerm.users_group_id ==
               UserGroupMember.users_group_id)) \
        .filter(UserGroupMember.user_id == user_id) \
        .join((UserGroup, UserGroupMember.users_group_id ==
               UserGroup.users_group_id)) \
        .filter(UserGroup.users_group_active == True) \
        .order_by(UserGroupToPerm.users_group_id) \
        .all()
    # need to group here by groups since user can be in more than
    # one group
    _grouped = [[x, list(y)] for x, y in
                itertools.groupby(user_perms_from_users_groups,
                                  lambda x:x.users_group)]
    for gr, perms in _grouped:
        # since user can be in multiple groups iterate over them and
        # select the lowest permissions first (more explicit)
        # TODO: do this^^
        if not gr.inherit_default_permissions:
            # NEED TO IGNORE all configurable permissions and
            # replace them with explicitly set
            permissions[GLOBAL] = permissions[GLOBAL] \
                                            .difference(_configurable)
        for perm in perms:
            permissions[GLOBAL].add(perm.permission.permission_name)

    # user specific global permissions
    user_perms = Session().query(UserToPerm) \
            .options(joinedload(UserToPerm.permission)) \
            .filter(UserToPerm.user_id == user_id).all()

    if not user_inherit_default_permissions:
        # NEED TO IGNORE all configurable permissions and
        # replace them with explicitly set
        permissions[GLOBAL] = permissions[GLOBAL] \
                                        .difference(_configurable)

        for perm in user_perms:
            permissions[GLOBAL].add(perm.permission.permission_name)
    ## END GLOBAL PERMISSIONS

    #======================================================================
    # !! PERMISSIONS FOR REPOSITORIES !!
    #======================================================================
    #======================================================================
    # check if user is part of user groups for this repository and
    # fill in his permission from it.
    #======================================================================

    # user group for repositories permissions
    user_repo_perms_from_users_groups = \
     Session().query(UserGroupRepoToPerm, Permission, Repository,) \
        .join((Repository, UserGroupRepoToPerm.repository_id ==
               Repository.repo_id)) \
        .join((Permission, UserGroupRepoToPerm.permission_id ==
               Permission.permission_id)) \
        .join((UserGroup, UserGroupRepoToPerm.users_group_id ==
               UserGroup.users_group_id)) \
        .filter(UserGroup.users_group_active == True) \
        .join((UserGroupMember, UserGroupRepoToPerm.users_group_id ==
               UserGroupMember.users_group_id)) \
        .filter(UserGroupMember.user_id == user_id) \
        .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_repo_perms_from_users_groups:
        r_k = perm.UserGroupRepoToPerm.repository.repo_name
        multiple_counter[r_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[RK][r_k]

        if perm.Repository.owner_id == user_id:
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
        if perm.Repository.owner_id == user_id:
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
    # fill in his permission from it.
    #======================================================================
    # user group for repo groups permissions
    user_repo_group_perms_from_users_groups = \
     Session().query(UserGroupRepoGroupToPerm, Permission, RepoGroup) \
     .join((RepoGroup, UserGroupRepoGroupToPerm.group_id == RepoGroup.group_id)) \
     .join((Permission, UserGroupRepoGroupToPerm.permission_id
            == Permission.permission_id)) \
     .join((UserGroup, UserGroupRepoGroupToPerm.users_group_id ==
            UserGroup.users_group_id)) \
     .filter(UserGroup.users_group_active == True) \
     .join((UserGroupMember, UserGroupRepoGroupToPerm.users_group_id
            == UserGroupMember.users_group_id)) \
     .filter(UserGroupMember.user_id == user_id) \
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
     Session().query(UserGroupUserGroupToPerm, Permission, UserGroup) \
     .join((UserGroup, UserGroupUserGroupToPerm.target_user_group_id
            == UserGroup.users_group_id)) \
     .join((Permission, UserGroupUserGroupToPerm.permission_id
            == Permission.permission_id)) \
     .join((UserGroupMember, UserGroupUserGroupToPerm.user_group_id
            == UserGroupMember.users_group_id)) \
     .filter(UserGroupMember.user_id == user_id) \
     .join((UserGroup, UserGroupMember.users_group_id ==
            UserGroup.users_group_id), aliased=True, from_joinpoint=True) \
     .filter(UserGroup.users_group_active == True) \
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

    # user explicit permission for user groups
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
            # if we use API key and don't have access it's a warning
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
    sets the `is_authenticated` field to False. It's up to other parts
    of the code to check e.g. if a supplied password is correct, and if
    so, set `is_authenticated` to True.

    However, `AuthUser` does refuse to load a user that is not `active`.

    Note that Kallithea distinguishes between the default user (an actual
    user in the database with username "default") and "no user" (no actual
    User object, AuthUser filled with blank values and username "None").

    If the default user is active, that will always be used instead of
    "no user". On the other hand, if the default user is disabled (and
    there is no login information), we instead get "no user"; this should
    only happen on the login page (as all other requests are redirected).

    `is_default_user` specifically checks if the AuthUser is the user named
    "default". Use `is_anonymous` to check for both "default" and "no user".
    """

    def __init__(self, user_id=None, dbuser=None, authenticating_api_key=None,
            is_external_auth=False):

        self.is_authenticated = False
        self.is_external_auth = is_external_auth
        self.authenticating_api_key = authenticating_api_key

        # These attributes will be overridden by fill_data, below, unless the
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
            dbuser = UserModel().get(user_id)
        else:
            # Note: dbuser is allowed to be None.
            log.debug('Auth User lookup by database user %s', dbuser)

        is_user_loaded = self._fill_data(dbuser)

        # If user cannot be found, try falling back to anonymous.
        if is_user_loaded:
            assert dbuser is not None
            self.is_default_user = dbuser.is_default_user
        else:
            default_user = User.get_default_user(cache=True)
            is_user_loaded = self._fill_data(default_user)
            self.is_default_user = is_user_loaded

        self.is_anonymous = not is_user_loaded or self.is_default_user

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

    def has_repository_permission_level(self, repo_name, level, purpose=None):
        required_perms = {
            'read': ['repository.read', 'repository.write', 'repository.admin'],
            'write': ['repository.write', 'repository.admin'],
            'admin': ['repository.admin'],
        }[level]
        actual_perm = self.permissions['repositories'].get(repo_name)
        ok = actual_perm in required_perms
        log.debug('Checking if user %r can %r repo %r (%s): %s (has %r)',
            self.username, level, repo_name, purpose, ok, actual_perm)
        return ok

    def has_repository_group_permission_level(self, repo_group_name, level, purpose=None):
        required_perms = {
            'read': ['group.read', 'group.write', 'group.admin'],
            'write': ['group.write', 'group.admin'],
            'admin': ['group.admin'],
        }[level]
        actual_perm = self.permissions['repositories_groups'].get(repo_group_name)
        ok = actual_perm in required_perms
        log.debug('Checking if user %r can %r repo group %r (%s): %s (has %r)',
            self.username, level, repo_group_name, purpose, ok, actual_perm)
        return ok

    def has_user_group_permission_level(self, user_group_name, level, purpose=None):
        required_perms = {
            'read': ['usergroup.read', 'usergroup.write', 'usergroup.admin'],
            'write': ['usergroup.write', 'usergroup.admin'],
            'admin': ['usergroup.admin'],
        }[level]
        actual_perm = self.permissions['user_groups'].get(user_group_name)
        ok = actual_perm in required_perms
        log.debug('Checking if user %r can %r user group %r (%s): %s (has %r)',
            self.username, level, user_group_name, purpose, ok, actual_perm)
        return ok

    @property
    def api_keys(self):
        return self._get_api_keys()

    def __get_perms(self, user, explicit=True, cache=False):
        """
        Fills user permission attribute with permissions taken from database
        works for permissions given for repositories, and for permissions that
        are granted to groups

        :param user: `AuthUser` instance
        :param explicit: In case there are permissions both for user and a group
            that user is part of, explicit flag will define if user will
            explicitly override permissions from group, if it's False it will
            compute the decision
        """
        user_id = user.user_id
        user_is_admin = user.is_admin
        user_inherit_default_permissions = user.inherit_default_permissions

        log.debug('Getting PERMISSION tree')
        compute = conditional_cache('short_term', 'cache_desc',
                                    condition=cache, func=_cached_perms_data)
        return compute(user_id, user_is_admin,
                       user_inherit_default_permissions, explicit)

    def _get_api_keys(self):
        api_keys = [self.api_key]
        for api_key in UserApiKeys.query() \
                .filter_by(user_id=self.user_id, is_expired=False):
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
        return "<AuthUser('id:%s[%s] auth:%s')>" \
            % (self.user_id, self.username, (self.is_authenticated or self.is_default_user))

    def to_cookie(self):
        """ Serializes this login session to a cookie `dict`. """
        return {
            'user_id': self.user_id,
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
        au.is_authenticated = True
        return au

    @classmethod
    def get_allowed_ips(cls, user_id, cache=False, inherit_from_default=False):
        _set = set()

        if inherit_from_default:
            default_ips = UserIpMap.query().filter(UserIpMap.user_id ==
                                            User.get_default_user(cache=True).user_id)
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
    This function will propagate globals with all available defined
    permission given in db. We don't want to check each time from db for new
    permissions since adding a new permission also requires application restart
    ie. to decorate new views with the newly created permission

    :param config: current config instance

    """
    log.info('getting information about all available permissions')
    try:
        all_perms = Session().query(Permission).all()
        config['available_permissions'] = [x.permission_name for x in all_perms]
    finally:
        Session.remove()


#==============================================================================
# CHECK DECORATORS
#==============================================================================

def _redirect_to_login(message=None):
    """Return an exception that must be raised. It will redirect to the login
    page which will redirect back to the current URL after authentication.
    The optional message will be shown in a flash message."""
    from kallithea.lib import helpers as h
    if message:
        h.flash(message, category='warning')
    p = request.path_qs
    log.debug('Redirecting to login page, origin: %s', p)
    return HTTPFound(location=url('login_home', came_from=p))


# Use as decorator
class LoginRequired(object):
    """Client must be logged in as a valid User, or we'll redirect to the login
    page.

    If the "default" user is enabled and allow_default_user is true, that is
    considered valid too.

    Also checks that IP address is allowed, and if using API key instead
    of regular cookie authentication, checks that API key access is allowed
    (based on `api_access` parameter and the API view whitelist).
    """

    def __init__(self, api_access=False, allow_default_user=False):
        self.api_access = api_access
        self.allow_default_user = allow_default_user

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        controller = fargs[0]
        user = request.authuser
        loc = "%s:%s" % (controller.__class__.__name__, func.__name__)
        log.debug('Checking access for user %s @ %s', user, loc)

        # Check if we used an API key to authenticate.
        api_key = user.authenticating_api_key
        if api_key is not None:
            # Check that controller is enabled for API key usage.
            if not self.api_access and not allowed_api_access(loc, api_key=api_key):
                # controller does not allow API access
                log.warning('API access to %s is not allowed', loc)
                raise HTTPForbidden()

            log.info('user %s authenticated with API key ****%s @ %s',
                     user, api_key[-4:], loc)
            return func(*fargs, **fkwargs)

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
                raise HTTPForbidden()

        # regular user authentication
        if user.is_authenticated:
            log.info('user %s authenticated with regular auth @ %s', user, loc)
            return func(*fargs, **fkwargs)
        elif user.is_default_user:
            if self.allow_default_user:
                log.info('default user @ %s', loc)
                return func(*fargs, **fkwargs)
            log.info('default user is not accepted here @ %s', loc)
        else:
            log.warning('user %s NOT authenticated with regular auth @ %s', user, loc)
        raise _redirect_to_login()


# Use as decorator
class NotAnonymous(object):
    """Ensures that client is not logged in as the "default" user, and
    redirects to the login page otherwise. Must be used together with
    LoginRequired."""

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        user = request.authuser

        log.debug('Checking that user %s is not anonymous @%s', user.username, cls)

        if user.is_default_user:
            raise _redirect_to_login(_('You need to be a registered user to '
                                       'perform this action'))
        else:
            return func(*fargs, **fkwargs)


class _PermsDecorator(object):
    """Base class for controller decorators with multiple permissions"""

    def __init__(self, *required_perms):
        self.required_perms = required_perms # usually very short - a list is thus fine

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        user = request.authuser
        log.debug('checking %s permissions %s for %s %s',
          self.__class__.__name__, self.required_perms, cls, user)

        if self.check_permissions(user):
            log.debug('Permission granted for %s %s', cls, user)
            return func(*fargs, **fkwargs)

        else:
            log.info('Permission denied for %s %s', cls, user)
            if user.is_default_user:
                raise _redirect_to_login(_('You need to be signed in to view this page'))
            else:
                raise HTTPForbidden()

    def check_permissions(self, user):
        raise NotImplementedError()


class HasPermissionAnyDecorator(_PermsDecorator):
    """
    Checks the user has any of the given global permissions.
    """

    def check_permissions(self, user):
        global_permissions = user.permissions['global'] # usually very short
        return any(p in global_permissions for p in self.required_perms)


class _PermDecorator(_PermsDecorator):
    """Base class for controller decorators with a single permission"""

    def __init__(self, required_perm):
        _PermsDecorator.__init__(self, [required_perm])
        self.required_perm = required_perm


class HasRepoPermissionLevelDecorator(_PermDecorator):
    """
    Checks the user has at least the specified permission level for the requested repository.
    """

    def check_permissions(self, user):
        repo_name = get_repo_slug(request)
        return user.has_repository_permission_level(repo_name, self.required_perm)


class HasRepoGroupPermissionLevelDecorator(_PermDecorator):
    """
    Checks the user has any of given permissions for the requested repository group.
    """

    def check_permissions(self, user):
        repo_group_name = get_repo_group_slug(request)
        return user.has_repository_group_permission_level(repo_group_name, self.required_perm)


class HasUserGroupPermissionLevelDecorator(_PermDecorator):
    """
    Checks for access permission for any of given predicates for specific
    user group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self, user):
        user_group_name = get_user_group_slug(request)
        return user.has_user_group_permission_level(user_group_name, self.required_perm)


#==============================================================================
# CHECK FUNCTIONS
#==============================================================================

class _PermsFunction(object):
    """Base function for other check functions with multiple permissions"""

    def __init__(self, *required_perms):
        self.required_perms = required_perms # usually very short - a list is thus fine

    def __nonzero__(self):
        """ Defend against accidentally forgetting to call the object
            and instead evaluating it directly in a boolean context,
            which could have security implications.
        """
        raise AssertionError(self.__class__.__name__ + ' is not a bool and must be called!')

    def __call__(self, *a, **b):
        raise NotImplementedError()


class HasPermissionAny(_PermsFunction):

    def __call__(self, purpose=None):
        global_permissions = request.authuser.permissions['global'] # usually very short
        ok = any(p in global_permissions for p in self.required_perms)

        log.debug('Check %s for global %s (%s): %s' %
            (request.authuser.username, self.required_perms, purpose, ok))
        return ok


class _PermFunction(_PermsFunction):
    """Base function for other check functions with a single permission"""

    def __init__(self, required_perm):
        _PermsFunction.__init__(self, [required_perm])
        self.required_perm = required_perm


class HasRepoPermissionLevel(_PermFunction):

    def __call__(self, repo_name, purpose=None):
        return request.authuser.has_repository_permission_level(repo_name, self.required_perm, purpose)


class HasRepoGroupPermissionLevel(_PermFunction):

    def __call__(self, group_name, purpose=None):
        return request.authuser.has_repository_group_permission_level(group_name, self.required_perm, purpose)


class HasUserGroupPermissionLevel(_PermFunction):

    def __call__(self, user_group_name, purpose=None):
        return request.authuser.has_user_group_permission_level(user_group_name, self.required_perm, purpose)


#==============================================================================
# SPECIAL VERSION TO HANDLE MIDDLEWARE AUTH
#==============================================================================

class HasPermissionAnyMiddleware(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, user, repo_name, purpose=None):
        # repo_name MUST be unicode, since we handle keys in ok
        # dict by unicode
        repo_name = safe_unicode(repo_name)
        user = AuthUser(user.user_id)

        try:
            ok = user.permissions['repositories'][repo_name] in self.required_perms
        except KeyError:
            ok = False

        log.debug('Middleware check %s for %s for repo %s (%s): %s' % (user.username, self.required_perms, repo_name, purpose, ok))
        return ok


def check_ip_access(source_ip, allowed_ips=None):
    """
    Checks if source_ip is a subnet of any of allowed_ips.

    :param source_ip:
    :param allowed_ips: list of allowed ips together with mask
    """
    from kallithea.lib import ipaddr
    source_ip = source_ip.split('%', 1)[0]
    log.debug('checking if ip:%s is subnet of %s', source_ip, allowed_ips)
    if isinstance(allowed_ips, (tuple, list, set)):
        for ip in allowed_ips:
            if ipaddr.IPAddress(source_ip) in ipaddr.IPNetwork(ip):
                log.debug('IP %s is network %s',
                          ipaddr.IPAddress(source_ip), ipaddr.IPNetwork(ip))
                return True
    return False
