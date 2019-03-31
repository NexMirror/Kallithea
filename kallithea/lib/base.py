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
import decorator
import logging
import time
import traceback
import warnings

import webob.exc
import paste.httpexceptions
import paste.auth.basic
import paste.httpheaders
from webhelpers.pylonslib import secure_form

from tg import config, tmpl_context as c, request, response, session, render_template
from tg import TGController
from tg.i18n import ugettext as _

from kallithea import __version__, BACKENDS

from kallithea.config.routing import url
from kallithea.lib.utils2 import str2bool, safe_unicode, AttributeDict, \
    safe_str, safe_int
from kallithea.lib import auth_modules
from kallithea.lib.auth import AuthUser, HasPermissionAnyMiddleware
from kallithea.lib.compat import json
from kallithea.lib.utils import get_repo_slug
from kallithea.lib.exceptions import UserCreationError
from kallithea.lib.vcs.exceptions import RepositoryError, EmptyRepositoryError, ChangesetDoesNotExistError
from kallithea.model import meta

from kallithea.model.db import PullRequest, Repository, Ui, User, Setting
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
    path = environ.get('PATH_INFO')
    org_req = environ.get('tg.original_request')
    if org_req:
        path = org_req.environ.get('PATH_INFO')
    return path


def log_in_user(user, remember, is_external_auth):
    """
    Log a `User` in and update session and cookies. If `remember` is True,
    the session cookie is set to expire in a year; otherwise, it expires at
    the end of the browser session.

    Returns populated `AuthUser` object.
    """
    user.update_lastlogin()
    meta.Session().commit()

    auth_user = AuthUser(dbuser=user,
                         is_external_auth=is_external_auth)
    # It should not be possible to explicitly log in as the default user.
    assert not auth_user.is_default_user
    auth_user.is_authenticated = True

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


def check_locking_state(action, repo_name, user):
    """
    Checks locking on this repository, if locking is enabled, and if lock
    is present. Returns a tuple of make_lock, locked, locked_by. make_lock
    can have 3 states: None (do nothing), True (make lock), and False
    (release lock). This value is later propagated to hooks, telling them
    what to do.
    """
    locked = False  # defines that locked error should be thrown to user
    make_lock = None
    repo = Repository.get_by_repo_name(repo_name)
    locked_by = repo.locked
    if repo and repo.enable_locking:
        if action == 'push':
            # Check if repo already is locked !, if it is compare users
            user_id, _date = locked_by
            if user.user_id == user_id:
                log.debug('Got push from user %s, now unlocking', user)
                # Unlock if we have push from the user who locked
                make_lock = False
            else:
                # Another used tried to push - deny access with something like 423 Locked!
                locked = True
        if action == 'pull':
            if repo.locked[0] and repo.locked[1]:
                locked = True
            else:
                log.debug('Setting lock on repo %s by %s', repo, user)
                make_lock = True
    else:
        log.debug('Repository %s does not have locking enabled', repo)
    log.debug('FINAL locking values make_lock:%s,locked:%s,locked_by:%s',
              make_lock, locked, locked_by)
    return make_lock, locked, locked_by


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

    def __init__(self, application, config):
        self.application = application
        self.config = config
        # base path of repo locations
        self.basepath = self.config['base_path']
        # authenticate this VCS request using the authentication modules
        self.authenticate = BasicAuth('', auth_modules.authenticate,
                                      config.get('auth_ret_code'))

    def _authorize(self, environ, start_response, action, repo_name, ip_addr):
        """Authenticate and authorize user.

        Since we're dealing with a VCS client and not a browser, we only
        support HTTP basic authentication, either directly via raw header
        inspection, or by using container authentication to delegate the
        authentication to the web server.

        Returns (user, None) on successful authentication and authorization.
        Returns (None, wsgi_app) to send the wsgi_app response to the client.
        """
        # Check if anonymous access is allowed.
        default_user = User.get_default_user(cache=True)
        is_default_user_allowed = (default_user.active and
            self._check_permission(action, default_user, repo_name, ip_addr))
        if is_default_user_allowed:
            return default_user, None

        if not default_user.active:
            log.debug('Anonymous access is disabled')
        else:
            log.debug('Not authorized to access this '
                      'repository as anonymous user')

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
            if user is None or not user.active:
                return None, webob.exc.HTTPForbidden()
        except Exception:
            log.error(traceback.format_exc())
            return None, webob.exc.HTTPInternalServerError()

        # check permissions for this repository
        perm = self._check_permission(action, user, repo_name, ip_addr)
        if not perm:
            return None, webob.exc.HTTPForbidden()

        return user, None

    def _handle_request(self, environ, start_response):
        raise NotImplementedError()

    def _get_by_id(self, repo_name):
        """
        Gets a special pattern _<ID> from clone url and tries to replace it
        with a repository_name for support of _<ID> permanent URLs

        :param repo_name:
        """

        data = repo_name.split('/')
        if len(data) >= 2:
            from kallithea.lib.utils import get_repo_by_id
            by_id_match = get_repo_by_id(repo_name)
            if by_id_match:
                data[1] = safe_str(by_id_match)

        return '/'.join(data)

    def _check_permission(self, action, user, repo_name, ip_addr=None):
        """
        Checks permissions using action (push/pull) user and repository
        name

        :param action: 'push' or 'pull' action
        :param user: `User` instance
        :param repo_name: repository name
        """
        # check IP
        ip_allowed = AuthUser.check_ip_allowed(user, ip_addr)
        if ip_allowed:
            log.info('Access for IP:%s allowed', ip_addr)
        else:
            return False

        if action == 'push':
            if not HasPermissionAnyMiddleware('repository.write',
                                              'repository.admin')(user,
                                                                  repo_name):
                return False

        else:
            #any other action need at least read permission
            if not HasPermissionAnyMiddleware('repository.read',
                                              'repository.write',
                                              'repository.admin')(user,
                                                                  repo_name):
                return False

        return True

    def _get_ip_addr(self, environ):
        return _get_ip_addr(environ)

    def __call__(self, environ, start_response):
        start = time.time()
        try:
            return self._handle_request(environ, start_response)
        finally:
            log = logging.getLogger('kallithea.' + self.__class__.__name__)
            log.debug('Request time: %.3fs', time.time() - start)
            meta.Session.remove()


class BaseController(TGController):

    def _before(self, *args, **kwargs):
        """
        _before is called before controller methods and after __call__
        """
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
        c.clone_uri_tmpl = rc_config.get('clone_uri_tmpl')

        ## INI stored
        c.visual.allow_repo_location_change = str2bool(config.get('allow_repo_location_change', True))
        c.visual.allow_custom_hooks_settings = str2bool(config.get('allow_custom_hooks_settings', True))

        c.instance_id = config.get('instance_id')
        c.issues_url = config.get('bugtracker', url('issues_url'))
        # END CONFIG VARS

        c.repo_name = get_repo_slug(request)  # can be empty
        c.backends = BACKENDS.keys()

        self.cut_off_limit = safe_int(config.get('cut_off_limit'))

        c.my_pr_count = PullRequest.query(reviewer_id=request.authuser.user_id, include_closed=False).count()

        self.scm_model = ScmModel()

    @staticmethod
    def _determine_auth_user(api_key, bearer_token, session_authuser):
        """
        Create an `AuthUser` object given the API key/bearer token
        (if any) and the value of the authuser session cookie.
        """

        # Authenticate by bearer token
        if bearer_token is not None:
            api_key = bearer_token

        # Authenticate by API key
        if api_key is not None:
            au = AuthUser(dbuser=User.get_by_api_key(api_key),
                authenticating_api_key=api_key, is_external_auth=True)
            if au.is_anonymous:
                log.warning('API key ****%s is NOT valid', api_key[-4:])
                raise webob.exc.HTTPForbidden(_('Invalid API key'))
            return au

        # Authenticate by session cookie
        # In ancient login sessions, 'authuser' may not be a dict.
        # In that case, the user will have to log in again.
        # v0.3 and earlier included an 'is_authenticated' key; if present,
        # this must be True.
        if isinstance(session_authuser, dict) and session_authuser.get('is_authenticated', True):
            return AuthUser.from_cookie(session_authuser)

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
                    return log_in_user(user, remember=False,
                                       is_external_auth=True)

        # User is anonymous
        return AuthUser()

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
        if secure_form.token_key in request.GET:
            log.error('CSRF key leak detected')
            session.pop(secure_form.token_key, None)
            session.save()
            from kallithea.lib import helpers as h
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
            request.ip_addr = _get_ip_addr(environ)
            # make sure that we update permissions each time we call controller

            self._basic_security_checks()

            # set globals for auth user

            bearer_token = None
            try:
                # Request.authorization may raise ValueError on invalid input
                type, params = request.authorization
            except (ValueError, TypeError):
                pass
            else:
                if type.lower() == 'bearer':
                    bearer_token = params

            authuser = self._determine_auth_user(
                request.GET.get('api_key'),
                bearer_token,
                session.get('authuser'),
            )

            if not AuthUser.check_ip_allowed(authuser, request.ip_addr):
                raise webob.exc.HTTPForbidden()

            request.authuser = authuser

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
