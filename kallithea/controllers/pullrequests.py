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
kallithea.controllers.pullrequests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pull requests controller for Kallithea for initializing pull requests

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 7, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

import formencode
from tg import request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPBadRequest, HTTPForbidden, HTTPFound, HTTPNotFound

from kallithea.config.routing import url
from kallithea.controllers.changeset import _context_url, _ignorews_url, create_cs_pr_comment, delete_cs_pr_comment
from kallithea.lib import diffs
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseRepoController, jsonify, render
from kallithea.lib.graphmod import graph_data
from kallithea.lib.page import Page
from kallithea.lib.utils2 import safe_int
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError, EmptyRepositoryError
from kallithea.lib.vcs.utils import safe_str
from kallithea.lib.vcs.utils.hgcompat import unionrepo
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.comment import ChangesetCommentsModel
from kallithea.model.db import ChangesetStatus, PullRequest, PullRequestReviewer, Repository, User
from kallithea.model.forms import PullRequestForm, PullRequestPostForm
from kallithea.model.meta import Session
from kallithea.model.pull_request import CreatePullRequestAction, CreatePullRequestIterationAction, PullRequestModel


log = logging.getLogger(__name__)


def _get_reviewer(user_id):
    """Look up user by ID and validate it as a potential reviewer."""
    try:
        user = User.get(int(user_id))
    except ValueError:
        user = None

    if user is None or user.is_default_user:
        h.flash(_('Invalid reviewer "%s" specified') % user_id, category='error')
        raise HTTPBadRequest()

    return user


class PullrequestsController(BaseRepoController):

    def _get_repo_refs(self, repo, rev=None, branch=None, branch_rev=None):
        """return a structure with repo's interesting changesets, suitable for
        the selectors in pullrequest.html

        rev: a revision that must be in the list somehow and selected by default
        branch: a branch that must be in the list and selected by default - even if closed
        branch_rev: a revision of which peers should be preferred and available."""
        # list named branches that has been merged to this named branch - it should probably merge back
        peers = []

        if rev:
            rev = safe_str(rev)

        if branch:
            branch = safe_str(branch)

        if branch_rev:
            branch_rev = safe_str(branch_rev)
            # a revset not restricting to merge() would be better
            # (especially because it would get the branch point)
            # ... but is currently too expensive
            # including branches of children could be nice too
            peerbranches = set()
            for i in repo._repo.revs(
                "sort(parents(branch(id(%s)) and merge()) - branch(id(%s)), -rev)",
                branch_rev, branch_rev
            ):
                for abranch in repo.get_changeset(i).branches:
                    if abranch not in peerbranches:
                        n = 'branch:%s:%s' % (abranch, repo.get_changeset(abranch).raw_id)
                        peers.append((n, abranch))
                        peerbranches.add(abranch)

        selected = None
        tiprev = repo.tags.get('tip')
        tipbranch = None

        branches = []
        for abranch, branchrev in repo.branches.iteritems():
            n = 'branch:%s:%s' % (abranch, branchrev)
            desc = abranch
            if branchrev == tiprev:
                tipbranch = abranch
                desc = '%s (current tip)' % desc
            branches.append((n, desc))
            if rev == branchrev:
                selected = n
            if branch == abranch:
                if not rev:
                    selected = n
                branch = None
        if branch:  # branch not in list - it is probably closed
            branchrev = repo.closed_branches.get(branch)
            if branchrev:
                n = 'branch:%s:%s' % (branch, branchrev)
                branches.append((n, _('%s (closed)') % branch))
                selected = n
                branch = None
            if branch:
                log.debug('branch %r not found in %s', branch, repo)

        bookmarks = []
        for bookmark, bookmarkrev in repo.bookmarks.iteritems():
            n = 'book:%s:%s' % (bookmark, bookmarkrev)
            bookmarks.append((n, bookmark))
            if rev == bookmarkrev:
                selected = n

        tags = []
        for tag, tagrev in repo.tags.iteritems():
            if tag == 'tip':
                continue
            n = 'tag:%s:%s' % (tag, tagrev)
            tags.append((n, tag))
            # note: even if rev == tagrev, don't select the static tag - it must be chosen explicitly

        # prio 1: rev was selected as existing entry above

        # prio 2: create special entry for rev; rev _must_ be used
        specials = []
        if rev and selected is None:
            selected = 'rev:%s:%s' % (rev, rev)
            specials = [(selected, '%s: %s' % (_("Changeset"), rev[:12]))]

        # prio 3: most recent peer branch
        if peers and not selected:
            selected = peers[0][0]

        # prio 4: tip revision
        if not selected:
            if h.is_hg(repo):
                if tipbranch:
                    selected = 'branch:%s:%s' % (tipbranch, tiprev)
                else:
                    selected = 'tag:null:' + repo.EMPTY_CHANGESET
                    tags.append((selected, 'null'))
            else:
                if 'master' in repo.branches:
                    selected = 'branch:master:%s' % repo.branches['master']
                else:
                    k, v = repo.branches.items()[0]
                    selected = 'branch:%s:%s' % (k, v)

        groups = [(specials, _("Special")),
                  (peers, _("Peer branches")),
                  (bookmarks, _("Bookmarks")),
                  (branches, _("Branches")),
                  (tags, _("Tags")),
                  ]
        return [g for g in groups if g[0]], selected

    def _is_allowed_to_change_status(self, pull_request):
        if pull_request.is_closed():
            return False

        owner = request.authuser.user_id == pull_request.owner_id
        reviewer = PullRequestReviewer.query() \
            .filter(PullRequestReviewer.pull_request == pull_request) \
            .filter(PullRequestReviewer.user_id == request.authuser.user_id) \
            .count() != 0

        return request.authuser.admin or owner or reviewer

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def show_all(self, repo_name):
        c.from_ = request.GET.get('from_') or ''
        c.closed = request.GET.get('closed') or ''
        p = safe_int(request.GET.get('page'), 1)

        q = PullRequest.query(include_closed=c.closed, sorted=True)
        if c.from_:
            q = q.filter_by(org_repo=c.db_repo)
        else:
            q = q.filter_by(other_repo=c.db_repo)
        c.pull_requests = q.all()

        c.pullrequests_pager = Page(c.pull_requests, page=p, items_per_page=100)

        return render('/pullrequests/pullrequest_show_all.html')

    @LoginRequired()
    def show_my(self):
        c.closed = request.GET.get('closed') or ''

        c.my_pull_requests = PullRequest.query(
            include_closed=c.closed,
            sorted=True,
        ).filter_by(owner_id=request.authuser.user_id).all()

        c.participate_in_pull_requests = []
        c.participate_in_pull_requests_todo = []
        done_status = set([ChangesetStatus.STATUS_APPROVED, ChangesetStatus.STATUS_REJECTED])
        for pr in PullRequest.query(
            include_closed=c.closed,
            reviewer_id=request.authuser.user_id,
            sorted=True,
        ):
            status = pr.user_review_status(request.authuser.user_id) # very inefficient!!!
            if status in done_status:
                c.participate_in_pull_requests.append(pr)
            else:
                c.participate_in_pull_requests_todo.append(pr)

        return render('/pullrequests/pullrequest_show_my.html')

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    def index(self):
        org_repo = c.db_repo
        org_scm_instance = org_repo.scm_instance
        try:
            org_scm_instance.get_changeset()
        except EmptyRepositoryError as e:
            h.flash(_('There are no changesets yet'),
                    category='warning')
            raise HTTPFound(location=url('summary_home', repo_name=org_repo.repo_name))

        org_rev = request.GET.get('rev_end')
        # rev_start is not directly useful - its parent could however be used
        # as default for other and thus give a simple compare view
        rev_start = request.GET.get('rev_start')
        other_rev = None
        if rev_start:
            starters = org_repo.get_changeset(rev_start).parents
            if starters:
                other_rev = starters[0].raw_id
            else:
                other_rev = org_repo.scm_instance.EMPTY_CHANGESET
        branch = request.GET.get('branch')

        c.cs_repos = [(org_repo.repo_name, org_repo.repo_name)]
        c.default_cs_repo = org_repo.repo_name
        c.cs_refs, c.default_cs_ref = self._get_repo_refs(org_scm_instance, rev=org_rev, branch=branch)

        default_cs_ref_type, default_cs_branch, default_cs_rev = c.default_cs_ref.split(':')
        if default_cs_ref_type != 'branch':
            default_cs_branch = org_repo.get_changeset(default_cs_rev).branch

        # add org repo to other so we can open pull request against peer branches on itself
        c.a_repos = [(org_repo.repo_name, '%s (self)' % org_repo.repo_name)]

        if org_repo.parent:
            # add parent of this fork also and select it.
            # use the same branch on destination as on source, if available.
            c.a_repos.append((org_repo.parent.repo_name, '%s (parent)' % org_repo.parent.repo_name))
            c.a_repo = org_repo.parent
            c.a_refs, c.default_a_ref = self._get_repo_refs(
                    org_repo.parent.scm_instance, branch=default_cs_branch, rev=other_rev)

        else:
            c.a_repo = org_repo
            c.a_refs, c.default_a_ref = self._get_repo_refs(org_scm_instance, rev=other_rev)

        # gather forks and add to this list ... even though it is rare to
        # request forks to pull from their parent
        for fork in org_repo.forks:
            c.a_repos.append((fork.repo_name, fork.repo_name))

        return render('/pullrequests/pullrequest.html')

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def repo_info(self, repo_name):
        repo = c.db_repo
        refs, selected_ref = self._get_repo_refs(repo.scm_instance)
        return {
            'description': repo.description.split('\n', 1)[0],
            'selected_ref': selected_ref,
            'refs': refs,
            }

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    def create(self, repo_name):
        repo = c.db_repo
        try:
            _form = PullRequestForm(repo.repo_id)().to_python(request.POST)
        except formencode.Invalid as errors:
            log.error(traceback.format_exc())
            log.error(str(errors))
            msg = _('Error creating pull request: %s') % errors.msg
            h.flash(msg, 'error')
            raise HTTPBadRequest

        # heads up: org and other might seem backward here ...
        org_ref = _form['org_ref'] # will have merge_rev as rev but symbolic name
        org_repo = Repository.guess_instance(_form['org_repo'])

        other_ref = _form['other_ref'] # will have symbolic name and head revision
        other_repo = Repository.guess_instance(_form['other_repo'])

        reviewers = []

        title = _form['pullrequest_title']
        description = _form['pullrequest_desc'].strip()
        owner = User.get(request.authuser.user_id)

        try:
            cmd = CreatePullRequestAction(org_repo, other_repo, org_ref, other_ref, title, description, owner, reviewers)
        except CreatePullRequestAction.ValidationError as e:
            h.flash(str(e), category='error', logf=log.error)
            raise HTTPNotFound

        try:
            pull_request = cmd.execute()
            Session().commit()
        except Exception:
            h.flash(_('Error occurred while creating pull request'),
                    category='error')
            log.error(traceback.format_exc())
            raise HTTPFound(location=url('pullrequest_home', repo_name=repo_name))

        h.flash(_('Successfully opened new pull request'),
                category='success')
        raise HTTPFound(location=pull_request.url())

    def create_new_iteration(self, old_pull_request, new_rev, title, description, reviewers):
        owner = User.get(request.authuser.user_id)
        new_org_rev = self._get_ref_rev(old_pull_request.org_repo, 'rev', new_rev)
        new_other_rev = self._get_ref_rev(old_pull_request.other_repo, old_pull_request.other_ref_parts[0], old_pull_request.other_ref_parts[1])
        try:
            cmd = CreatePullRequestIterationAction(old_pull_request, new_org_rev, new_other_rev, title, description, owner, reviewers)
        except CreatePullRequestAction.ValidationError as e:
            h.flash(str(e), category='error', logf=log.error)
            raise HTTPNotFound

        try:
            pull_request = cmd.execute()
            Session().commit()
        except Exception:
            h.flash(_('Error occurred while creating pull request'),
                    category='error')
            log.error(traceback.format_exc())
            raise HTTPFound(location=old_pull_request.url())

        h.flash(_('New pull request iteration created'),
                category='success')
        raise HTTPFound(location=pull_request.url())

    # pullrequest_post for PR editing
    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    def post(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)
        if pull_request.is_closed():
            raise HTTPForbidden()
        assert pull_request.other_repo.repo_name == repo_name
        # only owner or admin can update it
        owner = pull_request.owner_id == request.authuser.user_id
        repo_admin = h.HasRepoPermissionLevel('admin')(c.repo_name)
        if not (h.HasPermissionAny('hg.admin')() or repo_admin or owner):
            raise HTTPForbidden()

        _form = PullRequestPostForm()().to_python(request.POST)

        cur_reviewers = set(pull_request.get_reviewer_users())
        new_reviewers = set(_get_reviewer(s) for s in _form['review_members'])
        old_reviewers = set(_get_reviewer(s) for s in _form['org_review_members'])

        other_added = cur_reviewers - old_reviewers
        other_removed = old_reviewers - cur_reviewers

        if other_added:
            h.flash(_('Meanwhile, the following reviewers have been added: %s') %
                    (', '.join(u.username for u in other_added)),
                    category='warning')
        if other_removed:
            h.flash(_('Meanwhile, the following reviewers have been removed: %s') %
                    (', '.join(u.username for u in other_removed)),
                    category='warning')

        if _form['updaterev']:
            return self.create_new_iteration(pull_request,
                                      _form['updaterev'],
                                      _form['pullrequest_title'],
                                      _form['pullrequest_desc'],
                                      new_reviewers)

        added_reviewers = new_reviewers - old_reviewers - cur_reviewers
        removed_reviewers = (old_reviewers - new_reviewers) & cur_reviewers

        old_description = pull_request.description
        pull_request.title = _form['pullrequest_title']
        pull_request.description = _form['pullrequest_desc'].strip() or _('No description')
        pull_request.owner = User.get_by_username(_form['owner'])
        user = User.get(request.authuser.user_id)

        PullRequestModel().mention_from_description(user, pull_request, old_description)
        PullRequestModel().add_reviewers(user, pull_request, added_reviewers)
        PullRequestModel().remove_reviewers(user, pull_request, removed_reviewers)

        Session().commit()
        h.flash(_('Pull request updated'), category='success')

        raise HTTPFound(location=pull_request.url())

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def delete(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)
        # only owner can delete it !
        if pull_request.owner_id == request.authuser.user_id:
            PullRequestModel().delete(pull_request)
            Session().commit()
            h.flash(_('Successfully deleted pull request'),
                    category='success')
            raise HTTPFound(location=url('my_pullrequests'))
        raise HTTPForbidden()

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def show(self, repo_name, pull_request_id, extra=None):
        c.pull_request = PullRequest.get_or_404(pull_request_id)
        c.allowed_to_change_status = self._is_allowed_to_change_status(c.pull_request)
        cc_model = ChangesetCommentsModel()
        cs_model = ChangesetStatusModel()

        # pull_requests repo_name we opened it against
        # ie. other_repo must match
        if repo_name != c.pull_request.other_repo.repo_name:
            raise HTTPNotFound

        # load compare data into template context
        c.cs_repo = c.pull_request.org_repo
        (c.cs_ref_type,
         c.cs_ref_name,
         c.cs_rev) = c.pull_request.org_ref.split(':')

        c.a_repo = c.pull_request.other_repo
        (c.a_ref_type,
         c.a_ref_name,
         c.a_rev) = c.pull_request.other_ref.split(':') # a_rev is ancestor

        org_scm_instance = c.cs_repo.scm_instance # property with expensive cache invalidation check!!!
        try:
            c.cs_ranges = []
            for x in c.pull_request.revisions:
                c.cs_ranges.append(org_scm_instance.get_changeset(x))
        except ChangesetDoesNotExistError:
            c.cs_ranges = []
            h.flash(_('Revision %s not found in %s') % (x, c.cs_repo.repo_name),
                'error')
        c.cs_ranges_org = None # not stored and not important and moving target - could be calculated ...
        revs = [ctx.revision for ctx in reversed(c.cs_ranges)]
        c.jsdata = graph_data(org_scm_instance, revs)

        c.is_range = False
        try:
            if c.a_ref_type == 'rev': # this looks like a free range where target is ancestor
                cs_a = org_scm_instance.get_changeset(c.a_rev)
                root_parents = c.cs_ranges[0].parents
                c.is_range = cs_a in root_parents
                #c.merge_root = len(root_parents) > 1 # a range starting with a merge might deserve a warning
        except ChangesetDoesNotExistError: # probably because c.a_rev not found
            pass
        except IndexError: # probably because c.cs_ranges is empty, probably because revisions are missing
            pass

        avail_revs = set()
        avail_show = []
        c.cs_branch_name = c.cs_ref_name
        c.a_branch_name = None
        other_scm_instance = c.a_repo.scm_instance
        c.update_msg = ""
        c.update_msg_other = ""
        try:
            if not c.cs_ranges:
                c.update_msg = _('Error: changesets not found when displaying pull request from %s.') % c.cs_rev
            elif org_scm_instance.alias == 'hg' and c.a_ref_name != 'ancestor':
                if c.cs_ref_type != 'branch':
                    c.cs_branch_name = org_scm_instance.get_changeset(c.cs_ref_name).branch # use ref_type ?
                c.a_branch_name = c.a_ref_name
                if c.a_ref_type != 'branch':
                    try:
                        c.a_branch_name = other_scm_instance.get_changeset(c.a_ref_name).branch # use ref_type ?
                    except EmptyRepositoryError:
                        c.a_branch_name = 'null' # not a branch name ... but close enough
                # candidates: descendants of old head that are on the right branch
                #             and not are the old head itself ...
                #             and nothing at all if old head is a descendant of target ref name
                if not c.is_range and other_scm_instance._repo.revs('present(%s)::&%s', c.cs_ranges[-1].raw_id, c.a_branch_name):
                    c.update_msg = _('This pull request has already been merged to %s.') % c.a_branch_name
                elif c.pull_request.is_closed():
                    c.update_msg = _('This pull request has been closed and can not be updated.')
                else: # look for descendants of PR head on source branch in org repo
                    avail_revs = org_scm_instance._repo.revs('%s:: & branch(%s)',
                                                             revs[0], c.cs_branch_name)
                    if len(avail_revs) > 1: # more than just revs[0]
                        # also show changesets that not are descendants but would be merged in
                        targethead = other_scm_instance.get_changeset(c.a_branch_name).raw_id
                        if org_scm_instance.path != other_scm_instance.path:
                            # Note: org_scm_instance.path must come first so all
                            # valid revision numbers are 100% org_scm compatible
                            # - both for avail_revs and for revset results
                            try:
                                hgrepo = unionrepo.makeunionrepository(org_scm_instance.baseui,
                                                                       org_scm_instance.path,
                                                                       other_scm_instance.path)
                            except AttributeError: # makeunionrepository was introduced in Mercurial 4.8 23f2299e9e53
                                hgrepo = unionrepo.unionrepository(org_scm_instance.baseui,
                                                                   org_scm_instance.path,
                                                                   other_scm_instance.path)
                        else:
                            hgrepo = org_scm_instance._repo
                        show = set(hgrepo.revs('::%ld & !::parents(%s) & !::%s',
                                               avail_revs, revs[0], targethead))
                        if show:
                            c.update_msg = _('The following additional changes are available on %s:') % c.cs_branch_name
                        else:
                            c.update_msg = _('No additional changesets found for iterating on this pull request.')
                    else:
                        show = set()
                        avail_revs = set() # drop revs[0]
                        c.update_msg = _('No additional changesets found for iterating on this pull request.')

                    # TODO: handle branch heads that not are tip-most
                    brevs = org_scm_instance._repo.revs('%s - %ld - %s', c.cs_branch_name, avail_revs, revs[0])
                    if brevs:
                        # also show changesets that are on branch but neither ancestors nor descendants
                        show.update(org_scm_instance._repo.revs('::%ld - ::%ld - ::%s', brevs, avail_revs, c.a_branch_name))
                        show.add(revs[0]) # make sure graph shows this so we can see how they relate
                        c.update_msg_other = _('Note: Branch %s has another head: %s.') % (c.cs_branch_name,
                            h.short_id(org_scm_instance.get_changeset((max(brevs))).raw_id))

                    avail_show = sorted(show, reverse=True)

            elif org_scm_instance.alias == 'git':
                c.cs_repo.scm_instance.get_changeset(c.cs_rev) # check it exists - raise ChangesetDoesNotExistError if not
                c.update_msg = _("Git pull requests don't support iterating yet.")
        except ChangesetDoesNotExistError:
            c.update_msg = _('Error: some changesets not found when displaying pull request from %s.') % c.cs_rev

        c.avail_revs = avail_revs
        c.avail_cs = [org_scm_instance.get_changeset(r) for r in avail_show]
        c.avail_jsdata = graph_data(org_scm_instance, avail_show)

        raw_ids = [x.raw_id for x in c.cs_ranges]
        c.cs_comments = c.cs_repo.get_comments(raw_ids)
        c.cs_statuses = c.cs_repo.statuses(raw_ids)

        ignore_whitespace = request.GET.get('ignorews') == '1'
        line_context = safe_int(request.GET.get('context'), 3)
        c.ignorews_url = _ignorews_url
        c.context_url = _context_url
        fulldiff = request.GET.get('fulldiff')
        diff_limit = None if fulldiff else self.cut_off_limit

        # we swap org/other ref since we run a simple diff on one repo
        log.debug('running diff between %s and %s in %s',
                  c.a_rev, c.cs_rev, org_scm_instance.path)
        try:
            raw_diff = diffs.get_diff(org_scm_instance, rev1=safe_str(c.a_rev), rev2=safe_str(c.cs_rev),
                                      ignore_whitespace=ignore_whitespace, context=line_context)
        except ChangesetDoesNotExistError:
            raw_diff = _("The diff can't be shown - the PR revisions could not be found.")
        diff_processor = diffs.DiffProcessor(raw_diff or '', diff_limit=diff_limit)
        c.limited_diff = diff_processor.limited_diff
        c.file_diff_data = []
        c.lines_added = 0
        c.lines_deleted = 0

        for f in diff_processor.parsed:
            st = f['stats']
            c.lines_added += st['added']
            c.lines_deleted += st['deleted']
            filename = f['filename']
            fid = h.FID('', filename)
            html_diff = diffs.as_html(enable_comments=True, parsed_lines=[f])
            c.file_diff_data.append((fid, None, f['operation'], f['old_filename'], filename, html_diff, st))

        # inline comments
        c.inline_cnt = 0
        c.inline_comments = cc_model.get_inline_comments(
                                c.db_repo.repo_id,
                                pull_request=pull_request_id)
        # count inline comments
        for __, lines in c.inline_comments:
            for comments in lines.values():
                c.inline_cnt += len(comments)
        # comments
        c.comments = cc_model.get_comments(c.db_repo.repo_id, pull_request=pull_request_id)

        # (badly named) pull-request status calculation based on reviewer votes
        (c.pull_request_reviewers,
         c.pull_request_pending_reviewers,
         c.current_voting_result,
         ) = cs_model.calculate_pull_request_result(c.pull_request)
        c.changeset_statuses = ChangesetStatus.STATUSES

        c.is_ajax_preview = False
        c.ancestors = None # [c.a_rev] ... but that is shown in an other way
        return render('/pullrequests/pullrequest_show.html')

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def comment(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)
        allowed_to_change_status = self._is_allowed_to_change_status(pull_request)
        return create_cs_pr_comment(repo_name, pull_request=pull_request,
                allowed_to_change_status=allowed_to_change_status)

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def delete_comment(self, repo_name, comment_id):
        return delete_cs_pr_comment(repo_name, comment_id)
