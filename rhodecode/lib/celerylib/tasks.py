from celery.decorators import task

import os
import traceback
from time import mktime
from operator import itemgetter

from pylons import config
from pylons.i18n.translation import _

from rhodecode.lib.celerylib import run_task, locked_task, str2bool
from rhodecode.lib.helpers import person
from rhodecode.lib.smtp_mailer import SmtpMailer
from rhodecode.lib.utils import OrderedDict, add_cache
from rhodecode.model import init_model
from rhodecode.model import meta
from rhodecode.model.db import RhodeCodeUi

from vcs.backends import get_repo

from sqlalchemy import engine_from_config

add_cache(config)

try:
    import json
except ImportError:
    #python 2.5 compatibility
    import simplejson as json

__all__ = ['whoosh_index', 'get_commits_stats',
           'reset_user_password', 'send_email']

CELERY_ON = str2bool(config['app_conf'].get('use_celery'))

def get_session():
    if CELERY_ON:
        engine = engine_from_config(config, 'sqlalchemy.db1.')
        init_model(engine)
    sa = meta.Session()
    return sa

def get_repos_path():
    sa = get_session()
    q = sa.query(RhodeCodeUi).filter(RhodeCodeUi.ui_key == '/').one()
    return q.ui_value

@task
@locked_task
def whoosh_index(repo_location, full_index):
    log = whoosh_index.get_logger()
    from rhodecode.lib.indexers.daemon import WhooshIndexingDaemon
    index_location = config['index_dir']
    WhooshIndexingDaemon(index_location=index_location,
                         repo_location=repo_location, sa=get_session())\
                         .run(full_index=full_index)

@task
@locked_task
def get_commits_stats(repo_name, ts_min_y, ts_max_y):
    from rhodecode.model.db import Statistics, Repository
    log = get_commits_stats.get_logger()

    #for js data compatibilty
    author_key_cleaner = lambda k: person(k).replace('"', "")

    commits_by_day_author_aggregate = {}
    commits_by_day_aggregate = {}
    repos_path = get_repos_path()
    p = os.path.join(repos_path, repo_name)
    repo = get_repo(p)

    skip_date_limit = True
    parse_limit = 250 #limit for single task changeset parsing optimal for
    last_rev = 0
    last_cs = None
    timegetter = itemgetter('time')

    sa = get_session()

    dbrepo = sa.query(Repository)\
        .filter(Repository.repo_name == repo_name).scalar()
    cur_stats = sa.query(Statistics)\
        .filter(Statistics.repository == dbrepo).scalar()
    if cur_stats:
        last_rev = cur_stats.stat_on_revision
    if not repo.revisions:
        return True

    if last_rev == repo.revisions[-1] and len(repo.revisions) > 1:
        #pass silently without any work if we're not on first revision or 
        #current state of parsing revision(from db marker) is the last revision
        return True

    if cur_stats:
        commits_by_day_aggregate = OrderedDict(
                                       json.loads(
                                        cur_stats.commit_activity_combined))
        commits_by_day_author_aggregate = json.loads(cur_stats.commit_activity)

    log.debug('starting parsing %s', parse_limit)
    lmktime = mktime

    last_rev = last_rev + 1 if last_rev > 0 else last_rev
    for rev in repo.revisions[last_rev:last_rev + parse_limit]:
        last_cs = cs = repo.get_changeset(rev)
        k = lmktime([cs.date.timetuple()[0], cs.date.timetuple()[1],
                      cs.date.timetuple()[2], 0, 0, 0, 0, 0, 0])

        if commits_by_day_author_aggregate.has_key(author_key_cleaner(cs.author)):
            try:
                l = [timegetter(x) for x in commits_by_day_author_aggregate\
                        [author_key_cleaner(cs.author)]['data']]
                time_pos = l.index(k)
            except ValueError:
                time_pos = False

            if time_pos >= 0 and time_pos is not False:

                datadict = commits_by_day_author_aggregate\
                    [author_key_cleaner(cs.author)]['data'][time_pos]

                datadict["commits"] += 1
                datadict["added"] += len(cs.added)
                datadict["changed"] += len(cs.changed)
                datadict["removed"] += len(cs.removed)

            else:
                if k >= ts_min_y and k <= ts_max_y or skip_date_limit:

                    datadict = {"time":k,
                                "commits":1,
                                "added":len(cs.added),
                                "changed":len(cs.changed),
                                "removed":len(cs.removed),
                               }
                    commits_by_day_author_aggregate\
                        [author_key_cleaner(cs.author)]['data'].append(datadict)

        else:
            if k >= ts_min_y and k <= ts_max_y or skip_date_limit:
                commits_by_day_author_aggregate[author_key_cleaner(cs.author)] = {
                                    "label":author_key_cleaner(cs.author),
                                    "data":[{"time":k,
                                             "commits":1,
                                             "added":len(cs.added),
                                             "changed":len(cs.changed),
                                             "removed":len(cs.removed),
                                             }],
                                    "schema":["commits"],
                                    }

        #gather all data by day
        if commits_by_day_aggregate.has_key(k):
            commits_by_day_aggregate[k] += 1
        else:
            commits_by_day_aggregate[k] = 1

    overview_data = sorted(commits_by_day_aggregate.items(), key=itemgetter(0))
    if not commits_by_day_author_aggregate:
        commits_by_day_author_aggregate[author_key_cleaner(repo.contact)] = {
            "label":author_key_cleaner(repo.contact),
            "data":[0, 1],
            "schema":["commits"],
        }

    stats = cur_stats if cur_stats else Statistics()
    stats.commit_activity = json.dumps(commits_by_day_author_aggregate)
    stats.commit_activity_combined = json.dumps(overview_data)

    log.debug('last revison %s', last_rev)
    leftovers = len(repo.revisions[last_rev:])
    log.debug('revisions to parse %s', leftovers)

    if last_rev == 0 or leftovers < parse_limit:
        log.debug('getting code trending stats')
        stats.languages = json.dumps(__get_codes_stats(repo_name))

    stats.repository = dbrepo
    stats.stat_on_revision = last_cs.revision

    try:
        sa.add(stats)
        sa.commit()
    except:
        log.error(traceback.format_exc())
        sa.rollback()
        return False
    if len(repo.revisions) > 1:
        run_task(get_commits_stats, repo_name, ts_min_y, ts_max_y)

    return True

@task
def reset_user_password(user_email):
    log = reset_user_password.get_logger()
    from rhodecode.lib import auth
    from rhodecode.model.db import User

    try:
        try:
            sa = get_session()
            user = sa.query(User).filter(User.email == user_email).scalar()
            new_passwd = auth.PasswordGenerator().gen_password(8,
                             auth.PasswordGenerator.ALPHABETS_BIG_SMALL)
            if user:
                user.password = auth.get_crypt_password(new_passwd)
                sa.add(user)
                sa.commit()
                log.info('change password for %s', user_email)
            if new_passwd is None:
                raise Exception('unable to generate new password')

        except:
            log.error(traceback.format_exc())
            sa.rollback()

        run_task(send_email, user_email,
                 "Your new rhodecode password",
                 'Your new rhodecode password:%s' % (new_passwd))
        log.info('send new password mail to %s', user_email)


    except:
        log.error('Failed to update user password')
        log.error(traceback.format_exc())

    return True

@task
def send_email(recipients, subject, body):
    """
    Sends an email with defined parameters from the .ini files.
    
    
    :param recipients: list of recipients, it this is empty the defined email
        address from field 'email_to' is used instead
    :param subject: subject of the mail
    :param body: body of the mail
    """
    log = send_email.get_logger()
    email_config = config

    if not recipients:
        recipients = [email_config.get('email_to')]

    mail_from = email_config.get('app_email_from')
    user = email_config.get('smtp_username')
    passwd = email_config.get('smtp_password')
    mail_server = email_config.get('smtp_server')
    mail_port = email_config.get('smtp_port')
    tls = str2bool(email_config.get('smtp_use_tls'))
    ssl = str2bool(email_config.get('smtp_use_ssl'))

    try:
        m = SmtpMailer(mail_from, user, passwd, mail_server,
                       mail_port, ssl, tls)
        m.send(recipients, subject, body)
    except:
        log.error('Mail sending failed')
        log.error(traceback.format_exc())
        return False
    return True

@task
def create_repo_fork(form_data, cur_user):
    from rhodecode.model.repo import RepoModel
    from vcs import get_backend
    log = create_repo_fork.get_logger()
    repo_model = RepoModel(get_session())
    repo_model.create(form_data, cur_user, just_db=True, fork=True)
    repo_name = form_data['repo_name']
    repos_path = get_repos_path()
    repo_path = os.path.join(repos_path, repo_name)
    repo_fork_path = os.path.join(repos_path, form_data['fork_name'])
    alias = form_data['repo_type']

    log.info('creating repo fork %s as %s', repo_name, repo_path)
    backend = get_backend(alias)
    backend(str(repo_fork_path), create=True, src_url=str(repo_path))

def __get_codes_stats(repo_name):
    LANGUAGES_EXTENSIONS_MAP = {'scm': 'Scheme', 'asmx': 'VbNetAspx', 'Rout':
    'RConsole', 'rest': 'Rst', 'abap': 'ABAP', 'go': 'Go', 'phtml': 'HtmlPhp',
    'ns2': 'Newspeak', 'xml': 'EvoqueXml', 'sh-session': 'BashSession', 'ads':
    'Ada', 'clj': 'Clojure', 'll': 'Llvm', 'ebuild': 'Bash', 'adb': 'Ada',
    'ada': 'Ada', 'c++-objdump': 'CppObjdump', 'aspx':
    'VbNetAspx', 'ksh': 'Bash', 'coffee': 'CoffeeScript', 'vert': 'GLShader',
    'Makefile.*': 'Makefile', 'di': 'D', 'dpatch': 'DarcsPatch', 'rake':
    'Ruby', 'moo': 'MOOCode', 'erl-sh': 'ErlangShell', 'geo': 'GLShader',
    'pov': 'Povray', 'bas': 'VbNet', 'bat': 'Batch', 'd': 'D', 'lisp':
    'CommonLisp', 'h': 'C', 'rbx': 'Ruby', 'tcl': 'Tcl', 'c++': 'Cpp', 'md':
    'MiniD', '.vimrc': 'Vim', 'xsd': 'Xml', 'ml': 'Ocaml', 'el': 'CommonLisp',
    'befunge': 'Befunge', 'xsl': 'Xslt', 'pyx': 'Cython', 'cfm':
    'ColdfusionHtml', 'evoque': 'Evoque', 'cfg': 'Ini', 'htm': 'Html',
    'Makefile': 'Makefile', 'cfc': 'ColdfusionHtml', 'tex': 'Tex', 'cs':
    'CSharp', 'mxml': 'Mxml', 'patch': 'Diff', 'apache.conf': 'ApacheConf',
    'scala': 'Scala', 'applescript': 'AppleScript', 'GNUmakefile': 'Makefile',
    'c-objdump': 'CObjdump', 'lua': 'Lua', 'apache2.conf': 'ApacheConf', 'rb':
    'Ruby', 'gemspec': 'Ruby', 'rl': 'RagelObjectiveC', 'vala': 'Vala', 'tmpl':
    'Cheetah', 'bf': 'Brainfuck', 'plt': 'Gnuplot', 'G': 'AntlrRuby', 'xslt':
    'Xslt', 'flxh': 'Felix', 'asax': 'VbNetAspx', 'Rakefile': 'Ruby', 'S': 'S',
    'wsdl': 'Xml', 'js': 'Javascript', 'autodelegate': 'Myghty', 'properties':
    'Ini', 'bash': 'Bash', 'c': 'C', 'g': 'AntlrRuby', 'r3': 'Rebol', 's':
    'Gas', 'ashx': 'VbNetAspx', 'cxx': 'Cpp', 'boo': 'Boo', 'prolog': 'Prolog',
    'sqlite3-console': 'SqliteConsole', 'cl': 'CommonLisp', 'cc': 'Cpp', 'pot':
    'Gettext', 'vim': 'Vim', 'pxi': 'Cython', 'yaml': 'Yaml', 'SConstruct':
    'Python', 'diff': 'Diff', 'txt': 'Text', 'cw': 'Redcode', 'pxd': 'Cython',
    'plot': 'Gnuplot', 'java': 'Java', 'hrl': 'Erlang', 'py': 'Python',
    'makefile': 'Makefile', 'squid.conf': 'SquidConf', 'asm': 'Nasm', 'toc':
    'Tex', 'kid': 'Genshi', 'rhtml': 'Rhtml', 'po': 'Gettext', 'pl': 'Prolog',
    'pm': 'Perl', 'hx': 'Haxe', 'ascx': 'VbNetAspx', 'ooc': 'Ooc', 'asy':
    'Asymptote', 'hs': 'Haskell', 'SConscript': 'Python', 'pytb':
    'PythonTraceback', 'myt': 'Myghty', 'hh': 'Cpp', 'R': 'S', 'aux': 'Tex',
    'rst': 'Rst', 'cpp-objdump': 'CppObjdump', 'lgt': 'Logtalk', 'rss': 'Xml',
    'flx': 'Felix', 'b': 'Brainfuck', 'f': 'Fortran', 'rbw': 'Ruby',
    '.htaccess': 'ApacheConf', 'cxx-objdump': 'CppObjdump', 'j': 'ObjectiveJ',
    'mll': 'Ocaml', 'yml': 'Yaml', 'mu': 'MuPAD', 'r': 'Rebol', 'ASM': 'Nasm',
    'erl': 'Erlang', 'mly': 'Ocaml', 'mo': 'Modelica', 'def': 'Modula2', 'ini':
    'Ini', 'control': 'DebianControl', 'vb': 'VbNet', 'vapi': 'Vala', 'pro':
    'Prolog', 'spt': 'Cheetah', 'mli': 'Ocaml', 'as': 'ActionScript3', 'cmd':
    'Batch', 'cpp': 'Cpp', 'io': 'Io', 'tac': 'Python', 'haml': 'Haml', 'rkt':
    'Racket', 'st':'Smalltalk', 'inc': 'Povray', 'pas': 'Delphi', 'cmake':
    'CMake', 'csh':'Tcsh', 'hpp': 'Cpp', 'feature': 'Gherkin', 'html': 'Html',
    'php':'Php', 'php3':'Php', 'php4':'Php', 'php5':'Php', 'xhtml': 'Html',
    'hxx': 'Cpp', 'eclass': 'Bash', 'css': 'Css',
    'frag': 'GLShader', 'd-objdump': 'DObjdump', 'weechatlog': 'IrcLogs',
    'tcsh': 'Tcsh', 'objdump': 'Objdump', 'pyw': 'Python', 'h++': 'Cpp',
    'py3tb': 'Python3Traceback', 'jsp': 'Jsp', 'sql': 'Sql', 'mak': 'Makefile',
    'php': 'Php', 'mao': 'Mako', 'man': 'Groff', 'dylan': 'Dylan', 'sass':
    'Sass', 'cfml': 'ColdfusionHtml', 'darcspatch': 'DarcsPatch', 'tpl':
    'Smarty', 'm': 'ObjectiveC', 'f90': 'Fortran', 'mod': 'Modula2', 'sh':
    'Bash', 'lhs': 'LiterateHaskell', 'sources.list': 'SourcesList', 'axd':
    'VbNetAspx', 'sc': 'Python'}

    repos_path = get_repos_path()
    p = os.path.join(repos_path, repo_name)
    repo = get_repo(p)
    tip = repo.get_changeset()
    code_stats = {}

    def aggregate(cs):
        for f in cs[2]:
            ext = f.extension
            key = LANGUAGES_EXTENSIONS_MAP.get(ext, ext)
            key = key or ext
            if ext in LANGUAGES_EXTENSIONS_MAP.keys() and not f.is_binary:
                if code_stats.has_key(key):
                    code_stats[key] += 1
                else:
                    code_stats[key] = 1

    map(aggregate, tip.walk('/'))

    return code_stats or {}




