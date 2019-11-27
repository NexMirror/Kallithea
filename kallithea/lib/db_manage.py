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
kallithea.lib.db_manage
~~~~~~~~~~~~~~~~~~~~~~~

Database creation, and setup module for Kallithea. Used for creation
of database as well as for migration operations

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 10, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import print_function

import logging
import os
import sys
import uuid

import alembic.command
import alembic.config
import sqlalchemy
from sqlalchemy.engine import create_engine

from kallithea.model.base import init_model
from kallithea.model.db import Permission, RepoGroup, Repository, Setting, Ui, User, UserRepoGroupToPerm, UserToPerm
#from kallithea.model import meta
from kallithea.model.meta import Base, Session
from kallithea.model.permission import PermissionModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.user import UserModel


log = logging.getLogger(__name__)


class DbManage(object):
    def __init__(self, dbconf, root, tests=False, SESSION=None, cli_args=None):
        self.dbname = dbconf.split('/')[-1]
        self.tests = tests
        self.root = root
        self.dburi = dbconf
        self.db_exists = False
        self.cli_args = cli_args or {}
        self.init_db(SESSION=SESSION)

    def _ask_ok(self, msg):
        """Invoke ask_ok unless the force_ask option provides the answer"""
        force_ask = self.cli_args.get('force_ask')
        if force_ask is not None:
            return force_ask
        from kallithea.lib.utils2 import ask_ok
        return ask_ok(msg)

    def init_db(self, SESSION=None):
        if SESSION:
            self.sa = SESSION
        else:
            # init new sessions
            engine = create_engine(self.dburi)
            init_model(engine)
            self.sa = Session()

    def create_tables(self, override=False):
        """
        Create a auth database
        """

        log.info("Any existing database is going to be destroyed")
        if self.tests:
            destroy = True
        else:
            destroy = self._ask_ok('Are you sure to destroy old database ? [y/n]')
        if not destroy:
            print('Nothing done.')
            sys.exit(0)
        if destroy:
            # drop and re-create old schemas

            url = sqlalchemy.engine.url.make_url(self.dburi)
            database = url.database

            # Some databases enforce foreign key constraints and Base.metadata.drop_all() doesn't work
            if url.drivername == 'mysql':
                url.database = None  # don't connect to the database (it might not exist)
                engine = sqlalchemy.create_engine(url)
                with engine.connect() as conn:
                    conn.execute('DROP DATABASE IF EXISTS ' + database)
                    conn.execute('CREATE DATABASE ' + database)
            elif url.drivername == 'postgresql':
                from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                url.database = 'postgres'  # connect to the system database (as the real one might not exist)
                engine = sqlalchemy.create_engine(url)
                with engine.connect() as conn:
                    conn.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    conn.execute('DROP DATABASE IF EXISTS ' + database)
                    conn.execute('CREATE DATABASE ' + database)
            else:
                # known to work on SQLite - possibly not on other databases with strong referential integrity
                Base.metadata.drop_all()

        checkfirst = not override
        Base.metadata.create_all(checkfirst=checkfirst)

        # Create an Alembic configuration and generate the version table,
        # "stamping" it with the most recent Alembic migration revision, to
        # tell Alembic that all the schema upgrades are already in effect.
        alembic_cfg = alembic.config.Config()
        alembic_cfg.set_main_option('script_location', 'kallithea:alembic')
        alembic_cfg.set_main_option('sqlalchemy.url', self.dburi)
        # This command will give an error in an Alembic multi-head scenario,
        # but in practice, such a scenario should not come up during database
        # creation, even during development.
        alembic.command.stamp(alembic_cfg, 'head')

        log.info('Created tables for %s', self.dbname)

    def fix_repo_paths(self):
        """
        Fixes a old kallithea version path into new one without a '*'
        """

        paths = Ui.query() \
                .filter(Ui.ui_key == '/') \
                .scalar()

        paths.ui_value = paths.ui_value.replace('*', '')

        self.sa.commit()

    def fix_default_user(self):
        """
        Fixes a old default user with some 'nicer' default values,
        used mostly for anonymous access
        """
        def_user = User.query().filter_by(is_default_user=True).one()

        def_user.name = 'Anonymous'
        def_user.lastname = 'User'
        def_user.email = 'anonymous@kallithea-scm.org'

        self.sa.commit()

    def fix_settings(self):
        """
        Fixes kallithea settings adds ga_code key for google analytics
        """

        hgsettings3 = Setting('ga_code', '')

        self.sa.add(hgsettings3)
        self.sa.commit()

    def admin_prompt(self, second=False):
        if not self.tests:
            import getpass

            username = self.cli_args.get('username')
            password = self.cli_args.get('password')
            email = self.cli_args.get('email')

            def get_password():
                password = getpass.getpass('Specify admin password '
                                           '(min 6 chars):')
                confirm = getpass.getpass('Confirm password:')

                if password != confirm:
                    log.error('passwords mismatch')
                    return False
                if len(password) < 6:
                    log.error('password is to short use at least 6 characters')
                    return False

                return password
            if username is None:
                username = raw_input('Specify admin username:')
            if password is None:
                password = get_password()
                if not password:
                    # second try
                    password = get_password()
                    if not password:
                        sys.exit()
            if email is None:
                email = raw_input('Specify admin email:')
            self.create_user(username, password, email, True)
        else:
            log.info('creating admin and regular test users')
            from kallithea.tests.base import TEST_USER_ADMIN_LOGIN, \
                TEST_USER_ADMIN_PASS, TEST_USER_ADMIN_EMAIL, \
                TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS, \
                TEST_USER_REGULAR_EMAIL, TEST_USER_REGULAR2_LOGIN, \
                TEST_USER_REGULAR2_PASS, TEST_USER_REGULAR2_EMAIL

            self.create_user(TEST_USER_ADMIN_LOGIN, TEST_USER_ADMIN_PASS,
                             TEST_USER_ADMIN_EMAIL, True)

            self.create_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS,
                             TEST_USER_REGULAR_EMAIL, False)

            self.create_user(TEST_USER_REGULAR2_LOGIN, TEST_USER_REGULAR2_PASS,
                             TEST_USER_REGULAR2_EMAIL, False)

    def create_auth_plugin_options(self, skip_existing=False):
        """
        Create default auth plugin settings, and make it active

        :param skip_existing:
        """

        for k, v, t in [('auth_plugins', 'kallithea.lib.auth_modules.auth_internal', 'list'),
                        ('auth_internal_enabled', 'True', 'bool')]:
            if skip_existing and Setting.get_by_name(k) is not None:
                log.debug('Skipping option %s', k)
                continue
            setting = Setting(k, v, t)
            self.sa.add(setting)

    def create_default_options(self, skip_existing=False):
        """Creates default settings"""

        for k, v, t in [
            ('default_repo_enable_downloads', False, 'bool'),
            ('default_repo_enable_statistics', False, 'bool'),
            ('default_repo_private', False, 'bool'),
            ('default_repo_type', 'hg', 'unicode')
        ]:
            if skip_existing and Setting.get_by_name(k) is not None:
                log.debug('Skipping option %s', k)
                continue
            setting = Setting(k, v, t)
            self.sa.add(setting)

    def fixup_groups(self):
        def_usr = User.get_default_user()
        for g in RepoGroup.query().all():
            g.group_name = g.get_new_name(g.name)
            # get default perm
            default = UserRepoGroupToPerm.query() \
                .filter(UserRepoGroupToPerm.group == g) \
                .filter(UserRepoGroupToPerm.user == def_usr) \
                .scalar()

            if default is None:
                log.debug('missing default permission for group %s adding', g)
                RepoGroupModel()._create_default_perms(g)

    def reset_permissions(self, username):
        """
        Resets permissions to default state, useful when old systems had
        bad permissions, we must clean them up

        :param username:
        """
        default_user = User.get_by_username(username)
        if not default_user:
            return

        u2p = UserToPerm.query() \
            .filter(UserToPerm.user == default_user).all()
        fixed = False
        if len(u2p) != len(Permission.DEFAULT_USER_PERMISSIONS):
            for p in u2p:
                Session().delete(p)
            fixed = True
            self.populate_default_permissions()
        return fixed

    def update_repo_info(self):
        for repo in Repository.query():
            repo.update_changeset_cache()

    def prompt_repo_root_path(self, test_repo_path='', retries=3):
        _path = self.cli_args.get('repos_location')
        if retries == 3:
            log.info('Setting up repositories config')

        if _path is not None:
            path = _path
        elif not self.tests and not test_repo_path:
            path = raw_input(
                 'Enter a valid absolute path to store repositories. '
                 'All repositories in that path will be added automatically:'
            )
        else:
            path = test_repo_path
        path_ok = True

        # check proper dir
        if not os.path.isdir(path):
            path_ok = False
            log.error('Given path %s is not a valid directory', path)

        elif not os.path.isabs(path):
            path_ok = False
            log.error('Given path %s is not an absolute path', path)

        # check if path is at least readable.
        if not os.access(path, os.R_OK):
            path_ok = False
            log.error('Given path %s is not readable', path)

        # check write access, warn user about non writeable paths
        elif not os.access(path, os.W_OK) and path_ok:
            log.warning('No write permission to given path %s', path)
            if not self._ask_ok('Given path %s is not writeable, do you want to '
                          'continue with read only mode ? [y/n]' % (path,)):
                log.error('Canceled by user')
                sys.exit(-1)

        if retries == 0:
            sys.exit('max retries reached')
        if not path_ok:
            if _path is not None:
                sys.exit('Invalid repo path: %s' % _path)
            retries -= 1
            return self.prompt_repo_root_path(test_repo_path, retries) # recursing!!!

        real_path = os.path.normpath(os.path.realpath(path))

        if real_path != os.path.normpath(path):
            log.warning('Using normalized path %s instead of %s', real_path, path)

        return real_path

    def create_settings(self, repo_root_path):
        ui_config = [
            ('paths', '/', repo_root_path, True),
            #('phases', 'publish', 'false', False)
            ('hooks', Ui.HOOK_UPDATE, 'hg update >&2', False),
            ('hooks', Ui.HOOK_REPO_SIZE, 'python:kallithea.lib.hooks.repo_size', True),
            ('extensions', 'largefiles', '', True),
            ('largefiles', 'usercache', os.path.join(repo_root_path, '.cache', 'largefiles'), True),
            ('extensions', 'hgsubversion', '', False),
            ('extensions', 'hggit', '', False),
        ]
        for ui_section, ui_key, ui_value, ui_active in ui_config:
            ui_conf = Ui(
                ui_section=ui_section,
                ui_key=ui_key,
                ui_value=ui_value,
                ui_active=ui_active)
            self.sa.add(ui_conf)

        settings = [
            ('realm', 'Kallithea', 'unicode'),
            ('title', '', 'unicode'),
            ('ga_code', '', 'unicode'),
            ('show_public_icon', True, 'bool'),
            ('show_private_icon', True, 'bool'),
            ('stylify_metalabels', False, 'bool'),
            ('dashboard_items', 100, 'int'), # TODO: call it page_size
            ('admin_grid_items', 25, 'int'),
            ('show_version', True, 'bool'),
            ('use_gravatar', True, 'bool'),
            ('gravatar_url', User.DEFAULT_GRAVATAR_URL, 'unicode'),
            ('clone_uri_tmpl', Repository.DEFAULT_CLONE_URI, 'unicode'),
            ('clone_ssh_tmpl', Repository.DEFAULT_CLONE_SSH, 'unicode'),
        ]
        for key, val, type_ in settings:
            sett = Setting(key, val, type_)
            self.sa.add(sett)

        self.create_auth_plugin_options()
        self.create_default_options()

        log.info('Populated Ui and Settings defaults')

    def create_user(self, username, password, email='', admin=False):
        log.info('creating user %s', username)
        UserModel().create_or_update(username, password, email,
                                     firstname=u'Kallithea', lastname=u'Admin',
                                     active=True, admin=admin,
                                     extern_type=User.DEFAULT_AUTH_TYPE)

    def create_default_user(self):
        log.info('creating default user')
        # create default user for handling default permissions.
        user = UserModel().create_or_update(username=User.DEFAULT_USER,
                                            password=str(uuid.uuid1())[:20],
                                            email='anonymous@kallithea-scm.org',
                                            firstname=u'Anonymous',
                                            lastname=u'User')
        # based on configuration options activate/deactivate this user which
        # controls anonymous access
        if self.cli_args.get('public_access') is False:
            log.info('Public access disabled')
            user.active = False
            Session().commit()

    def create_permissions(self):
        """
        Creates all permissions defined in the system
        """
        # module.(access|create|change|delete)_[name]
        # module.(none|read|write|admin)
        log.info('creating permissions')
        PermissionModel().create_permissions()

    def populate_default_permissions(self):
        """
        Populate default permissions. It will create only the default
        permissions that are missing, and not alter already defined ones
        """
        log.info('creating default user permissions')
        PermissionModel().create_default_permissions(user=User.DEFAULT_USER)
