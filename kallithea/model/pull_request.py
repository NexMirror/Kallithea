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
from kallithea.model.db import PullRequest, PullRequestReviewer, Notification, \
    ChangesetStatus
from kallithea.model.notification import NotificationModel
from kallithea.lib.utils2 import extract_mentioned_users, safe_unicode


log = logging.getLogger(__name__)


def _assert_valid_reviewers(seq):
    """Sanity check: elements are actual User objects, and not the default user."""
    assert not any(user.is_default_user for user in seq)


class PullRequestModel(object):

    def create(self, created_by, org_repo, org_ref, other_repo, other_ref,
               revisions, title, description, reviewers):
        reviewers = set(reviewers)
        _assert_valid_reviewers(reviewers)

        pr = PullRequest()
        pr.org_repo = org_repo
        pr.org_ref = org_ref
        pr.other_repo = other_repo
        pr.other_ref = other_ref
        pr.revisions = revisions
        pr.title = title
        pr.description = description
        pr.owner = created_by
        Session().add(pr)
        Session().flush() # make database assign pull_request_id

        #reset state to under-review
        from kallithea.model.changeset_status import ChangesetStatusModel
        from kallithea.model.comment import ChangesetCommentsModel
        comment = ChangesetCommentsModel().create(
            text=u'',
            repo=org_repo,
            author=created_by,
            pull_request=pr,
            send_email=False,
            status_change=ChangesetStatus.STATUS_UNDER_REVIEW,
        )
        ChangesetStatusModel().set_status(
            org_repo,
            ChangesetStatus.STATUS_UNDER_REVIEW,
            created_by,
            comment,
            pull_request=pr,
        )

        mention_recipients = extract_mentioned_users(description)
        self.add_reviewers(created_by, pr, reviewers, mention_recipients)

        return pr

    def add_reviewers(self, user, pr, reviewers, mention_recipients=None):
        """Add reviewer and send notification to them.
        """
        reviewers = set(reviewers)
        _assert_valid_reviewers(reviewers)
        if mention_recipients is not None:
            mention_recipients = set(mention_recipients) - reviewers
            _assert_valid_reviewers(mention_recipients)

        #members
        for reviewer in reviewers:
            prr = PullRequestReviewer(reviewer, pr)
            Session().add(prr)

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
        revision_data = [(x.raw_id, x.message)
                         for x in map(pr.org_repo.get_changeset, pr.revisions)]
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
        self.add_reviewers(user, pr, set(), mention_recipients)

    def remove_reviewers(self, user, pull_request, reviewers):
        """Remove specified users from being reviewers of the PR."""

        PullRequestReviewer.query() \
            .filter_by(pull_request=pull_request) \
            .filter(PullRequestReviewer.user_id.in_(r.user_id for r in reviewers)) \
            .delete(synchronize_session='fetch') # the default of 'evaluate' is not available

    def delete(self, pull_request):
        pull_request = PullRequest.guess_instance(pull_request)
        Session().delete(pull_request)

    def close_pull_request(self, pull_request):
        pull_request = PullRequest.guess_instance(pull_request)
        pull_request.status = PullRequest.STATUS_CLOSED
        pull_request.updated_on = datetime.datetime.now()
