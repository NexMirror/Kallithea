#!/usr/bin/env python
# encoding: utf-8
# authentication and permission libraries
# Copyright (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>
#
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
"""
Created on April 4, 2010

@author: marcink
"""
from beaker.cache import cache_region
from pylons import config, session, url, request
from pylons.controllers.util import abort, redirect
from rhodecode.lib.utils import get_repo_slug
from rhodecode.model import meta
from rhodecode.model.db import User, RepoToPerm, Repository, Permission, \
    UserToPerm
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
import bcrypt
from decorator import decorator
import logging
import random

log = logging.getLogger(__name__) 

class PasswordGenerator(object):
    """This is a simple class for generating password from
        different sets of characters
        usage:
        passwd_gen = PasswordGenerator()
        #print 8-letter password containing only big and small letters of alphabet
        print passwd_gen.gen_password(8, passwd_gen.ALPHABETS_BIG_SMALL)        
    """
    ALPHABETS_NUM = r'''1234567890'''#[0]
    ALPHABETS_SMALL = r'''qwertyuiopasdfghjklzxcvbnm'''#[1]
    ALPHABETS_BIG = r'''QWERTYUIOPASDFGHJKLZXCVBNM'''#[2]
    ALPHABETS_SPECIAL = r'''`-=[]\;',./~!@#$%^&*()_+{}|:"<>?'''    #[3]
    ALPHABETS_FULL = ALPHABETS_BIG + ALPHABETS_SMALL + ALPHABETS_NUM + ALPHABETS_SPECIAL#[4]
    ALPHABETS_ALPHANUM = ALPHABETS_BIG + ALPHABETS_SMALL + ALPHABETS_NUM#[5]
    ALPHABETS_BIG_SMALL = ALPHABETS_BIG + ALPHABETS_SMALL
    ALPHABETS_ALPHANUM_BIG = ALPHABETS_BIG + ALPHABETS_NUM#[6]
    ALPHABETS_ALPHANUM_SMALL = ALPHABETS_SMALL + ALPHABETS_NUM#[7]
            
    def __init__(self, passwd=''):
        self.passwd = passwd

    def gen_password(self, len, type):
        self.passwd = ''.join([random.choice(type) for _ in xrange(len)])
        return self.passwd

    
def get_crypt_password(password):
    """Cryptographic function used for password hashing based on sha1
    @param password: password to hash
    """    
    return bcrypt.hashpw(password, bcrypt.gensalt(10))

def check_password(password, hashed):
    return bcrypt.hashpw(password, hashed) == hashed

@cache_region('super_short_term', 'cached_user')
def get_user_cached(username):
    sa = meta.Session
    try:
        user = sa.query(User).filter(User.username == username).one()
    finally:
        meta.Session.remove()
    return user

def authfunc(environ, username, password):
    try:
        user = get_user_cached(username)
    except (NoResultFound, MultipleResultsFound, OperationalError) as e:
        log.error(e)
        user = None
        
    if user:
        if user.active:
            if user.username == username and check_password(password, user.password):
                log.info('user %s authenticated correctly', username)
                return True
        else:
            log.error('user %s is disabled', username)
            
    return False

class  AuthUser(object):
    """
    A simple object that handles a mercurial username for authentication
    """
    def __init__(self):
        self.username = 'None'
        self.name = ''
        self.lastname = ''
        self.email = ''
        self.user_id = None
        self.is_authenticated = False
        self.is_admin = False
        self.permissions = {}


def set_available_permissions(config):
    """
    This function will propagate pylons globals with all available defined
    permission given in db. We don't wannt to check each time from db for new 
    permissions since adding a new permission also requires application restart
    ie. to decorate new views with the newly created permission
    @param config:
    """
    log.info('getting information about all available permissions')
    try:
        sa = meta.Session
        all_perms = sa.query(Permission).all()
    finally:
        meta.Session.remove()
    
    config['available_permissions'] = [x.permission_name for x in all_perms]

def set_base_path(config):
    config['base_path'] = config['pylons.app_globals'].base_path

def fill_data(user):
    """
    Fills user data with those from database and log out user if not present
    in database
    @param user:
    """
    sa = meta.Session
    dbuser = sa.query(User).get(user.user_id)
    if dbuser:
        user.username = dbuser.username
        user.is_admin = dbuser.admin
        user.name = dbuser.name
        user.lastname = dbuser.lastname
        user.email = dbuser.email
    else:
        user.is_authenticated = False
    meta.Session.remove()
    return user
            
def fill_perms(user):
    """
    Fills user permission attribute with permissions taken from database
    @param user:
    """
    
    sa = meta.Session
    user.permissions['repositories'] = {}
    user.permissions['global'] = set()
    
    #===========================================================================
    # fetch default permissions
    #===========================================================================
    default_perms = sa.query(RepoToPerm, Repository, Permission)\
        .join((Repository, RepoToPerm.repository_id == Repository.repo_id))\
        .join((Permission, RepoToPerm.permission_id == Permission.permission_id))\
        .filter(RepoToPerm.user == sa.query(User).filter(User.username == 
                                            'default').scalar()).all()
                                            
    if user.is_admin:
        #=======================================================================
        # #admin have all default rights set to admin        
        #=======================================================================
        user.permissions['global'].add('hg.admin')
        
        for perm in default_perms:
            p = 'repository.admin'
            user.permissions['repositories'][perm.RepoToPerm.repository.repo_name] = p
    
    else:
        #=======================================================================
        # set default permissions
        #=======================================================================
        
        #default global
        default_global_perms = sa.query(UserToPerm)\
            .filter(UserToPerm.user == sa.query(User).filter(User.username == 
            'default').one())
        
        for perm in default_global_perms:
            user.permissions['global'].add(perm.permission.permission_name)
                    
        #default repositories
        for perm in default_perms:
            if perm.Repository.private and not perm.Repository.user_id == user.user_id:
                #disable defaults for private repos,
                p = 'repository.none'
            elif perm.Repository.user_id == user.user_id:
                #set admin if owner
                p = 'repository.admin'
            else:
                p = perm.Permission.permission_name
                
            user.permissions['repositories'][perm.RepoToPerm.repository.repo_name] = p
                                                
        #=======================================================================
        # #overwrite default with user permissions if any
        #=======================================================================
        user_perms = sa.query(RepoToPerm, Permission, Repository)\
            .join((Repository, RepoToPerm.repository_id == Repository.repo_id))\
            .join((Permission, RepoToPerm.permission_id == Permission.permission_id))\
            .filter(RepoToPerm.user_id == user.user_id).all()
            
        for perm in user_perms:
            if perm.Repository.user_id == user.user_id:#set admin if owner
                p = 'repository.admin'
            else:
                p = perm.Permission.permission_name
            user.permissions['repositories'][perm.RepoToPerm.repository.repo_name] = p
    meta.Session.remove()         
    return user
    
def get_user(session):
    """
    Gets user from session, and wraps permissions into user
    @param session:
    """
    user = session.get('rhodecode_user', AuthUser())
    if user.is_authenticated:
        user = fill_data(user)
    user = fill_perms(user)
    session['rhodecode_user'] = user
    session.save()
    return user
        
#===============================================================================
# CHECK DECORATORS
#===============================================================================
class LoginRequired(object):
    """Must be logged in to execute this function else redirect to login page"""
   
    def __call__(self, func):
        return decorator(self.__wrapper, func)
    
    def __wrapper(self, func, *fargs, **fkwargs):
        user = session.get('rhodecode_user', AuthUser())
        log.debug('Checking login required for user:%s', user.username)
        if user.is_authenticated:
            log.debug('user %s is authenticated', user.username)
            return func(*fargs, **fkwargs)
        else:
            log.warn('user %s not authenticated', user.username)
            
            p = ''
            if request.environ.get('SCRIPT_NAME') != '/':
                p += request.environ.get('SCRIPT_NAME')
                
            p += request.environ.get('PATH_INFO')
            if request.environ.get('QUERY_STRING'):
                p += '?' + request.environ.get('QUERY_STRING')
                
            log.debug('redirecting to login page with %s', p)                
            return redirect(url('login_home', came_from=p))

class PermsDecorator(object):
    """Base class for decorators"""
    
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
#        _wrapper.__name__ = func.__name__
#        _wrapper.__dict__.update(func.__dict__)
#        _wrapper.__doc__ = func.__doc__

        self.user_perms = session.get('rhodecode_user', AuthUser()).permissions
        log.debug('checking %s permissions %s for %s',
           self.__class__.__name__, self.required_perms, func.__name__)
        
        if self.check_permissions():
            log.debug('Permission granted for %s', func.__name__)
            
            return func(*fargs, **fkwargs)
        
        else:
            log.warning('Permission denied for %s', func.__name__)
            #redirect with forbidden ret code
            return abort(403)

        
        
    def check_permissions(self):
        """Dummy function for overriding"""
        raise Exception('You have to write this function in child class')

class HasPermissionAllDecorator(PermsDecorator):
    """Checks for access permission for all given predicates. All of them 
    have to be meet in order to fulfill the request
    """
        
    def check_permissions(self):
        if self.required_perms.issubset(self.user_perms.get('global')):
            return True
        return False
            

class HasPermissionAnyDecorator(PermsDecorator):
    """Checks for access permission for any of given predicates. In order to 
    fulfill the request any of predicates must be meet
    """
    
    def check_permissions(self):
        if self.required_perms.intersection(self.user_perms.get('global')):
            return True
        return False

class HasRepoPermissionAllDecorator(PermsDecorator):
    """Checks for access permission for all given predicates for specific 
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
    """Checks for access permission for any of given predicates for specific 
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
#===============================================================================
# CHECK FUNCTIONS
#===============================================================================

class PermsFunction(object):
    """Base function for other check functions"""
    
    def __init__(self, *perms):
        available_perms = config['available_permissions']
        
        for perm in perms:
            if perm not in available_perms:
                raise Exception("'%s' permission in not defined" % perm)
        self.required_perms = set(perms)
        self.user_perms = None
        self.granted_for = ''
        self.repo_name = None
        
    def __call__(self, check_Location=''):
        user = session.get('rhodecode_user', False)
        if not user:
            return False
        self.user_perms = user.permissions
        self.granted_for = user.username        
        log.debug('checking %s %s', self.__class__.__name__, self.required_perms)            
        
        if self.check_permissions():
            log.debug('Permission granted for %s @%s', self.granted_for,
                      check_Location)
            return True
        
        else:
            log.warning('Permission denied for %s @%s', self.granted_for,
                        check_Location)
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
    
    def __call__(self, repo_name=None, check_Location=''):
        self.repo_name = repo_name
        return super(HasRepoPermissionAll, self).__call__(check_Location)
            
    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self.user_perms = set([self.user_perms['repositories']\
                                   [self.repo_name]])
        except KeyError:
            return False
        self.granted_for = self.repo_name       
        if self.required_perms.issubset(self.user_perms):
            return True
        return False
            
class HasRepoPermissionAny(PermsFunction):
    
    def __call__(self, repo_name=None, check_Location=''):
        self.repo_name = repo_name
        return super(HasRepoPermissionAny, self).__call__(check_Location)
        
    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self.user_perms = set([self.user_perms['repositories']\
                                   [self.repo_name]])
        except KeyError:
            return False
        self.granted_for = self.repo_name
        if self.required_perms.intersection(self.user_perms):
            return True
        return False

#===============================================================================
# SPECIAL VERSION TO HANDLE MIDDLEWARE AUTH
#===============================================================================

class HasPermissionAnyMiddleware(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)
    
    def __call__(self, user, repo_name):
        usr = AuthUser()
        usr.user_id = user.user_id
        usr.username = user.username
        usr.is_admin = user.admin
        
        try:
            self.user_perms = set([fill_perms(usr)\
                                   .permissions['repositories'][repo_name]])
        except:
            self.user_perms = set()
        self.granted_for = ''
        self.username = user.username
        self.repo_name = repo_name        
        return self.check_permissions()
            
    def check_permissions(self):
        log.debug('checking mercurial protocol '
                  'permissions for user:%s repository:%s',
                                                self.username, self.repo_name)
        if self.required_perms.intersection(self.user_perms):
            log.debug('permission granted')
            return True
        log.debug('permission denied')
        return False
