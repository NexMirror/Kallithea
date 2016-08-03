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
kallithea.model.pull_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pull request model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jun 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import datetime

from pylons.i18n.translation import _

from sqlalchemy.orm import joinedload

from kallithea.model.meta import Session
from kallithea.lib import helpers as h
from kallithea.lib.exceptions import UserInvalidException
from kallithea.model import BaseModel
from kallithea.model.db import PullRequest, PullRequestReviewers, Notification, \
    ChangesetStatus, User
from kallithea.model.notification import NotificationModel
from kallithea.lib.utils2 import extract_mentioned_users, safe_unicode


log = logging.getLogger(__name__)


class PullRequestModel(BaseModel):

    cls = PullRequest

    def get_pullrequest_cnt_for_user(self, user):
        return PullRequest.query() \
                                .join(PullRequestReviewers) \
                                .filter(PullRequestReviewers.user_id == user) \
                                .filter(PullRequest.status != PullRequest.STATUS_CLOSED) \
                                .count()

    def get_all(self, repo_name, from_=False, closed=False):
        """Get all PRs for repo.
        Default is all PRs to the repo, PRs from the repo if from_.
        Closed PRs are only included if closed is true."""
        repo = self._get_repo(repo_name)
        q = PullRequest.query()
        if from_:
            q = q.filter(PullRequest.org_repo == repo)
        else:
            q = q.filter(PullRequest.other_repo == repo)
        if not closed:
            q = q.filter(PullRequest.status != PullRequest.STATUS_CLOSED)
        return q.order_by(PullRequest.created_on.desc()).all()

    def _get_valid_reviewers(self, seq):
        """ Generate User objects from a sequence of user IDs, usernames or
        User objects. Raises UserInvalidException if the DEFAULT user is
        specified, or if a given ID or username does not match any user.
        """
        for user_spec in seq:
            user = self._get_user(user_spec)
            if user is None or user.username == User.DEFAULT_USER:
                raise UserInvalidException(user_spec)
            yield user

    def create(self, created_by, org_repo, org_ref, other_repo, other_ref,
               revisions, reviewers, title, description=None):
        from kallithea.model.changeset_status import ChangesetStatusModel

        created_by_user = self._get_user(created_by)
        org_repo = self._get_repo(org_repo)
        other_repo = self._get_repo(other_repo)

        new = PullRequest()
        new.org_repo = org_repo
        new.org_ref = org_ref
        new.other_repo = other_repo
        new.other_ref = other_ref
        new.revisions = revisions
        new.title = title
        new.description = description
        new.owner = created_by_user
        Session().add(new)
        Session().flush()

        #reset state to under-review
        from kallithea.model.comment import ChangesetCommentsModel
        comment = ChangesetCommentsModel().create(
            text=u'',
            repo=org_repo,
            user=new.owner,
            pull_request=new,
            send_email=False,
            status_change=ChangesetStatus.STATUS_UNDER_REVIEW,
        )
        ChangesetStatusModel().set_status(
            org_repo,
            ChangesetStatus.STATUS_UNDER_REVIEW,
            new.owner,
            comment,
            pull_request=new
        )

        reviewers = set(self._get_valid_reviewers(reviewers))
        mention_recipients = extract_mentioned_users(new.description)
        self.__add_reviewers(created_by_user, new, reviewers, mention_recipients)

        return new

    def __add_reviewers(self, user, pr, reviewers, mention_recipients):
        # reviewers and mention_recipients should be sets of User objects.
        #members
        for reviewer in reviewers:
            reviewer = PullRequestReviewers(reviewer, pr)
            Session().add(reviewer)

        revision_data = [(x.raw_id, x.message)
                         for x in map(pr.org_repo.get_changeset, pr.revisions)]

        #notification to reviewers
        pr_url = pr.url(canonical=True)
        threading = ['%s-pr-%s@%s' % (pr.other_repo.repo_name,
                                      pr.pull_request_id,
                                      h.canonical_hostname())]
        subject = safe_unicode(
            h.link_to(
              _('%(user)s wants you to review pull request %(pr_nice_id)s: %(pr_title)s') % \
                {'user': user.username,
                 'pr_title': pr.title,
                 'pr_nice_id': pr.nice_id()},
                pr_url)
            )
        body = pr.description
        _org_ref_type, org_ref_name, _org_rev = pr.org_ref.split(':')
        _other_ref_type, other_ref_name, _other_rev = pr.other_ref.split(':')
        email_kwargs = {
            'pr_title': pr.title,
            'pr_title_short': h.shorter(pr.title, 50),
            'pr_user_created': user.full_name_and_username,
            'pr_repo_url': h.canonical_url('summary_home', repo_name=pr.other_repo.repo_name),
            'pr_url': pr_url,
            'pr_revisions': revision_data,
            'repo_name': pr.other_repo.repo_name,
            'org_repo_name': pr.org_repo.repo_name,
            'pr_nice_id': pr.nice_id(),
            'pr_target_repo': h.canonical_url('summary_home',
                               repo_name=pr.other_repo.repo_name),
            'pr_target_branch': other_ref_name,
            'pr_source_repo': h.canonical_url('summary_home',
                               repo_name=pr.org_repo.repo_name),
            'pr_source_branch': org_ref_name,
            'pr_owner': pr.owner,
            'pr_owner_username': pr.owner.username,
            'pr_username': user.username,
            'threading': threading,
            'is_mention': False,
            }
        if reviewers:
            NotificationModel().create(created_by=user, subject=subject, body=body,
                                       recipients=reviewers,
                                       type_=Notification.TYPE_PULL_REQUEST,
                                       email_kwargs=email_kwargs)

        if mention_recipients:
            mention_recipients.difference_update(reviewers)
        if mention_recipients:
            email_kwargs['is_mention'] = True
            subject = _('[Mention]') + ' ' + subject
            # FIXME: this subject is wrong and unused!
            NotificationModel().create(created_by=user, subject=subject, body=body,
                                       recipients=mention_recipients,
                                       type_=Notification.TYPE_PULL_REQUEST,
                                       email_kwargs=email_kwargs)

    def mention_from_description(self, user, pr, old_description=''):
        mention_recipients = (extract_mentioned_users(pr.description) -
                              extract_mentioned_users(old_description))

        log.debug("Mentioning %s", mention_recipients)
        self.__add_reviewers(user, pr, set(), mention_recipients)

    def update_reviewers(self, user, pull_request, reviewers_ids):
        reviewers_ids = set(reviewers_ids)
        pull_request = self._get_instance(PullRequest, pull_request)
        current_reviewers = PullRequestReviewers.query() \
            .options(joinedload('user')) \
            .filter_by(pull_request=pull_request) \
            .all()
        current_reviewer_users = set(x.user for x in current_reviewers)
        new_reviewer_users = set(self._get_valid_reviewers(reviewers_ids))

        to_add = new_reviewer_users - current_reviewer_users
        to_remove = current_reviewer_users - new_reviewer_users

        if not to_add and not to_remove:
            return # all done

        log.debug("Adding %s reviewers", to_add)
        self.__add_reviewers(user, pull_request, to_add, set())

        log.debug("Removing %s reviewers", to_remove)
        for prr in current_reviewers:
            if prr.user in to_remove:
                Session().delete(prr)

    def delete(self, pull_request):
        pull_request = self._get_instance(PullRequest, pull_request)
        Session().delete(pull_request)

    def close_pull_request(self, pull_request):
        pull_request = self._get_instance(PullRequest, pull_request)
        pull_request.status = PullRequest.STATUS_CLOSED
        pull_request.updated_on = datetime.datetime.now()
        Session().add(pull_request)
