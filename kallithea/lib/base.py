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
kallithea.lib.base
~~~~~~~~~~~~~~~~~~

The base Controller API
Provides the BaseController class for subclassing. And usage in different
controllers

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 06, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import datetime
import logging
import time
import traceback
import warnings

import decorator
import paste.auth.basic
import paste.httpexceptions
import paste.httpheaders
import webob.exc
from tg import TGController, config, render_template, request, response, session
from tg import tmpl_context as c
from tg.i18n import ugettext as _

from kallithea import BACKENDS, __version__
from kallithea.config.routing import url
from kallithea.lib import auth_modules
from kallithea.lib.auth import AuthUser, HasPermissionAnyMiddleware
from kallithea.lib.compat import json
from kallithea.lib.exceptions import UserCreationError
from kallithea.lib.utils import get_repo_slug, is_valid_repo
from kallithea.lib.utils2 import AttributeDict, safe_int, safe_str, safe_unicode, set_hook_environment, str2bool
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError, EmptyRepositoryError, RepositoryError
from kallithea.model import meta
from kallithea.model.db import PullRequest, Repository, Setting, User
from kallithea.model.scm import ScmModel


log = logging.getLogger(__name__)


def render(template_path):
    return render_template({'url': url}, 'mako', template_path)


def _filter_proxy(ip):
    """
    HEADERS can have multiple ips inside the left-most being the original
    client, and each successive proxy that passed the request adding the IP
    address where it received the request from.

    :param ip:
    """
    if ',' in ip:
        _ips = ip.split(',')
        _first_ip = _ips[0].strip()
        log.debug('Got multiple IPs %s, using %s', ','.join(_ips), _first_ip)
        return _first_ip
    return ip


def _get_ip_addr(environ):
    proxy_key = 'HTTP_X_REAL_IP'
    proxy_key2 = 'HTTP_X_FORWARDED_FOR'
    def_key = 'REMOTE_ADDR'

    ip = environ.get(proxy_key)
    if ip:
        return _filter_proxy(ip)

    ip = environ.get(proxy_key2)
    if ip:
        return _filter_proxy(ip)

    ip = environ.get(def_key, '0.0.0.0')
    return _filter_proxy(ip)


def _get_access_path(environ):
    """Return PATH_INFO from environ ... using tg.original_request if available."""
    org_req = environ.get('tg.original_request')
    if org_req is not None:
        environ = org_req.environ
    return environ.get('PATH_INFO')


def log_in_user(user, remember, is_external_auth, ip_addr):
    """
    Log a `User` in and update session and cookies. If `remember` is True,
    the session cookie is set to expire in a year; otherwise, it expires at
    the end of the browser session.

    Returns populated `AuthUser` object.
    """
    # It should not be possible to explicitly log in as the default user.
    assert not user.is_default_user, user

    auth_user = AuthUser.make(dbuser=user, is_external_auth=is_external_auth, ip_addr=ip_addr)
    if auth_user is None:
        return None

    user.update_lastlogin()
    meta.Session().commit()

    # Start new session to prevent session fixation attacks.
    session.invalidate()
    session['authuser'] = cookie = auth_user.to_cookie()

    # If they want to be remembered, update the cookie.
    # NOTE: Assumes that beaker defaults to browser session cookie.
    if remember:
        t = datetime.datetime.now() + datetime.timedelta(days=365)
        session._set_cookie_expires(t)

    session.save()

    log.info('user %s is now authenticated and stored in '
             'session, session attrs %s', user.username, cookie)

    # dumps session attrs back to cookie
    session._update_cookie_out()

    return auth_user


class BasicAuth(paste.auth.basic.AuthBasicAuthenticator):

    def __init__(self, realm, authfunc, auth_http_code=None):
        self.realm = realm
        self.authfunc = authfunc
        self._rc_auth_http_code = auth_http_code

    def build_authentication(self, environ):
        head = paste.httpheaders.WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
        # Consume the whole body before sending a response
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0
        environ['wsgi.input'].read(request_body_size)
        if self._rc_auth_http_code and self._rc_auth_http_code == '403':
            # return 403 if alternative http return code is specified in
            # Kallithea config
            return paste.httpexceptions.HTTPForbidden(headers=head)
        return paste.httpexceptions.HTTPUnauthorized(headers=head)

    def authenticate(self, environ):
        authorization = paste.httpheaders.AUTHORIZATION(environ)
        if not authorization:
            return self.build_authentication(environ)
        (authmeth, auth) = authorization.split(' ', 1)
        if 'basic' != authmeth.lower():
            return self.build_authentication(environ)
        auth = auth.strip().decode('base64')
        _parts = auth.split(':', 1)
        if len(_parts) == 2:
            username, password = _parts
            if self.authfunc(username, password, environ) is not None:
                return username
        return self.build_authentication(environ)

    __call__ = authenticate


class BaseVCSController(object):
    """Base controller for handling Mercurial/Git protocol requests
    (coming from a VCS client, and not a browser).
    """

    scm_alias = None # 'hg' / 'git'

    def __init__(self, application, config):
        self.application = application
        self.config = config
        # base path of repo locations
        self.basepath = self.config['base_path']
        # authenticate this VCS request using the authentication modules
        self.authenticate = BasicAuth('', auth_modules.authenticate,
                                      config.get('auth_ret_code'))

    @classmethod
    def parse_request(cls, environ):
        """If request is parsed as a request for this VCS, return a namespace with the parsed request.
        If the request is unknown, return None.
        """
        raise NotImplementedError()

    def _authorize(self, environ, action, repo_name, ip_addr):
        """Authenticate and authorize user.

        Since we're dealing with a VCS client and not a browser, we only
        support HTTP basic authentication, either directly via raw header
        inspection, or by using container authentication to delegate the
        authentication to the web server.

        Returns (user, None) on successful authentication and authorization.
        Returns (None, wsgi_app) to send the wsgi_app response to the client.
        """
        # Use anonymous access if allowed for action on repo.
        default_user = User.get_default_user(cache=True)
        default_authuser = AuthUser.make(dbuser=default_user, ip_addr=ip_addr)
        if default_authuser is None:
            log.debug('No anonymous access at all') # move on to proper user auth
        else:
            if self._check_permission(action, default_authuser, repo_name):
                return default_authuser, None
            log.debug('Not authorized to access this repository as anonymous user')

        username = None
        #==============================================================
        # DEFAULT PERM FAILED OR ANONYMOUS ACCESS IS DISABLED SO WE
        # NEED TO AUTHENTICATE AND ASK FOR AUTH USER PERMISSIONS
        #==============================================================

        # try to auth based on environ, container auth methods
        log.debug('Running PRE-AUTH for container based authentication')
        pre_auth = auth_modules.authenticate('', '', environ)
        if pre_auth is not None and pre_auth.get('username'):
            username = pre_auth['username']
        log.debug('PRE-AUTH got %s as username', username)

        # If not authenticated by the container, running basic auth
        if not username:
            self.authenticate.realm = safe_str(self.config['realm'])
            result = self.authenticate(environ)
            if isinstance(result, str):
                paste.httpheaders.AUTH_TYPE.update(environ, 'basic')
                paste.httpheaders.REMOTE_USER.update(environ, result)
                username = result
            else:
                return None, result.wsgi_application

        #==============================================================
        # CHECK PERMISSIONS FOR THIS REQUEST USING GIVEN USERNAME
        #==============================================================
        try:
            user = User.get_by_username_or_email(username)
        except Exception:
            log.error(traceback.format_exc())
            return None, webob.exc.HTTPInternalServerError()

        authuser = AuthUser.make(dbuser=user, ip_addr=ip_addr)
        if authuser is None:
            return None, webob.exc.HTTPForbidden()
        if not self._check_permission(action, authuser, repo_name):
            return None, webob.exc.HTTPForbidden()

        return user, None

    def _handle_request(self, environ, start_response):
        raise NotImplementedError()

    def _check_permission(self, action, authuser, repo_name):
        """
        Checks permissions using action (push/pull) user and repository
        name

        :param action: 'push' or 'pull' action
        :param user: `User` instance
        :param repo_name: repository name
        """
        if action == 'push':
            if not HasPermissionAnyMiddleware('repository.write',
                                              'repository.admin')(authuser,
                                                                  repo_name):
                return False

        else:
            #any other action need at least read permission
            if not HasPermissionAnyMiddleware('repository.read',
                                              'repository.write',
                                              'repository.admin')(authuser,
                                                                  repo_name):
                return False

        return True

    def _get_ip_addr(self, environ):
        return _get_ip_addr(environ)

    def __call__(self, environ, start_response):
        start = time.time()
        try:
            # try parsing a request for this VCS - if it fails, call the wrapped app
            parsed_request = self.parse_request(environ)
            if parsed_request is None:
                return self.application(environ, start_response)

            # skip passing error to error controller
            environ['pylons.status_code_redirect'] = True

            # quick check if repo exists...
            if not is_valid_repo(parsed_request.repo_name, self.basepath, self.scm_alias):
                raise webob.exc.HTTPNotFound()

            if parsed_request.action is None:
                # Note: the client doesn't get the helpful error message
                raise webob.exc.HTTPBadRequest('Unable to detect pull/push action for %r! Are you using a nonstandard command or client?' % parsed_request.repo_name)

            #======================================================================
            # CHECK PERMISSIONS
            #======================================================================
            ip_addr = self._get_ip_addr(environ)
            user, response_app = self._authorize(environ, parsed_request.action, parsed_request.repo_name, ip_addr)
            if response_app is not None:
                return response_app(environ, start_response)

            #======================================================================
            # REQUEST HANDLING
            #======================================================================
            set_hook_environment(user.username, ip_addr,
                parsed_request.repo_name, self.scm_alias, parsed_request.action)

            try:
                log.info('%s action on %s repo "%s" by "%s" from %s',
                         parsed_request.action, self.scm_alias, parsed_request.repo_name, safe_str(user.username), ip_addr)
                app = self._make_app(parsed_request)
                return app(environ, start_response)
            except Exception:
                log.error(traceback.format_exc())
                raise webob.exc.HTTPInternalServerError()

        except webob.exc.HTTPException as e:
            return e(environ, start_response)
        finally:
            log_ = logging.getLogger('kallithea.' + self.__class__.__name__)
            log_.debug('Request time: %.3fs', time.time() - start)
            meta.Session.remove()


class BaseController(TGController):

    def _before(self, *args, **kwargs):
        """
        _before is called before controller methods and after __call__
        """
        if request.needs_csrf_check:
            # CSRF protection: Whenever a request has ambient authority (whether
            # through a session cookie or its origin IP address), it must include
            # the correct token, unless the HTTP method is GET or HEAD (and thus
            # guaranteed to be side effect free. In practice, the only situation
            # where we allow side effects without ambient authority is when the
            # authority comes from an API key; and that is handled above.
            from kallithea.lib import helpers as h
            token = request.POST.get(h.session_csrf_secret_name)
            if not token or token != h.session_csrf_secret_token():
                log.error('CSRF check failed')
                raise webob.exc.HTTPForbidden()

        c.kallithea_version = __version__
        rc_config = Setting.get_app_settings()

        # Visual options
        c.visual = AttributeDict({})

        ## DB stored
        c.visual.show_public_icon = str2bool(rc_config.get('show_public_icon'))
        c.visual.show_private_icon = str2bool(rc_config.get('show_private_icon'))
        c.visual.stylify_metalabels = str2bool(rc_config.get('stylify_metalabels'))
        c.visual.page_size = safe_int(rc_config.get('dashboard_items', 100))
        c.visual.admin_grid_items = safe_int(rc_config.get('admin_grid_items', 100))
        c.visual.repository_fields = str2bool(rc_config.get('repository_fields'))
        c.visual.show_version = str2bool(rc_config.get('show_version'))
        c.visual.use_gravatar = str2bool(rc_config.get('use_gravatar'))
        c.visual.gravatar_url = rc_config.get('gravatar_url')

        c.ga_code = rc_config.get('ga_code')
        # TODO: replace undocumented backwards compatibility hack with db upgrade and rename ga_code
        if c.ga_code and '<' not in c.ga_code:
            c.ga_code = '''<script type="text/javascript">
                var _gaq = _gaq || [];
                _gaq.push(['_setAccount', '%s']);
                _gaq.push(['_trackPageview']);

                (function() {
                    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
                    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
                    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
                    })();
            </script>''' % c.ga_code
        c.site_name = rc_config.get('title')
        c.clone_uri_tmpl = rc_config.get('clone_uri_tmpl') or Repository.DEFAULT_CLONE_URI
        c.clone_ssh_tmpl = rc_config.get('clone_ssh_tmpl') or Repository.DEFAULT_CLONE_SSH

        ## INI stored
        c.visual.allow_repo_location_change = str2bool(config.get('allow_repo_location_change', True))
        c.visual.allow_custom_hooks_settings = str2bool(config.get('allow_custom_hooks_settings', True))
        c.ssh_enabled = str2bool(config.get('ssh_enabled', False))

        c.instance_id = config.get('instance_id')
        c.issues_url = config.get('bugtracker', url('issues_url'))
        # END CONFIG VARS

        c.repo_name = get_repo_slug(request)  # can be empty
        c.backends = BACKENDS.keys()

        self.cut_off_limit = safe_int(config.get('cut_off_limit'))

        c.my_pr_count = PullRequest.query(reviewer_id=request.authuser.user_id, include_closed=False).count()

        self.scm_model = ScmModel()

    @staticmethod
    def _determine_auth_user(session_authuser, ip_addr):
        """
        Create an `AuthUser` object given the API key/bearer token
        (if any) and the value of the authuser session cookie.
        Returns None if no valid user is found (like not active or no access for IP).
        """

        # Authenticate by session cookie
        # In ancient login sessions, 'authuser' may not be a dict.
        # In that case, the user will have to log in again.
        # v0.3 and earlier included an 'is_authenticated' key; if present,
        # this must be True.
        if isinstance(session_authuser, dict) and session_authuser.get('is_authenticated', True):
            return AuthUser.from_cookie(session_authuser, ip_addr=ip_addr)

        # Authenticate by auth_container plugin (if enabled)
        if any(
            plugin.is_container_auth
            for plugin in auth_modules.get_auth_plugins()
        ):
            try:
                user_info = auth_modules.authenticate('', '', request.environ)
            except UserCreationError as e:
                from kallithea.lib import helpers as h
                h.flash(e, 'error', logf=log.error)
            else:
                if user_info is not None:
                    username = user_info['username']
                    user = User.get_by_username(username, case_insensitive=True)
                    return log_in_user(user, remember=False, is_external_auth=True, ip_addr=ip_addr)

        # User is default user (if active) or anonymous
        default_user = User.get_default_user(cache=True)
        authuser = AuthUser.make(dbuser=default_user, ip_addr=ip_addr)
        if authuser is None: # fall back to anonymous
            authuser = AuthUser(dbuser=default_user) # TODO: somehow use .make?
        return authuser

    @staticmethod
    def _basic_security_checks():
        """Perform basic security/sanity checks before processing the request."""

        # Only allow the following HTTP request methods.
        if request.method not in ['GET', 'HEAD', 'POST']:
            raise webob.exc.HTTPMethodNotAllowed()

        # Also verify the _method override - no longer allowed.
        if request.params.get('_method') is None:
            pass # no override, no problem
        else:
            raise webob.exc.HTTPMethodNotAllowed()

        # Make sure CSRF token never appears in the URL. If so, invalidate it.
        from kallithea.lib import helpers as h
        if h.session_csrf_secret_name in request.GET:
            log.error('CSRF key leak detected')
            session.pop(h.session_csrf_secret_name, None)
            session.save()
            h.flash(_('CSRF token leak has been detected - all form tokens have been expired'),
                    category='error')

        # WebOb already ignores request payload parameters for anything other
        # than POST/PUT, but double-check since other Kallithea code relies on
        # this assumption.
        if request.method not in ['POST', 'PUT'] and request.POST:
            log.error('%r request with payload parameters; WebOb should have stopped this', request.method)
            raise webob.exc.HTTPBadRequest()

    def __call__(self, environ, context):
        try:
            ip_addr = _get_ip_addr(environ)
            self._basic_security_checks()

            api_key = request.GET.get('api_key')
            try:
                # Request.authorization may raise ValueError on invalid input
                type, params = request.authorization
            except (ValueError, TypeError):
                pass
            else:
                if type.lower() == 'bearer':
                    api_key = params # bearer token is an api key too

            if api_key is None:
                authuser = self._determine_auth_user(
                    session.get('authuser'),
                    ip_addr=ip_addr,
                )
                needs_csrf_check = request.method not in ['GET', 'HEAD']

            else:
                dbuser = User.get_by_api_key(api_key)
                if dbuser is None:
                    log.info('No db user found for authentication with API key ****%s from %s',
                             api_key[-4:], ip_addr)
                authuser = AuthUser.make(dbuser=dbuser, is_external_auth=True, ip_addr=ip_addr)
                needs_csrf_check = False # API key provides CSRF protection

            if authuser is None:
                log.info('No valid user found')
                raise webob.exc.HTTPForbidden()

            # set globals for auth user
            request.authuser = authuser
            request.ip_addr = ip_addr
            request.needs_csrf_check = needs_csrf_check

            log.info('IP: %s User: %s accessed %s',
                request.ip_addr, request.authuser,
                safe_unicode(_get_access_path(environ)),
            )
            return super(BaseController, self).__call__(environ, context)
        except webob.exc.HTTPException as e:
            return e


class BaseRepoController(BaseController):
    """
    Base class for controllers responsible for loading all needed data for
    repository loaded items are

    c.db_repo_scm_instance: instance of scm repository
    c.db_repo: instance of db
    c.repository_followers: number of followers
    c.repository_forks: number of forks
    c.repository_following: weather the current user is following the current repo
    """

    def _before(self, *args, **kwargs):
        super(BaseRepoController, self)._before(*args, **kwargs)
        if c.repo_name:  # extracted from routes
            _dbr = Repository.get_by_repo_name(c.repo_name)
            if not _dbr:
                return

            log.debug('Found repository in database %s with state `%s`',
                      safe_unicode(_dbr), safe_unicode(_dbr.repo_state))
            route = getattr(request.environ.get('routes.route'), 'name', '')

            # allow to delete repos that are somehow damages in filesystem
            if route in ['delete_repo']:
                return

            if _dbr.repo_state in [Repository.STATE_PENDING]:
                if route in ['repo_creating_home']:
                    return
                check_url = url('repo_creating_home', repo_name=c.repo_name)
                raise webob.exc.HTTPFound(location=check_url)

            dbr = c.db_repo = _dbr
            c.db_repo_scm_instance = c.db_repo.scm_instance
            if c.db_repo_scm_instance is None:
                log.error('%s this repository is present in database but it '
                          'cannot be created as an scm instance', c.repo_name)
                from kallithea.lib import helpers as h
                h.flash(_('Repository not found in the filesystem'),
                        category='error')
                raise webob.exc.HTTPNotFound()

            # some globals counter for menu
            c.repository_followers = self.scm_model.get_followers(dbr)
            c.repository_forks = self.scm_model.get_forks(dbr)
            c.repository_pull_requests = self.scm_model.get_pull_requests(dbr)
            c.repository_following = self.scm_model.is_following_repo(
                                    c.repo_name, request.authuser.user_id)

    @staticmethod
    def _get_ref_rev(repo, ref_type, ref_name, returnempty=False):
        """
        Safe way to get changeset. If error occurs show error.
        """
        from kallithea.lib import helpers as h
        try:
            return repo.scm_instance.get_ref_revision(ref_type, ref_name)
        except EmptyRepositoryError as e:
            if returnempty:
                return repo.scm_instance.EMPTY_CHANGESET
            h.flash(_('There are no changesets yet'), category='error')
            raise webob.exc.HTTPNotFound()
        except ChangesetDoesNotExistError as e:
            h.flash(_('Changeset for %s %s not found in %s') %
                              (ref_type, ref_name, repo.repo_name),
                    category='error')
            raise webob.exc.HTTPNotFound()
        except RepositoryError as e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='error')
            raise webob.exc.HTTPBadRequest()


@decorator.decorator
def jsonify(func, *args, **kwargs):
    """Action decorator that formats output for JSON

    Given a function that will return content, this decorator will turn
    the result into JSON, with a content-type of 'application/json' and
    output it.
    """
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    data = func(*args, **kwargs)
    if isinstance(data, (list, tuple)):
        # A JSON list response is syntactically valid JavaScript and can be
        # loaded and executed as JavaScript by a malicious third-party site
        # using <script>, which can lead to cross-site data leaks.
        # JSON responses should therefore be scalars or objects (i.e. Python
        # dicts), because a JSON object is a syntax error if intepreted as JS.
        msg = "JSON responses with Array envelopes are susceptible to " \
              "cross-site data leak attacks, see " \
              "https://web.archive.org/web/20120519231904/http://wiki.pylonshq.com/display/pylonsfaq/Warnings"
        warnings.warn(msg, Warning, 2)
        log.warning(msg)
    log.debug("Returning JSON wrapped action output")
    return json.dumps(data, encoding='utf-8')

@decorator.decorator
def IfSshEnabled(func, *args, **kwargs):
    """Decorator for functions that can only be called if SSH access is enabled.

    If SSH access is disabled in the configuration file, HTTPNotFound is raised.
    """
    if not c.ssh_enabled:
        from kallithea.lib import helpers as h
        h.flash(_("SSH access is disabled."), category='warning')
        raise webob.exc.HTTPNotFound()
    return func(*args, **kwargs)
