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
kallithea.lib.celerylib.tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea task modules, containing all task that suppose to be run
by celery daemon

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 6, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import email.utils
import os
import traceback
from collections import OrderedDict
from operator import itemgetter
from time import mktime

import celery.utils.log
from tg import config

import kallithea
from kallithea.lib import celerylib, ext_json
from kallithea.lib.helpers import person
from kallithea.lib.hooks import log_create_repository
from kallithea.lib.rcmail.smtp_mailer import SmtpMailer
from kallithea.lib.utils import action_logger
from kallithea.lib.utils2 import ascii_bytes, str2bool
from kallithea.lib.vcs.utils import author_email
from kallithea.model.db import RepoGroup, Repository, Statistics, User


__all__ = ['whoosh_index', 'get_commits_stats', 'send_email']


log = celery.utils.log.get_task_logger(__name__)


@celerylib.task
@celerylib.locked_task
@celerylib.dbsession
def whoosh_index(repo_location, full_index):
    from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
    celerylib.get_session() # initialize database connection

    index_location = config['index_dir']
    WhooshIndexingDaemon(index_location=index_location,
                         repo_location=repo_location) \
                         .run(full_index=full_index)


# for js data compatibility cleans the key for person from '
def akc(k):
    return person(k).replace('"', '')


@celerylib.task
@celerylib.dbsession
def get_commits_stats(repo_name, ts_min_y, ts_max_y, recurse_limit=100):
    DBS = celerylib.get_session()
    lockkey = celerylib.__get_lockkey('get_commits_stats', repo_name, ts_min_y,
                            ts_max_y)
    lockkey_path = config.get('cache_dir') or config['app_conf']['cache_dir']  # Backward compatibility for TurboGears < 2.4

    log.info('running task with lockkey %s', lockkey)

    try:
        lock = celerylib.DaemonLock(os.path.join(lockkey_path, lockkey))

        co_day_auth_aggr = {}
        commits_by_day_aggregate = {}
        repo = Repository.get_by_repo_name(repo_name)
        if repo is None:
            return True

        repo = repo.scm_instance
        repo_size = repo.count()
        # return if repo have no revisions
        if repo_size < 1:
            lock.release()
            return True

        skip_date_limit = True
        parse_limit = int(config.get('commit_parse_limit'))
        last_rev = None
        last_cs = None
        timegetter = itemgetter('time')

        dbrepo = DBS.query(Repository) \
            .filter(Repository.repo_name == repo_name).scalar()
        cur_stats = DBS.query(Statistics) \
            .filter(Statistics.repository == dbrepo).scalar()

        if cur_stats is not None:
            last_rev = cur_stats.stat_on_revision

        if last_rev == repo.get_changeset().revision and repo_size > 1:
            # pass silently without any work if we're not on first revision or
            # current state of parsing revision(from db marker) is the
            # last revision
            lock.release()
            return True

        if cur_stats:
            commits_by_day_aggregate = OrderedDict(ext_json.loads(
                                        cur_stats.commit_activity_combined))
            co_day_auth_aggr = ext_json.loads(cur_stats.commit_activity)

        log.debug('starting parsing %s', parse_limit)

        last_rev = last_rev + 1 if last_rev and last_rev >= 0 else 0
        log.debug('Getting revisions from %s to %s',
             last_rev, last_rev + parse_limit
        )
        for cs in repo[last_rev:last_rev + parse_limit]:
            log.debug('parsing %s', cs)
            last_cs = cs  # remember last parsed changeset
            tt = cs.date.timetuple()
            k = mktime(tt[:3] + (0, 0, 0, 0, 0, 0))

            if akc(cs.author) in co_day_auth_aggr:
                try:
                    l = [timegetter(x) for x in
                         co_day_auth_aggr[akc(cs.author)]['data']]
                    time_pos = l.index(k)
                except ValueError:
                    time_pos = None

                if time_pos is not None and time_pos >= 0:
                    datadict = \
                        co_day_auth_aggr[akc(cs.author)]['data'][time_pos]

                    datadict["commits"] += 1
                    datadict["added"] += len(cs.added)
                    datadict["changed"] += len(cs.changed)
                    datadict["removed"] += len(cs.removed)

                else:
                    if k >= ts_min_y and k <= ts_max_y or skip_date_limit:

                        datadict = {"time": k,
                                    "commits": 1,
                                    "added": len(cs.added),
                                    "changed": len(cs.changed),
                                    "removed": len(cs.removed),
                                   }
                        co_day_auth_aggr[akc(cs.author)]['data'] \
                            .append(datadict)

            else:
                if k >= ts_min_y and k <= ts_max_y or skip_date_limit:
                    co_day_auth_aggr[akc(cs.author)] = {
                                        "label": akc(cs.author),
                                        "data": [{"time": k,
                                                 "commits": 1,
                                                 "added": len(cs.added),
                                                 "changed": len(cs.changed),
                                                 "removed": len(cs.removed),
                                                 }],
                                        "schema": ["commits"],
                                        }

            # gather all data by day
            if k in commits_by_day_aggregate:
                commits_by_day_aggregate[k] += 1
            else:
                commits_by_day_aggregate[k] = 1

        overview_data = sorted(commits_by_day_aggregate.items(),
                               key=itemgetter(0))

        if not co_day_auth_aggr:
            co_day_auth_aggr[akc(repo.contact)] = {
                "label": akc(repo.contact),
                "data": [0, 1],
                "schema": ["commits"],
            }

        stats = cur_stats if cur_stats else Statistics()
        stats.commit_activity = ascii_bytes(ext_json.dumps(co_day_auth_aggr))
        stats.commit_activity_combined = ascii_bytes(ext_json.dumps(overview_data))

        log.debug('last revision %s', last_rev)
        leftovers = len(repo.revisions[last_rev:])
        log.debug('revisions to parse %s', leftovers)

        if last_rev == 0 or leftovers < parse_limit:
            log.debug('getting code trending stats')
            stats.languages = ascii_bytes(ext_json.dumps(__get_codes_stats(repo_name)))

        try:
            stats.repository = dbrepo
            stats.stat_on_revision = last_cs.revision if last_cs else 0
            DBS.add(stats)
            DBS.commit()
        except:
            log.error(traceback.format_exc())
            DBS.rollback()
            lock.release()
            return False

        # final release
        lock.release()

        # execute another task if celery is enabled
        if len(repo.revisions) > 1 and kallithea.CELERY_APP and recurse_limit > 0:
            get_commits_stats(repo_name, ts_min_y, ts_max_y, recurse_limit - 1)
        elif recurse_limit <= 0:
            log.debug('Not recursing - limit has been reached')
        else:
            log.debug('Not recursing')
    except celerylib.LockHeld:
        log.info('Task with key %s already running', lockkey)
        return 'Task with key %s already running' % lockkey


@celerylib.task
@celerylib.dbsession
def send_email(recipients, subject, body='', html_body='', headers=None, from_name=None):
    """
    Sends an email with defined parameters from the .ini files.

    :param recipients: list of recipients, if this is None, the defined email
        address from field 'email_to' and all admins is used instead
    :param subject: subject of the mail
    :param body: body of the mail
    :param html_body: html version of body
    :param headers: dictionary of prepopulated e-mail headers
    :param from_name: full name to be used as sender of this mail - often a
    .full_name_or_username value
    """
    assert isinstance(recipients, list), recipients
    if headers is None:
        headers = {}
    else:
        # do not modify the original headers object passed by the caller
        headers = headers.copy()

    email_config = config
    email_prefix = email_config.get('email_prefix', '')
    if email_prefix:
        subject = "%s %s" % (email_prefix, subject)

    if not recipients:
        # if recipients are not defined we send to email_config + all admins
        recipients = [u.email for u in User.query()
                      .filter(User.admin == True).all()]
        if email_config.get('email_to') is not None:
            recipients += email_config.get('email_to').split(',')

        # If there are still no recipients, there are no admins and no address
        # configured in email_to, so return.
        if not recipients:
            log.error("No recipients specified and no fallback available.")
            return False

        log.warning("No recipients specified for '%s' - sending to admins %s", subject, ' '.join(recipients))

    # SMTP sender
    envelope_from = email_config.get('app_email_from', 'Kallithea')
    # 'From' header
    if from_name is not None:
        # set From header based on from_name but with a generic e-mail address
        # In case app_email_from is in "Some Name <e-mail>" format, we first
        # extract the e-mail address.
        envelope_addr = author_email(envelope_from)
        headers['From'] = '"%s" <%s>' % (
            email.utils.quote('%s (no-reply)' % from_name),
            envelope_addr)

    user = email_config.get('smtp_username')
    passwd = email_config.get('smtp_password')
    mail_server = email_config.get('smtp_server')
    mail_port = email_config.get('smtp_port')
    tls = str2bool(email_config.get('smtp_use_tls'))
    ssl = str2bool(email_config.get('smtp_use_ssl'))
    debug = str2bool(email_config.get('debug'))
    smtp_auth = email_config.get('smtp_auth')

    logmsg = ("Mail details:\n"
              "recipients: %s\n"
              "headers: %s\n"
              "subject: %s\n"
              "body:\n%s\n"
              "html:\n%s\n"
              % (' '.join(recipients), headers, subject, body, html_body))

    if mail_server:
        log.debug("Sending e-mail. " + logmsg)
    else:
        log.error("SMTP mail server not configured - cannot send e-mail.")
        log.warning(logmsg)
        return False

    try:
        m = SmtpMailer(envelope_from, user, passwd, mail_server, smtp_auth,
                       mail_port, ssl, tls, debug=debug)
        m.send(recipients, subject, body, html_body, headers=headers)
    except:
        log.error('Mail sending failed')
        log.error(traceback.format_exc())
        return False
    return True


@celerylib.task
@celerylib.dbsession
def create_repo(form_data, cur_user):
    from kallithea.model.repo import RepoModel
    from kallithea.model.db import Setting

    DBS = celerylib.get_session()

    cur_user = User.guess_instance(cur_user)

    owner = cur_user
    repo_name = form_data['repo_name']
    repo_name_full = form_data['repo_name_full']
    repo_type = form_data['repo_type']
    description = form_data['repo_description']
    private = form_data['repo_private']
    clone_uri = form_data.get('clone_uri')
    repo_group = form_data['repo_group']
    landing_rev = form_data['repo_landing_rev']
    copy_fork_permissions = form_data.get('copy_permissions')
    copy_group_permissions = form_data.get('repo_copy_permissions')
    fork_of = form_data.get('fork_parent_id')
    state = form_data.get('repo_state', Repository.STATE_PENDING)

    # repo creation defaults, private and repo_type are filled in form
    defs = Setting.get_default_repo_settings(strip_prefix=True)
    enable_statistics = defs.get('repo_enable_statistics')
    enable_downloads = defs.get('repo_enable_downloads')

    try:
        repo = RepoModel()._create_repo(
            repo_name=repo_name_full,
            repo_type=repo_type,
            description=description,
            owner=owner,
            private=private,
            clone_uri=clone_uri,
            repo_group=repo_group,
            landing_rev=landing_rev,
            fork_of=fork_of,
            copy_fork_permissions=copy_fork_permissions,
            copy_group_permissions=copy_group_permissions,
            enable_statistics=enable_statistics,
            enable_downloads=enable_downloads,
            state=state
        )

        action_logger(cur_user, 'user_created_repo',
                      form_data['repo_name_full'], '')

        DBS.commit()
        # now create this repo on Filesystem
        RepoModel()._create_filesystem_repo(
            repo_name=repo_name,
            repo_type=repo_type,
            repo_group=RepoGroup.guess_instance(repo_group),
            clone_uri=clone_uri,
        )
        repo = Repository.get_by_repo_name(repo_name_full)
        log_create_repository(repo.get_dict(), created_by=owner.username)

        # update repo changeset caches initially
        repo.update_changeset_cache()

        # set new created state
        repo.set_state(Repository.STATE_CREATED)
        DBS.commit()
    except Exception as e:
        log.warning('Exception %s occurred when forking repository, '
                    'doing cleanup...' % e)
        # rollback things manually !
        repo = Repository.get_by_repo_name(repo_name_full)
        if repo:
            Repository.delete(repo.repo_id)
            DBS.commit()
            RepoModel()._delete_filesystem_repo(repo)
        raise

    return True


@celerylib.task
@celerylib.dbsession
def create_repo_fork(form_data, cur_user):
    """
    Creates a fork of repository using interval VCS methods

    :param form_data:
    :param cur_user:
    """
    from kallithea.model.repo import RepoModel

    DBS = celerylib.get_session()

    base_path = kallithea.CONFIG['base_path']
    cur_user = User.guess_instance(cur_user)

    repo_name = form_data['repo_name']  # fork in this case
    repo_name_full = form_data['repo_name_full']

    repo_type = form_data['repo_type']
    owner = cur_user
    private = form_data['private']
    clone_uri = form_data.get('clone_uri')
    repo_group = form_data['repo_group']
    landing_rev = form_data['landing_rev']
    copy_fork_permissions = form_data.get('copy_permissions')

    try:
        fork_of = Repository.guess_instance(form_data.get('fork_parent_id'))

        RepoModel()._create_repo(
            repo_name=repo_name_full,
            repo_type=repo_type,
            description=form_data['description'],
            owner=owner,
            private=private,
            clone_uri=clone_uri,
            repo_group=repo_group,
            landing_rev=landing_rev,
            fork_of=fork_of,
            copy_fork_permissions=copy_fork_permissions
        )
        action_logger(cur_user, 'user_forked_repo:%s' % repo_name_full,
                      fork_of.repo_name, '')
        DBS.commit()

        source_repo_path = os.path.join(base_path, fork_of.repo_name)

        # now create this repo on Filesystem
        RepoModel()._create_filesystem_repo(
            repo_name=repo_name,
            repo_type=repo_type,
            repo_group=RepoGroup.guess_instance(repo_group),
            clone_uri=source_repo_path,
        )
        repo = Repository.get_by_repo_name(repo_name_full)
        log_create_repository(repo.get_dict(), created_by=owner.username)

        # update repo changeset caches initially
        repo.update_changeset_cache()

        # set new created state
        repo.set_state(Repository.STATE_CREATED)
        DBS.commit()
    except Exception as e:
        log.warning('Exception %s occurred when forking repository, '
                    'doing cleanup...' % e)
        # rollback things manually !
        repo = Repository.get_by_repo_name(repo_name_full)
        if repo:
            Repository.delete(repo.repo_id)
            DBS.commit()
            RepoModel()._delete_filesystem_repo(repo)
        raise

    return True


def __get_codes_stats(repo_name):
    from kallithea.config.conf import LANGUAGES_EXTENSIONS_MAP
    repo = Repository.get_by_repo_name(repo_name).scm_instance

    tip = repo.get_changeset()
    code_stats = {}

    for _topnode, _dirnodes, filenodes in tip.walk('/'):
        for filenode in filenodes:
            ext = filenode.extension.lower()
            if ext in LANGUAGES_EXTENSIONS_MAP and not filenode.is_binary:
                if ext in code_stats:
                    code_stats[ext] += 1
                else:
                    code_stats[ext] = 1

    return code_stats or {}
