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
Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""

import routes
from tg import request

from kallithea.lib.utils2 import safe_str


# prefix for non repository related links needs to be prefixed with `/`
ADMIN_PREFIX = '/_admin'


class Mapper(routes.Mapper):
    """
    Subclassed Mapper with routematch patched to decode "unicode" str url to
    *real* unicode str before applying matches and invoking controller methods.
    """

    def routematch(self, url=None, environ=None):
        """
        routematch that also decode url from "fake bytes" to real unicode
        string before matching and invoking controllers.
        """
        # Process url like get_path_info does ... but PATH_INFO has already
        # been retrieved from environ and is passed, so - let's just use that
        # instead.
        url = safe_str(url.encode('latin1'))
        return super().routematch(url=url, environ=environ)


def make_map(config):
    """Create, configure and return the routes Mapper"""
    rmap = Mapper(directory=config['paths']['controllers'],
                  always_scan=config['debug'])
    rmap.minimization = False
    rmap.explicit = False

    from kallithea.lib.utils import is_valid_repo, is_valid_repo_group

    def check_repo(environ, match_dict):
        """
        Check for valid repository for proper 404 handling.
        Also, a bit of side effect modifying match_dict ...
        """
        if match_dict.get('f_path'):
            # fix for multiple initial slashes that causes errors
            match_dict['f_path'] = match_dict['f_path'].lstrip('/')

        return is_valid_repo(match_dict['repo_name'], config['base_path'])

    def check_group(environ, match_dict):
        """
        check for valid repository group for proper 404 handling

        :param environ:
        :param match_dict:
        """
        repo_group_name = match_dict.get('group_name')
        return is_valid_repo_group(repo_group_name, config['base_path'])

    def check_group_skip_path(environ, match_dict):
        """
        check for valid repository group for proper 404 handling, but skips
        verification of existing path

        :param environ:
        :param match_dict:
        """
        repo_group_name = match_dict.get('group_name')
        return is_valid_repo_group(repo_group_name, config['base_path'],
                                   skip_path_check=True)

    def check_user_group(environ, match_dict):
        """
        check for valid user group for proper 404 handling

        :param environ:
        :param match_dict:
        """
        return True

    def check_int(environ, match_dict):
        return match_dict.get('id').isdigit()

    #==========================================================================
    # CUSTOM ROUTES HERE
    #==========================================================================

    # MAIN PAGE
    rmap.connect('home', '/', controller='home')
    rmap.connect('about', '/about', controller='home', action='about')
    rmap.redirect('/favicon.ico', '/images/favicon.ico')
    rmap.connect('repo_switcher_data', '/_repos', controller='home',
                 action='repo_switcher_data')
    rmap.connect('users_and_groups_data', '/_users_and_groups', controller='home',
                 action='users_and_groups_data')

    rmap.connect('rst_help',
                 "http://docutils.sourceforge.net/docs/user/rst/quickref.html",
                 _static=True)
    rmap.connect('kallithea_project_url', "https://kallithea-scm.org/", _static=True)
    rmap.connect('issues_url', 'https://bitbucket.org/conservancy/kallithea/issues', _static=True)

    # ADMIN REPOSITORY ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/repos') as m:
        m.connect("repos", "/repos",
                  action="create", conditions=dict(method=["POST"]))
        m.connect("repos", "/repos",
                  conditions=dict(method=["GET"]))
        m.connect("new_repo", "/create_repository",
                  action="create_repository", conditions=dict(method=["GET"]))
        m.connect("update_repo", "/repos/{repo_name:.*?}",
                  action="update", conditions=dict(method=["POST"],
                  function=check_repo))
        m.connect("delete_repo", "/repos/{repo_name:.*?}/delete",
                  action="delete", conditions=dict(method=["POST"]))

    # ADMIN REPOSITORY GROUPS ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/repo_groups') as m:
        m.connect("repos_groups", "/repo_groups",
                  action="create", conditions=dict(method=["POST"]))
        m.connect("repos_groups", "/repo_groups",
                  conditions=dict(method=["GET"]))
        m.connect("new_repos_group", "/repo_groups/new",
                  action="new", conditions=dict(method=["GET"]))
        m.connect("update_repos_group", "/repo_groups/{group_name:.*?}",
                  action="update", conditions=dict(method=["POST"],
                                                   function=check_group))

        m.connect("repos_group", "/repo_groups/{group_name:.*?}",
                  action="show", conditions=dict(method=["GET"],
                                                 function=check_group))

        # EXTRAS REPO GROUP ROUTES
        m.connect("edit_repo_group", "/repo_groups/{group_name:.*?}/edit",
                  action="edit",
                  conditions=dict(method=["GET"], function=check_group))

        m.connect("edit_repo_group_advanced", "/repo_groups/{group_name:.*?}/edit/advanced",
                  action="edit_repo_group_advanced",
                  conditions=dict(method=["GET"], function=check_group))

        m.connect("edit_repo_group_perms", "/repo_groups/{group_name:.*?}/edit/permissions",
                  action="edit_repo_group_perms",
                  conditions=dict(method=["GET"], function=check_group))
        m.connect("edit_repo_group_perms_update", "/repo_groups/{group_name:.*?}/edit/permissions",
                  action="update_perms",
                  conditions=dict(method=["POST"], function=check_group))
        m.connect("edit_repo_group_perms_delete", "/repo_groups/{group_name:.*?}/edit/permissions/delete",
                  action="delete_perms",
                  conditions=dict(method=["POST"], function=check_group))

        m.connect("delete_repo_group", "/repo_groups/{group_name:.*?}/delete",
                  action="delete", conditions=dict(method=["POST"],
                                                   function=check_group_skip_path))

    # ADMIN USER ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/users') as m:
        m.connect("new_user", "/users/new",
                  action="create", conditions=dict(method=["POST"]))
        m.connect("users", "/users",
                  conditions=dict(method=["GET"]))
        m.connect("formatted_users", "/users.{format}",
                  conditions=dict(method=["GET"]))
        m.connect("new_user", "/users/new",
                  action="new", conditions=dict(method=["GET"]))
        m.connect("update_user", "/users/{id}",
                  action="update", conditions=dict(method=["POST"]))
        m.connect("delete_user", "/users/{id}/delete",
                  action="delete", conditions=dict(method=["POST"]))
        m.connect("edit_user", "/users/{id}/edit",
                  action="edit", conditions=dict(method=["GET"]))

        # EXTRAS USER ROUTES
        m.connect("edit_user_advanced", "/users/{id}/edit/advanced",
                  action="edit_advanced", conditions=dict(method=["GET"]))

        m.connect("edit_user_api_keys", "/users/{id}/edit/api_keys",
                  action="edit_api_keys", conditions=dict(method=["GET"]))
        m.connect("edit_user_api_keys_update", "/users/{id}/edit/api_keys",
                  action="add_api_key", conditions=dict(method=["POST"]))
        m.connect("edit_user_api_keys_delete", "/users/{id}/edit/api_keys/delete",
                  action="delete_api_key", conditions=dict(method=["POST"]))

        m.connect("edit_user_ssh_keys", "/users/{id}/edit/ssh_keys",
                  action="edit_ssh_keys", conditions=dict(method=["GET"]))
        m.connect("edit_user_ssh_keys", "/users/{id}/edit/ssh_keys",
                  action="ssh_keys_add", conditions=dict(method=["POST"]))
        m.connect("edit_user_ssh_keys_delete", "/users/{id}/edit/ssh_keys/delete",
                  action="ssh_keys_delete", conditions=dict(method=["POST"]))

        m.connect("edit_user_perms", "/users/{id}/edit/permissions",
                  action="edit_perms", conditions=dict(method=["GET"]))
        m.connect("edit_user_perms_update", "/users/{id}/edit/permissions",
                  action="update_perms", conditions=dict(method=["POST"]))

        m.connect("edit_user_emails", "/users/{id}/edit/emails",
                  action="edit_emails", conditions=dict(method=["GET"]))
        m.connect("edit_user_emails_update", "/users/{id}/edit/emails",
                  action="add_email", conditions=dict(method=["POST"]))
        m.connect("edit_user_emails_delete", "/users/{id}/edit/emails/delete",
                  action="delete_email", conditions=dict(method=["POST"]))

        m.connect("edit_user_ips", "/users/{id}/edit/ips",
                  action="edit_ips", conditions=dict(method=["GET"]))
        m.connect("edit_user_ips_update", "/users/{id}/edit/ips",
                  action="add_ip", conditions=dict(method=["POST"]))
        m.connect("edit_user_ips_delete", "/users/{id}/edit/ips/delete",
                  action="delete_ip", conditions=dict(method=["POST"]))

    # ADMIN USER GROUPS REST ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/user_groups') as m:
        m.connect("users_groups", "/user_groups",
                  action="create", conditions=dict(method=["POST"]))
        m.connect("users_groups", "/user_groups",
                  conditions=dict(method=["GET"]))
        m.connect("new_users_group", "/user_groups/new",
                  action="new", conditions=dict(method=["GET"]))
        m.connect("update_users_group", "/user_groups/{id}",
                  action="update", conditions=dict(method=["POST"]))
        m.connect("delete_users_group", "/user_groups/{id}/delete",
                  action="delete", conditions=dict(method=["POST"]))
        m.connect("edit_users_group", "/user_groups/{id}/edit",
                  action="edit", conditions=dict(method=["GET"]),
                  function=check_user_group)

        # EXTRAS USER GROUP ROUTES
        m.connect("edit_user_group_default_perms", "/user_groups/{id}/edit/default_perms",
                  action="edit_default_perms", conditions=dict(method=["GET"]))
        m.connect("edit_user_group_default_perms_update", "/user_groups/{id}/edit/default_perms",
                  action="update_default_perms", conditions=dict(method=["POST"]))

        m.connect("edit_user_group_perms", "/user_groups/{id}/edit/perms",
                  action="edit_perms", conditions=dict(method=["GET"]))
        m.connect("edit_user_group_perms_update", "/user_groups/{id}/edit/perms",
                  action="update_perms", conditions=dict(method=["POST"]))
        m.connect("edit_user_group_perms_delete", "/user_groups/{id}/edit/perms/delete",
                  action="delete_perms", conditions=dict(method=["POST"]))

        m.connect("edit_user_group_advanced", "/user_groups/{id}/edit/advanced",
                  action="edit_advanced", conditions=dict(method=["GET"]))

        m.connect("edit_user_group_members", "/user_groups/{id}/edit/members",
                  action="edit_members", conditions=dict(method=["GET"]))

    # ADMIN PERMISSIONS ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/permissions') as m:
        m.connect("admin_permissions", "/permissions",
                  action="permission_globals", conditions=dict(method=["POST"]))
        m.connect("admin_permissions", "/permissions",
                  action="permission_globals", conditions=dict(method=["GET"]))

        m.connect("admin_permissions_ips", "/permissions/ips",
                  action="permission_ips", conditions=dict(method=["GET"]))

        m.connect("admin_permissions_perms", "/permissions/perms",
                  action="permission_perms", conditions=dict(method=["GET"]))

    # ADMIN DEFAULTS ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/defaults') as m:
        m.connect('defaults', '/defaults')
        m.connect('defaults_update', 'defaults/{id}/update',
                  action="update", conditions=dict(method=["POST"]))

    # ADMIN AUTH SETTINGS
    rmap.connect('auth_settings', '%s/auth' % ADMIN_PREFIX,
                 controller='admin/auth_settings', action='auth_settings',
                 conditions=dict(method=["POST"]))
    rmap.connect('auth_home', '%s/auth' % ADMIN_PREFIX,
                 controller='admin/auth_settings')

    # ADMIN SETTINGS ROUTES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/settings') as m:
        m.connect("admin_settings", "/settings",
                  action="settings_vcs", conditions=dict(method=["POST"]))
        m.connect("admin_settings", "/settings",
                  action="settings_vcs", conditions=dict(method=["GET"]))

        m.connect("admin_settings_mapping", "/settings/mapping",
                  action="settings_mapping", conditions=dict(method=["POST"]))
        m.connect("admin_settings_mapping", "/settings/mapping",
                  action="settings_mapping", conditions=dict(method=["GET"]))

        m.connect("admin_settings_global", "/settings/global",
                  action="settings_global", conditions=dict(method=["POST"]))
        m.connect("admin_settings_global", "/settings/global",
                  action="settings_global", conditions=dict(method=["GET"]))

        m.connect("admin_settings_visual", "/settings/visual",
                  action="settings_visual", conditions=dict(method=["POST"]))
        m.connect("admin_settings_visual", "/settings/visual",
                  action="settings_visual", conditions=dict(method=["GET"]))

        m.connect("admin_settings_email", "/settings/email",
                  action="settings_email", conditions=dict(method=["POST"]))
        m.connect("admin_settings_email", "/settings/email",
                  action="settings_email", conditions=dict(method=["GET"]))

        m.connect("admin_settings_hooks", "/settings/hooks",
                  action="settings_hooks", conditions=dict(method=["POST"]))
        m.connect("admin_settings_hooks_delete", "/settings/hooks/delete",
                  action="settings_hooks", conditions=dict(method=["POST"]))
        m.connect("admin_settings_hooks", "/settings/hooks",
                  action="settings_hooks", conditions=dict(method=["GET"]))

        m.connect("admin_settings_search", "/settings/search",
                  action="settings_search", conditions=dict(method=["POST"]))
        m.connect("admin_settings_search", "/settings/search",
                  action="settings_search", conditions=dict(method=["GET"]))

        m.connect("admin_settings_system", "/settings/system",
                  action="settings_system", conditions=dict(method=["POST"]))
        m.connect("admin_settings_system", "/settings/system",
                  action="settings_system", conditions=dict(method=["GET"]))

    # ADMIN MY ACCOUNT
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/my_account') as m:

        m.connect("my_account", "/my_account",
                  action="my_account", conditions=dict(method=["GET"]))
        m.connect("my_account", "/my_account",
                  action="my_account", conditions=dict(method=["POST"]))

        m.connect("my_account_password", "/my_account/password",
                  action="my_account_password", conditions=dict(method=["GET"]))
        m.connect("my_account_password", "/my_account/password",
                  action="my_account_password", conditions=dict(method=["POST"]))

        m.connect("my_account_repos", "/my_account/repos",
                  action="my_account_repos", conditions=dict(method=["GET"]))

        m.connect("my_account_watched", "/my_account/watched",
                  action="my_account_watched", conditions=dict(method=["GET"]))

        m.connect("my_account_perms", "/my_account/perms",
                  action="my_account_perms", conditions=dict(method=["GET"]))

        m.connect("my_account_emails", "/my_account/emails",
                  action="my_account_emails", conditions=dict(method=["GET"]))
        m.connect("my_account_emails", "/my_account/emails",
                  action="my_account_emails_add", conditions=dict(method=["POST"]))
        m.connect("my_account_emails_delete", "/my_account/emails/delete",
                  action="my_account_emails_delete", conditions=dict(method=["POST"]))

        m.connect("my_account_api_keys", "/my_account/api_keys",
                  action="my_account_api_keys", conditions=dict(method=["GET"]))
        m.connect("my_account_api_keys", "/my_account/api_keys",
                  action="my_account_api_keys_add", conditions=dict(method=["POST"]))
        m.connect("my_account_api_keys_delete", "/my_account/api_keys/delete",
                  action="my_account_api_keys_delete", conditions=dict(method=["POST"]))

        m.connect("my_account_ssh_keys", "/my_account/ssh_keys",
                  action="my_account_ssh_keys", conditions=dict(method=["GET"]))
        m.connect("my_account_ssh_keys", "/my_account/ssh_keys",
                  action="my_account_ssh_keys_add", conditions=dict(method=["POST"]))
        m.connect("my_account_ssh_keys_delete", "/my_account/ssh_keys/delete",
                  action="my_account_ssh_keys_delete", conditions=dict(method=["POST"]))

    # ADMIN GIST
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/gists') as m:
        m.connect("gists", "/gists",
                  action="create", conditions=dict(method=["POST"]))
        m.connect("gists", "/gists",
                  conditions=dict(method=["GET"]))
        m.connect("new_gist", "/gists/new",
                  action="new", conditions=dict(method=["GET"]))

        m.connect("gist_delete", "/gists/{gist_id}/delete",
                  action="delete", conditions=dict(method=["POST"]))
        m.connect("edit_gist", "/gists/{gist_id}/edit",
                  action="edit", conditions=dict(method=["GET", "POST"]))
        m.connect("edit_gist_check_revision", "/gists/{gist_id}/edit/check_revision",
                  action="check_revision", conditions=dict(method=["POST"]))

        m.connect("gist", "/gists/{gist_id}",
                  action="show", conditions=dict(method=["GET"]))
        m.connect("gist_rev", "/gists/{gist_id}/{revision}",
                  revision="tip",
                  action="show", conditions=dict(method=["GET"]))
        m.connect("formatted_gist", "/gists/{gist_id}/{revision}/{format}",
                  revision="tip",
                  action="show", conditions=dict(method=["GET"]))
        m.connect("formatted_gist_file", "/gists/{gist_id}/{revision}/{format}/{f_path:.*}",
                  revision='tip',
                  action="show", conditions=dict(method=["GET"]))

    # ADMIN MAIN PAGES
    with rmap.submapper(path_prefix=ADMIN_PREFIX,
                        controller='admin/admin') as m:
        m.connect('admin_home', '')
        m.connect('admin_add_repo', '/add_repo/{new_repo:[a-z0-9. _-]*}',
                  action='add_repo')
    #==========================================================================
    # API V2
    #==========================================================================
    with rmap.submapper(path_prefix=ADMIN_PREFIX, controller='api/api',
                        action='_dispatch') as m:
        m.connect('api', '/api')

    # USER JOURNAL
    rmap.connect('journal', '%s/journal' % ADMIN_PREFIX,
                 controller='journal')
    rmap.connect('journal_rss', '%s/journal/rss' % ADMIN_PREFIX,
                 controller='journal', action='journal_rss')
    rmap.connect('journal_atom', '%s/journal/atom' % ADMIN_PREFIX,
                 controller='journal', action='journal_atom')

    rmap.connect('public_journal', '%s/public_journal' % ADMIN_PREFIX,
                 controller='journal', action="public_journal")

    rmap.connect('public_journal_rss', '%s/public_journal/rss' % ADMIN_PREFIX,
                 controller='journal', action="public_journal_rss")

    rmap.connect('public_journal_rss_old', '%s/public_journal_rss' % ADMIN_PREFIX,
                 controller='journal', action="public_journal_rss")

    rmap.connect('public_journal_atom',
                 '%s/public_journal/atom' % ADMIN_PREFIX, controller='journal',
                 action="public_journal_atom")

    rmap.connect('public_journal_atom_old',
                 '%s/public_journal_atom' % ADMIN_PREFIX, controller='journal',
                 action="public_journal_atom")

    rmap.connect('toggle_following', '%s/toggle_following' % ADMIN_PREFIX,
                 controller='journal', action='toggle_following',
                 conditions=dict(method=["POST"]))

    # SEARCH
    rmap.connect('search', '%s/search' % ADMIN_PREFIX, controller='search',)
    rmap.connect('search_repo_admin', '%s/search/{repo_name:.*}' % ADMIN_PREFIX,
                 controller='search',
                 conditions=dict(function=check_repo))
    rmap.connect('search_repo', '/{repo_name:.*?}/search',
                 controller='search',
                 conditions=dict(function=check_repo),
                 )

    # LOGIN/LOGOUT/REGISTER/SIGN IN
    rmap.connect('session_csrf_secret_token', '%s/session_csrf_secret_token' % ADMIN_PREFIX, controller='login', action='session_csrf_secret_token')
    rmap.connect('login_home', '%s/login' % ADMIN_PREFIX, controller='login')
    rmap.connect('logout_home', '%s/logout' % ADMIN_PREFIX, controller='login',
                 action='logout')

    rmap.connect('register', '%s/register' % ADMIN_PREFIX, controller='login',
                 action='register')

    rmap.connect('reset_password', '%s/password_reset' % ADMIN_PREFIX,
                 controller='login', action='password_reset')

    rmap.connect('reset_password_confirmation',
                 '%s/password_reset_confirmation' % ADMIN_PREFIX,
                 controller='login', action='password_reset_confirmation')

    # FEEDS
    rmap.connect('rss_feed_home', '/{repo_name:.*?}/feed/rss',
                controller='feed', action='rss',
                conditions=dict(function=check_repo))

    rmap.connect('atom_feed_home', '/{repo_name:.*?}/feed/atom',
                controller='feed', action='atom',
                conditions=dict(function=check_repo))

    #==========================================================================
    # REPOSITORY ROUTES
    #==========================================================================
    rmap.connect('repo_creating_home', '/{repo_name:.*?}/repo_creating',
                controller='admin/repos', action='repo_creating')
    rmap.connect('repo_check_home', '/{repo_name:.*?}/repo_check_creating',
                controller='admin/repos', action='repo_check')

    rmap.connect('summary_home', '/{repo_name:.*?}',
                controller='summary',
                conditions=dict(function=check_repo))

    # must be here for proper group/repo catching
    rmap.connect('repos_group_home', '/{group_name:.*}',
                controller='admin/repo_groups', action="show_by_name",
                conditions=dict(function=check_group))
    rmap.connect('repo_stats_home', '/{repo_name:.*?}/statistics',
                controller='summary', action='statistics',
                conditions=dict(function=check_repo))

    rmap.connect('repo_size', '/{repo_name:.*?}/repo_size',
                controller='summary', action='repo_size',
                conditions=dict(function=check_repo))

    rmap.connect('repo_refs_data', '/{repo_name:.*?}/refs-data',
                 controller='home', action='repo_refs_data')

    rmap.connect('changeset_home', '/{repo_name:.*?}/changeset/{revision:.*}',
                controller='changeset', revision='tip',
                conditions=dict(function=check_repo))
    rmap.connect('changeset_children', '/{repo_name:.*?}/changeset_children/{revision}',
                controller='changeset', revision='tip', action="changeset_children",
                conditions=dict(function=check_repo))
    rmap.connect('changeset_parents', '/{repo_name:.*?}/changeset_parents/{revision}',
                controller='changeset', revision='tip', action="changeset_parents",
                conditions=dict(function=check_repo))

    # repo edit options
    rmap.connect("edit_repo", "/{repo_name:.*?}/settings",
                 controller='admin/repos', action="edit",
                 conditions=dict(method=["GET"], function=check_repo))

    rmap.connect("edit_repo_perms", "/{repo_name:.*?}/settings/permissions",
                 controller='admin/repos', action="edit_permissions",
                 conditions=dict(method=["GET"], function=check_repo))
    rmap.connect("edit_repo_perms_update", "/{repo_name:.*?}/settings/permissions",
                 controller='admin/repos', action="edit_permissions_update",
                 conditions=dict(method=["POST"], function=check_repo))
    rmap.connect("edit_repo_perms_revoke", "/{repo_name:.*?}/settings/permissions/delete",
                 controller='admin/repos', action="edit_permissions_revoke",
                 conditions=dict(method=["POST"], function=check_repo))

    rmap.connect("edit_repo_fields", "/{repo_name:.*?}/settings/fields",
                 controller='admin/repos', action="edit_fields",
                 conditions=dict(method=["GET"], function=check_repo))
    rmap.connect('create_repo_fields', "/{repo_name:.*?}/settings/fields/new",
                 controller='admin/repos', action="create_repo_field",
                 conditions=dict(method=["POST"], function=check_repo))
    rmap.connect('delete_repo_fields', "/{repo_name:.*?}/settings/fields/{field_id}/delete",
                 controller='admin/repos', action="delete_repo_field",
                 conditions=dict(method=["POST"], function=check_repo))

    rmap.connect("edit_repo_advanced", "/{repo_name:.*?}/settings/advanced",
                 controller='admin/repos', action="edit_advanced",
                 conditions=dict(method=["GET"], function=check_repo))

    rmap.connect("edit_repo_advanced_journal", "/{repo_name:.*?}/settings/advanced/journal",
                 controller='admin/repos', action="edit_advanced_journal",
                 conditions=dict(method=["POST"], function=check_repo))

    rmap.connect("edit_repo_advanced_fork", "/{repo_name:.*?}/settings/advanced/fork",
                 controller='admin/repos', action="edit_advanced_fork",
                 conditions=dict(method=["POST"], function=check_repo))

    rmap.connect("edit_repo_remote", "/{repo_name:.*?}/settings/remote",
                 controller='admin/repos', action="edit_remote",
                 conditions=dict(method=["GET"], function=check_repo))
    rmap.connect("edit_repo_remote_update", "/{repo_name:.*?}/settings/remote",
                 controller='admin/repos', action="edit_remote",
                 conditions=dict(method=["POST"], function=check_repo))

    rmap.connect("edit_repo_statistics", "/{repo_name:.*?}/settings/statistics",
                 controller='admin/repos', action="edit_statistics",
                 conditions=dict(method=["GET"], function=check_repo))
    rmap.connect("edit_repo_statistics_update", "/{repo_name:.*?}/settings/statistics",
                 controller='admin/repos', action="edit_statistics",
                 conditions=dict(method=["POST"], function=check_repo))

    # still working url for backward compat.
    rmap.connect('raw_changeset_home_depraced',
                 '/{repo_name:.*?}/raw-changeset/{revision}',
                 controller='changeset', action='changeset_raw',
                 revision='tip', conditions=dict(function=check_repo))

    ## new URLs
    rmap.connect('changeset_raw_home',
                 '/{repo_name:.*?}/changeset-diff/{revision}',
                 controller='changeset', action='changeset_raw',
                 revision='tip', conditions=dict(function=check_repo))

    rmap.connect('changeset_patch_home',
                 '/{repo_name:.*?}/changeset-patch/{revision}',
                 controller='changeset', action='changeset_patch',
                 revision='tip', conditions=dict(function=check_repo))

    rmap.connect('changeset_download_home',
                 '/{repo_name:.*?}/changeset-download/{revision}',
                 controller='changeset', action='changeset_download',
                 revision='tip', conditions=dict(function=check_repo))

    rmap.connect('changeset_comment',
                 '/{repo_name:.*?}/changeset-comment/{revision}',
                controller='changeset', revision='tip', action='comment',
                conditions=dict(function=check_repo))

    rmap.connect('changeset_comment_delete',
                 '/{repo_name:.*?}/changeset-comment/{comment_id}/delete',
                controller='changeset', action='delete_comment',
                conditions=dict(function=check_repo, method=["POST"]))

    rmap.connect('changeset_info', '/changeset_info/{repo_name:.*?}/{revision}',
                 controller='changeset', action='changeset_info')

    rmap.connect('compare_home',
                 '/{repo_name:.*?}/compare',
                 controller='compare',
                 conditions=dict(function=check_repo))

    rmap.connect('compare_url',
                 '/{repo_name:.*?}/compare/{org_ref_type}@{org_ref_name:.*?}...{other_ref_type}@{other_ref_name:.*?}',
                 controller='compare', action='compare',
                 conditions=dict(function=check_repo),
                 requirements=dict(
                            org_ref_type='(branch|book|tag|rev|__other_ref_type__)',
                            other_ref_type='(branch|book|tag|rev|__org_ref_type__)')
                 )

    rmap.connect('pullrequest_home',
                 '/{repo_name:.*?}/pull-request/new', controller='pullrequests',
                 conditions=dict(function=check_repo,
                                                 method=["GET"]))

    rmap.connect('pullrequest_repo_info',
                 '/{repo_name:.*?}/pull-request-repo-info',
                 controller='pullrequests', action='repo_info',
                 conditions=dict(function=check_repo, method=["GET"]))

    rmap.connect('pullrequest',
                 '/{repo_name:.*?}/pull-request/new', controller='pullrequests',
                 action='create', conditions=dict(function=check_repo,
                                                  method=["POST"]))

    rmap.connect('pullrequest_show',
                 '/{repo_name:.*?}/pull-request/{pull_request_id:\\d+}{extra:(/.*)?}', extra='',
                 controller='pullrequests',
                 action='show', conditions=dict(function=check_repo,
                                                method=["GET"]))
    rmap.connect('pullrequest_post',
                 '/{repo_name:.*?}/pull-request/{pull_request_id}',
                 controller='pullrequests',
                 action='post', conditions=dict(function=check_repo,
                                                method=["POST"]))
    rmap.connect('pullrequest_delete',
                 '/{repo_name:.*?}/pull-request/{pull_request_id}/delete',
                 controller='pullrequests',
                 action='delete', conditions=dict(function=check_repo,
                                                  method=["POST"]))

    rmap.connect('pullrequest_show_all',
                 '/{repo_name:.*?}/pull-request',
                 controller='pullrequests',
                 action='show_all', conditions=dict(function=check_repo,
                                                method=["GET"]))

    rmap.connect('my_pullrequests',
                 '/my_pullrequests',
                 controller='pullrequests',
                 action='show_my', conditions=dict(method=["GET"]))

    rmap.connect('pullrequest_comment',
                 '/{repo_name:.*?}/pull-request-comment/{pull_request_id}',
                 controller='pullrequests',
                 action='comment', conditions=dict(function=check_repo,
                                                method=["POST"]))

    rmap.connect('pullrequest_comment_delete',
                 '/{repo_name:.*?}/pull-request-comment/{comment_id}/delete',
                controller='pullrequests', action='delete_comment',
                conditions=dict(function=check_repo, method=["POST"]))

    rmap.connect('summary_home_summary', '/{repo_name:.*?}/summary',
                controller='summary', conditions=dict(function=check_repo))

    rmap.connect('changelog_home', '/{repo_name:.*?}/changelog',
                controller='changelog', conditions=dict(function=check_repo))

    rmap.connect('changelog_file_home', '/{repo_name:.*?}/changelog/{revision}/{f_path:.*}',
                controller='changelog',
                conditions=dict(function=check_repo))

    rmap.connect('changelog_details', '/{repo_name:.*?}/changelog_details/{cs}',
                controller='changelog', action='changelog_details',
                conditions=dict(function=check_repo))

    rmap.connect('files_home', '/{repo_name:.*?}/files/{revision}/{f_path:.*}',
                controller='files', revision='tip', f_path='',
                conditions=dict(function=check_repo))

    rmap.connect('files_home_nopath', '/{repo_name:.*?}/files/{revision}',
                controller='files', revision='tip', f_path='',
                conditions=dict(function=check_repo))

    rmap.connect('files_history_home',
                 '/{repo_name:.*?}/history/{revision}/{f_path:.*}',
                 controller='files', action='history', revision='tip', f_path='',
                 conditions=dict(function=check_repo))

    rmap.connect('files_authors_home',
                 '/{repo_name:.*?}/authors/{revision}/{f_path:.*}',
                 controller='files', action='authors', revision='tip', f_path='',
                 conditions=dict(function=check_repo))

    rmap.connect('files_diff_home', '/{repo_name:.*?}/diff/{f_path:.*}',
                controller='files', action='diff', revision='tip', f_path='',
                conditions=dict(function=check_repo))

    rmap.connect('files_diff_2way_home', '/{repo_name:.*?}/diff-2way/{f_path:.+}',
                controller='files', action='diff_2way', revision='tip', f_path='',
                conditions=dict(function=check_repo))

    rmap.connect('files_rawfile_home',
                 '/{repo_name:.*?}/rawfile/{revision}/{f_path:.*}',
                 controller='files', action='rawfile', revision='tip',
                 f_path='', conditions=dict(function=check_repo))

    rmap.connect('files_raw_home',
                 '/{repo_name:.*?}/raw/{revision}/{f_path:.*}',
                 controller='files', action='raw', revision='tip', f_path='',
                 conditions=dict(function=check_repo))

    rmap.connect('files_annotate_home',
                 '/{repo_name:.*?}/annotate/{revision}/{f_path:.*}',
                 controller='files', revision='tip',
                 f_path='', annotate='1', conditions=dict(function=check_repo))

    rmap.connect('files_edit_home',
                 '/{repo_name:.*?}/edit/{revision}/{f_path:.*}',
                 controller='files', action='edit', revision='tip',
                 f_path='', conditions=dict(function=check_repo))

    rmap.connect('files_add_home',
                 '/{repo_name:.*?}/add/{revision}/{f_path:.*}',
                 controller='files', action='add', revision='tip',
                 f_path='', conditions=dict(function=check_repo))

    rmap.connect('files_delete_home',
                 '/{repo_name:.*?}/delete/{revision}/{f_path:.*}',
                 controller='files', action='delete', revision='tip',
                 f_path='', conditions=dict(function=check_repo))

    rmap.connect('files_archive_home', '/{repo_name:.*?}/archive/{fname}',
                controller='files', action='archivefile',
                conditions=dict(function=check_repo))

    rmap.connect('files_nodelist_home',
                 '/{repo_name:.*?}/nodelist/{revision}/{f_path:.*}',
                controller='files', action='nodelist',
                conditions=dict(function=check_repo))

    rmap.connect('repo_fork_create_home', '/{repo_name:.*?}/fork',
                controller='forks', action='fork_create',
                conditions=dict(function=check_repo, method=["POST"]))

    rmap.connect('repo_fork_home', '/{repo_name:.*?}/fork',
                controller='forks', action='fork',
                conditions=dict(function=check_repo))

    rmap.connect('repo_forks_home', '/{repo_name:.*?}/forks',
                 controller='forks', action='forks',
                 conditions=dict(function=check_repo))

    rmap.connect('repo_followers_home', '/{repo_name:.*?}/followers',
                 controller='followers', action='followers',
                 conditions=dict(function=check_repo))

    return rmap


class UrlGenerator(object):
    """Emulate pylons.url in providing a wrapper around routes.url

    This code was added during migration from Pylons to Turbogears2. Pylons
    already provided a wrapper like this, but Turbogears2 does not.

    When the routing of Kallithea is changed to use less Routes and more
    Turbogears2-style routing, this class may disappear or change.

    url() (the __call__ method) returns the URL based on a route name and
    arguments.
    url.current() returns the URL of the current page with arguments applied.

    Refer to documentation of Routes for details:
    https://routes.readthedocs.io/en/latest/generating.html#generation
    """
    def __call__(self, *args, **kwargs):
        return request.environ['routes.url'](*args, **kwargs)

    def current(self, *args, **kwargs):
        return request.environ['routes.url'].current(*args, **kwargs)


url = UrlGenerator()
