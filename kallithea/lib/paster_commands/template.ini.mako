## -*- coding: utf-8 -*-
<%text>################################################################################</%text>
<%text>################################################################################</%text>
# Kallithea - config file generated with kallithea-config                      #
#                                                                              #
# The %(here)s variable will be replaced with the parent directory of this file#
<%text>################################################################################</%text>
<%text>################################################################################</%text>

[DEFAULT]

<%text>################################################################################</%text>
<%text>## Email settings                                                             ##</%text>
<%text>##                                                                            ##</%text>
<%text>## Refer to the documentation ("Email settings") for more details.            ##</%text>
<%text>##                                                                            ##</%text>
<%text>## It is recommended to use a valid sender address that passes access         ##</%text>
<%text>## validation and spam filtering in mail servers.                             ##</%text>
<%text>################################################################################</%text>

<%text>## 'From' header for application emails. You can optionally add a name.</%text>
<%text>## Default:</%text>
#app_email_from = Kallithea
<%text>## Examples:</%text>
#app_email_from = Kallithea <kallithea-noreply@example.com>
#app_email_from = kallithea-noreply@example.com

<%text>## Subject prefix for application emails.</%text>
<%text>## A space between this prefix and the real subject is automatically added.</%text>
<%text>## Default:</%text>
#email_prefix =
<%text>## Example:</%text>
#email_prefix = [Kallithea]

<%text>## Recipients for error emails and fallback recipients of application mails.</%text>
<%text>## Multiple addresses can be specified, comma-separated.</%text>
<%text>## Only addresses are allowed, do not add any name part.</%text>
<%text>## Default:</%text>
#email_to =
<%text>## Examples:</%text>
#email_to = admin@example.com
#email_to = admin@example.com,another_admin@example.com
email_to =

<%text>## 'From' header for error emails. You can optionally add a name.</%text>
<%text>## Default: (none)</%text>
<%text>## Examples:</%text>
#error_email_from = Kallithea Errors <kallithea-noreply@example.com>
#error_email_from = kallithea_errors@example.com
error_email_from =

<%text>## SMTP server settings</%text>
<%text>## If specifying credentials, make sure to use secure connections.</%text>
<%text>## Default: Send unencrypted unauthenticated mails to the specified smtp_server.</%text>
<%text>## For "SSL", use smtp_use_ssl = true and smtp_port = 465.</%text>
<%text>## For "STARTTLS", use smtp_use_tls = true and smtp_port = 587.</%text>
smtp_server =
#smtp_username =
#smtp_password =
smtp_port =
#smtp_use_ssl = false
#smtp_use_tls = false

%if http_server != 'uwsgi':
<%text>## Entry point for 'gearbox serve'</%text>
[server:main]
host = ${host}
port = ${port}

%if http_server == 'gearbox':
<%text>## Gearbox default web server ##</%text>
use = egg:gearbox#wsgiref
<%text>## nr of worker threads to spawn</%text>
threadpool_workers = 1
<%text>## max request before thread respawn</%text>
threadpool_max_requests = 100
<%text>## option to use threads of process</%text>
use_threadpool = true

%elif http_server == 'gevent':
<%text>## Gearbox gevent web server ##</%text>
use = egg:gearbox#gevent

%elif http_server == 'waitress':
<%text>## WAITRESS ##</%text>
use = egg:waitress#main
<%text>## number of worker threads</%text>
threads = 1
<%text>## MAX BODY SIZE 100GB</%text>
max_request_body_size = 107374182400
<%text>## use poll instead of select, fixes fd limits, may not work on old</%text>
<%text>## windows systems.</%text>
#asyncore_use_poll = True

%elif http_server == 'gunicorn':
<%text>## GUNICORN ##</%text>
use = egg:gunicorn#main
<%text>## number of process workers. You must set `instance_id = *` when this option</%text>
<%text>## is set to more than one worker</%text>
workers = 4
<%text>## process name</%text>
proc_name = kallithea
<%text>## type of worker class, one of sync, eventlet, gevent, tornado</%text>
<%text>## recommended for bigger setup is using of of other than sync one</%text>
worker_class = sync
max_requests = 1000
<%text>## amount of time a worker can handle request before it gets killed and</%text>
<%text>## restarted</%text>
timeout = 3600

%endif
%else:
<%text>## UWSGI ##</%text>
<%text>## run with uwsgi --ini-paste-logged <inifile.ini></%text>
[uwsgi]
socket = /tmp/uwsgi.sock
master = true
http = ${host}:${port}

<%text>## set as daemon and redirect all output to file</%text>
#daemonize = ./uwsgi_kallithea.log

<%text>## master process PID</%text>
pidfile = ./uwsgi_kallithea.pid

<%text>## stats server with workers statistics, use uwsgitop</%text>
<%text>## for monitoring, `uwsgitop 127.0.0.1:1717`</%text>
stats = 127.0.0.1:1717
memory-report = true

<%text>## log 5XX errors</%text>
log-5xx = true

<%text>## Set the socket listen queue size.</%text>
listen = 128

<%text>## Gracefully Reload workers after the specified amount of managed requests</%text>
<%text>## (avoid memory leaks).</%text>
max-requests = 1000

<%text>## enable large buffers</%text>
buffer-size = 65535

<%text>## socket and http timeouts ##</%text>
http-timeout = 3600
socket-timeout = 3600

<%text>## Log requests slower than the specified number of milliseconds.</%text>
log-slow = 10

<%text>## Exit if no app can be loaded.</%text>
need-app = true

<%text>## Set lazy mode (load apps in workers instead of master).</%text>
lazy = true

<%text>## scaling ##</%text>
<%text>## set cheaper algorithm to use, if not set default will be used</%text>
cheaper-algo = spare

<%text>## minimum number of workers to keep at all times</%text>
cheaper = 1

<%text>## number of workers to spawn at startup</%text>
cheaper-initial = 1

<%text>## maximum number of workers that can be spawned</%text>
workers = 4

<%text>## how many workers should be spawned at a time</%text>
cheaper-step = 1

%endif
<%text>## middleware for hosting the WSGI application under a URL prefix</%text>
#[filter:proxy-prefix]
#use = egg:PasteDeploy#prefix
#prefix = /<your-prefix>

[app:main]
use = egg:kallithea
<%text>## enable proxy prefix middleware</%text>
#filter-with = proxy-prefix

full_stack = true
static_files = true

<%text>## Internationalization (see setup documentation for details)</%text>
<%text>## By default, the languages requested by the browser are used if available, with English as default.</%text>
<%text>## Set i18n.enabled=false to disable automatic language choice.</%text>
#i18n.enabled = true
<%text>## To Force a language, set i18n.enabled=false and specify the language in i18n.lang.</%text>
<%text>## Valid values are the names of subdirectories in kallithea/i18n with a LC_MESSAGES/kallithea.mo</%text>
#i18n.lang = en

cache_dir = %(here)s/data
index_dir = %(here)s/data/index

<%text>## uncomment and set this path to use archive download cache</%text>
archive_cache_dir = %(here)s/tarballcache

<%text>## change this to unique ID for security</%text>
app_instance_uuid = ${uuid()}

<%text>## cut off limit for large diffs (size in bytes)</%text>
cut_off_limit = 256000

<%text>## force https in Kallithea, fixes https redirects, assumes it's always https</%text>
force_https = false

<%text>## use Strict-Transport-Security headers</%text>
use_htsts = false

<%text>## number of commits stats will parse on each iteration</%text>
commit_parse_limit = 25

<%text>## Path to Python executable to be used for git hooks.</%text>
<%text>## This value will be written inside the git hook scripts as the text</%text>
<%text>## after '#!' (shebang). When empty or not defined, the value of</%text>
<%text>## 'sys.executable' at the time of installation of the git hooks is</%text>
<%text>## used, which is correct in many cases but for example not when using uwsgi.</%text>
<%text>## If you change this setting, you should reinstall the Git hooks via</%text>
<%text>## Admin > Settings > Remap and Rescan.</%text>
# git_hook_interpreter = /srv/kallithea/venv/bin/python2
%if git_hook_interpreter:
git_hook_interpreter = ${git_hook_interpreter}
%endif

<%text>## path to git executable</%text>
git_path = git

<%text>## git rev filter option, --all is the default filter, if you need to</%text>
<%text>## hide all refs in changelog switch this to --branches --tags</%text>
#git_rev_filter = --branches --tags

<%text>## RSS feed options</%text>
rss_cut_off_limit = 256000
rss_items_per_page = 10
rss_include_diff = false

<%text>## options for showing and identifying changesets</%text>
show_sha_length = 12
show_revision_number = false

<%text>## Canonical URL to use when creating full URLs in UI and texts.</%text>
<%text>## Useful when the site is available under different names or protocols.</%text>
<%text>## Defaults to what is provided in the WSGI environment.</%text>
#canonical_url = https://kallithea.example.com/repos

<%text>## gist URL alias, used to create nicer urls for gist. This should be an</%text>
<%text>## url that does rewrites to _admin/gists/<gistid>.</%text>
<%text>## example: http://gist.example.com/{gistid}. Empty means use the internal</%text>
<%text>## Kallithea url, ie. http[s]://kallithea.example.com/_admin/gists/<gistid></%text>
gist_alias_url =

<%text>## default encoding used to convert from and to unicode</%text>
<%text>## can be also a comma separated list of encoding in case of mixed encodings</%text>
default_encoding = utf-8

<%text>## Set Mercurial encoding, similar to setting HGENCODING before launching Kallithea</%text>
hgencoding = utf-8

<%text>## issue tracker for Kallithea (leave blank to disable, absent for default)</%text>
#bugtracker = https://bitbucket.org/conservancy/kallithea/issues

<%text>## issue tracking mapping for commit messages, comments, PR descriptions, ...</%text>
<%text>## Refer to the documentation ("Integration with issue trackers") for more details.</%text>

<%text>## regular expression to match issue references</%text>
<%text>## This pattern may/should contain parenthesized groups, that can</%text>
<%text>## be referred to in issue_server_link or issue_sub using Python backreferences</%text>
<%text>## (e.g. \1, \2, ...). You can also create named groups with '(?P<groupname>)'.</%text>
<%text>## To require mandatory whitespace before the issue pattern, use:</%text>
<%text>## (?:^|(?<=\s)) before the actual pattern, and for mandatory whitespace</%text>
<%text>## behind the issue pattern, use (?:$|(?=\s)) after the actual pattern.</%text>

issue_pat = #(\d+)

<%text>## server url to the issue</%text>
<%text>## This pattern may/should contain backreferences to parenthesized groups in issue_pat.</%text>
<%text>## A backreference can be \1, \2, ... or \g<groupname> if you specified a named group</%text>
<%text>## called 'groupname' in issue_pat.</%text>
<%text>## The special token {repo} is replaced with the full repository name</%text>
<%text>## including repository groups, while {repo_name} is replaced with just</%text>
<%text>## the name of the repository.</%text>

issue_server_link = https://issues.example.com/{repo}/issue/\1

<%text>## substitution pattern to use as the link text</%text>
<%text>## If issue_sub is empty, the text matched by issue_pat is retained verbatim</%text>
<%text>## for the link text. Otherwise, the link text is that of issue_sub, with any</%text>
<%text>## backreferences to groups in issue_pat replaced.</%text>

issue_sub =

<%text>## issue_pat, issue_server_link and issue_sub can have suffixes to specify</%text>
<%text>## multiple patterns, to other issues server, wiki or others</%text>
<%text>## below an example how to create a wiki pattern</%text>
# wiki-some-id -> https://wiki.example.com/some-id

#issue_pat_wiki = wiki-(\S+)
#issue_server_link_wiki = https://wiki.example.com/\1
#issue_sub_wiki = WIKI-\1

<%text>## alternative return HTTP header for failed authentication. Default HTTP</%text>
<%text>## response is 401 HTTPUnauthorized. Currently Mercurial clients have trouble with</%text>
<%text>## handling that. Set this variable to 403 to return HTTPForbidden</%text>
auth_ret_code =

<%text>## allows to change the repository location in settings page</%text>
allow_repo_location_change = True

<%text>## allows to setup custom hooks in settings page</%text>
allow_custom_hooks_settings = True

<%text>## extra extensions for indexing, space separated and without the leading '.'.</%text>
# index.extensions =
#    gemfile
#    lock

<%text>## extra filenames for indexing, space separated</%text>
# index.filenames =
#    .dockerignore
#    .editorconfig
#    INSTALL
#    CHANGELOG

<%text>####################################</%text>
<%text>###           SSH CONFIG        ####</%text>
<%text>####################################</%text>

<%text>## SSH is disabled by default, until an Administrator decides to enable it.</%text>
ssh_enabled = false

<%text>## File where users' SSH keys will be stored *if* ssh_enabled is true.</%text>
#ssh_authorized_keys = /home/kallithea/.ssh/authorized_keys
%if user_home_path:
ssh_authorized_keys = ${user_home_path}/.ssh/authorized_keys
%endif

<%text>## Path to be used in ssh_authorized_keys file to invoke kallithea-cli with ssh-serve.</%text>
#kallithea_cli_path = /srv/kallithea/venv/bin/kallithea-cli
%if kallithea_cli_path:
kallithea_cli_path = ${kallithea_cli_path}
%endif

<%text>## Locale to be used in the ssh-serve command.</%text>
<%text>## This is needed because an SSH client may try to use its own locale</%text>
<%text>## settings, which may not be available on the server.</%text>
<%text>## See `locale -a` for valid values on this system.</%text>
#ssh_locale = C.UTF-8
%if ssh_locale:
ssh_locale = ${ssh_locale}
%endif

<%text>####################################</%text>
<%text>###        CELERY CONFIG        ####</%text>
<%text>####################################</%text>

use_celery = false

<%text>## Example: connect to the virtual host 'rabbitmqhost' on localhost as rabbitmq:</%text>
broker.url = amqp://rabbitmq:qewqew@localhost:5672/rabbitmqhost

celery.imports = kallithea.lib.celerylib.tasks
celery.accept.content = pickle
celery.result.backend = amqp
celery.result.dburi = amqp://
celery.result.serialier = json

#celery.send.task.error.emails = true
#celery.amqp.task.result.expires = 18000

celeryd.concurrency = 2
celeryd.max.tasks.per.child = 1

<%text>## If true, tasks will never be sent to the queue, but executed locally instead.</%text>
celery.always.eager = false

<%text>####################################</%text>
<%text>###         BEAKER CACHE        ####</%text>
<%text>####################################</%text>

beaker.cache.data_dir = %(here)s/data/cache/data
beaker.cache.lock_dir = %(here)s/data/cache/lock

beaker.cache.regions = short_term,long_term,sql_cache_short

beaker.cache.short_term.type = memory
beaker.cache.short_term.expire = 60
beaker.cache.short_term.key_length = 256

beaker.cache.long_term.type = memory
beaker.cache.long_term.expire = 36000
beaker.cache.long_term.key_length = 256

beaker.cache.sql_cache_short.type = memory
beaker.cache.sql_cache_short.expire = 10
beaker.cache.sql_cache_short.key_length = 256

<%text>####################################</%text>
<%text>###       BEAKER SESSION        ####</%text>
<%text>####################################</%text>

<%text>## Name of session cookie. Should be unique for a given host and path, even when running</%text>
<%text>## on different ports. Otherwise, cookie sessions will be shared and messed up.</%text>
session.key = kallithea
<%text>## Sessions should always only be accessible by the browser, not directly by JavaScript.</%text>
session.httponly = true
<%text>## Session lifetime. 2592000 seconds is 30 days.</%text>
session.timeout = 2592000

<%text>## Server secret used with HMAC to ensure integrity of cookies.</%text>
session.secret = ${uuid()}
<%text>## Further, encrypt the data with AES.</%text>
#session.encrypt_key = <key_for_encryption>
#session.validate_key = <validation_key>

<%text>## Type of storage used for the session, current types are</%text>
<%text>## dbm, file, memcached, database, and memory.</%text>

<%text>## File system storage of session data. (default)</%text>
#session.type = file

<%text>## Cookie only, store all session data inside the cookie. Requires secure secrets.</%text>
#session.type = cookie

<%text>## Database storage of session data.</%text>
#session.type = ext:database
#session.sa.url = postgresql://postgres:qwe@localhost/kallithea
#session.table_name = db_session

<%text>############################</%text>
<%text>## ERROR HANDLING SYSTEMS ##</%text>
<%text>############################</%text>

# Propagate email settings to ErrorReporter of TurboGears2
# You do not normally need to change these lines
get trace_errors.error_email = email_to
get trace_errors.smtp_server = smtp_server
get trace_errors.smtp_port = smtp_port
get trace_errors.from_address = error_email_from

%if error_aggregation_service == 'appenlight':
<%text>####################</%text>
<%text>### [appenlight] ###</%text>
<%text>####################</%text>

<%text>## AppEnlight is tailored to work with Kallithea, see</%text>
<%text>## http://appenlight.com for details how to obtain an account</%text>
<%text>## you must install python package `appenlight_client` to make it work</%text>

<%text>## appenlight enabled</%text>
appenlight = false

appenlight.server_url = https://api.appenlight.com
appenlight.api_key = YOUR_API_KEY

<%text>## TWEAK AMOUNT OF INFO SENT HERE</%text>

<%text>## enables 404 error logging (default False)</%text>
appenlight.report_404 = false

<%text>## time in seconds after request is considered being slow (default 1)</%text>
appenlight.slow_request_time = 1

<%text>## record slow requests in application</%text>
<%text>## (needs to be enabled for slow datastore recording and time tracking)</%text>
appenlight.slow_requests = true

<%text>## enable hooking to application loggers</%text>
#appenlight.logging = true

<%text>## minimum log level for log capture</%text>
#appenlight.logging.level = WARNING

<%text>## send logs only from erroneous/slow requests</%text>
<%text>## (saves API quota for intensive logging)</%text>
appenlight.logging_on_error = false

<%text>## list of additional keywords that should be grabbed from environ object</%text>
<%text>## can be string with comma separated list of words in lowercase</%text>
<%text>## (by default client will always send following info:</%text>
<%text>## 'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE' + all keys that</%text>
<%text>## start with HTTP* this list be extended with additional keywords here</%text>
appenlight.environ_keys_whitelist =

<%text>## list of keywords that should be blanked from request object</%text>
<%text>## can be string with comma separated list of words in lowercase</%text>
<%text>## (by default client will always blank keys that contain following words</%text>
<%text>## 'password', 'passwd', 'pwd', 'auth_tkt', 'secret', 'csrf'</%text>
<%text>## this list be extended with additional keywords set here</%text>
appenlight.request_keys_blacklist =

<%text>## list of namespaces that should be ignores when gathering log entries</%text>
<%text>## can be string with comma separated list of namespaces</%text>
<%text>## (by default the client ignores own entries: appenlight_client.client)</%text>
appenlight.log_namespace_blacklist =

%elif error_aggregation_service == 'sentry':
<%text>################</%text>
<%text>### [sentry] ###</%text>
<%text>################</%text>

<%text>## sentry is a alternative open source error aggregator</%text>
<%text>## you must install python packages `sentry` and `raven` to enable</%text>

sentry.dsn = YOUR_DNS
sentry.servers =
sentry.name =
sentry.key =
sentry.public_key =
sentry.secret_key =
sentry.project =
sentry.site =
sentry.include_paths =
sentry.exclude_paths =

%endif
<%text>################################################################################</%text>
<%text>## WARNING: *DEBUG MODE MUST BE OFF IN A PRODUCTION ENVIRONMENT*              ##</%text>
<%text>## Debug mode will enable the interactive debugging tool, allowing ANYONE to  ##</%text>
<%text>## execute malicious code after an exception is raised.                       ##</%text>
<%text>################################################################################</%text>
debug = false

<%text>##################################</%text>
<%text>###       LOGVIEW CONFIG       ###</%text>
<%text>##################################</%text>

logview.sqlalchemy = #faa
logview.pylons.templating = #bfb
logview.pylons.util = #eee

<%text>#########################################################</%text>
<%text>### DB CONFIGS - EACH DB WILL HAVE IT'S OWN CONFIG    ###</%text>
<%text>#########################################################</%text>

%if database_engine == 'sqlite':
# SQLITE [default]
sqlalchemy.url = sqlite:///%(here)s/kallithea.db?timeout=60

%elif database_engine == 'postgres':
# POSTGRESQL
sqlalchemy.url = postgresql://user:pass@localhost/kallithea

%elif database_engine == 'mysql':
# MySQL
sqlalchemy.url = mysql://user:pass@localhost/kallithea?charset=utf8

%endif
# see sqlalchemy docs for others

sqlalchemy.pool_recycle = 3600

<%text>################################</%text>
<%text>### ALEMBIC CONFIGURATION   ####</%text>
<%text>################################</%text>

[alembic]
script_location = kallithea:alembic

<%text>################################</%text>
<%text>### LOGGING CONFIGURATION   ####</%text>
<%text>################################</%text>

[loggers]
keys = root, routes, kallithea, sqlalchemy, tg, gearbox, beaker, templates, whoosh_indexer, werkzeug, backlash

[handlers]
keys = console, console_color, console_color_sql, null

[formatters]
keys = generic, color_formatter, color_formatter_sql

<%text>#############</%text>
<%text>## LOGGERS ##</%text>
<%text>#############</%text>

[logger_root]
level = NOTSET
handlers = console
# For coloring based on log level:
# handlers = console_color

[logger_routes]
level = WARN
handlers =
qualname = routes.middleware
<%text>## "level = DEBUG" logs the route matched and routing variables.</%text>

[logger_beaker]
level = WARN
handlers =
qualname = beaker.container

[logger_templates]
level = WARN
handlers =
qualname = pylons.templating

[logger_kallithea]
level = WARN
handlers =
qualname = kallithea

[logger_tg]
level = WARN
handlers =
qualname = tg

[logger_gearbox]
level = WARN
handlers =
qualname = gearbox

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
# For coloring based on log level and pretty printing of SQL:
# level = INFO
# handlers = console_color_sql
# propagate = 0

[logger_whoosh_indexer]
level = WARN
handlers =
qualname = whoosh_indexer

[logger_werkzeug]
level = WARN
handlers =
qualname = werkzeug

[logger_backlash]
level = WARN
handlers =
qualname = backlash

<%text>##############</%text>
<%text>## HANDLERS ##</%text>
<%text>##############</%text>

[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic

[handler_console_color]
# ANSI color coding based on log level
class = StreamHandler
args = (sys.stderr,)
formatter = color_formatter

[handler_console_color_sql]
# ANSI color coding and pretty printing of SQL statements
class = StreamHandler
args = (sys.stderr,)
formatter = color_formatter_sql

[handler_null]
class = NullHandler
args = ()

<%text>################</%text>
<%text>## FORMATTERS ##</%text>
<%text>################</%text>

[formatter_generic]
format = %(asctime)s.%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %Y-%m-%d %H:%M:%S

[formatter_color_formatter]
class = kallithea.lib.colored_formatter.ColorFormatter
format = %(asctime)s.%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %Y-%m-%d %H:%M:%S

[formatter_color_formatter_sql]
class = kallithea.lib.colored_formatter.ColorFormatterSql
format = %(asctime)s.%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %Y-%m-%d %H:%M:%S

<%text>#################</%text>
<%text>## SSH LOGGING ##</%text>
<%text>#################</%text>

# The default loggers use 'handler_console' that uses StreamHandler with
# destination 'sys.stderr'. In the context of the SSH server process, these log
# messages would be sent to the client, which is normally not what you want.
# By default, when running ssh-serve, just use NullHandler and disable logging
# completely. For other logging options, see:
# https://docs.python.org/2/library/logging.handlers.html

[ssh_serve:logger_root]
level = CRITICAL
handlers = null

# Note: If logging is configured with other handlers, they might need similar
# muting for ssh-serve too.
