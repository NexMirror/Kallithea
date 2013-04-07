# -*- coding: utf-8 -*-
"""
    rhodecode.lib.celerylib.tasks
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    RhodeCode task modules, containing all task that suppose to be run
    by celery daemon

    :created_on: Oct 6, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
    :license: GPLv3, see COPYING for more details.
"""
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
from celery.decorators import task

import os
import traceback
import logging
from os.path import join as jn

from time import mktime
from operator import itemgetter
from string import lower

from pylons import config, url
from pylons.i18n.translation import _

from rhodecode.lib.vcs import get_backend

from rhodecode import CELERY_ON, CELERY_EAGER
from rhodecode.lib.utils2 import safe_str
from rhodecode.lib.celerylib import run_task, locked_task, dbsession, \
    str2bool, __get_lockkey, LockHeld, DaemonLock, get_session
from rhodecode.lib.helpers import person
from rhodecode.lib.rcmail.smtp_mailer import SmtpMailer
from rhodecode.lib.utils import add_cache, action_logger
from rhodecode.lib.compat import json, OrderedDict
from rhodecode.lib.hooks import log_create_repository

from rhodecode.model.db import Statistics, Repository, User
from rhodecode.model.scm import ScmModel


add_cache(config)

__all__ = ['whoosh_index', 'get_commits_stats',
           'reset_user_password', 'send_email']


def get_logger(cls):
    if CELERY_ON:
        try:
            log = cls.get_logger()
        except:
            log = logging.getLogger(__name__)
    else:
        log = logging.getLogger(__name__)

    return log


@task(ignore_result=True)
@locked_task
@dbsession
def whoosh_index(repo_location, full_index):
    from rhodecode.lib.indexers.daemon import WhooshIndexingDaemon
    log = get_logger(whoosh_index)
    DBS = get_session()

    index_location = config['index_dir']
    WhooshIndexingDaemon(index_location=index_location,
                         repo_location=repo_location, sa=DBS)\
                         .run(full_index=full_index)


@task(ignore_result=True)
@dbsession
def get_commits_stats(repo_name, ts_min_y, ts_max_y, recurse_limit=100):
    log = get_logger(get_commits_stats)
    DBS = get_session()
    lockkey = __get_lockkey('get_commits_stats', repo_name, ts_min_y,
                            ts_max_y)
    lockkey_path = config['app_conf']['cache_dir']

    log.info('running task with lockkey %s' % lockkey)

    try:
        lock = l = DaemonLock(file_=jn(lockkey_path, lockkey))

        # for js data compatibility cleans the key for person from '
        akc = lambda k: person(k).replace('"', "")

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
        parse_limit = int(config['app_conf'].get('commit_parse_limit'))
        last_rev = None
        last_cs = None
        timegetter = itemgetter('time')

        dbrepo = DBS.query(Repository)\
            .filter(Repository.repo_name == repo_name).scalar()
        cur_stats = DBS.query(Statistics)\
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
            commits_by_day_aggregate = OrderedDict(json.loads(
                                        cur_stats.commit_activity_combined))
            co_day_auth_aggr = json.loads(cur_stats.commit_activity)

        log.debug('starting parsing %s' % parse_limit)
        lmktime = mktime

        last_rev = last_rev + 1 if last_rev >= 0 else 0
        log.debug('Getting revisions from %s to %s' % (
             last_rev, last_rev + parse_limit)
        )
        for cs in repo[last_rev:last_rev + parse_limit]:
            log.debug('parsing %s' % cs)
            last_cs = cs  # remember last parsed changeset
            k = lmktime([cs.date.timetuple()[0], cs.date.timetuple()[1],
                          cs.date.timetuple()[2], 0, 0, 0, 0, 0, 0])

            if akc(cs.author) in co_day_auth_aggr:
                try:
                    l = [timegetter(x) for x in
                         co_day_auth_aggr[akc(cs.author)]['data']]
                    time_pos = l.index(k)
                except ValueError:
                    time_pos = None

                if time_pos >= 0 and time_pos is not None:

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
                        co_day_auth_aggr[akc(cs.author)]['data']\
                            .append(datadict)

            else:
                if k >= ts_min_y and k <= ts_max_y or skip_date_limit:
                    co_day_auth_aggr[akc(cs.author)] = {
                                        "label": akc(cs.author),
                                        "data": [{"time":k,
                                                 "commits":1,
                                                 "added":len(cs.added),
                                                 "changed":len(cs.changed),
                                                 "removed":len(cs.removed),
                                                 }],
                                        "schema": ["commits"],
                                        }

            #gather all data by day
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
        stats.commit_activity = json.dumps(co_day_auth_aggr)
        stats.commit_activity_combined = json.dumps(overview_data)

        log.debug('last revison %s' % last_rev)
        leftovers = len(repo.revisions[last_rev:])
        log.debug('revisions to parse %s' % leftovers)

        if last_rev == 0 or leftovers < parse_limit:
            log.debug('getting code trending stats')
            stats.languages = json.dumps(__get_codes_stats(repo_name))

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
        if len(repo.revisions) > 1 and CELERY_ON and recurse_limit > 0:
            recurse_limit -= 1
            run_task(get_commits_stats, repo_name, ts_min_y, ts_max_y,
                     recurse_limit)
        if recurse_limit <= 0:
            log.debug('Breaking recursive mode due to reach of recurse limit')
        return True
    except LockHeld:
        log.info('LockHeld')
        return 'Task with key %s already running' % lockkey


@task(ignore_result=True)
@dbsession
def send_email(recipients, subject, body='', html_body=''):
    """
    Sends an email with defined parameters from the .ini files.

    :param recipients: list of recipients, it this is empty the defined email
        address from field 'email_to' is used instead
    :param subject: subject of the mail
    :param body: body of the mail
    :param html_body: html version of body
    """
    log = get_logger(send_email)
    DBS = get_session()

    email_config = config
    subject = "%s %s" % (email_config.get('email_prefix', ''), subject)
    if not recipients:
        # if recipients are not defined we send to email_config + all admins
        admins = [u.email for u in User.query()
                  .filter(User.admin == True).all()]
        recipients = [email_config.get('email_to')] + admins

    mail_from = email_config.get('app_email_from', 'RhodeCode')
    user = email_config.get('smtp_username')
    passwd = email_config.get('smtp_password')
    mail_server = email_config.get('smtp_server')
    mail_port = email_config.get('smtp_port')
    tls = str2bool(email_config.get('smtp_use_tls'))
    ssl = str2bool(email_config.get('smtp_use_ssl'))
    debug = str2bool(email_config.get('debug'))
    smtp_auth = email_config.get('smtp_auth')

    if not mail_server:
        log.error("SMTP mail server not configured - cannot send mail")
        return False

    try:
        m = SmtpMailer(mail_from, user, passwd, mail_server, smtp_auth,
                       mail_port, ssl, tls, debug=debug)
        m.send(recipients, subject, body, html_body)
    except:
        log.error('Mail sending failed')
        log.error(traceback.format_exc())
        return False
    return True


@task(ignore_result=True)
@dbsession
def create_repo_fork(form_data, cur_user):
    """
    Creates a fork of repository using interval VCS methods

    :param form_data:
    :param cur_user:
    """
    from rhodecode.model.repo import RepoModel
    from rhodecode.model.user import UserModel

    log = get_logger(create_repo_fork)
    DBS = get_session()

    base_path = Repository.base_path()
    cur_user = UserModel(DBS)._get_user(cur_user)

    fork_name = form_data['repo_name_full']
    repo_type = form_data['repo_type']
    description = form_data['description']
    owner = cur_user
    private = form_data['private']
    clone_uri = form_data.get('clone_uri')
    repos_group = form_data['repo_group']
    landing_rev = form_data['landing_rev']
    copy_fork_permissions = form_data.get('copy_permissions')
    fork_of = RepoModel(DBS)._get_repo(form_data.get('fork_parent_id'))

    fork_repo = RepoModel(DBS).create_repo(
        fork_name, repo_type, description, owner, private, clone_uri,
        repos_group, landing_rev, just_db=True, fork_of=fork_of,
        copy_fork_permissions=copy_fork_permissions
    )

    update_after_clone = form_data['update_after_clone']

    source_repo_path = os.path.join(base_path, fork_of.repo_name)
    destination_fork_path = os.path.join(base_path, fork_name)

    log.info('creating fork of %s as %s', source_repo_path,
             destination_fork_path)
    backend = get_backend(repo_type)

    if repo_type == 'git':
        r = backend(safe_str(destination_fork_path), create=True,
                src_url=safe_str(source_repo_path),
                update_after_clone=update_after_clone,
                bare=True)
        # add rhodecode hook into this repo
        ScmModel().install_git_hook(repo=r)
    elif repo_type == 'hg':
        r = backend(safe_str(destination_fork_path), create=True,
                src_url=safe_str(source_repo_path),
                update_after_clone=update_after_clone)
    else:
        raise Exception('Unknown backend type %s' % repo_type)

    log_create_repository(fork_repo.get_dict(), created_by=cur_user.username)

    action_logger(cur_user, 'user_forked_repo:%s' % fork_name,
                   fork_of.repo_name, '', DBS)

    action_logger(cur_user, 'user_created_fork:%s' % fork_name,
                   fork_name, '', DBS)
    # finally commit at latest possible stage
    DBS.commit()
    fork_repo.update_changeset_cache()


def __get_codes_stats(repo_name):
    from rhodecode.config.conf import  LANGUAGES_EXTENSIONS_MAP
    repo = Repository.get_by_repo_name(repo_name).scm_instance

    tip = repo.get_changeset()
    code_stats = {}

    def aggregate(cs):
        for f in cs[2]:
            ext = lower(f.extension)
            if ext in LANGUAGES_EXTENSIONS_MAP.keys() and not f.is_binary:
                if ext in code_stats:
                    code_stats[ext] += 1
                else:
                    code_stats[ext] = 1

    map(aggregate, tip.walk('/'))

    return code_stats or {}
