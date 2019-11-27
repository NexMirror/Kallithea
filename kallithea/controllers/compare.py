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
kallithea.controllers.compare
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

compare controller showing differences between two
repos, branches, bookmarks or tips

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import re

from tg import request
from tg import tmpl_context as c
from tg.i18n import ugettext as _
from webob.exc import HTTPBadRequest, HTTPFound, HTTPNotFound

from kallithea.config.routing import url
from kallithea.controllers.changeset import _context_url, _ignorews_url
from kallithea.lib import diffs
from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionLevelDecorator, LoginRequired
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.graphmod import graph_data
from kallithea.lib.utils2 import safe_int, safe_str
from kallithea.lib.vcs.utils.hgcompat import unionrepo
from kallithea.model.db import Repository


log = logging.getLogger(__name__)


class CompareController(BaseRepoController):

    def _before(self, *args, **kwargs):
        super(CompareController, self)._before(*args, **kwargs)

        # The base repository has already been retrieved.
        c.a_repo = c.db_repo

        # Retrieve the "changeset" repository (default: same as base).
        other_repo = request.GET.get('other_repo', None)
        if other_repo is None:
            c.cs_repo = c.a_repo
        else:
            c.cs_repo = Repository.get_by_repo_name(other_repo)
            if c.cs_repo is None:
                msg = _('Could not find other repository %s') % other_repo
                h.flash(msg, category='error')
                raise HTTPFound(location=url('compare_home', repo_name=c.a_repo.repo_name))

        # Verify that it's even possible to compare these two repositories.
        if c.a_repo.scm_instance.alias != c.cs_repo.scm_instance.alias:
            msg = _('Cannot compare repositories of different types')
            h.flash(msg, category='error')
            raise HTTPFound(location=url('compare_home', repo_name=c.a_repo.repo_name))

    @staticmethod
    def _get_changesets(alias, org_repo, org_rev, other_repo, other_rev):
        """
        Returns lists of changesets that can be merged from org_repo@org_rev
        to other_repo@other_rev
        ... and the other way
        ... and the ancestors that would be used for merge

        :param org_repo: repo object, that is most likely the original repo we forked from
        :param org_rev: the revision we want our compare to be made
        :param other_repo: repo object, most likely the fork of org_repo. It has
            all changesets that we need to obtain
        :param other_rev: revision we want out compare to be made on other_repo
        """
        ancestors = None
        if org_rev == other_rev:
            org_changesets = []
            other_changesets = []

        elif alias == 'hg':
            # case two independent repos
            if org_repo != other_repo:
                try:
                    hgrepo = unionrepo.makeunionrepository(other_repo.baseui,
                                                           other_repo.path,
                                                           org_repo.path)
                except AttributeError: # makeunionrepository was introduced in Mercurial 4.8 23f2299e9e53
                    hgrepo = unionrepo.unionrepository(other_repo.baseui,
                                                       other_repo.path,
                                                       org_repo.path)
                # all ancestors of other_rev will be in other_repo and
                # rev numbers from hgrepo can be used in other_repo - org_rev ancestors cannot

            # no remote compare do it on the same repository
            else:
                hgrepo = other_repo._repo

            ancestors = [hgrepo[ancestor].hex() for ancestor in
                         hgrepo.revs("id(%s) & ::id(%s)", other_rev, org_rev)]
            if ancestors:
                log.debug("shortcut found: %s is already an ancestor of %s", other_rev, org_rev)
            else:
                log.debug("no shortcut found: %s is not an ancestor of %s", other_rev, org_rev)
                ancestors = [hgrepo[ancestor].hex() for ancestor in
                             hgrepo.revs("heads(::id(%s) & ::id(%s))", org_rev, other_rev)] # FIXME: expensive!

            other_revs = hgrepo.revs("ancestors(id(%s)) and not ancestors(id(%s)) and not id(%s)",
                                     other_rev, org_rev, org_rev)
            other_changesets = [other_repo.get_changeset(rev) for rev in other_revs]
            org_revs = hgrepo.revs("ancestors(id(%s)) and not ancestors(id(%s)) and not id(%s)",
                                   org_rev, other_rev, other_rev)
            org_changesets = [org_repo.get_changeset(hgrepo[rev].hex()) for rev in org_revs]

        elif alias == 'git':
            if org_repo != other_repo:
                from dulwich.repo import Repo
                from dulwich.client import SubprocessGitClient

                gitrepo = Repo(org_repo.path)
                SubprocessGitClient(thin_packs=False).fetch(safe_str(other_repo.path), gitrepo)

                gitrepo_remote = Repo(other_repo.path)
                SubprocessGitClient(thin_packs=False).fetch(safe_str(org_repo.path), gitrepo_remote)

                revs = [
                    x.commit.id
                    for x in gitrepo_remote.get_walker(include=[other_rev],
                                                       exclude=[org_rev])
                ]
                other_changesets = [other_repo.get_changeset(rev) for rev in reversed(revs)]
                if other_changesets:
                    ancestors = [other_changesets[0].parents[0].raw_id]
                else:
                    # no changesets from other repo, ancestor is the other_rev
                    ancestors = [other_rev]

                gitrepo.close()
                gitrepo_remote.close()

            else:
                so, se = org_repo.run_git_command(
                    ['log', '--reverse', '--pretty=format:%H',
                     '-s', '%s..%s' % (org_rev, other_rev)]
                )
                other_changesets = [org_repo.get_changeset(cs)
                              for cs in re.findall(r'[0-9a-fA-F]{40}', so)]
                so, se = org_repo.run_git_command(
                    ['merge-base', org_rev, other_rev]
                )
                ancestors = [re.findall(r'[0-9a-fA-F]{40}', so)[0]]
            org_changesets = []

        else:
            raise Exception('Bad alias only git and hg is allowed')

        return other_changesets, org_changesets, ancestors

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def index(self, repo_name):
        c.compare_home = True
        c.a_ref_name = c.cs_ref_name = None
        return render('compare/compare_diff.html')

    @LoginRequired(allow_default_user=True)
    @HasRepoPermissionLevelDecorator('read')
    def compare(self, repo_name, org_ref_type, org_ref_name, other_ref_type, other_ref_name):
        org_ref_name = org_ref_name.strip()
        other_ref_name = other_ref_name.strip()

        # If merge is True:
        #   Show what org would get if merged with other:
        #   List changesets that are ancestors of other but not of org.
        #   New changesets in org is thus ignored.
        #   Diff will be from common ancestor, and merges of org to other will thus be ignored.
        # If merge is False:
        #   Make a raw diff from org to other, no matter if related or not.
        #   Changesets in one and not in the other will be ignored
        merge = bool(request.GET.get('merge'))
        # fulldiff disables cut_off_limit
        fulldiff = request.GET.get('fulldiff')
        # partial uses compare_cs.html template directly
        partial = request.environ.get('HTTP_X_PARTIAL_XHR')
        # is_ajax_preview puts hidden input field with changeset revisions
        c.is_ajax_preview = partial and request.GET.get('is_ajax_preview')
        # swap url for compare_diff page - never partial and never is_ajax_preview
        c.swap_url = h.url('compare_url',
            repo_name=c.cs_repo.repo_name,
            org_ref_type=other_ref_type, org_ref_name=other_ref_name,
            other_repo=c.a_repo.repo_name,
            other_ref_type=org_ref_type, other_ref_name=org_ref_name,
            merge=merge or '')

        # set callbacks for generating markup for icons
        c.ignorews_url = _ignorews_url
        c.context_url = _context_url
        ignore_whitespace = request.GET.get('ignorews') == '1'
        line_context = safe_int(request.GET.get('context'), 3)

        c.a_rev = self._get_ref_rev(c.a_repo, org_ref_type, org_ref_name,
            returnempty=True)
        c.cs_rev = self._get_ref_rev(c.cs_repo, other_ref_type, other_ref_name)

        c.compare_home = False
        c.a_ref_name = org_ref_name
        c.a_ref_type = org_ref_type
        c.cs_ref_name = other_ref_name
        c.cs_ref_type = other_ref_type

        c.cs_ranges, c.cs_ranges_org, c.ancestors = self._get_changesets(
            c.a_repo.scm_instance.alias, c.a_repo.scm_instance, c.a_rev,
            c.cs_repo.scm_instance, c.cs_rev)
        raw_ids = [x.raw_id for x in c.cs_ranges]
        c.cs_comments = c.cs_repo.get_comments(raw_ids)
        c.cs_statuses = c.cs_repo.statuses(raw_ids)

        revs = [ctx.revision for ctx in reversed(c.cs_ranges)]
        c.jsdata = graph_data(c.cs_repo.scm_instance, revs)

        if partial:
            return render('compare/compare_cs.html')

        org_repo = c.a_repo
        other_repo = c.cs_repo

        if merge:
            rev1 = msg = None
            if not c.cs_ranges:
                msg = _('Cannot show empty diff')
            elif not c.ancestors:
                msg = _('No ancestor found for merge diff')
            elif len(c.ancestors) == 1:
                rev1 = c.ancestors[0]
            else:
                msg = _('Multiple merge ancestors found for merge compare')
            if rev1 is None:
                h.flash(msg, category='error')
                log.error(msg)
                raise HTTPNotFound

            # case we want a simple diff without incoming changesets,
            # previewing what will be merged.
            # Make the diff on the other repo (which is known to have other_rev)
            log.debug('Using ancestor %s as rev1 instead of %s',
                      rev1, c.a_rev)
            org_repo = other_repo
        else: # comparing tips, not necessarily linearly related
            if org_repo != other_repo:
                # TODO: we could do this by using hg unionrepo
                log.error('cannot compare across repos %s and %s', org_repo, other_repo)
                h.flash(_('Cannot compare repositories without using common ancestor'), category='error')
                raise HTTPBadRequest
            rev1 = c.a_rev

        diff_limit = None if fulldiff else self.cut_off_limit

        log.debug('running diff between %s and %s in %s',
                  rev1, c.cs_rev, org_repo.scm_instance.path)
        raw_diff = diffs.get_diff(org_repo.scm_instance, rev1=rev1, rev2=c.cs_rev,
                                      ignore_whitespace=ignore_whitespace,
                                      context=line_context)

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
            html_diff = diffs.as_html(enable_comments=False, parsed_lines=[f])
            c.file_diff_data.append((fid, None, f['operation'], f['old_filename'], filename, html_diff, st))

        return render('compare/compare_diff.html')
