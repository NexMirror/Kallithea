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
kallithea.model.db
~~~~~~~~~~~~~~~~~~

Database Models for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 08, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import collections
import datetime
import functools
import hashlib
import logging
import os
import time
import traceback

import ipaddr
import sqlalchemy
from beaker.cache import cache_region, region_invalidate
from sqlalchemy import *
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import class_mapper, joinedload, relationship, validates
from tg.i18n import lazy_ugettext as _
from webob.exc import HTTPNotFound

import kallithea
from kallithea.lib.caching_query import FromCache
from kallithea.lib.compat import json
from kallithea.lib.exceptions import DefaultUserException
from kallithea.lib.utils2 import Optional, aslist, get_changeset_safe, get_clone_url, remove_prefix, safe_int, safe_str, safe_unicode, str2bool, urlreadable
from kallithea.lib.vcs import get_backend
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.utils.helpers import get_scm
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.model.meta import Base, Session


URL_SEP = '/'
log = logging.getLogger(__name__)

#==============================================================================
# BASE CLASSES
#==============================================================================

_hash_key = lambda k: hashlib.md5(safe_str(k)).hexdigest()


class BaseDbModel(object):
    """
    Base Model for all classes
    """

    @classmethod
    def _get_keys(cls):
        """return column names for this model """
        return class_mapper(cls).c.keys()

    def get_dict(self):
        """
        return dict with keys and values corresponding
        to this model data """

        d = {}
        for k in self._get_keys():
            d[k] = getattr(self, k)

        # also use __json__() if present to get additional fields
        _json_attr = getattr(self, '__json__', None)
        if _json_attr:
            # update with attributes from __json__
            if callable(_json_attr):
                _json_attr = _json_attr()
            for k, val in _json_attr.iteritems():
                d[k] = val
        return d

    def get_appstruct(self):
        """return list with keys and values tuples corresponding
        to this model data """

        return [
            (k, getattr(self, k))
            for k in self._get_keys()
        ]

    def populate_obj(self, populate_dict):
        """populate model with data from given populate_dict"""

        for k in self._get_keys():
            if k in populate_dict:
                setattr(self, k, populate_dict[k])

    @classmethod
    def query(cls):
        return Session().query(cls)

    @classmethod
    def get(cls, id_):
        if id_:
            return cls.query().get(id_)

    @classmethod
    def guess_instance(cls, value, callback=None):
        """Haphazardly attempt to convert `value` to a `cls` instance.

        If `value` is None or already a `cls` instance, return it. If `value`
        is a number (or looks like one if you squint just right), assume it's
        a database primary key and let SQLAlchemy sort things out. Otherwise,
        fall back to resolving it using `callback` (if specified); this could
        e.g. be a function that looks up instances by name (though that won't
        work if the name begins with a digit). Otherwise, raise Exception.
        """

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, (int, long)) or safe_str(value).isdigit():
            return cls.get(value)
        if callback is not None:
            return callback(value)

        raise Exception(
            'given object must be int, long or Instance of %s '
            'got %s, no callback provided' % (cls, type(value))
        )

    @classmethod
    def get_or_404(cls, id_):
        try:
            id_ = int(id_)
        except (TypeError, ValueError):
            raise HTTPNotFound

        res = cls.query().get(id_)
        if res is None:
            raise HTTPNotFound
        return res

    @classmethod
    def delete(cls, id_):
        obj = cls.query().get(id_)
        Session().delete(obj)

    def __repr__(self):
        if hasattr(self, '__unicode__'):
            # python repr needs to return str
            try:
                return safe_str(self.__unicode__())
            except UnicodeDecodeError:
                pass
        return '<DB:%s>' % (self.__class__.__name__)


_table_args_default_dict = {'extend_existing': True,
                            'mysql_engine': 'InnoDB',
                            'mysql_charset': 'utf8',
                            'sqlite_autoincrement': True,
                           }

class Setting(Base, BaseDbModel):
    __tablename__ = 'settings'
    __table_args__ = (
        _table_args_default_dict,
    )

    SETTINGS_TYPES = {
        'str': safe_str,
        'int': safe_int,
        'unicode': safe_unicode,
        'bool': str2bool,
        'list': functools.partial(aslist, sep=',')
    }
    DEFAULT_UPDATE_URL = ''

    app_settings_id = Column(Integer(), primary_key=True)
    app_settings_name = Column(String(255), nullable=False, unique=True)
    _app_settings_value = Column("app_settings_value", Unicode(4096), nullable=False)
    _app_settings_type = Column("app_settings_type", String(255), nullable=True) # FIXME: not nullable?

    def __init__(self, key='', val='', type='unicode'):
        self.app_settings_name = key
        self.app_settings_value = val
        self.app_settings_type = type

    @validates('_app_settings_value')
    def validate_settings_value(self, key, val):
        assert type(val) == unicode
        return val

    @hybrid_property
    def app_settings_value(self):
        v = self._app_settings_value
        _type = self.app_settings_type
        converter = self.SETTINGS_TYPES.get(_type) or self.SETTINGS_TYPES['unicode']
        return converter(v)

    @app_settings_value.setter
    def app_settings_value(self, val):
        """
        Setter that will always make sure we use unicode in app_settings_value

        :param val:
        """
        self._app_settings_value = safe_unicode(val)

    @hybrid_property
    def app_settings_type(self):
        return self._app_settings_type

    @app_settings_type.setter
    def app_settings_type(self, val):
        if val not in self.SETTINGS_TYPES:
            raise Exception('type must be one of %s got %s'
                            % (self.SETTINGS_TYPES.keys(), val))
        self._app_settings_type = val

    def __unicode__(self):
        return u"<%s('%s:%s[%s]')>" % (
            self.__class__.__name__,
            self.app_settings_name, self.app_settings_value, self.app_settings_type
        )

    @classmethod
    def get_by_name(cls, key):
        return cls.query() \
            .filter(cls.app_settings_name == key).scalar()

    @classmethod
    def get_by_name_or_create(cls, key, val='', type='unicode'):
        res = cls.get_by_name(key)
        if res is None:
            res = cls(key, val, type)
        return res

    @classmethod
    def create_or_update(cls, key, val=Optional(''), type=Optional('unicode')):
        """
        Creates or updates Kallithea setting. If updates are triggered, it will only
        update parameters that are explicitly set. Optional instance will be skipped.

        :param key:
        :param val:
        :param type:
        :return:
        """
        res = cls.get_by_name(key)
        if res is None:
            val = Optional.extract(val)
            type = Optional.extract(type)
            res = cls(key, val, type)
            Session().add(res)
        else:
            res.app_settings_name = key
            if not isinstance(val, Optional):
                # update if set
                res.app_settings_value = val
            if not isinstance(type, Optional):
                # update if set
                res.app_settings_type = type
        return res

    @classmethod
    def get_app_settings(cls, cache=False):

        ret = cls.query()

        if cache:
            ret = ret.options(FromCache("sql_cache_short", "get_hg_settings"))

        if ret is None:
            raise Exception('Could not get application settings !')
        settings = {}
        for each in ret:
            settings[each.app_settings_name] = \
                each.app_settings_value

        return settings

    @classmethod
    def get_auth_settings(cls, cache=False):
        ret = cls.query() \
                .filter(cls.app_settings_name.startswith('auth_')).all()
        fd = {}
        for row in ret:
            fd[row.app_settings_name] = row.app_settings_value
        return fd

    @classmethod
    def get_default_repo_settings(cls, cache=False, strip_prefix=False):
        ret = cls.query() \
                .filter(cls.app_settings_name.startswith('default_')).all()
        fd = {}
        for row in ret:
            key = row.app_settings_name
            if strip_prefix:
                key = remove_prefix(key, prefix='default_')
            fd.update({key: row.app_settings_value})

        return fd

    @classmethod
    def get_server_info(cls):
        import pkg_resources
        import platform
        from kallithea.lib.utils import check_git_version
        mods = [(p.project_name, p.version) for p in pkg_resources.working_set]
        info = {
            'modules': sorted(mods, key=lambda k: k[0].lower()),
            'py_version': platform.python_version(),
            'platform': safe_unicode(platform.platform()),
            'kallithea_version': kallithea.__version__,
            'git_version': safe_unicode(check_git_version()),
            'git_path': kallithea.CONFIG.get('git_path')
        }
        return info


class Ui(Base, BaseDbModel):
    __tablename__ = 'ui'
    __table_args__ = (
        # FIXME: ui_key as key is wrong and should be removed when the corresponding
        # Ui.get_by_key has been replaced by the composite key
        UniqueConstraint('ui_key'),
        UniqueConstraint('ui_section', 'ui_key'),
        _table_args_default_dict,
    )

    HOOK_UPDATE = 'changegroup.update'
    HOOK_REPO_SIZE = 'changegroup.repo_size'

    ui_id = Column(Integer(), primary_key=True)
    ui_section = Column(String(255), nullable=False)
    ui_key = Column(String(255), nullable=False)
    ui_value = Column(String(255), nullable=True) # FIXME: not nullable?
    ui_active = Column(Boolean(), nullable=False, default=True)

    @classmethod
    def get_by_key(cls, section, key):
        """ Return specified Ui object, or None if not found. """
        return cls.query().filter_by(ui_section=section, ui_key=key).scalar()

    @classmethod
    def get_or_create(cls, section, key):
        """ Return specified Ui object, creating it if necessary. """
        setting = cls.get_by_key(section, key)
        if setting is None:
            setting = cls(ui_section=section, ui_key=key)
            Session().add(setting)
        return setting

    @classmethod
    def get_builtin_hooks(cls):
        q = cls.query()
        q = q.filter(cls.ui_key.in_([cls.HOOK_UPDATE, cls.HOOK_REPO_SIZE]))
        q = q.filter(cls.ui_section == 'hooks')
        return q.all()

    @classmethod
    def get_custom_hooks(cls):
        q = cls.query()
        q = q.filter(~cls.ui_key.in_([cls.HOOK_UPDATE, cls.HOOK_REPO_SIZE]))
        q = q.filter(cls.ui_section == 'hooks')
        return q.all()

    @classmethod
    def get_repos_location(cls):
        return cls.get_by_key('paths', '/').ui_value

    @classmethod
    def create_or_update_hook(cls, key, val):
        new_ui = cls.get_or_create('hooks', key)
        new_ui.ui_active = True
        new_ui.ui_value = val

    def __repr__(self):
        return '<%s[%s]%s=>%s]>' % (self.__class__.__name__, self.ui_section,
                                    self.ui_key, self.ui_value)


class User(Base, BaseDbModel):
    __tablename__ = 'users'
    __table_args__ = (
        Index('u_username_idx', 'username'),
        Index('u_email_idx', 'email'),
        _table_args_default_dict,
    )

    DEFAULT_USER = 'default'
    DEFAULT_GRAVATAR_URL = 'https://secure.gravatar.com/avatar/{md5email}?d=identicon&s={size}'
    # The name of the default auth type in extern_type, 'internal' lives in auth_internal.py
    DEFAULT_AUTH_TYPE = 'internal'

    user_id = Column(Integer(), primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    active = Column(Boolean(), nullable=False, default=True)
    admin = Column(Boolean(), nullable=False, default=False)
    name = Column("firstname", Unicode(255), nullable=False)
    lastname = Column(Unicode(255), nullable=False)
    _email = Column("email", String(255), nullable=True, unique=True) # FIXME: not nullable?
    last_login = Column(DateTime(timezone=False), nullable=True)
    extern_type = Column(String(255), nullable=True) # FIXME: not nullable?
    extern_name = Column(String(255), nullable=True) # FIXME: not nullable?
    api_key = Column(String(255), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    _user_data = Column("user_data", LargeBinary(), nullable=True)  # JSON data # FIXME: not nullable?

    user_log = relationship('UserLog')
    user_perms = relationship('UserToPerm', primaryjoin="User.user_id==UserToPerm.user_id", cascade='all')

    repositories = relationship('Repository')
    repo_groups = relationship('RepoGroup')
    user_groups = relationship('UserGroup')
    user_followers = relationship('UserFollowing', primaryjoin='UserFollowing.follows_user_id==User.user_id', cascade='all')
    followings = relationship('UserFollowing', primaryjoin='UserFollowing.user_id==User.user_id', cascade='all')

    repo_to_perm = relationship('UserRepoToPerm', primaryjoin='UserRepoToPerm.user_id==User.user_id', cascade='all')
    repo_group_to_perm = relationship('UserRepoGroupToPerm', primaryjoin='UserRepoGroupToPerm.user_id==User.user_id', cascade='all')

    group_member = relationship('UserGroupMember', cascade='all')

    # comments created by this user
    user_comments = relationship('ChangesetComment', cascade='all')
    # extra emails for this user
    user_emails = relationship('UserEmailMap', cascade='all')
    # extra API keys
    user_api_keys = relationship('UserApiKeys', cascade='all')
    ssh_keys = relationship('UserSshKeys', cascade='all')

    @hybrid_property
    def email(self):
        return self._email

    @email.setter
    def email(self, val):
        self._email = val.lower() if val else None

    @property
    def firstname(self):
        # alias for future
        return self.name

    @property
    def emails(self):
        other = UserEmailMap.query().filter(UserEmailMap.user == self).all()
        return [self.email] + [x.email for x in other]

    @property
    def api_keys(self):
        other = UserApiKeys.query().filter(UserApiKeys.user == self).all()
        return [self.api_key] + [x.api_key for x in other]

    @property
    def ip_addresses(self):
        ret = UserIpMap.query().filter(UserIpMap.user == self).all()
        return [x.ip_addr for x in ret]

    @property
    def full_name(self):
        return '%s %s' % (self.firstname, self.lastname)

    @property
    def full_name_or_username(self):
        """
        Show full name.
        If full name is not set, fall back to username.
        """
        return ('%s %s' % (self.firstname, self.lastname)
                if (self.firstname and self.lastname) else self.username)

    @property
    def full_name_and_username(self):
        """
        Show full name and username as 'Firstname Lastname (username)'.
        If full name is not set, fall back to username.
        """
        return ('%s %s (%s)' % (self.firstname, self.lastname, self.username)
                if (self.firstname and self.lastname) else self.username)

    @property
    def full_contact(self):
        return '%s %s <%s>' % (self.firstname, self.lastname, self.email)

    @property
    def short_contact(self):
        return '%s %s' % (self.firstname, self.lastname)

    @property
    def is_admin(self):
        return self.admin

    @hybrid_property
    def is_default_user(self):
        return self.username == User.DEFAULT_USER

    @hybrid_property
    def user_data(self):
        if not self._user_data:
            return {}

        try:
            return json.loads(self._user_data)
        except TypeError:
            return {}

    @user_data.setter
    def user_data(self, val):
        try:
            self._user_data = json.dumps(val)
        except Exception:
            log.error(traceback.format_exc())

    def __unicode__(self):
        return u"<%s('id:%s:%s')>" % (self.__class__.__name__,
                                      self.user_id, self.username)

    @classmethod
    def guess_instance(cls, value):
        return super(User, cls).guess_instance(value, User.get_by_username)

    @classmethod
    def get_or_404(cls, id_, allow_default=True):
        '''
        Overridden version of BaseDbModel.get_or_404, with an extra check on
        the default user.
        '''
        user = super(User, cls).get_or_404(id_)
        if not allow_default and user.is_default_user:
            raise DefaultUserException()
        return user

    @classmethod
    def get_by_username_or_email(cls, username_or_email, case_insensitive=False, cache=False):
        """
        For anything that looks like an email address, look up by the email address (matching
        case insensitively).
        For anything else, try to look up by the user name.

        This assumes no normal username can have '@' symbol.
        """
        if '@' in username_or_email:
            return User.get_by_email(username_or_email, cache=cache)
        else:
            return User.get_by_username(username_or_email, case_insensitive=case_insensitive, cache=cache)

    @classmethod
    def get_by_username(cls, username, case_insensitive=False, cache=False):
        if case_insensitive:
            q = cls.query().filter(func.lower(cls.username) == func.lower(username))
        else:
            q = cls.query().filter(cls.username == username)

        if cache:
            q = q.options(FromCache(
                            "sql_cache_short",
                            "get_user_%s" % _hash_key(username)
                          )
            )
        return q.scalar()

    @classmethod
    def get_by_api_key(cls, api_key, cache=False, fallback=True):
        if len(api_key) != 40 or not api_key.isalnum():
            return None

        q = cls.query().filter(cls.api_key == api_key)

        if cache:
            q = q.options(FromCache("sql_cache_short",
                                    "get_api_key_%s" % api_key))
        res = q.scalar()

        if fallback and not res:
            # fallback to additional keys
            _res = UserApiKeys.query().filter_by(api_key=api_key, is_expired=False).first()
            if _res:
                res = _res.user
        if res is None or not res.active or res.is_default_user:
            return None
        return res

    @classmethod
    def get_by_email(cls, email, cache=False):
        q = cls.query().filter(func.lower(cls.email) == func.lower(email))

        if cache:
            q = q.options(FromCache("sql_cache_short",
                                    "get_email_key_%s" % email))

        ret = q.scalar()
        if ret is None:
            q = UserEmailMap.query()
            # try fetching in alternate email map
            q = q.filter(func.lower(UserEmailMap.email) == func.lower(email))
            q = q.options(joinedload(UserEmailMap.user))
            if cache:
                q = q.options(FromCache("sql_cache_short",
                                        "get_email_map_key_%s" % email))
            ret = getattr(q.scalar(), 'user', None)

        return ret

    @classmethod
    def get_from_cs_author(cls, author):
        """
        Tries to get User objects out of commit author string

        :param author:
        """
        from kallithea.lib.helpers import email, author_name
        # Valid email in the attribute passed, see if they're in the system
        _email = email(author)
        if _email:
            user = cls.get_by_email(_email)
            if user is not None:
                return user
        # Maybe we can match by username?
        _author = author_name(author)
        user = cls.get_by_username(_author, case_insensitive=True)
        if user is not None:
            return user

    def update_lastlogin(self):
        """Update user lastlogin"""
        self.last_login = datetime.datetime.now()
        log.debug('updated user %s lastlogin', self.username)

    @classmethod
    def get_first_admin(cls):
        user = User.query().filter(User.admin == True).first()
        if user is None:
            raise Exception('Missing administrative account!')
        return user

    @classmethod
    def get_default_user(cls, cache=False):
        user = User.get_by_username(User.DEFAULT_USER, cache=cache)
        if user is None:
            raise Exception('Missing default account!')
        return user

    def get_api_data(self, details=False):
        """
        Common function for generating user related data for API
        """
        user = self
        data = dict(
            user_id=user.user_id,
            username=user.username,
            firstname=user.name,
            lastname=user.lastname,
            email=user.email,
            emails=user.emails,
            active=user.active,
            admin=user.admin,
        )
        if details:
            data.update(dict(
                extern_type=user.extern_type,
                extern_name=user.extern_name,
                api_key=user.api_key,
                api_keys=user.api_keys,
                last_login=user.last_login,
                ip_addresses=user.ip_addresses
                ))
        return data

    def __json__(self):
        data = dict(
            full_name=self.full_name,
            full_name_or_username=self.full_name_or_username,
            short_contact=self.short_contact,
            full_contact=self.full_contact
        )
        data.update(self.get_api_data())
        return data


class UserApiKeys(Base, BaseDbModel):
    __tablename__ = 'user_api_keys'
    __table_args__ = (
        Index('uak_api_key_idx', 'api_key'),
        Index('uak_api_key_expires_idx', 'api_key', 'expires'),
        _table_args_default_dict,
    )

    user_api_key_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    api_key = Column(String(255), nullable=False, unique=True)
    description = Column(UnicodeText(), nullable=False)
    expires = Column(Float(53), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    user = relationship('User')

    @hybrid_property
    def is_expired(self):
        return (self.expires != -1) & (time.time() > self.expires)


class UserEmailMap(Base, BaseDbModel):
    __tablename__ = 'user_email_map'
    __table_args__ = (
        Index('uem_email_idx', 'email'),
        _table_args_default_dict,
    )

    email_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    _email = Column("email", String(255), nullable=False, unique=True)
    user = relationship('User')

    @validates('_email')
    def validate_email(self, key, email):
        # check if this email is not main one
        main_email = Session().query(User).filter(User.email == email).scalar()
        if main_email is not None:
            raise AttributeError('email %s is present is user table' % email)
        return email

    @hybrid_property
    def email(self):
        return self._email

    @email.setter
    def email(self, val):
        self._email = val.lower() if val else None


class UserIpMap(Base, BaseDbModel):
    __tablename__ = 'user_ip_map'
    __table_args__ = (
        UniqueConstraint('user_id', 'ip_addr'),
        _table_args_default_dict,
    )

    ip_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    ip_addr = Column(String(255), nullable=False)
    active = Column(Boolean(), nullable=False, default=True)
    user = relationship('User')

    @classmethod
    def _get_ip_range(cls, ip_addr):
        net = ipaddr.IPNetwork(address=ip_addr)
        return [str(net.network), str(net.broadcast)]

    def __json__(self):
        return dict(
          ip_addr=self.ip_addr,
          ip_range=self._get_ip_range(self.ip_addr)
        )

    def __unicode__(self):
        return u"<%s('user_id:%s=>%s')>" % (self.__class__.__name__,
                                            self.user_id, self.ip_addr)


class UserLog(Base, BaseDbModel):
    __tablename__ = 'user_logs'
    __table_args__ = (
        _table_args_default_dict,
    )

    user_log_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=True)
    username = Column(String(255), nullable=False)
    repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=True)
    repository_name = Column(Unicode(255), nullable=False)
    user_ip = Column(String(255), nullable=True)
    action = Column(UnicodeText(), nullable=False)
    action_date = Column(DateTime(timezone=False), nullable=False)

    def __unicode__(self):
        return u"<%s('id:%s:%s')>" % (self.__class__.__name__,
                                      self.repository_name,
                                      self.action)

    @property
    def action_as_day(self):
        return datetime.date(*self.action_date.timetuple()[:3])

    user = relationship('User')
    repository = relationship('Repository', cascade='')


class UserGroup(Base, BaseDbModel):
    __tablename__ = 'users_groups'
    __table_args__ = (
        _table_args_default_dict,
    )

    users_group_id = Column(Integer(), primary_key=True)
    users_group_name = Column(Unicode(255), nullable=False, unique=True)
    user_group_description = Column(Unicode(10000), nullable=True) # FIXME: not nullable?
    users_group_active = Column(Boolean(), nullable=False)
    owner_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    _group_data = Column("group_data", LargeBinary(), nullable=True)  # JSON data # FIXME: not nullable?

    members = relationship('UserGroupMember', cascade="all, delete-orphan")
    users_group_to_perm = relationship('UserGroupToPerm', cascade='all')
    users_group_repo_to_perm = relationship('UserGroupRepoToPerm', cascade='all')
    users_group_repo_group_to_perm = relationship('UserGroupRepoGroupToPerm', cascade='all')
    user_user_group_to_perm = relationship('UserUserGroupToPerm ', cascade='all')
    user_group_user_group_to_perm = relationship('UserGroupUserGroupToPerm ', primaryjoin="UserGroupUserGroupToPerm.target_user_group_id==UserGroup.users_group_id", cascade='all')

    owner = relationship('User')

    @hybrid_property
    def group_data(self):
        if not self._group_data:
            return {}

        try:
            return json.loads(self._group_data)
        except TypeError:
            return {}

    @group_data.setter
    def group_data(self, val):
        try:
            self._group_data = json.dumps(val)
        except Exception:
            log.error(traceback.format_exc())

    def __unicode__(self):
        return u"<%s('id:%s:%s')>" % (self.__class__.__name__,
                                      self.users_group_id,
                                      self.users_group_name)

    @classmethod
    def guess_instance(cls, value):
        return super(UserGroup, cls).guess_instance(value, UserGroup.get_by_group_name)

    @classmethod
    def get_by_group_name(cls, group_name, cache=False,
                          case_insensitive=False):
        if case_insensitive:
            q = cls.query().filter(func.lower(cls.users_group_name) == func.lower(group_name))
        else:
            q = cls.query().filter(cls.users_group_name == group_name)
        if cache:
            q = q.options(FromCache(
                            "sql_cache_short",
                            "get_group_%s" % _hash_key(group_name)
                          )
            )
        return q.scalar()

    @classmethod
    def get(cls, user_group_id, cache=False):
        user_group = cls.query()
        if cache:
            user_group = user_group.options(FromCache("sql_cache_short",
                                    "get_users_group_%s" % user_group_id))
        return user_group.get(user_group_id)

    def get_api_data(self, with_members=True):
        user_group = self

        data = dict(
            users_group_id=user_group.users_group_id,
            group_name=user_group.users_group_name,
            group_description=user_group.user_group_description,
            active=user_group.users_group_active,
            owner=user_group.owner.username,
        )
        if with_members:
            data['members'] = [
                ugm.user.get_api_data()
                for ugm in user_group.members
            ]

        return data


class UserGroupMember(Base, BaseDbModel):
    __tablename__ = 'users_groups_members'
    __table_args__ = (
        _table_args_default_dict,
    )

    users_group_member_id = Column(Integer(), primary_key=True)
    users_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)

    user = relationship('User')
    users_group = relationship('UserGroup')

    def __init__(self, gr_id='', u_id=''):
        self.users_group_id = gr_id
        self.user_id = u_id


class RepositoryField(Base, BaseDbModel):
    __tablename__ = 'repositories_fields'
    __table_args__ = (
        UniqueConstraint('repository_id', 'field_key'),  # no-multi field
        _table_args_default_dict,
    )

    PREFIX = 'ex_'  # prefix used in form to not conflict with already existing fields

    repo_field_id = Column(Integer(), primary_key=True)
    repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)
    field_key = Column(String(250), nullable=False)
    field_label = Column(String(1024), nullable=False)
    field_value = Column(String(10000), nullable=False)
    field_desc = Column(String(1024), nullable=False)
    field_type = Column(String(255), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    repository = relationship('Repository')

    @property
    def field_key_prefixed(self):
        return 'ex_%s' % self.field_key

    @classmethod
    def un_prefix_key(cls, key):
        if key.startswith(cls.PREFIX):
            return key[len(cls.PREFIX):]
        return key

    @classmethod
    def get_by_key_name(cls, key, repo):
        row = cls.query() \
                .filter(cls.repository == repo) \
                .filter(cls.field_key == key).scalar()
        return row


class Repository(Base, BaseDbModel):
    __tablename__ = 'repositories'
    __table_args__ = (
        Index('r_repo_name_idx', 'repo_name'),
        _table_args_default_dict,
    )

    DEFAULT_CLONE_URI = '{scheme}://{user}@{netloc}/{repo}'
    DEFAULT_CLONE_SSH = 'ssh://{system_user}@{hostname}/{repo}'

    STATE_CREATED = u'repo_state_created'
    STATE_PENDING = u'repo_state_pending'
    STATE_ERROR = u'repo_state_error'

    repo_id = Column(Integer(), primary_key=True)
    repo_name = Column(Unicode(255), nullable=False, unique=True)
    repo_state = Column(String(255), nullable=False)

    clone_uri = Column(String(255), nullable=True) # FIXME: not nullable?
    repo_type = Column(String(255), nullable=False) # 'hg' or 'git'
    owner_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    private = Column(Boolean(), nullable=False)
    enable_statistics = Column("statistics", Boolean(), nullable=False, default=True)
    enable_downloads = Column("downloads", Boolean(), nullable=False, default=True)
    description = Column(Unicode(10000), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    updated_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    _landing_revision = Column("landing_revision", String(255), nullable=False)
    _changeset_cache = Column("changeset_cache", LargeBinary(), nullable=True) # JSON data # FIXME: not nullable?

    fork_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=True)
    group_id = Column(Integer(), ForeignKey('groups.group_id'), nullable=True)

    owner = relationship('User')
    fork = relationship('Repository', remote_side=repo_id)
    group = relationship('RepoGroup')
    repo_to_perm = relationship('UserRepoToPerm', cascade='all', order_by='UserRepoToPerm.repo_to_perm_id')
    users_group_to_perm = relationship('UserGroupRepoToPerm', cascade='all')
    stats = relationship('Statistics', cascade='all', uselist=False)

    followers = relationship('UserFollowing',
                             primaryjoin='UserFollowing.follows_repository_id==Repository.repo_id',
                             cascade='all')
    extra_fields = relationship('RepositoryField',
                                cascade="all, delete-orphan")

    logs = relationship('UserLog')
    comments = relationship('ChangesetComment', cascade="all, delete-orphan")

    pull_requests_org = relationship('PullRequest',
                    primaryjoin='PullRequest.org_repo_id==Repository.repo_id',
                    cascade="all, delete-orphan")

    pull_requests_other = relationship('PullRequest',
                    primaryjoin='PullRequest.other_repo_id==Repository.repo_id',
                    cascade="all, delete-orphan")

    def __unicode__(self):
        return u"<%s('%s:%s')>" % (self.__class__.__name__, self.repo_id,
                                   safe_unicode(self.repo_name))

    @hybrid_property
    def landing_rev(self):
        # always should return [rev_type, rev]
        if self._landing_revision:
            _rev_info = self._landing_revision.split(':')
            if len(_rev_info) < 2:
                _rev_info.insert(0, 'rev')
            return [_rev_info[0], _rev_info[1]]
        return [None, None]

    @landing_rev.setter
    def landing_rev(self, val):
        if ':' not in val:
            raise ValueError('value must be delimited with `:` and consist '
                             'of <rev_type>:<rev>, got %s instead' % val)
        self._landing_revision = val

    @hybrid_property
    def changeset_cache(self):
        try:
            cs_cache = json.loads(self._changeset_cache) # might raise on bad data
            cs_cache['raw_id'] # verify data, raise exception on error
            return cs_cache
        except (TypeError, KeyError, ValueError):
            return EmptyChangeset().__json__()

    @changeset_cache.setter
    def changeset_cache(self, val):
        try:
            self._changeset_cache = json.dumps(val)
        except Exception:
            log.error(traceback.format_exc())

    @classmethod
    def query(cls, sorted=False):
        """Add Repository-specific helpers for common query constructs.

        sorted: if True, apply the default ordering (name, case insensitive).
        """
        q = super(Repository, cls).query()

        if sorted:
            q = q.order_by(func.lower(Repository.repo_name))

        return q

    @classmethod
    def url_sep(cls):
        return URL_SEP

    @classmethod
    def normalize_repo_name(cls, repo_name):
        """
        Normalizes os specific repo_name to the format internally stored inside
        database using URL_SEP

        :param cls:
        :param repo_name:
        """
        return cls.url_sep().join(repo_name.split(os.sep))

    @classmethod
    def guess_instance(cls, value):
        return super(Repository, cls).guess_instance(value, Repository.get_by_repo_name)

    @classmethod
    def get_by_repo_name(cls, repo_name, case_insensitive=False):
        """Get the repo, defaulting to database case sensitivity.
        case_insensitive will be slower and should only be specified if necessary."""
        if case_insensitive:
            q = Session().query(cls).filter(func.lower(cls.repo_name) == func.lower(repo_name))
        else:
            q = Session().query(cls).filter(cls.repo_name == repo_name)
        q = q.options(joinedload(Repository.fork)) \
                .options(joinedload(Repository.owner)) \
                .options(joinedload(Repository.group))
        return q.scalar()

    @classmethod
    def get_by_full_path(cls, repo_full_path):
        base_full_path = os.path.realpath(cls.base_path())
        repo_full_path = os.path.realpath(repo_full_path)
        assert repo_full_path.startswith(base_full_path + os.path.sep)
        repo_name = repo_full_path[len(base_full_path) + 1:]
        repo_name = cls.normalize_repo_name(repo_name)
        return cls.get_by_repo_name(repo_name.strip(URL_SEP))

    @classmethod
    def get_repo_forks(cls, repo_id):
        return cls.query().filter(Repository.fork_id == repo_id)

    @classmethod
    def base_path(cls):
        """
        Returns base path where all repos are stored

        :param cls:
        """
        q = Session().query(Ui) \
            .filter(Ui.ui_key == cls.url_sep())
        q = q.options(FromCache("sql_cache_short", "repository_repo_path"))
        return q.one().ui_value

    @property
    def forks(self):
        """
        Return forks of this repo
        """
        return Repository.get_repo_forks(self.repo_id)

    @property
    def parent(self):
        """
        Returns fork parent
        """
        return self.fork

    @property
    def just_name(self):
        return self.repo_name.split(Repository.url_sep())[-1]

    @property
    def groups_with_parents(self):
        groups = []
        group = self.group
        while group is not None:
            groups.append(group)
            group = group.parent_group
            assert group not in groups, group # avoid recursion on bad db content
        groups.reverse()
        return groups

    @LazyProperty
    def repo_path(self):
        """
        Returns base full path for that repository means where it actually
        exists on a filesystem
        """
        q = Session().query(Ui).filter(Ui.ui_key ==
                                              Repository.url_sep())
        q = q.options(FromCache("sql_cache_short", "repository_repo_path"))
        return q.one().ui_value

    @property
    def repo_full_path(self):
        p = [self.repo_path]
        # we need to split the name by / since this is how we store the
        # names in the database, but that eventually needs to be converted
        # into a valid system path
        p += self.repo_name.split(Repository.url_sep())
        return os.path.join(*map(safe_unicode, p))

    @property
    def cache_keys(self):
        """
        Returns associated cache keys for that repo
        """
        return CacheInvalidation.query() \
            .filter(CacheInvalidation.cache_args == self.repo_name) \
            .order_by(CacheInvalidation.cache_key) \
            .all()

    def get_new_name(self, repo_name):
        """
        returns new full repository name based on assigned group and new new

        :param group_name:
        """
        path_prefix = self.group.full_path_splitted if self.group else []
        return Repository.url_sep().join(path_prefix + [repo_name])

    @property
    def _ui(self):
        """
        Creates an db based ui object for this repository
        """
        from kallithea.lib.utils import make_ui
        return make_ui(clear_session=False)

    @classmethod
    def is_valid(cls, repo_name):
        """
        returns True if given repo name is a valid filesystem repository

        :param cls:
        :param repo_name:
        """
        from kallithea.lib.utils import is_valid_repo

        return is_valid_repo(repo_name, cls.base_path())

    def get_api_data(self, with_revision_names=False,
                           with_pullrequests=False):
        """
        Common function for generating repo api data.
        Optionally, also return tags, branches, bookmarks and PRs.
        """
        repo = self
        data = dict(
            repo_id=repo.repo_id,
            repo_name=repo.repo_name,
            repo_type=repo.repo_type,
            clone_uri=repo.clone_uri,
            private=repo.private,
            created_on=repo.created_on,
            description=repo.description,
            landing_rev=repo.landing_rev,
            owner=repo.owner.username,
            fork_of=repo.fork.repo_name if repo.fork else None,
            enable_statistics=repo.enable_statistics,
            enable_downloads=repo.enable_downloads,
            last_changeset=repo.changeset_cache,
        )
        if with_revision_names:
            scm_repo = repo.scm_instance_no_cache()
            data.update(dict(
                tags=scm_repo.tags,
                branches=scm_repo.branches,
                bookmarks=scm_repo.bookmarks,
            ))
        if with_pullrequests:
            data['pull_requests'] = repo.pull_requests_other
        rc_config = Setting.get_app_settings()
        repository_fields = str2bool(rc_config.get('repository_fields'))
        if repository_fields:
            for f in self.extra_fields:
                data[f.field_key_prefixed] = f.field_value

        return data

    @property
    def last_db_change(self):
        return self.updated_on

    @property
    def clone_uri_hidden(self):
        clone_uri = self.clone_uri
        if clone_uri:
            import urlobject
            url_obj = urlobject.URLObject(self.clone_uri)
            if url_obj.password:
                clone_uri = url_obj.with_password('*****')
        return clone_uri

    def clone_url(self, clone_uri_tmpl, with_id=False, username=None):
        if '{repo}' not in clone_uri_tmpl and '_{repoid}' not in clone_uri_tmpl:
            log.error("Configured clone_uri_tmpl %r has no '{repo}' or '_{repoid}' and cannot toggle to use repo id URLs", clone_uri_tmpl)
        elif with_id:
            clone_uri_tmpl = clone_uri_tmpl.replace('{repo}', '_{repoid}')
        else:
            clone_uri_tmpl = clone_uri_tmpl.replace('_{repoid}', '{repo}')

        import kallithea.lib.helpers as h
        prefix_url = h.canonical_url('home')

        return get_clone_url(clone_uri_tmpl=clone_uri_tmpl,
                             prefix_url=prefix_url,
                             repo_name=self.repo_name,
                             repo_id=self.repo_id,
                             username=username)

    def set_state(self, state):
        self.repo_state = state

    #==========================================================================
    # SCM PROPERTIES
    #==========================================================================

    def get_changeset(self, rev=None):
        return get_changeset_safe(self.scm_instance, rev)

    def get_landing_changeset(self):
        """
        Returns landing changeset, or if that doesn't exist returns the tip
        """
        _rev_type, _rev = self.landing_rev
        cs = self.get_changeset(_rev)
        if isinstance(cs, EmptyChangeset):
            return self.get_changeset()
        return cs

    def update_changeset_cache(self, cs_cache=None):
        """
        Update cache of last changeset for repository, keys should be::

            short_id
            raw_id
            revision
            message
            date
            author

        :param cs_cache:
        """
        from kallithea.lib.vcs.backends.base import BaseChangeset
        if cs_cache is None:
            cs_cache = EmptyChangeset()
            # use no-cache version here
            scm_repo = self.scm_instance_no_cache()
            if scm_repo:
                cs_cache = scm_repo.get_changeset()

        if isinstance(cs_cache, BaseChangeset):
            cs_cache = cs_cache.__json__()

        if (not self.changeset_cache or cs_cache['raw_id'] != self.changeset_cache['raw_id']):
            _default = datetime.datetime.fromtimestamp(0)
            last_change = cs_cache.get('date') or _default
            log.debug('updated repo %s with new cs cache %s',
                      self.repo_name, cs_cache)
            self.updated_on = last_change
            self.changeset_cache = cs_cache
            Session().commit()
        else:
            log.debug('changeset_cache for %s already up to date with %s',
                      self.repo_name, cs_cache['raw_id'])

    @property
    def tip(self):
        return self.get_changeset('tip')

    @property
    def author(self):
        return self.tip.author

    @property
    def last_change(self):
        return self.scm_instance.last_change

    def get_comments(self, revisions=None):
        """
        Returns comments for this repository grouped by revisions

        :param revisions: filter query by revisions only
        """
        cmts = ChangesetComment.query() \
            .filter(ChangesetComment.repo == self)
        if revisions is not None:
            if not revisions:
                return {} # don't use sql 'in' on empty set
            cmts = cmts.filter(ChangesetComment.revision.in_(revisions))
        grouped = collections.defaultdict(list)
        for cmt in cmts.all():
            grouped[cmt.revision].append(cmt)
        return grouped

    def statuses(self, revisions):
        """
        Returns statuses for this repository.
        PRs without any votes do _not_ show up as unreviewed.

        :param revisions: list of revisions to get statuses for
        """
        if not revisions:
            return {}

        statuses = ChangesetStatus.query() \
            .filter(ChangesetStatus.repo == self) \
            .filter(ChangesetStatus.version == 0) \
            .filter(ChangesetStatus.revision.in_(revisions))

        grouped = {}
        for stat in statuses.all():
            pr_id = pr_nice_id = pr_repo = None
            if stat.pull_request:
                pr_id = stat.pull_request.pull_request_id
                pr_nice_id = PullRequest.make_nice_id(pr_id)
                pr_repo = stat.pull_request.other_repo.repo_name
            grouped[stat.revision] = [str(stat.status), stat.status_lbl,
                                      pr_id, pr_repo, pr_nice_id,
                                      stat.author]
        return grouped

    def _repo_size(self):
        from kallithea.lib import helpers as h
        log.debug('calculating repository size...')
        return h.format_byte_size(self.scm_instance.size)

    #==========================================================================
    # SCM CACHE INSTANCE
    #==========================================================================

    def set_invalidate(self):
        """
        Mark caches of this repo as invalid.
        """
        CacheInvalidation.set_invalidate(self.repo_name)

    _scm_instance = None

    @property
    def scm_instance(self):
        if self._scm_instance is None:
            self._scm_instance = self.scm_instance_cached()
        return self._scm_instance

    def scm_instance_cached(self, valid_cache_keys=None):
        @cache_region('long_term', 'scm_instance_cached')
        def _c(repo_name): # repo_name is just for the cache key
            log.debug('Creating new %s scm_instance and populating cache', repo_name)
            return self.scm_instance_no_cache()
        rn = self.repo_name

        valid = CacheInvalidation.test_and_set_valid(rn, None, valid_cache_keys=valid_cache_keys)
        if not valid:
            log.debug('Cache for %s invalidated, getting new object', rn)
            region_invalidate(_c, None, 'scm_instance_cached', rn)
        else:
            log.debug('Trying to get scm_instance of %s from cache', rn)
        return _c(rn)

    def scm_instance_no_cache(self):
        repo_full_path = safe_str(self.repo_full_path)
        alias = get_scm(repo_full_path)[0]
        log.debug('Creating instance of %s repository from %s',
                  alias, self.repo_full_path)
        backend = get_backend(alias)

        if alias == 'hg':
            repo = backend(repo_full_path, create=False,
                           baseui=self._ui)
        else:
            repo = backend(repo_full_path, create=False)

        return repo

    def __json__(self):
        return dict(
            repo_id=self.repo_id,
            repo_name=self.repo_name,
            landing_rev=self.landing_rev,
        )


class RepoGroup(Base, BaseDbModel):
    __tablename__ = 'groups'
    __table_args__ = (
        _table_args_default_dict,
    )

    SEP = ' &raquo; '

    group_id = Column(Integer(), primary_key=True)
    group_name = Column(Unicode(255), nullable=False, unique=True) # full path
    parent_group_id = Column('group_parent_id', Integer(), ForeignKey('groups.group_id'), nullable=True)
    group_description = Column(Unicode(10000), nullable=False)
    owner_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    repo_group_to_perm = relationship('UserRepoGroupToPerm', cascade='all', order_by='UserRepoGroupToPerm.group_to_perm_id')
    users_group_to_perm = relationship('UserGroupRepoGroupToPerm', cascade='all')
    parent_group = relationship('RepoGroup', remote_side=group_id)
    owner = relationship('User')

    @classmethod
    def query(cls, sorted=False):
        """Add RepoGroup-specific helpers for common query constructs.

        sorted: if True, apply the default ordering (name, case insensitive).
        """
        q = super(RepoGroup, cls).query()

        if sorted:
            q = q.order_by(func.lower(RepoGroup.group_name))

        return q

    def __init__(self, group_name='', parent_group=None):
        self.group_name = group_name
        self.parent_group = parent_group

    def __unicode__(self):
        return u"<%s('id:%s:%s')>" % (self.__class__.__name__, self.group_id,
                                      self.group_name)

    @classmethod
    def _generate_choice(cls, repo_group):
        """Return tuple with group_id and name as html literal"""
        from webhelpers2.html import literal
        if repo_group is None:
            return (-1, u'-- %s --' % _('top level'))
        return repo_group.group_id, literal(cls.SEP.join(repo_group.full_path_splitted))

    @classmethod
    def groups_choices(cls, groups):
        """Return tuples with group_id and name as html literal."""
        return sorted((cls._generate_choice(g) for g in groups),
                      key=lambda c: c[1].split(cls.SEP))

    @classmethod
    def url_sep(cls):
        return URL_SEP

    @classmethod
    def guess_instance(cls, value):
        return super(RepoGroup, cls).guess_instance(value, RepoGroup.get_by_group_name)

    @classmethod
    def get_by_group_name(cls, group_name, cache=False, case_insensitive=False):
        group_name = group_name.rstrip('/')
        if case_insensitive:
            gr = cls.query() \
                .filter(func.lower(cls.group_name) == func.lower(group_name))
        else:
            gr = cls.query() \
                .filter(cls.group_name == group_name)
        if cache:
            gr = gr.options(FromCache(
                            "sql_cache_short",
                            "get_group_%s" % _hash_key(group_name)
                            )
            )
        return gr.scalar()

    @property
    def parents(self):
        groups = []
        group = self.parent_group
        while group is not None:
            groups.append(group)
            group = group.parent_group
            assert group not in groups, group # avoid recursion on bad db content
        groups.reverse()
        return groups

    @property
    def children(self):
        return RepoGroup.query().filter(RepoGroup.parent_group == self)

    @property
    def name(self):
        return self.group_name.split(RepoGroup.url_sep())[-1]

    @property
    def full_path(self):
        return self.group_name

    @property
    def full_path_splitted(self):
        return self.group_name.split(RepoGroup.url_sep())

    @property
    def repositories(self):
        return Repository.query(sorted=True).filter_by(group=self)

    @property
    def repositories_recursive_count(self):
        cnt = self.repositories.count()

        def children_count(group):
            cnt = 0
            for child in group.children:
                cnt += child.repositories.count()
                cnt += children_count(child)
            return cnt

        return cnt + children_count(self)

    def _recursive_objects(self, include_repos=True):
        all_ = []

        def _get_members(root_gr):
            if include_repos:
                for r in root_gr.repositories:
                    all_.append(r)
            childs = root_gr.children.all()
            if childs:
                for gr in childs:
                    all_.append(gr)
                    _get_members(gr)

        _get_members(self)
        return [self] + all_

    def recursive_groups_and_repos(self):
        """
        Recursive return all groups, with repositories in those groups
        """
        return self._recursive_objects()

    def recursive_groups(self):
        """
        Returns all children groups for this group including children of children
        """
        return self._recursive_objects(include_repos=False)

    def get_new_name(self, group_name):
        """
        returns new full group name based on parent and new name

        :param group_name:
        """
        path_prefix = (self.parent_group.full_path_splitted if
                       self.parent_group else [])
        return RepoGroup.url_sep().join(path_prefix + [group_name])

    def get_api_data(self):
        """
        Common function for generating api data

        """
        group = self
        data = dict(
            group_id=group.group_id,
            group_name=group.group_name,
            group_description=group.group_description,
            parent_group=group.parent_group.group_name if group.parent_group else None,
            repositories=[x.repo_name for x in group.repositories],
            owner=group.owner.username
        )
        return data


class Permission(Base, BaseDbModel):
    __tablename__ = 'permissions'
    __table_args__ = (
        Index('p_perm_name_idx', 'permission_name'),
        _table_args_default_dict,
    )

    PERMS = (
        ('hg.admin', _('Kallithea Administrator')),

        ('repository.none', _('Default user has no access to new repositories')),
        ('repository.read', _('Default user has read access to new repositories')),
        ('repository.write', _('Default user has write access to new repositories')),
        ('repository.admin', _('Default user has admin access to new repositories')),

        ('group.none', _('Default user has no access to new repository groups')),
        ('group.read', _('Default user has read access to new repository groups')),
        ('group.write', _('Default user has write access to new repository groups')),
        ('group.admin', _('Default user has admin access to new repository groups')),

        ('usergroup.none', _('Default user has no access to new user groups')),
        ('usergroup.read', _('Default user has read access to new user groups')),
        ('usergroup.write', _('Default user has write access to new user groups')),
        ('usergroup.admin', _('Default user has admin access to new user groups')),

        ('hg.repogroup.create.false', _('Only admins can create repository groups')),
        ('hg.repogroup.create.true', _('Non-admins can create repository groups')),

        ('hg.usergroup.create.false', _('Only admins can create user groups')),
        ('hg.usergroup.create.true', _('Non-admins can create user groups')),

        ('hg.create.none', _('Only admins can create top level repositories')),
        ('hg.create.repository', _('Non-admins can create top level repositories')),

        ('hg.create.write_on_repogroup.true', _('Repository creation enabled with write permission to a repository group')),
        ('hg.create.write_on_repogroup.false', _('Repository creation disabled with write permission to a repository group')),

        ('hg.fork.none', _('Only admins can fork repositories')),
        ('hg.fork.repository', _('Non-admins can fork repositories')),

        ('hg.register.none', _('Registration disabled')),
        ('hg.register.manual_activate', _('User registration with manual account activation')),
        ('hg.register.auto_activate', _('User registration with automatic account activation')),

        ('hg.extern_activate.manual', _('Manual activation of external account')),
        ('hg.extern_activate.auto', _('Automatic activation of external account')),
    )

    # definition of system default permissions for DEFAULT user
    DEFAULT_USER_PERMISSIONS = (
        'repository.read',
        'group.read',
        'usergroup.read',
        'hg.create.repository',
        'hg.create.write_on_repogroup.true',
        'hg.fork.repository',
        'hg.register.manual_activate',
        'hg.extern_activate.auto',
    )

    # defines which permissions are more important higher the more important
    # Weight defines which permissions are more important.
    # The higher number the more important.
    PERM_WEIGHTS = {
        'repository.none': 0,
        'repository.read': 1,
        'repository.write': 3,
        'repository.admin': 4,

        'group.none': 0,
        'group.read': 1,
        'group.write': 3,
        'group.admin': 4,

        'usergroup.none': 0,
        'usergroup.read': 1,
        'usergroup.write': 3,
        'usergroup.admin': 4,

        'hg.repogroup.create.false': 0,
        'hg.repogroup.create.true': 1,

        'hg.usergroup.create.false': 0,
        'hg.usergroup.create.true': 1,

        'hg.fork.none': 0,
        'hg.fork.repository': 1,

        'hg.create.none': 0,
        'hg.create.repository': 1,

        'hg.create.write_on_repogroup.false': 0,
        'hg.create.write_on_repogroup.true': 1,

        'hg.register.none': 0,
        'hg.register.manual_activate': 1,
        'hg.register.auto_activate': 2,

        'hg.extern_activate.manual': 0,
        'hg.extern_activate.auto': 1,
    }

    permission_id = Column(Integer(), primary_key=True)
    permission_name = Column(String(255), nullable=False)

    def __unicode__(self):
        return u"<%s('%s:%s')>" % (
            self.__class__.__name__, self.permission_id, self.permission_name
        )

    @classmethod
    def guess_instance(cls, value):
        return super(Permission, cls).guess_instance(value, Permission.get_by_key)

    @classmethod
    def get_by_key(cls, key):
        return cls.query().filter(cls.permission_name == key).scalar()

    @classmethod
    def get_default_perms(cls, default_user_id):
        q = Session().query(UserRepoToPerm, Repository, cls) \
         .join((Repository, UserRepoToPerm.repository_id == Repository.repo_id)) \
         .join((cls, UserRepoToPerm.permission_id == cls.permission_id)) \
         .filter(UserRepoToPerm.user_id == default_user_id)

        return q.all()

    @classmethod
    def get_default_group_perms(cls, default_user_id):
        q = Session().query(UserRepoGroupToPerm, RepoGroup, cls) \
         .join((RepoGroup, UserRepoGroupToPerm.group_id == RepoGroup.group_id)) \
         .join((cls, UserRepoGroupToPerm.permission_id == cls.permission_id)) \
         .filter(UserRepoGroupToPerm.user_id == default_user_id)

        return q.all()

    @classmethod
    def get_default_user_group_perms(cls, default_user_id):
        q = Session().query(UserUserGroupToPerm, UserGroup, cls) \
         .join((UserGroup, UserUserGroupToPerm.user_group_id == UserGroup.users_group_id)) \
         .join((cls, UserUserGroupToPerm.permission_id == cls.permission_id)) \
         .filter(UserUserGroupToPerm.user_id == default_user_id)

        return q.all()


class UserRepoToPerm(Base, BaseDbModel):
    __tablename__ = 'repo_to_perm'
    __table_args__ = (
        UniqueConstraint('user_id', 'repository_id', 'permission_id'),
        _table_args_default_dict,
    )

    repo_to_perm_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)
    repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)

    user = relationship('User')
    repository = relationship('Repository')
    permission = relationship('Permission')

    @classmethod
    def create(cls, user, repository, permission):
        n = cls()
        n.user = user
        n.repository = repository
        n.permission = permission
        Session().add(n)
        return n

    def __unicode__(self):
        return u'<%s => %s >' % (self.user, self.repository)


class UserUserGroupToPerm(Base, BaseDbModel):
    __tablename__ = 'user_user_group_to_perm'
    __table_args__ = (
        UniqueConstraint('user_id', 'user_group_id', 'permission_id'),
        _table_args_default_dict,
    )

    user_user_group_to_perm_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)
    user_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)

    user = relationship('User')
    user_group = relationship('UserGroup')
    permission = relationship('Permission')

    @classmethod
    def create(cls, user, user_group, permission):
        n = cls()
        n.user = user
        n.user_group = user_group
        n.permission = permission
        Session().add(n)
        return n

    def __unicode__(self):
        return u'<%s => %s >' % (self.user, self.user_group)


class UserToPerm(Base, BaseDbModel):
    __tablename__ = 'user_to_perm'
    __table_args__ = (
        UniqueConstraint('user_id', 'permission_id'),
        _table_args_default_dict,
    )

    user_to_perm_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)

    user = relationship('User')
    permission = relationship('Permission')

    def __unicode__(self):
        return u'<%s => %s >' % (self.user, self.permission)


class UserGroupRepoToPerm(Base, BaseDbModel):
    __tablename__ = 'users_group_repo_to_perm'
    __table_args__ = (
        UniqueConstraint('repository_id', 'users_group_id', 'permission_id'),
        _table_args_default_dict,
    )

    users_group_to_perm_id = Column(Integer(), primary_key=True)
    users_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)
    repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)

    users_group = relationship('UserGroup')
    permission = relationship('Permission')
    repository = relationship('Repository')

    @classmethod
    def create(cls, users_group, repository, permission):
        n = cls()
        n.users_group = users_group
        n.repository = repository
        n.permission = permission
        Session().add(n)
        return n

    def __unicode__(self):
        return u'<UserGroupRepoToPerm:%s => %s >' % (self.users_group, self.repository)


class UserGroupUserGroupToPerm(Base, BaseDbModel):
    __tablename__ = 'user_group_user_group_to_perm'
    __table_args__ = (
        UniqueConstraint('target_user_group_id', 'user_group_id', 'permission_id'),
        _table_args_default_dict,
    )

    user_group_user_group_to_perm_id = Column(Integer(), primary_key=True)
    target_user_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)
    user_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)

    target_user_group = relationship('UserGroup', primaryjoin='UserGroupUserGroupToPerm.target_user_group_id==UserGroup.users_group_id')
    user_group = relationship('UserGroup', primaryjoin='UserGroupUserGroupToPerm.user_group_id==UserGroup.users_group_id')
    permission = relationship('Permission')

    @classmethod
    def create(cls, target_user_group, user_group, permission):
        n = cls()
        n.target_user_group = target_user_group
        n.user_group = user_group
        n.permission = permission
        Session().add(n)
        return n

    def __unicode__(self):
        return u'<UserGroupUserGroup:%s => %s >' % (self.target_user_group, self.user_group)


class UserGroupToPerm(Base, BaseDbModel):
    __tablename__ = 'users_group_to_perm'
    __table_args__ = (
        UniqueConstraint('users_group_id', 'permission_id',),
        _table_args_default_dict,
    )

    users_group_to_perm_id = Column(Integer(), primary_key=True)
    users_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)

    users_group = relationship('UserGroup')
    permission = relationship('Permission')


class UserRepoGroupToPerm(Base, BaseDbModel):
    __tablename__ = 'user_repo_group_to_perm'
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', 'permission_id'),
        _table_args_default_dict,
    )

    group_to_perm_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    group_id = Column(Integer(), ForeignKey('groups.group_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)

    user = relationship('User')
    group = relationship('RepoGroup')
    permission = relationship('Permission')

    @classmethod
    def create(cls, user, repository_group, permission):
        n = cls()
        n.user = user
        n.group = repository_group
        n.permission = permission
        Session().add(n)
        return n


class UserGroupRepoGroupToPerm(Base, BaseDbModel):
    __tablename__ = 'users_group_repo_group_to_perm'
    __table_args__ = (
        UniqueConstraint('users_group_id', 'group_id'),
        _table_args_default_dict,
    )

    users_group_repo_group_to_perm_id = Column(Integer(), primary_key=True)
    users_group_id = Column(Integer(), ForeignKey('users_groups.users_group_id'), nullable=False)
    group_id = Column(Integer(), ForeignKey('groups.group_id'), nullable=False)
    permission_id = Column(Integer(), ForeignKey('permissions.permission_id'), nullable=False)

    users_group = relationship('UserGroup')
    permission = relationship('Permission')
    group = relationship('RepoGroup')

    @classmethod
    def create(cls, user_group, repository_group, permission):
        n = cls()
        n.users_group = user_group
        n.group = repository_group
        n.permission = permission
        Session().add(n)
        return n


class Statistics(Base, BaseDbModel):
    __tablename__ = 'statistics'
    __table_args__ = (
         _table_args_default_dict,
    )

    stat_id = Column(Integer(), primary_key=True)
    repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False, unique=True)
    stat_on_revision = Column(Integer(), nullable=False)
    commit_activity = Column(LargeBinary(1000000), nullable=False) # JSON data
    commit_activity_combined = Column(LargeBinary(), nullable=False) # JSON data
    languages = Column(LargeBinary(1000000), nullable=False) # JSON data

    repository = relationship('Repository', single_parent=True)


class UserFollowing(Base, BaseDbModel):
    __tablename__ = 'user_followings'
    __table_args__ = (
        UniqueConstraint('user_id', 'follows_repository_id', name='uq_user_followings_user_repo'),
        UniqueConstraint('user_id', 'follows_user_id', name='uq_user_followings_user_user'),
        _table_args_default_dict,
    )

    user_following_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    follows_repository_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=True)
    follows_user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=True)
    follows_from = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    user = relationship('User', primaryjoin='User.user_id==UserFollowing.user_id')

    follows_user = relationship('User', primaryjoin='User.user_id==UserFollowing.follows_user_id')
    follows_repository = relationship('Repository', order_by=lambda: func.lower(Repository.repo_name))

    @classmethod
    def get_repo_followers(cls, repo_id):
        return cls.query().filter(cls.follows_repository_id == repo_id)


class CacheInvalidation(Base, BaseDbModel):
    __tablename__ = 'cache_invalidation'
    __table_args__ = (
        Index('key_idx', 'cache_key'),
        _table_args_default_dict,
    )

    # cache_id, not used
    cache_id = Column(Integer(), primary_key=True)
    # cache_key as created by _get_cache_key
    cache_key = Column(Unicode(255), nullable=False, unique=True)
    # cache_args is a repo_name
    cache_args = Column(Unicode(255), nullable=False)
    # instance sets cache_active True when it is caching, other instances set
    # cache_active to False to indicate that this cache is invalid
    cache_active = Column(Boolean(), nullable=False, default=False)

    def __init__(self, cache_key, repo_name=''):
        self.cache_key = cache_key
        self.cache_args = repo_name
        self.cache_active = False

    def __unicode__(self):
        return u"<%s('%s:%s[%s]')>" % (
            self.__class__.__name__,
            self.cache_id, self.cache_key, self.cache_active)

    def _cache_key_partition(self):
        prefix, repo_name, suffix = self.cache_key.partition(self.cache_args)
        return prefix, repo_name, suffix

    def get_prefix(self):
        """
        get prefix that might have been used in _get_cache_key to
        generate self.cache_key. Only used for informational purposes
        in repo_edit.html.
        """
        # prefix, repo_name, suffix
        return self._cache_key_partition()[0]

    def get_suffix(self):
        """
        get suffix that might have been used in _get_cache_key to
        generate self.cache_key. Only used for informational purposes
        in repo_edit.html.
        """
        # prefix, repo_name, suffix
        return self._cache_key_partition()[2]

    @classmethod
    def clear_cache(cls):
        """
        Delete all cache keys from database.
        Should only be run when all instances are down and all entries thus stale.
        """
        cls.query().delete()
        Session().commit()

    @classmethod
    def _get_cache_key(cls, key):
        """
        Wrapper for generating a unique cache key for this instance and "key".
        key must / will start with a repo_name which will be stored in .cache_args .
        """
        prefix = kallithea.CONFIG.get('instance_id', '')
        return "%s%s" % (prefix, key)

    @classmethod
    def set_invalidate(cls, repo_name):
        """
        Mark all caches of a repo as invalid in the database.
        """
        inv_objs = Session().query(cls).filter(cls.cache_args == repo_name).all()
        log.debug('for repo %s got %s invalidation objects',
                  safe_str(repo_name), inv_objs)

        for inv_obj in inv_objs:
            log.debug('marking %s key for invalidation based on repo_name=%s',
                      inv_obj, safe_str(repo_name))
            Session().delete(inv_obj)
        Session().commit()

    @classmethod
    def test_and_set_valid(cls, repo_name, kind, valid_cache_keys=None):
        """
        Mark this cache key as active and currently cached.
        Return True if the existing cache registration still was valid.
        Return False to indicate that it had been invalidated and caches should be refreshed.
        """

        key = (repo_name + '_' + kind) if kind else repo_name
        cache_key = cls._get_cache_key(key)

        if valid_cache_keys and cache_key in valid_cache_keys:
            return True

        inv_obj = cls.query().filter(cls.cache_key == cache_key).scalar()
        if inv_obj is None:
            inv_obj = cls(cache_key, repo_name)
            Session().add(inv_obj)
        elif inv_obj.cache_active:
            return True
        inv_obj.cache_active = True
        try:
            Session().commit()
        except sqlalchemy.exc.IntegrityError:
            log.error('commit of CacheInvalidation failed - retrying')
            Session().rollback()
            inv_obj = cls.query().filter(cls.cache_key == cache_key).scalar()
            if inv_obj is None:
                log.error('failed to create CacheInvalidation entry')
                # TODO: fail badly?
            # else: TOCTOU - another thread added the key at the same time; no further action required
        return False

    @classmethod
    def get_valid_cache_keys(cls):
        """
        Return opaque object with information of which caches still are valid
        and can be used without checking for invalidation.
        """
        return set(inv_obj.cache_key for inv_obj in cls.query().filter(cls.cache_active).all())


class ChangesetComment(Base, BaseDbModel):
    __tablename__ = 'changeset_comments'
    __table_args__ = (
        Index('cc_revision_idx', 'revision'),
        Index('cc_pull_request_id_idx', 'pull_request_id'),
        _table_args_default_dict,
    )

    comment_id = Column(Integer(), primary_key=True)
    repo_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)
    revision = Column(String(40), nullable=True)
    pull_request_id = Column(Integer(), ForeignKey('pull_requests.pull_request_id'), nullable=True)
    line_no = Column(Unicode(10), nullable=True)
    f_path = Column(Unicode(1000), nullable=True)
    author_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    text = Column(UnicodeText(), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    modified_at = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    author = relationship('User')
    repo = relationship('Repository')
    # status_change is frequently used directly in templates - make it a lazy
    # join to avoid fetching each related ChangesetStatus on demand.
    # There will only be one ChangesetStatus referencing each comment so the join will not explode.
    status_change = relationship('ChangesetStatus',
                                 cascade="all, delete-orphan", lazy='joined')
    pull_request = relationship('PullRequest')

    def url(self):
        anchor = "comment-%s" % self.comment_id
        import kallithea.lib.helpers as h
        if self.revision:
            return h.url('changeset_home', repo_name=self.repo.repo_name, revision=self.revision, anchor=anchor)
        elif self.pull_request_id is not None:
            return self.pull_request.url(anchor=anchor)

    def __json__(self):
        return dict(
            comment_id=self.comment_id,
            username=self.author.username,
            text=self.text,
        )

    def deletable(self):
        return self.created_on > datetime.datetime.now() - datetime.timedelta(minutes=5)


class ChangesetStatus(Base, BaseDbModel):
    __tablename__ = 'changeset_statuses'
    __table_args__ = (
        Index('cs_revision_idx', 'revision'),
        Index('cs_version_idx', 'version'),
        Index('cs_pull_request_id_idx', 'pull_request_id'),
        Index('cs_changeset_comment_id_idx', 'changeset_comment_id'),
        Index('cs_pull_request_id_user_id_version_idx', 'pull_request_id', 'user_id', 'version'),
        Index('cs_repo_id_pull_request_id_idx', 'repo_id', 'pull_request_id'),
        UniqueConstraint('repo_id', 'revision', 'version'),
        _table_args_default_dict,
    )

    STATUS_NOT_REVIEWED = DEFAULT = 'not_reviewed'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected' # is shown as "Not approved" - TODO: change database content / scheme
    STATUS_UNDER_REVIEW = 'under_review'

    STATUSES = [
        (STATUS_NOT_REVIEWED, _("Not reviewed")),  # (no icon) and default
        (STATUS_UNDER_REVIEW, _("Under review")),
        (STATUS_REJECTED, _("Not approved")),
        (STATUS_APPROVED, _("Approved")),
    ]
    STATUSES_DICT = dict(STATUSES)

    changeset_status_id = Column(Integer(), primary_key=True)
    repo_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    revision = Column(String(40), nullable=True)
    status = Column(String(128), nullable=False, default=DEFAULT)
    comment_id = Column('changeset_comment_id', Integer(), ForeignKey('changeset_comments.comment_id'), nullable=False)
    modified_at = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    version = Column(Integer(), nullable=False, default=0)
    pull_request_id = Column(Integer(), ForeignKey('pull_requests.pull_request_id'), nullable=True)

    author = relationship('User')
    repo = relationship('Repository')
    comment = relationship('ChangesetComment')
    pull_request = relationship('PullRequest')

    def __unicode__(self):
        return u"<%s('%s:%s')>" % (
            self.__class__.__name__,
            self.status, self.author
        )

    @classmethod
    def get_status_lbl(cls, value):
        return cls.STATUSES_DICT.get(value)

    @property
    def status_lbl(self):
        return ChangesetStatus.get_status_lbl(self.status)

    def __json__(self):
        return dict(
            status=self.status,
            modified_at=self.modified_at.replace(microsecond=0),
            reviewer=self.author.username,
            )


class PullRequest(Base, BaseDbModel):
    __tablename__ = 'pull_requests'
    __table_args__ = (
        Index('pr_org_repo_id_idx', 'org_repo_id'),
        Index('pr_other_repo_id_idx', 'other_repo_id'),
        _table_args_default_dict,
    )

    # values for .status
    STATUS_NEW = u'new'
    STATUS_CLOSED = u'closed'

    pull_request_id = Column(Integer(), primary_key=True)
    title = Column(Unicode(255), nullable=False)
    description = Column(UnicodeText(), nullable=False)
    status = Column(Unicode(255), nullable=False, default=STATUS_NEW) # only for closedness, not approve/reject/etc
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    updated_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    owner_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    _revisions = Column('revisions', UnicodeText(), nullable=False)
    org_repo_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)
    org_ref = Column(Unicode(255), nullable=False)
    other_repo_id = Column(Integer(), ForeignKey('repositories.repo_id'), nullable=False)
    other_ref = Column(Unicode(255), nullable=False)

    @hybrid_property
    def revisions(self):
        return self._revisions.split(':')

    @revisions.setter
    def revisions(self, val):
        self._revisions = safe_unicode(':'.join(val))

    @property
    def org_ref_parts(self):
        return self.org_ref.split(':')

    @property
    def other_ref_parts(self):
        return self.other_ref.split(':')

    owner = relationship('User')
    reviewers = relationship('PullRequestReviewer',
                             cascade="all, delete-orphan")
    org_repo = relationship('Repository', primaryjoin='PullRequest.org_repo_id==Repository.repo_id')
    other_repo = relationship('Repository', primaryjoin='PullRequest.other_repo_id==Repository.repo_id')
    statuses = relationship('ChangesetStatus', order_by='ChangesetStatus.changeset_status_id')
    comments = relationship('ChangesetComment', order_by='ChangesetComment.comment_id',
                             cascade="all, delete-orphan")

    @classmethod
    def query(cls, reviewer_id=None, include_closed=True, sorted=False):
        """Add PullRequest-specific helpers for common query constructs.

        reviewer_id: only PRs with the specified user added as reviewer.

        include_closed: if False, do not include closed PRs.

        sorted: if True, apply the default ordering (newest first).
        """
        q = super(PullRequest, cls).query()

        if reviewer_id is not None:
            q = q.join(PullRequestReviewer).filter(PullRequestReviewer.user_id == reviewer_id)

        if not include_closed:
            q = q.filter(PullRequest.status != PullRequest.STATUS_CLOSED)

        if sorted:
            q = q.order_by(PullRequest.created_on.desc())

        return q

    def get_reviewer_users(self):
        """Like .reviewers, but actually returning the users"""
        return User.query() \
            .join(PullRequestReviewer) \
            .filter(PullRequestReviewer.pull_request == self) \
            .order_by(PullRequestReviewer.pull_request_reviewers_id) \
            .all()

    def is_closed(self):
        return self.status == self.STATUS_CLOSED

    def user_review_status(self, user_id):
        """Return the user's latest status votes on PR"""
        # note: no filtering on repo - that would be redundant
        status = ChangesetStatus.query() \
            .filter(ChangesetStatus.pull_request == self) \
            .filter(ChangesetStatus.user_id == user_id) \
            .order_by(ChangesetStatus.version) \
            .first()
        return str(status.status) if status else ''

    @classmethod
    def make_nice_id(cls, pull_request_id):
        '''Return pull request id nicely formatted for displaying'''
        return '#%s' % pull_request_id

    def nice_id(self):
        '''Return the id of this pull request, nicely formatted for displaying'''
        return self.make_nice_id(self.pull_request_id)

    def get_api_data(self):
        return self.__json__()

    def __json__(self):
        clone_uri_tmpl = kallithea.CONFIG.get('clone_uri_tmpl') or Repository.DEFAULT_CLONE_URI
        return dict(
            pull_request_id=self.pull_request_id,
            url=self.url(),
            reviewers=self.reviewers,
            revisions=self.revisions,
            owner=self.owner.username,
            title=self.title,
            description=self.description,
            org_repo_url=self.org_repo.clone_url(clone_uri_tmpl=clone_uri_tmpl),
            org_ref_parts=self.org_ref_parts,
            other_ref_parts=self.other_ref_parts,
            status=self.status,
            comments=self.comments,
            statuses=self.statuses,
        )

    def url(self, **kwargs):
        canonical = kwargs.pop('canonical', None)
        import kallithea.lib.helpers as h
        b = self.org_ref_parts[1]
        if b != self.other_ref_parts[1]:
            s = '/_/' + b
        else:
            s = '/_/' + self.title
        kwargs['extra'] = urlreadable(s)
        if canonical:
            return h.canonical_url('pullrequest_show', repo_name=self.other_repo.repo_name,
                                   pull_request_id=self.pull_request_id, **kwargs)
        return h.url('pullrequest_show', repo_name=self.other_repo.repo_name,
                     pull_request_id=self.pull_request_id, **kwargs)


class PullRequestReviewer(Base, BaseDbModel):
    __tablename__ = 'pull_request_reviewers'
    __table_args__ = (
        Index('pull_request_reviewers_user_id_idx', 'user_id'),
        _table_args_default_dict,
    )

    def __init__(self, user=None, pull_request=None):
        self.user = user
        self.pull_request = pull_request

    pull_request_reviewers_id = Column('pull_requests_reviewers_id', Integer(), primary_key=True)
    pull_request_id = Column(Integer(), ForeignKey('pull_requests.pull_request_id'), nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)

    user = relationship('User')
    pull_request = relationship('PullRequest')

    def __json__(self):
        return dict(
            username=self.user.username if self.user else None,
        )


class Notification(object):
    __tablename__ = 'notifications'

class UserNotification(object):
    __tablename__ = 'user_to_notification'


class Gist(Base, BaseDbModel):
    __tablename__ = 'gists'
    __table_args__ = (
        Index('g_gist_access_id_idx', 'gist_access_id'),
        Index('g_created_on_idx', 'created_on'),
        _table_args_default_dict,
    )

    GIST_PUBLIC = u'public'
    GIST_PRIVATE = u'private'
    DEFAULT_FILENAME = u'gistfile1.txt'

    gist_id = Column(Integer(), primary_key=True)
    gist_access_id = Column(Unicode(250), nullable=False)
    gist_description = Column(UnicodeText(), nullable=False)
    owner_id = Column('user_id', Integer(), ForeignKey('users.user_id'), nullable=False)
    gist_expires = Column(Float(53), nullable=False)
    gist_type = Column(Unicode(128), nullable=False)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    modified_at = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)

    owner = relationship('User')

    @hybrid_property
    def is_expired(self):
        return (self.gist_expires != -1) & (time.time() > self.gist_expires)

    def __repr__(self):
        return '<Gist:[%s]%s>' % (self.gist_type, self.gist_access_id)

    @classmethod
    def guess_instance(cls, value):
        return super(Gist, cls).guess_instance(value, Gist.get_by_access_id)

    @classmethod
    def get_or_404(cls, id_):
        res = cls.query().filter(cls.gist_access_id == id_).scalar()
        if res is None:
            raise HTTPNotFound
        return res

    @classmethod
    def get_by_access_id(cls, gist_access_id):
        return cls.query().filter(cls.gist_access_id == gist_access_id).scalar()

    def gist_url(self):
        alias_url = kallithea.CONFIG.get('gist_alias_url')
        if alias_url:
            return alias_url.replace('{gistid}', self.gist_access_id)

        import kallithea.lib.helpers as h
        return h.canonical_url('gist', gist_id=self.gist_access_id)

    @classmethod
    def base_path(cls):
        """
        Returns base path where all gists are stored

        :param cls:
        """
        from kallithea.model.gist import GIST_STORE_LOC
        q = Session().query(Ui) \
            .filter(Ui.ui_key == URL_SEP)
        q = q.options(FromCache("sql_cache_short", "repository_repo_path"))
        return os.path.join(q.one().ui_value, GIST_STORE_LOC)

    def get_api_data(self):
        """
        Common function for generating gist related data for API
        """
        gist = self
        data = dict(
            gist_id=gist.gist_id,
            type=gist.gist_type,
            access_id=gist.gist_access_id,
            description=gist.gist_description,
            url=gist.gist_url(),
            expires=gist.gist_expires,
            created_on=gist.created_on,
        )
        return data

    def __json__(self):
        data = dict(
        )
        data.update(self.get_api_data())
        return data
    ## SCM functions

    @property
    def scm_instance(self):
        from kallithea.lib.vcs import get_repo
        base_path = self.base_path()
        return get_repo(os.path.join(*map(safe_str,
                                          [base_path, self.gist_access_id])))


class UserSshKeys(Base, BaseDbModel):
    __tablename__ = 'user_ssh_keys'
    __table_args__ = (
        Index('usk_fingerprint_idx', 'fingerprint'),
        UniqueConstraint('fingerprint'),
        _table_args_default_dict
    )
    __mapper_args__ = {}

    user_ssh_key_id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    _public_key = Column('public_key', UnicodeText(), nullable=False)
    description = Column(UnicodeText(), nullable=False)
    fingerprint = Column(String(255), nullable=False, unique=True)
    created_on = Column(DateTime(timezone=False), nullable=False, default=datetime.datetime.now)
    last_seen = Column(DateTime(timezone=False), nullable=True)

    user = relationship('User')

    @property
    def public_key(self):
        return self._public_key

    @public_key.setter
    def public_key(self, full_key):
        # the full public key is too long to be suitable as database key - instead,
        # use fingerprints similar to 'ssh-keygen -E sha256 -lf ~/.ssh/id_rsa.pub'
        self._public_key = full_key
        enc_key = full_key.split(" ")[1]
        self.fingerprint = hashlib.sha256(enc_key.decode('base64')).digest().encode('base64').replace('\n', '').rstrip('=')
