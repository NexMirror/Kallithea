# -*- coding: utf-8 -*-
"""
    rhodecode.lib.auth
    ~~~~~~~~~~~~~~~~~~

    authentication and permission libraries

    :created_on: Apr 4, 2010
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

import random
import logging
import traceback
import hashlib

from tempfile import _RandomNameSequence
from decorator import decorator

from pylons import config, url, request
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _
from sqlalchemy.orm.exc import ObjectDeletedError

from rhodecode import __platform__, is_windows, is_unix
from rhodecode.model.meta import Session

from rhodecode.lib.utils2 import str2bool, safe_unicode, aslist
from rhodecode.lib.exceptions import LdapPasswordError, LdapUsernameError,\
    LdapImportError
from rhodecode.lib.utils import get_repo_slug, get_repos_group_slug,\
    get_user_group_slug
from rhodecode.lib.auth_ldap import AuthLdap

from rhodecode.model import meta
from rhodecode.model.user import UserModel
from rhodecode.model.db import Permission, RhodeCodeSetting, User, UserIpMap
from rhodecode.lib.caching_query import FromCache

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

    def __init__(self, passwd=''):
        self.passwd = passwd

    def gen_password(self, length, type_=None):
        if type_ is None:
            type_ = self.ALPHABETS_FULL
        self.passwd = ''.join([random.choice(type_) for _ in xrange(length)])
        return self.passwd


class RhodeCodeCrypto(object):

    @classmethod
    def hash_string(cls, str_):
        """
        Cryptographic function used for password hashing based on pybcrypt
        or pycrypto in windows

        :param password: password to hash
        """
        if is_windows:
            from hashlib import sha256
            return sha256(str_).hexdigest()
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
            from hashlib import sha256
            return sha256(password).hexdigest() == hashed
        elif is_unix:
            import bcrypt
            return bcrypt.hashpw(password, hashed) == hashed
        else:
            raise Exception('Unknown or unsupported platform %s' \
                            % __platform__)


def get_crypt_password(password):
    return RhodeCodeCrypto.hash_string(password)


def check_password(password, hashed):
    return RhodeCodeCrypto.hash_check(password, hashed)


def generate_api_key(str_, salt=None):
    """
    Generates API KEY from given string

    :param str_:
    :param salt:
    """

    if salt is None:
        salt = _RandomNameSequence().next()

    return hashlib.sha1(str_ + salt).hexdigest()


def authfunc(environ, username, password):
    """
    Dummy authentication wrapper function used in Mercurial and Git for
    access control.

    :param environ: needed only for using in Basic auth
    """
    return authenticate(username, password)


def authenticate(username, password):
    """
    Authentication function used for access control,
    firstly checks for db authentication then if ldap is enabled for ldap
    authentication, also creates ldap user if not in database

    :param username: username
    :param password: password
    """

    user_model = UserModel()
    user = User.get_by_username(username)

    log.debug('Authenticating user using RhodeCode account')
    if user is not None and not user.ldap_dn:
        if user.active:
            if user.username == 'default' and user.active:
                log.info('user %s authenticated correctly as anonymous user' %
                         username)
                return True

            elif user.username == username and check_password(password,
                                                              user.password):
                log.info('user %s authenticated correctly' % username)
                return True
        else:
            log.warning('user %s tried auth but is disabled' % username)

    else:
        log.debug('Regular authentication failed')
        user_obj = User.get_by_username(username, case_insensitive=True)

        if user_obj is not None and not user_obj.ldap_dn:
            log.debug('this user already exists as non ldap')
            return False

        ldap_settings = RhodeCodeSetting.get_ldap_settings()
        #======================================================================
        # FALLBACK TO LDAP AUTH IF ENABLE
        #======================================================================
        if str2bool(ldap_settings.get('ldap_active')):
            log.debug("Authenticating user using ldap")
            kwargs = {
                  'server': ldap_settings.get('ldap_host', ''),
                  'base_dn': ldap_settings.get('ldap_base_dn', ''),
                  'port': ldap_settings.get('ldap_port'),
                  'bind_dn': ldap_settings.get('ldap_dn_user'),
                  'bind_pass': ldap_settings.get('ldap_dn_pass'),
                  'tls_kind': ldap_settings.get('ldap_tls_kind'),
                  'tls_reqcert': ldap_settings.get('ldap_tls_reqcert'),
                  'ldap_filter': ldap_settings.get('ldap_filter'),
                  'search_scope': ldap_settings.get('ldap_search_scope'),
                  'attr_login': ldap_settings.get('ldap_attr_login'),
                  'ldap_version': 3,
                  }
            log.debug('Checking for ldap authentication')
            try:
                aldap = AuthLdap(**kwargs)
                (user_dn, ldap_attrs) = aldap.authenticate_ldap(username,
                                                                password)
                log.debug('Got ldap DN response %s' % user_dn)

                get_ldap_attr = lambda k: ldap_attrs.get(ldap_settings\
                                                           .get(k), [''])[0]

                user_attrs = {
                 'name': safe_unicode(get_ldap_attr('ldap_attr_firstname')),
                 'lastname': safe_unicode(get_ldap_attr('ldap_attr_lastname')),
                 'email': get_ldap_attr('ldap_attr_email'),
                 'active': 'hg.extern_activate.auto' in User.get_default_user()\
                                                .AuthUser.permissions['global']
                }

                # don't store LDAP password since we don't need it. Override
                # with some random generated password
                _password = PasswordGenerator().gen_password(length=8)
                # create this user on the fly if it doesn't exist in rhodecode
                # database
                if user_model.create_ldap(username, _password, user_dn,
                                          user_attrs):
                    log.info('created new ldap user %s' % username)

                Session().commit()
                return True
            except (LdapUsernameError, LdapPasswordError, LdapImportError):
                pass
            except (Exception,):
                log.error(traceback.format_exc())
                pass
    return False


def login_container_auth(username):
    user = User.get_by_username(username)
    if user is None:
        user_attrs = {
            'name': username,
            'lastname': None,
            'email': None,
            'active': 'hg.extern_activate.auto' in User.get_default_user()\
                                            .AuthUser.permissions['global']
        }
        user = UserModel().create_for_container_auth(username, user_attrs)
        if not user:
            return None
        log.info('User %s was created by container authentication' % username)

    if not user.active:
        return None

    user.update_lastlogin()
    Session().commit()

    log.debug('User %s is now logged in by container authentication',
              user.username)
    return user


def get_container_username(environ, config, clean_username=False):
    """
    Gets the container_auth username (or email). It tries to get username
    from REMOTE_USER if container_auth_enabled is enabled, if that fails
    it tries to get username from HTTP_X_FORWARDED_USER if proxypass_auth_enabled
    is enabled. clean_username extracts the username from this data if it's
    having @ in it.

    :param environ:
    :param config:
    :param clean_username:
    """
    username = None

    if str2bool(config.get('container_auth_enabled', False)):
        from paste.httpheaders import REMOTE_USER
        username = REMOTE_USER(environ)
        log.debug('extracted REMOTE_USER:%s' % (username))

    if not username and str2bool(config.get('proxypass_auth_enabled', False)):
        username = environ.get('HTTP_X_FORWARDED_USER')
        log.debug('extracted HTTP_X_FORWARDED_USER:%s' % (username))

    if username and clean_username:
        # Removing realm and domain from username
        username = username.partition('@')[0]
        username = username.rpartition('\\')[2]
    log.debug('Received username %s from container' % username)

    return username


class CookieStoreWrapper(object):

    def __init__(self, cookie_store):
        self.cookie_store = cookie_store

    def __repr__(self):
        return 'CookieStore<%s>' % (self.cookie_store)

    def get(self, key, other=None):
        if isinstance(self.cookie_store, dict):
            return self.cookie_store.get(key, other)
        elif isinstance(self.cookie_store, AuthUser):
            return self.cookie_store.__dict__.get(key, other)


class  AuthUser(object):
    """
    A simple object that handles all attributes of user in RhodeCode

    It does lookup based on API key,given user, or user present in session
    Then it fills all required information for such user. It also checks if
    anonymous access is enabled and if so, it returns default user as logged
    in
    """

    def __init__(self, user_id=None, api_key=None, username=None, ip_addr=None):

        self.user_id = user_id
        self.api_key = None
        self.username = username
        self.ip_addr = ip_addr

        self.name = ''
        self.lastname = ''
        self.email = ''
        self.is_authenticated = False
        self.admin = False
        self.inherit_default_permissions = False
        self.permissions = {}
        self._api_key = api_key
        self.propagate_data()
        self._instance = None

    def propagate_data(self):
        user_model = UserModel()
        self.anonymous_user = User.get_by_username('default', cache=True)
        is_user_loaded = False

        # try go get user by api key
        if self._api_key and self._api_key != self.anonymous_user.api_key:
            log.debug('Auth User lookup by API KEY %s' % self._api_key)
            is_user_loaded = user_model.fill_data(self, api_key=self._api_key)
        # lookup by userid
        elif (self.user_id is not None and
              self.user_id != self.anonymous_user.user_id):
            log.debug('Auth User lookup by USER ID %s' % self.user_id)
            is_user_loaded = user_model.fill_data(self, user_id=self.user_id)
        # lookup by username
        elif self.username and \
            str2bool(config.get('container_auth_enabled', False)):

            log.debug('Auth User lookup by USER NAME %s' % self.username)
            dbuser = login_container_auth(self.username)
            if dbuser is not None:
                log.debug('filling all attributes to object')
                for k, v in dbuser.get_dict().items():
                    setattr(self, k, v)
                self.set_authenticated()
                is_user_loaded = True
        else:
            log.debug('No data in %s that could been used to log in' % self)

        if not is_user_loaded:
            # if we cannot authenticate user try anonymous
            if self.anonymous_user.active:
                user_model.fill_data(self, user_id=self.anonymous_user.user_id)
                # then we set this user is logged in
                self.is_authenticated = True
            else:
                self.user_id = None
                self.username = None
                self.is_authenticated = False

        if not self.username:
            self.username = 'None'

        log.debug('Auth User is now %s' % self)
        user_model.fill_perms(self)

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

    @property
    def ip_allowed(self):
        """
        Checks if ip_addr used in constructor is allowed from defined list of
        allowed ip_addresses for user

        :returns: boolean, True if ip is in allowed ip range
        """
        #check IP
        allowed_ips = AuthUser.get_allowed_ips(self.user_id, cache=True)
        if check_ip_access(source_ip=self.ip_addr, allowed_ips=allowed_ips):
            log.debug('IP:%s is in range of %s' % (self.ip_addr, allowed_ips))
            return True
        else:
            log.info('Access for IP:%s forbidden, '
                     'not in %s' % (self.ip_addr, allowed_ips))
            return False

    def __repr__(self):
        return "<AuthUser('id:%s[%s] ip:%s auth:%s')>"\
            % (self.user_id, self.username, self.ip_addr, self.is_authenticated)

    def set_authenticated(self, authenticated=True):
        if self.user_id != self.anonymous_user.user_id:
            self.is_authenticated = authenticated

    def get_cookie_store(self):
        return {'username': self.username,
                'user_id': self.user_id,
                'is_authenticated': self.is_authenticated}

    @classmethod
    def from_cookie_store(cls, cookie_store):
        """
        Creates AuthUser from a cookie store

        :param cls:
        :param cookie_store:
        """
        user_id = cookie_store.get('user_id')
        username = cookie_store.get('username')
        api_key = cookie_store.get('api_key')
        return AuthUser(user_id, api_key, username)

    @classmethod
    def get_allowed_ips(cls, user_id, cache=False):
        _set = set()
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
    except Exception:
        log.error(traceback.format_exc())
    finally:
        meta.Session.remove()


#==============================================================================
# CHECK DECORATORS
#==============================================================================
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
        cls = fargs[0]
        user = cls.rhodecode_user
        loc = "%s:%s" % (cls.__class__.__name__, func.__name__)
        # defined whitelist of controllers which API access will be enabled
        whitelist = aslist(config.get('api_access_controllers_whitelist'),
                           sep=',')
        api_access_whitelist = loc in whitelist
        log.debug('loc:%s is in API whitelist:%s:%s' % (loc, whitelist,
                                                        api_access_whitelist))
        #check IP
        ip_access_ok = True
        if not user.ip_allowed:
            from rhodecode.lib import helpers as h
            h.flash(h.literal(_('IP %s not allowed' % (user.ip_addr))),
                    category='warning')
            ip_access_ok = False

        api_access_ok = False
        if self.api_access or api_access_whitelist:
            log.debug('Checking API KEY access for %s' % cls)
            if user.api_key == request.GET.get('api_key'):
                api_access_ok = True
            else:
                log.debug("API KEY token not valid")

        log.debug('Checking if %s is authenticated @ %s' % (user.username, loc))
        if (user.is_authenticated or api_access_ok) and ip_access_ok:
            reason = 'RegularAuth' if user.is_authenticated else 'APIAuth'
            log.info('user %s is authenticated and granted access to %s '
                     'using %s' % (user.username, loc, reason)
            )
            return func(*fargs, **fkwargs)
        else:
            log.warn('user %s NOT authenticated on func: %s' % (
                user, loc)
            )
            p = url.current()

            log.debug('redirecting to login page with %s' % p)
            return redirect(url('login_home', came_from=p))


class NotAnonymous(object):
    """
    Must be logged in to execute this function else
    redirect to login page"""

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.rhodecode_user

        log.debug('Checking if user is not anonymous @%s' % cls)

        anonymous = self.user.username == 'default'

        if anonymous:
            p = url.current()

            import rhodecode.lib.helpers as h
            h.flash(_('You need to be a registered user to '
                      'perform this action'),
                    category='warning')
            return redirect(url('login_home', came_from=p))
        else:
            return func(*fargs, **fkwargs)


class PermsDecorator(object):
    """Base class for controller decorators"""

    def __init__(self, *required_perms):
        available_perms = config['available_permissions']
        for perm in required_perms:
            if perm not in available_perms:
                raise Exception("'%s' permission is not defined" % perm)
        self.required_perms = set(required_perms)
        self.user_perms = None

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.rhodecode_user
        self.user_perms = self.user.permissions
        log.debug('checking %s permissions %s for %s %s',
           self.__class__.__name__, self.required_perms, cls, self.user)

        if self.check_permissions():
            log.debug('Permission granted for %s %s' % (cls, self.user))
            return func(*fargs, **fkwargs)

        else:
            log.debug('Permission denied for %s %s' % (cls, self.user))
            anonymous = self.user.username == 'default'

            if anonymous:
                p = url.current()

                import rhodecode.lib.helpers as h
                h.flash(_('You need to be a signed in to '
                          'view this page'),
                        category='warning')
                return redirect(url('login_home', came_from=p))

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


class HasReposGroupPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    repository group. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        group_name = get_repos_group_slug(request)
        try:
            user_perms = set([self.user_perms['repositories_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasReposGroupPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    repository group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        group_name = get_repos_group_slug(request)
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
        available_perms = config['available_permissions']

        for perm in perms:
            if perm not in available_perms:
                raise Exception("'%s' permission is not defined" % perm)
        self.required_perms = set(perms)
        self.user_perms = None
        self.repo_name = None
        self.group_name = None

    def __call__(self, check_location=''):
        #TODO: put user as attribute here
        user = request.user
        cls_name = self.__class__.__name__
        check_scope = {
            'HasPermissionAll': '',
            'HasPermissionAny': '',
            'HasRepoPermissionAll': 'repo:%s' % self.repo_name,
            'HasRepoPermissionAny': 'repo:%s' % self.repo_name,
            'HasReposGroupPermissionAll': 'group:%s' % self.group_name,
            'HasReposGroupPermissionAny': 'group:%s' % self.group_name,
        }.get(cls_name, '?')
        log.debug('checking cls:%s %s usr:%s %s @ %s', cls_name,
                  self.required_perms, user, check_scope,
                  check_location or 'unspecified location')
        if not user:
            log.debug('Empty request user')
            return False
        self.user_perms = user.permissions
        if self.check_permissions():
            log.debug('Permission to %s granted for user: %s @ %s', self.repo_name, user,
                      check_location or 'unspecified location')
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s', self.repo_name, user,
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
    def __call__(self, repo_name=None, check_location=''):
        self.repo_name = repo_name
        return super(HasRepoPermissionAll, self).__call__(check_location)

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
    def __call__(self, repo_name=None, check_location=''):
        self.repo_name = repo_name
        return super(HasRepoPermissionAny, self).__call__(check_location)

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


class HasReposGroupPermissionAny(PermsFunction):
    def __call__(self, group_name=None, check_location=''):
        self.group_name = group_name
        return super(HasReposGroupPermissionAny, self).__call__(check_location)

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


class HasReposGroupPermissionAll(PermsFunction):
    def __call__(self, group_name=None, check_location=''):
        self.group_name = group_name
        return super(HasReposGroupPermissionAll, self).__call__(check_location)

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
    def __call__(self, user_group_name=None, check_location=''):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAny, self).__call__(check_location)

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
    def __call__(self, user_group_name=None, check_location=''):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAll, self).__call__(check_location)

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
        try:
            self.user_perms = set([usr.permissions['repositories'][repo_name]])
        except Exception:
            log.error('Exception while accessing permissions %s' %
                      traceback.format_exc())
            self.user_perms = set()
        self.username = user.username
        self.repo_name = repo_name
        return self.check_permissions()

    def check_permissions(self):
        log.debug('checking VCS protocol '
                  'permissions %s for user:%s repository:%s', self.user_perms,
                                                self.username, self.repo_name)
        if self.required_perms.intersection(self.user_perms):
            log.debug('permission granted for user:%s on repo:%s' % (
                          self.username, self.repo_name
                     )
            )
            return True
        log.debug('permission denied for user:%s on repo:%s' % (
                      self.username, self.repo_name
                 )
        )
        return False


#==============================================================================
# SPECIAL VERSION TO HANDLE API AUTH
#==============================================================================
class _BaseApiPerm(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, check_location='unspecified', user=None, repo_name=None):
        cls_name = self.__class__.__name__
        check_scope = 'user:%s, repo:%s' % (user, repo_name)
        log.debug('checking cls:%s %s %s @ %s', cls_name,
                  self.required_perms, check_scope, check_location)
        if not user:
            log.debug('Empty User passed into arguments')
            return False

        ## process user
        if not isinstance(user, AuthUser):
            user = AuthUser(user.user_id)

        if self.check_permissions(user.permissions, repo_name):
            log.debug('Permission to %s granted for user: %s @ %s', repo_name,
                      user, check_location)
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s', repo_name,
                      user, check_location)
            return False

    def check_permissions(self, perm_defs, repo_name):
        """
        implement in child class should return True if permissions are ok,
        False otherwise

        :param perm_defs: dict with permission definitions
        :param repo_name: repo name
        """
        raise NotImplementedError()


class HasPermissionAllApi(_BaseApiPerm):
    def __call__(self, user, check_location=''):
        return super(HasPermissionAllApi, self)\
            .__call__(check_location=check_location, user=user)

    def check_permissions(self, perm_defs, repo):
        if self.required_perms.issubset(perm_defs.get('global')):
            return True
        return False


class HasPermissionAnyApi(_BaseApiPerm):
    def __call__(self, user, check_location=''):
        return super(HasPermissionAnyApi, self)\
            .__call__(check_location=check_location, user=user)

    def check_permissions(self, perm_defs, repo):
        if self.required_perms.intersection(perm_defs.get('global')):
            return True
        return False


class HasRepoPermissionAllApi(_BaseApiPerm):
    def __call__(self, user, repo_name, check_location=''):
        return super(HasRepoPermissionAllApi, self)\
            .__call__(check_location=check_location, user=user,
                      repo_name=repo_name)

    def check_permissions(self, perm_defs, repo_name):

        try:
            self._user_perms = set(
                [perm_defs['repositories'][repo_name]]
            )
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


class HasRepoPermissionAnyApi(_BaseApiPerm):
    def __call__(self, user, repo_name, check_location=''):
        return super(HasRepoPermissionAnyApi, self)\
            .__call__(check_location=check_location, user=user,
                      repo_name=repo_name)

    def check_permissions(self, perm_defs, repo_name):

        try:
            _user_perms = set(
                [perm_defs['repositories'][repo_name]]
            )
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.intersection(_user_perms):
            return True
        return False


def check_ip_access(source_ip, allowed_ips=None):
    """
    Checks if source_ip is a subnet of any of allowed_ips.

    :param source_ip:
    :param allowed_ips: list of allowed ips together with mask
    """
    from rhodecode.lib import ipaddr
    log.debug('checking if ip:%s is subnet of %s' % (source_ip, allowed_ips))
    if isinstance(allowed_ips, (tuple, list, set)):
        for ip in allowed_ips:
            try:
                if ipaddr.IPAddress(source_ip) in ipaddr.IPNetwork(ip):
                    return True
                # for any case we cannot determine the IP, don't crash just
                # skip it and log as error, we want to say forbidden still when
                # sending bad IP
            except Exception:
                log.error(traceback.format_exc())
                continue
    return False
