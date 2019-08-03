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
kallithea.controllers.changeset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

changeset controller showing changes between revisions

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 25, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
from collections import OrderedDict, defaultdict

from tg import request, response
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPBadRequest, HTTPForbidden, HTTPFound, HTTPNotFound

import kallithea.lib.helpers as h
from kallithea.lib import diffs
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseRepoController, jsonify, render
from kallithea.lib.graphmod import graph_data
from kallithea.lib.utils import action_logger
from kallithea.lib.utils2 import safe_unicode
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError, EmptyRepositoryError, RepositoryError
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.comment import ChangesetCommentsModel
from kallithea.model.db import ChangesetComment, ChangesetStatus
from kallithea.model.meta import Session
from kallithea.model.pull_request import PullRequestModel


log = logging.getLogger(__name__)


def _update_with_GET(params, GET):
    for k in ['diff1', 'diff2', 'diff']:
        params[k] += GET.getall(k)


def anchor_url(revision, path, GET):
    fid = h.FID(revision, path)
    return h.url.current(anchor=fid, **dict(GET))


def get_ignore_ws(fid, GET):
    ig_ws_global = GET.get('ignorews')
    ig_ws = filter(lambda k: k.startswith('WS'), GET.getall(fid))
    if ig_ws:
        try:
            return int(ig_ws[0].split(':')[-1])
        except ValueError:
            raise HTTPBadRequest()
    return ig_ws_global


def _ignorews_url(GET, fileid=None):
    fileid = str(fileid) if fileid else None
    params = defaultdict(list)
    _update_with_GET(params, GET)
    lbl = _('Show whitespace')
    ig_ws = get_ignore_ws(fileid, GET)
    ln_ctx = get_line_ctx(fileid, GET)
    # global option
    if fileid is None:
        if ig_ws is None:
            params['ignorews'] += [1]
            lbl = _('Ignore whitespace')
        ctx_key = 'context'
        ctx_val = ln_ctx
    # per file options
    else:
        if ig_ws is None:
            params[fileid] += ['WS:1']
            lbl = _('Ignore whitespace')

        ctx_key = fileid
        ctx_val = 'C:%s' % ln_ctx
    # if we have passed in ln_ctx pass it along to our params
    if ln_ctx:
        params[ctx_key] += [ctx_val]

    params['anchor'] = fileid
    icon = h.literal('<i class="icon-strike"></i>')
    return h.link_to(icon, h.url.current(**params), title=lbl, **{'data-toggle': 'tooltip'})


def get_line_ctx(fid, GET):
    ln_ctx_global = GET.get('context')
    if fid:
        ln_ctx = filter(lambda k: k.startswith('C'), GET.getall(fid))
    else:
        _ln_ctx = filter(lambda k: k.startswith('C'), GET)
        ln_ctx = GET.get(_ln_ctx[0]) if _ln_ctx else ln_ctx_global
        if ln_ctx:
            ln_ctx = [ln_ctx]

    if ln_ctx:
        retval = ln_ctx[0].split(':')[-1]
    else:
        retval = ln_ctx_global

    try:
        return int(retval)
    except Exception:
        return 3


def _context_url(GET, fileid=None):
    """
    Generates url for context lines

    :param fileid:
    """

    fileid = str(fileid) if fileid else None
    ig_ws = get_ignore_ws(fileid, GET)
    ln_ctx = (get_line_ctx(fileid, GET) or 3) * 2

    params = defaultdict(list)
    _update_with_GET(params, GET)

    # global option
    if fileid is None:
        if ln_ctx > 0:
            params['context'] += [ln_ctx]

        if ig_ws:
            ig_ws_key = 'ignorews'
            ig_ws_val = 1

    # per file option
    else:
        params[fileid] += ['C:%s' % ln_ctx]
        ig_ws_key = fileid
        ig_ws_val = 'WS:%s' % 1

    if ig_ws:
        params[ig_ws_key] += [ig_ws_val]

    lbl = _('Increase diff context to %(num)s lines') % {'num': ln_ctx}

    params['anchor'] = fileid
    icon = h.literal('<i class="icon-sort"></i>')
    return h.link_to(icon, h.url.current(**params), title=lbl, **{'data-toggle': 'tooltip'})


def create_cs_pr_comment(repo_name, revision=None, pull_request=None, allowed_to_change_status=True):
    """
    Add a comment to the specified changeset or pull request, using POST values
    from the request.

    Comments can be inline (when a file path and line number is specified in
    POST) or general comments.
    A comment can be accompanied by a review status change (accepted, rejected,
    etc.). Pull requests can be closed or deleted.

    Parameter 'allowed_to_change_status' is used for both status changes and
    closing of pull requests. For deleting of pull requests, more specific
    checks are done.
    """

    assert request.environ.get('HTTP_X_PARTIAL_XHR')
    if pull_request:
        pull_request_id = pull_request.pull_request_id
    else:
        pull_request_id = None

    status = request.POST.get('changeset_status')
    close_pr = request.POST.get('save_close')
    delete = request.POST.get('save_delete')
    f_path = request.POST.get('f_path')
    line_no = request.POST.get('line')

    if (status or close_pr or delete) and (f_path or line_no):
        # status votes and closing is only possible in general comments
        raise HTTPBadRequest()

    if not allowed_to_change_status:
        if status or close_pr:
            h.flash(_('No permission to change status'), 'error')
            raise HTTPForbidden()

    if pull_request and delete == "delete":
        if (pull_request.owner_id == request.authuser.user_id or
            h.HasPermissionAny('hg.admin')() or
            h.HasRepoPermissionLevel('admin')(pull_request.org_repo.repo_name) or
            h.HasRepoPermissionLevel('admin')(pull_request.other_repo.repo_name)
        ) and not pull_request.is_closed():
            PullRequestModel().delete(pull_request)
            Session().commit()
            h.flash(_('Successfully deleted pull request %s') % pull_request_id,
                    category='success')
            return {
               'location': h.url('my_pullrequests'), # or repo pr list?
            }
            raise HTTPFound(location=h.url('my_pullrequests')) # or repo pr list?
        raise HTTPForbidden()

    text = request.POST.get('text', '').strip()

    comment = ChangesetCommentsModel().create(
        text=text,
        repo=c.db_repo.repo_id,
        author=request.authuser.user_id,
        revision=revision,
        pull_request=pull_request_id,
        f_path=f_path or None,
        line_no=line_no or None,
        status_change=ChangesetStatus.get_status_lbl(status) if status else None,
        closing_pr=close_pr,
    )

    if status:
        ChangesetStatusModel().set_status(
            c.db_repo.repo_id,
            status,
            request.authuser.user_id,
            comment,
            revision=revision,
            pull_request=pull_request_id,
        )

    if pull_request:
        action = 'user_commented_pull_request:%s' % pull_request_id
    else:
        action = 'user_commented_revision:%s' % revision
    action_logger(request.authuser, action, c.db_repo, request.ip_addr)

    if pull_request and close_pr:
        PullRequestModel().close_pull_request(pull_request_id)
        action_logger(request.authuser,
                      'user_closed_pull_request:%s' % pull_request_id,
                      c.db_repo, request.ip_addr)

    Session().commit()

    data = {
       'target_id': h.safeid(h.safe_unicode(request.POST.get('f_path'))),
    }
    if comment is not None:
        c.comment = comment
        data.update(comment.get_dict())
        data.update({'rendered_text':
                     render('changeset/changeset_comment_block.html')})

    return data

def delete_cs_pr_comment(repo_name, comment_id):
    """Delete a comment from a changeset or pull request"""
    co = ChangesetComment.get_or_404(comment_id)
    if co.repo.repo_name != repo_name:
        raise HTTPNotFound()
    if co.pull_request and co.pull_request.is_closed():
        # don't allow deleting comments on closed pull request
        raise HTTPForbidden()

    owner = co.author_id == request.authuser.user_id
    repo_admin = h.HasRepoPermissionLevel('admin')(repo_name)
    if h.HasPermissionAny('hg.admin')() or repo_admin or owner:
        ChangesetCommentsModel().delete(comment=co)
        Session().commit()
        return True
    else:
        raise HTTPForbidden()

class ChangesetController(BaseRepoController):

    def _before(self, *args, **kwargs):
        super(ChangesetController, self)._before(*args, **kwargs)
        c.affected_files_cut_off = 60

    def _index(self, revision, method):
        c.pull_request = None
        c.anchor_url = anchor_url
        c.ignorews_url = _ignorews_url
        c.context_url = _context_url
        c.fulldiff = request.GET.get('fulldiff') # for reporting number of changed files
        # get ranges of revisions if preset
        rev_range = revision.split('...')[:2]
        enable_comments = True
        c.cs_repo = c.db_repo
        try:
            if len(rev_range) == 2:
                enable_comments = False
                rev_start = rev_range[0]
                rev_end = rev_range[1]
                rev_ranges = c.db_repo_scm_instance.get_changesets(start=rev_start,
                                                             end=rev_end)
            else:
                rev_ranges = [c.db_repo_scm_instance.get_changeset(revision)]

            c.cs_ranges = list(rev_ranges)
            if not c.cs_ranges:
                raise RepositoryError('Changeset range returned empty result')

        except (ChangesetDoesNotExistError, EmptyRepositoryError):
            log.debug(traceback.format_exc())
            msg = _('Such revision does not exist for this repository')
            h.flash(msg, category='error')
            raise HTTPNotFound()

        c.changes = OrderedDict()

        c.lines_added = 0  # count of lines added
        c.lines_deleted = 0  # count of lines removes

        c.changeset_statuses = ChangesetStatus.STATUSES
        comments = dict()
        c.statuses = []
        c.inline_comments = []
        c.inline_cnt = 0

        # Iterate over ranges (default changeset view is always one changeset)
        for changeset in c.cs_ranges:
            if method == 'show':
                c.statuses.extend([ChangesetStatusModel().get_status(
                            c.db_repo.repo_id, changeset.raw_id)])

                # Changeset comments
                comments.update((com.comment_id, com)
                                for com in ChangesetCommentsModel()
                                .get_comments(c.db_repo.repo_id,
                                              revision=changeset.raw_id))

                # Status change comments - mostly from pull requests
                comments.update((st.comment_id, st.comment)
                                for st in ChangesetStatusModel()
                                .get_statuses(c.db_repo.repo_id,
                                              changeset.raw_id, with_revisions=True)
                                if st.comment_id is not None)

                inlines = ChangesetCommentsModel() \
                            .get_inline_comments(c.db_repo.repo_id,
                                                 revision=changeset.raw_id)
                c.inline_comments.extend(inlines)

            cs2 = changeset.raw_id
            cs1 = changeset.parents[0].raw_id if changeset.parents else EmptyChangeset().raw_id
            context_lcl = get_line_ctx('', request.GET)
            ign_whitespace_lcl = get_ignore_ws('', request.GET)

            raw_diff = diffs.get_diff(c.db_repo_scm_instance, cs1, cs2,
                ignore_whitespace=ign_whitespace_lcl, context=context_lcl)
            diff_limit = None if c.fulldiff else self.cut_off_limit
            file_diff_data = []
            if method == 'show':
                diff_processor = diffs.DiffProcessor(raw_diff,
                                                     vcs=c.db_repo_scm_instance.alias,
                                                     diff_limit=diff_limit)
                c.limited_diff = diff_processor.limited_diff
                for f in diff_processor.parsed:
                    st = f['stats']
                    c.lines_added += st['added']
                    c.lines_deleted += st['deleted']
                    filename = f['filename']
                    fid = h.FID(changeset.raw_id, filename)
                    url_fid = h.FID('', filename)
                    html_diff = diffs.as_html(enable_comments=enable_comments, parsed_lines=[f])
                    file_diff_data.append((fid, url_fid, f['operation'], f['old_filename'], filename, html_diff, st))
            else:
                # downloads/raw we only need RAW diff nothing else
                file_diff_data.append(('', None, None, None, raw_diff, None))
            c.changes[changeset.raw_id] = (cs1, cs2, file_diff_data)

        # sort comments in creation order
        c.comments = [com for com_id, com in sorted(comments.items())]

        # count inline comments
        for __, lines in c.inline_comments:
            for comments in lines.values():
                c.inline_cnt += len(comments)

        if len(c.cs_ranges) == 1:
            c.changeset = c.cs_ranges[0]
            c.parent_tmpl = ''.join(['# Parent  %s\n' % x.raw_id
                                     for x in c.changeset.parents])
        if method == 'download':
            response.content_type = 'text/plain'
            response.content_disposition = 'attachment; filename=%s.diff' \
                                            % revision[:12]
            return raw_diff
        elif method == 'patch':
            response.content_type = 'text/plain'
            c.diff = safe_unicode(raw_diff)
            return render('changeset/patch_changeset.html')
        elif method == 'raw':
            response.content_type = 'text/plain'
            return raw_diff
        elif method == 'show':
            if len(c.cs_ranges) == 1:
                return render('changeset/changeset.html')
            else:
                c.cs_ranges_org = None
                c.cs_comments = {}
                revs = [ctx.revision for ctx in reversed(c.cs_ranges)]
                c.jsdata = graph_data(c.db_repo_scm_instance, revs)
                return render('changeset/changeset_range.html')

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def index(self, revision, method='show'):
        return self._index(revision, method=method)

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def changeset_raw(self, revision):
        return self._index(revision, method='raw')

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def changeset_patch(self, revision):
        return self._index(revision, method='patch')

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def changeset_download(self, revision):
        return self._index(revision, method='download')

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def comment(self, repo_name, revision):
        return create_cs_pr_comment(repo_name, revision=revision)

    @LoginRequired()
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def delete_comment(self, repo_name, comment_id):
        return delete_cs_pr_comment(repo_name, comment_id)

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def changeset_info(self, repo_name, revision):
        if request.is_xhr:
            try:
                return c.db_repo_scm_instance.get_changeset(revision)
            except ChangesetDoesNotExistError as e:
                return EmptyChangeset(message=str(e))
        else:
            raise HTTPBadRequest()

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def changeset_children(self, repo_name, revision):
        if request.is_xhr:
            changeset = c.db_repo_scm_instance.get_changeset(revision)
            result = {"results": []}
            if changeset.children:
                result = {"results": changeset.children}
            return result
        else:
            raise HTTPBadRequest()

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    @jsonify
    def changeset_parents(self, repo_name, revision):
        if request.is_xhr:
            changeset = c.db_repo_scm_instance.get_changeset(revision)
            result = {"results": []}
            if changeset.parents:
                result = {"results": changeset.parents}
            return result
        else:
            raise HTTPBadRequest()
