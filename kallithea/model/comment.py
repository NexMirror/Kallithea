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
kallithea.model.comment
~~~~~~~~~~~~~~~~~~~~~~~

comments model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 11, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
from collections import defaultdict

from tg.i18n import ugettext as _

from kallithea.lib import helpers as h
from kallithea.lib.utils2 import extract_mentioned_users
from kallithea.model.db import ChangesetComment, PullRequest, Repository, User
from kallithea.model.meta import Session
from kallithea.model.notification import NotificationModel


log = logging.getLogger(__name__)


def _list_changeset_commenters(revision):
    return (Session().query(User)
        .join(ChangesetComment.author)
        .filter(ChangesetComment.revision == revision)
        .all())

def _list_pull_request_commenters(pull_request):
    return (Session().query(User)
        .join(ChangesetComment.author)
        .filter(ChangesetComment.pull_request_id == pull_request.pull_request_id)
        .all())


class ChangesetCommentsModel(object):

    def _get_notification_data(self, repo, comment, author, comment_text,
                               line_no=None, revision=None, pull_request=None,
                               status_change=None, closing_pr=False):
        """
        :returns: tuple (subj,body,recipients,notification_type,email_kwargs)
        """
        # make notification
        body = comment_text  # text of the comment
        line = ''
        if line_no:
            line = _('on line %s') % line_no

        # changeset
        if revision:
            notification_type = NotificationModel.TYPE_CHANGESET_COMMENT
            cs = repo.scm_instance.get_changeset(revision)
            desc = cs.short_id

            threading = ['%s-rev-%s@%s' % (repo.repo_name, revision, h.canonical_hostname())]
            if line_no: # TODO: url to file _and_ line number
                threading.append('%s-rev-%s-line-%s@%s' % (repo.repo_name, revision, line_no,
                                                           h.canonical_hostname()))
            comment_url = h.canonical_url('changeset_home',
                repo_name=repo.repo_name,
                revision=revision,
                anchor='comment-%s' % comment.comment_id)
            subj = h.link_to(
                'Re changeset: %(desc)s %(line)s' %
                          {'desc': desc, 'line': line},
                 comment_url)
            # get the current participants of this changeset
            recipients = _list_changeset_commenters(revision)
            # add changeset author if it's known locally
            cs_author = User.get_from_cs_author(cs.author)
            if not cs_author:
                # use repo owner if we cannot extract the author correctly
                # FIXME: just use committer name even if not a user
                cs_author = repo.owner
            recipients.append(cs_author)

            email_kwargs = {
                'status_change': status_change,
                'cs_comment_user': author.full_name_and_username,
                'cs_target_repo': h.canonical_url('summary_home', repo_name=repo.repo_name),
                'cs_comment_url': comment_url,
                'cs_url': h.canonical_url('changeset_home', repo_name=repo.repo_name, revision=revision),
                'raw_id': revision,
                'message': cs.message,
                'message_short': h.shorter(cs.message, 50, firstline=True),
                'cs_author': cs_author,
                'repo_name': repo.repo_name,
                'short_id': h.short_id(revision),
                'branch': cs.branch,
                'comment_username': author.username,
                'threading': threading,
            }
        # pull request
        elif pull_request:
            notification_type = NotificationModel.TYPE_PULL_REQUEST_COMMENT
            desc = comment.pull_request.title
            _org_ref_type, org_ref_name, _org_rev = comment.pull_request.org_ref.split(':')
            _other_ref_type, other_ref_name, _other_rev = comment.pull_request.other_ref.split(':')
            threading = ['%s-pr-%s@%s' % (pull_request.other_repo.repo_name,
                                          pull_request.pull_request_id,
                                          h.canonical_hostname())]
            if line_no: # TODO: url to file _and_ line number
                threading.append('%s-pr-%s-line-%s@%s' % (pull_request.other_repo.repo_name,
                                                          pull_request.pull_request_id, line_no,
                                                          h.canonical_hostname()))
            comment_url = pull_request.url(canonical=True,
                anchor='comment-%s' % comment.comment_id)
            subj = h.link_to(
                'Re pull request %(pr_nice_id)s: %(desc)s %(line)s' %
                          {'desc': desc,
                           'pr_nice_id': comment.pull_request.nice_id(),
                           'line': line},
                comment_url)
            # get the current participants of this pull request
            recipients = _list_pull_request_commenters(pull_request)
            recipients.append(pull_request.owner)
            recipients += pull_request.get_reviewer_users()

            # set some variables for email notification
            email_kwargs = {
                'pr_title': pull_request.title,
                'pr_title_short': h.shorter(pull_request.title, 50),
                'pr_nice_id': pull_request.nice_id(),
                'status_change': status_change,
                'closing_pr': closing_pr,
                'pr_comment_url': comment_url,
                'pr_url': pull_request.url(canonical=True),
                'pr_comment_user': author.full_name_and_username,
                'pr_target_repo': h.canonical_url('summary_home',
                                   repo_name=pull_request.other_repo.repo_name),
                'pr_target_branch': other_ref_name,
                'pr_source_repo': h.canonical_url('summary_home',
                                   repo_name=pull_request.org_repo.repo_name),
                'pr_source_branch': org_ref_name,
                'pr_owner': pull_request.owner,
                'pr_owner_username': pull_request.owner.username,
                'repo_name': pull_request.other_repo.repo_name,
                'comment_username': author.username,
                'threading': threading,
            }

        return subj, body, recipients, notification_type, email_kwargs

    def create(self, text, repo, author, revision=None, pull_request=None,
               f_path=None, line_no=None, status_change=None, closing_pr=False,
               send_email=True):
        """
        Creates a new comment for either a changeset or a pull request.
        status_change and closing_pr is only for the optional email.

        Returns the created comment.
        """
        if not status_change and not text:
            log.warning('Missing text for comment, skipping...')
            return None

        repo = Repository.guess_instance(repo)
        author = User.guess_instance(author)
        comment = ChangesetComment()
        comment.repo = repo
        comment.author = author
        comment.text = text
        comment.f_path = f_path
        comment.line_no = line_no

        if revision is not None:
            comment.revision = revision
        elif pull_request is not None:
            pull_request = PullRequest.guess_instance(pull_request)
            comment.pull_request = pull_request
        else:
            raise Exception('Please specify revision or pull_request_id')

        Session().add(comment)
        Session().flush()

        if send_email:
            (subj, body, recipients, notification_type,
             email_kwargs) = self._get_notification_data(
                                repo, comment, author,
                                comment_text=text,
                                line_no=line_no,
                                revision=revision,
                                pull_request=pull_request,
                                status_change=status_change,
                                closing_pr=closing_pr)
            email_kwargs['is_mention'] = False
            # create notification objects, and emails
            NotificationModel().create(
                created_by=author, subject=subj, body=body,
                recipients=recipients, type_=notification_type,
                email_kwargs=email_kwargs,
            )

            mention_recipients = extract_mentioned_users(body).difference(recipients)
            if mention_recipients:
                email_kwargs['is_mention'] = True
                subj = _('[Mention]') + ' ' + subj
                # FIXME: this subject is wrong and unused!
                NotificationModel().create(
                    created_by=author, subject=subj, body=body,
                    recipients=mention_recipients,
                    type_=notification_type,
                    email_kwargs=email_kwargs
                )

        return comment

    def delete(self, comment):
        comment = ChangesetComment.guess_instance(comment)
        Session().delete(comment)

        return comment

    def get_comments(self, repo_id, revision=None, pull_request=None):
        """
        Gets general comments for either revision or pull_request.

        Returns a list, ordered by creation date.
        """
        return self._get_comments(repo_id, revision=revision, pull_request=pull_request,
                                  inline=False)

    def get_inline_comments(self, repo_id, revision=None, pull_request=None,
                f_path=None, line_no=None):
        """
        Gets inline comments for either revision or pull_request.

        Returns a list of tuples with file path and list of comments per line number.
        """
        comments = self._get_comments(repo_id, revision=revision, pull_request=pull_request,
                                      inline=True, f_path=f_path, line_no=line_no)

        paths = defaultdict(lambda: defaultdict(list))
        for co in comments:
            paths[co.f_path][co.line_no].append(co)
        return sorted(paths.items())

    def _get_comments(self, repo_id, revision=None, pull_request=None,
                inline=False, f_path=None, line_no=None):
        """
        Gets comments for either revision or pull_request_id, either inline or general.
        If a file path and optionally line number are given, return only the matching inline comments.
        """
        if f_path is None and line_no is not None:
            raise Exception("line_no only makes sense if f_path is given.")

        if inline is None and f_path is not None:
            raise Exception("f_path only makes sense for inline comments.")

        q = Session().query(ChangesetComment)

        if inline:
            if f_path is not None:
                # inline comments for a given file...
                q = q.filter(ChangesetComment.f_path == f_path)
                if line_no is None:
                    # ... on any line
                    q = q.filter(ChangesetComment.line_no != None)
                else:
                    # ... on specific line
                    q = q.filter(ChangesetComment.line_no == line_no)
            else:
                # all inline comments
                q = q.filter(ChangesetComment.line_no != None) \
                    .filter(ChangesetComment.f_path != None)
        else:
            # all general comments
            q = q.filter(ChangesetComment.line_no == None) \
                .filter(ChangesetComment.f_path == None)

        if revision is not None:
            q = q.filter(ChangesetComment.revision == revision) \
                .filter(ChangesetComment.repo_id == repo_id)
        elif pull_request is not None:
            pull_request = PullRequest.guess_instance(pull_request)
            q = q.filter(ChangesetComment.pull_request == pull_request)
        else:
            raise Exception('Please specify either revision or pull_request')

        return q.order_by(ChangesetComment.created_on).all()
