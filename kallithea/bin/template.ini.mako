## -*- coding: utf-8 -*-
<%text>################################################################################</%text>
<%text>################################################################################</%text>
# Kallithea - config file generated with kallithea-config                      #
<%text>################################################################################</%text>
<%text>################################################################################</%text>

[DEFAULT]
debug = true
pdebug = false

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
<%text>## Multiple addresses can be specified, space-separated.</%text>
<%text>## Only addresses are allowed, do not add any name part.</%text>
<%text>## Default:</%text>
#email_to =
<%text>## Examples:</%text>
#email_to = admin@example.com
#email_to = admin@example.com another_admin@example.com

<%text>## 'From' header for error emails. You can optionally add a name.</%text>
<%text>## Default:</%text>
#error_email_from = pylons@yourapp.com
<%text>## Examples:</%text>
#error_email_from = Kallithea Errors <kallithea-noreply@example.com>
#error_email_from = paste_error@example.com

<%text>## SMTP server settings</%text>
<%text>## Only smtp_server is mandatory. All other settings take the specified default</%text>
<%text>## values.</%text>
#smtp_server = smtp.example.com
#smtp_username =
#smtp_password =
#smtp_port = 25
#smtp_use_tls = false
#smtp_use_ssl = false
<%text>## SMTP authentication parameters to use (e.g. LOGIN PLAIN CRAM-MD5, etc.).</%text>
<%text>## If empty, use any of the authentication parameters supported by the server.</%text>
#smtp_auth =

[server:main]
%if http_server == 'paste':
<%text>## PASTE ##</%text>
use = egg:Paste#http
<%text>## nr of worker threads to spawn</%text>
threadpool_workers = 5
<%text>## max request before thread respawn</%text>
threadpool_max_requests = 10
<%text>## option to use threads of process</%text>
use_threadpool = true

%elif http_server == 'waitress':
<%text>## WAITRESS ##</%text>
use = egg:waitress#main
<%text>## number of worker threads</%text>
threads = 5
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
workers = 1
<%text>## process name</%text>
proc_name = kallithea
<%text>## type of worker class, one of sync, eventlet, gevent, tornado</%text>
<%text>## recommended for bigger setup is using of of other than sync one</%text>
worker_class = sync
max_requests = 1000
<%text>## ammount of time a worker can handle request before it gets killed and</%text>
<%text>## restarted</%text>
timeout = 3600

%elif http_server == 'uwsgi':
<%text>## UWSGI ##</%text>
<%text>## run with uwsgi --ini-paste-logged <inifile.ini></%text>
[uwsgi]
socket = /tmp/uwsgi.sock
master = true
http = 127.0.0.1:5000

<%text>## set as deamon and redirect all output to file</%text>
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
listen = 256

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
<%text>## COMMON ##</%text>
host = ${host}
port = ${port}

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
<%text>## Available Languages:</%text>
<%text>## cs de fr hu ja nl_BE pl pt_BR ru sk zh_CN zh_TW</%text>
lang =
cache_dir = ${here}/data
index_dir = ${here}/data/index

<%text>## perform a full repository scan on each server start, this should be</%text>
<%text>## set to false after first startup, to allow faster server restarts.</%text>
initial_repo_scan = false

<%text>## uncomment and set this path to use archive download cache</%text>
archive_cache_dir = ${here}/tarballcache

<%text>## change this to unique ID for security</%text>
app_instance_uuid = ${uuid()}

<%text>## cut off limit for large diffs (size in bytes)</%text>
cut_off_limit = 256000

<%text>## use cache version of scm repo everywhere</%text>
vcs_full_cache = true

<%text>## force https in Kallithea, fixes https redirects, assumes it's always https</%text>
force_https = false

<%text>## use Strict-Transport-Security headers</%text>
use_htsts = false

<%text>## number of commits stats will parse on each iteration</%text>
commit_parse_limit = 25

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

<%text>## gist URL alias, used to create nicer urls for gist. This should be an</%text>
<%text>## url that does rewrites to _admin/gists/<gistid>.</%text>
<%text>## example: http://gist.example.com/{gistid}. Empty means use the internal</%text>
<%text>## Kallithea url, ie. http[s]://kallithea.example.com/_admin/gists/<gistid></%text>
gist_alias_url =

<%text>## white list of API enabled controllers. This allows to add list of</%text>
<%text>## controllers to which access will be enabled by api_key. eg: to enable</%text>
<%text>## api access to raw_files put `FilesController:raw`, to enable access to patches</%text>
<%text>## add `ChangesetController:changeset_patch`. This list should be "," separated</%text>
<%text>## Syntax is <ControllerClass>:<function>. Check debug logs for generated names</%text>
<%text>## Recommended settings below are commented out:</%text>
api_access_controllers_whitelist =
#    ChangesetController:changeset_patch,
#    ChangesetController:changeset_raw,
#    FilesController:raw,
#    FilesController:archivefile

<%text>## default encoding used to convert from and to unicode</%text>
<%text>## can be also a comma seperated list of encoding in case of mixed encodings</%text>
default_encoding = utf8

<%text>## issue tracker for Kallithea (leave blank to disable, absent for default)</%text>
#bugtracker = https://bitbucket.org/conservancy/kallithea/issues

<%text>## issue tracking mapping for commits messages</%text>
<%text>## comment out issue_pat, issue_server, issue_prefix to enable</%text>

<%text>## pattern to get the issues from commit messages</%text>
<%text>## default one used here is #<numbers> with a regex passive group for `#`</%text>
<%text>## {id} will be all groups matched from this pattern</%text>

issue_pat = (?:\s*#)(\d+)

<%text>## server url to the issue, each {id} will be replaced with match</%text>
<%text>## fetched from the regex and {repo} is replaced with full repository name</%text>
<%text>## including groups {repo_name} is replaced with just name of repo</%text>

issue_server_link = https://issues.example.com/{repo}/issue/{id}

<%text>## prefix to add to link to indicate it's an url</%text>
<%text>## #314 will be replaced by <issue_prefix><id></%text>

issue_prefix = #

<%text>## issue_pat, issue_server_link, issue_prefix can have suffixes to specify</%text>
<%text>## multiple patterns, to other issues server, wiki or others</%text>
<%text>## below an example how to create a wiki pattern</%text>
# wiki-some-id -> https://wiki.example.com/some-id

#issue_pat_wiki = (?:wiki-)(.+)
#issue_server_link_wiki = https://wiki.example.com/{id}
#issue_prefix_wiki = WIKI-

<%text>## alternative return HTTP header for failed authentication. Default HTTP</%text>
<%text>## response is 401 HTTPUnauthorized. Currently Mercurial clients have trouble with</%text>
<%text>## handling that. Set this variable to 403 to return HTTPForbidden</%text>
auth_ret_code =

<%text>## locking return code. When repository is locked return this HTTP code. 2XX</%text>
<%text>## codes don't break the transactions while 4XX codes do</%text>
lock_ret_code = 423

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
<%text>###        CELERY CONFIG        ####</%text>
<%text>####################################</%text>

use_celery = false
broker.host = localhost
broker.vhost = rabbitmqhost
broker.port = 5672
broker.user = rabbitmq
broker.password = qweqwe

celery.imports = kallithea.lib.celerylib.tasks

celery.result.backend = amqp
celery.result.dburi = amqp://
celery.result.serialier = json

#celery.send.task.error.emails = true
#celery.amqp.task.result.expires = 18000

celeryd.concurrency = 2
#celeryd.log.file = celeryd.log
celeryd.log.level = DEBUG
celeryd.max.tasks.per.child = 1

<%text>## tasks will never be sent to the queue, but executed locally instead.</%text>
celery.always.eager = false

<%text>####################################</%text>
<%text>###         BEAKER CACHE        ####</%text>
<%text>####################################</%text>

beaker.cache.data_dir = ${here}/data/cache/data
beaker.cache.lock_dir = ${here}/data/cache/lock

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
beaker.session.key = kallithea
<%text>## Sessions should always only be accessible by the browser, not directly by JavaScript.</%text>
beaker.session.httponly = true
<%text>## Session lifetime. 2592000 seconds is 30 days.</%text>
beaker.session.timeout = 2592000

<%text>## Server secret used with HMAC to ensure integrity of cookies.</%text>
beaker.session.secret = ${uuid()}
<%text>## Further, encrypt the data with AES.</%text>
#beaker.session.encrypt_key = <key_for_encryption>
#beaker.session.validate_key = <validation_key>

<%text>## Type of storage used for the session, current types are</%text>
<%text>## dbm, file, memcached, database, and memory.</%text>

<%text>## File system storage of session data. (default)</%text>
#beaker.session.type = file

<%text>## Cookie only, store all session data inside the cookie. Requires secure secrets.</%text>
#beaker.session.type = cookie

<%text>## Database storage of session data.</%text>
#beaker.session.type = ext:database
#beaker.session.sa.url = postgresql://postgres:qwe@localhost/kallithea
#beaker.session.table_name = db_session

%if error_aggregation_service == 'errormator':
<%text>############################</%text>
<%text>## ERROR HANDLING SYSTEMS ##</%text>
<%text>############################</%text>

<%text>####################</%text>
<%text>### [errormator] ###</%text>
<%text>####################</%text>

<%text>## Errormator is tailored to work with Kallithea, see</%text>
<%text>## http://errormator.com for details how to obtain an account</%text>
<%text>## you must install python package `errormator_client` to make it work</%text>

<%text>## errormator enabled</%text>
errormator = false

errormator.server_url = https://api.errormator.com
errormator.api_key = YOUR_API_KEY

<%text>## TWEAK AMOUNT OF INFO SENT HERE</%text>

<%text>## enables 404 error logging (default False)</%text>
errormator.report_404 = false

<%text>## time in seconds after request is considered being slow (default 1)</%text>
errormator.slow_request_time = 1

<%text>## record slow requests in application</%text>
<%text>## (needs to be enabled for slow datastore recording and time tracking)</%text>
errormator.slow_requests = true

<%text>## enable hooking to application loggers</%text>
#errormator.logging = true

<%text>## minimum log level for log capture</%text>
#errormator.logging.level = WARNING

<%text>## send logs only from erroneous/slow requests</%text>
<%text>## (saves API quota for intensive logging)</%text>
errormator.logging_on_error = false

<%text>## list of additonal keywords that should be grabbed from environ object</%text>
<%text>## can be string with comma separated list of words in lowercase</%text>
<%text>## (by default client will always send following info:</%text>
<%text>## 'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'CONTENT_TYPE' + all keys that</%text>
<%text>## start with HTTP* this list be extended with additional keywords here</%text>
errormator.environ_keys_whitelist =

<%text>## list of keywords that should be blanked from request object</%text>
<%text>## can be string with comma separated list of words in lowercase</%text>
<%text>## (by default client will always blank keys that contain following words</%text>
<%text>## 'password', 'passwd', 'pwd', 'auth_tkt', 'secret', 'csrf'</%text>
<%text>## this list be extended with additional keywords set here</%text>
errormator.request_keys_blacklist =

<%text>## list of namespaces that should be ignores when gathering log entries</%text>
<%text>## can be string with comma separated list of namespaces</%text>
<%text>## (by default the client ignores own entries: errormator_client.client)</%text>
errormator.log_namespace_blacklist =

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
<%text>## WARNING: *THE LINE BELOW MUST BE UNCOMMENTED ON A PRODUCTION ENVIRONMENT*  ##</%text>
<%text>## Debug mode will enable the interactive debugging tool, allowing ANYONE to  ##</%text>
<%text>## execute malicious code after an exception is raised.                       ##</%text>
<%text>################################################################################</%text>
set debug = false

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
sqlalchemy.db1.url = sqlite:///${here}/kallithea.db?timeout=60

%elif database_engine == 'postgres':
# POSTGRESQL
sqlalchemy.db1.url = postgresql://user:pass@localhost/kallithea

%elif database_engine == 'mysql':
# MySQL
sqlalchemy.db1.url = mysql://user:pass@localhost/kallithea

%endif
# see sqlalchemy docs for others

sqlalchemy.db1.echo = false
sqlalchemy.db1.pool_recycle = 3600
sqlalchemy.db1.convert_unicode = true

<%text>################################</%text>
<%text>### LOGGING CONFIGURATION   ####</%text>
<%text>################################</%text>

[loggers]
keys = root, routes, kallithea, sqlalchemy, beaker, templates, whoosh_indexer

[handlers]
keys = console, console_sql

[formatters]
keys = generic, color_formatter, color_formatter_sql

<%text>#############</%text>
<%text>## LOGGERS ##</%text>
<%text>#############</%text>

[logger_root]
level = NOTSET
handlers = console

[logger_routes]
level = DEBUG
handlers =
qualname = routes.middleware
<%text>## "level = DEBUG" logs the route matched and routing variables.</%text>
propagate = 1

[logger_beaker]
level = DEBUG
handlers =
qualname = beaker.container
propagate = 1

[logger_templates]
level = INFO
handlers =
qualname = pylons.templating
propagate = 1

[logger_kallithea]
level = DEBUG
handlers =
qualname = kallithea
propagate = 1

[logger_sqlalchemy]
level = INFO
handlers = console_sql
qualname = sqlalchemy.engine
propagate = 0

[logger_whoosh_indexer]
level = DEBUG
handlers =
qualname = whoosh_indexer
propagate = 1

<%text>##############</%text>
<%text>## HANDLERS ##</%text>
<%text>##############</%text>

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = INFO
formatter = generic

[handler_console_sql]
class = StreamHandler
args = (sys.stderr,)
level = WARN
formatter = generic

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
