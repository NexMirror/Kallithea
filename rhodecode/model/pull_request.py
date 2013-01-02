# -*- coding: utf-8 -*-
"""
    rhodecode.model.pull_request
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    pull request model for RhodeCode

    :created_on: Jun 6, 2012
    :author: marcink
    :copyright: (C) 2012-2012 Marcin Kuzminski <marcin@python-works.com>
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

import logging
import binascii
import datetime
import re

from pylons.i18n.translation import _

from rhodecode.model.meta import Session
from rhodecode.lib import helpers as h
from rhodecode.model import BaseModel
from rhodecode.model.db import PullRequest, PullRequestReviewers, Notification,\
    ChangesetStatus
from rhodecode.model.notification import NotificationModel
from rhodecode.lib.utils2 import safe_unicode

from rhodecode.lib.vcs.utils.hgcompat import discovery, localrepo, scmutil, \
    findcommonoutgoing

log = logging.getLogger(__name__)


class PullRequestModel(BaseModel):

    cls = PullRequest

    def __get_pull_request(self, pull_request):
        return self._get_instance(PullRequest, pull_request)

    def get_all(self, repo):
        repo = self._get_repo(repo)
        return PullRequest.query().filter(PullRequest.other_repo == repo).all()

    def create(self, created_by, org_repo, org_ref, other_repo, other_ref,
               revisions, reviewers, title, description=None):
        from rhodecode.model.changeset_status import ChangesetStatusModel

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
        new.author = created_by_user
        self.sa.add(new)
        Session().flush()
        #members
        for member in reviewers:
            _usr = self._get_user(member)
            reviewer = PullRequestReviewers(_usr, new)
            self.sa.add(reviewer)

        #reset state to under-review
        ChangesetStatusModel().set_status(
            repo=org_repo,
            status=ChangesetStatus.STATUS_UNDER_REVIEW,
            user=created_by_user,
            pull_request=new
        )

        #notification to reviewers
        notif = NotificationModel()

        pr_url = h.url('pullrequest_show', repo_name=other_repo.repo_name,
                       pull_request_id=new.pull_request_id,
                       qualified=True,
        )
        subject = safe_unicode(
            h.link_to(
              _('%(user)s wants you to review pull request #%(pr_id)s') % \
                {'user': created_by_user.username,
                 'pr_id': new.pull_request_id},
                pr_url
            )
        )
        body = description
        kwargs = {
            'pr_title': title,
            'pr_user_created': h.person(created_by_user.email),
            'pr_repo_url': h.url('summary_home', repo_name=other_repo.repo_name,
                                 qualified=True,),
            'pr_url': pr_url,
            'pr_revisions': revisions
        }
        notif.create(created_by=created_by_user, subject=subject, body=body,
                     recipients=reviewers,
                     type_=Notification.TYPE_PULL_REQUEST, email_kwargs=kwargs)
        return new

    def update_reviewers(self, pull_request, reviewers_ids):
        reviewers_ids = set(reviewers_ids)
        pull_request = self.__get_pull_request(pull_request)
        current_reviewers = PullRequestReviewers.query()\
                            .filter(PullRequestReviewers.pull_request==
                                   pull_request)\
                            .all()
        current_reviewers_ids = set([x.user.user_id for x in current_reviewers])

        to_add = reviewers_ids.difference(current_reviewers_ids)
        to_remove = current_reviewers_ids.difference(reviewers_ids)

        log.debug("Adding %s reviewers" % to_add)
        log.debug("Removing %s reviewers" % to_remove)

        for uid in to_add:
            _usr = self._get_user(uid)
            reviewer = PullRequestReviewers(_usr, pull_request)
            self.sa.add(reviewer)

        for uid in to_remove:
            reviewer = PullRequestReviewers.query()\
                    .filter(PullRequestReviewers.user_id==uid,
                            PullRequestReviewers.pull_request==pull_request)\
                    .scalar()
            if reviewer:
                self.sa.delete(reviewer)

    def delete(self, pull_request):
        pull_request = self.__get_pull_request(pull_request)
        Session().delete(pull_request)

    def close_pull_request(self, pull_request):
        pull_request = self.__get_pull_request(pull_request)
        pull_request.status = PullRequest.STATUS_CLOSED
        pull_request.updated_on = datetime.datetime.now()
        self.sa.add(pull_request)

    def _get_changesets(self, alias, org_repo, org_ref, other_repo, other_ref):
        """
        Returns a list of changesets that are incoming from org_repo@org_ref
        to other_repo@other_ref

        :param org_repo:
        :param org_ref:
        :param other_repo:
        :param other_ref:
        :param tmp:
        """

        changesets = []
        #case two independent repos
        if org_repo != other_repo:
            revs = [
                org_repo._repo.lookup(org_ref[1]),
                org_repo._repo.lookup(other_ref[1]),
            ]

            obj = findcommonoutgoing(org_repo._repo,
                        localrepo.locallegacypeer(other_repo._repo.local()),
                        revs,
                        force=True)
            revs = obj.missing

            for cs in map(binascii.hexlify, revs):
                _cs = org_repo.get_changeset(cs)
                changesets.append(_cs)
            # in case we have revisions filter out the ones not in given range
            if org_ref[0] == 'rev' and other_ref[0] == 'rev':
                revs = [x.raw_id for x in changesets]
                start = org_ref[1]
                stop = other_ref[1]
                changesets = changesets[revs.index(start):revs.index(stop) + 1]
        else:
            #no remote compare do it on the same repository
            if alias == 'hg':
                _revset_predicates = {
                        'branch': 'branch',
                        'book': 'bookmark',
                        'tag': 'tag',
                        'rev': 'id',
                    }

                revs = [
                    "ancestors(%s('%s')) and not ancestors(%s('%s'))" % (
                        _revset_predicates[other_ref[0]], other_ref[1],
                        _revset_predicates[org_ref[0]], org_ref[1],
                   )
                ]

                out = scmutil.revrange(org_repo._repo, revs)
                for cs in (out):
                    changesets.append(org_repo.get_changeset(cs))
            elif alias == 'git':
                so, se = org_repo.run_git_command(
                    'log --reverse --pretty="format: %%H" -s -p %s..%s' % (org_ref[1],
                                                                     other_ref[1])
                )
                ids = re.findall(r'[0-9a-fA-F]{40}', so)
                for cs in (ids):
                    changesets.append(org_repo.get_changeset(cs))

        return changesets

    def get_compare_data(self, org_repo, org_ref, other_repo, other_ref):
        """
        Returns incomming changesets for mercurial repositories

        :param org_repo:
        :type org_repo:
        :param org_ref:
        :type org_ref:
        :param other_repo:
        :type other_repo:
        :param other_ref:
        :type other_ref:
        """

        if len(org_ref) != 2 or not isinstance(org_ref, (list, tuple)):
            raise Exception('org_ref must be a two element list/tuple')

        if len(other_ref) != 2 or not isinstance(org_ref, (list, tuple)):
            raise Exception('other_ref must be a two element list/tuple')

        org_repo_scm = org_repo.scm_instance
        other_repo_scm = other_repo.scm_instance

        alias = org_repo.scm_instance.alias
        cs_ranges = self._get_changesets(alias,
                                         org_repo_scm, org_ref,
                                         other_repo_scm, other_ref)
        return cs_ranges
