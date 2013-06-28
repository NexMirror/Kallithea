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

compare controller for pylons showing differences between two
repos, branches, bookmarks or tips

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import traceback
import re

from webob.exc import HTTPNotFound, HTTPBadRequest
from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _

from kallithea.lib.vcs.exceptions import EmptyRepositoryError, RepositoryError
from kallithea.lib.vcs.utils import safe_str
from kallithea.lib.vcs.utils.hgcompat import unionrepo
from kallithea.lib import helpers as h
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib import diffs
from kallithea.model.db import Repository
from kallithea.lib.diffs import LimitedDiffContainer


log = logging.getLogger(__name__)


class CompareController(BaseRepoController):

    def __before__(self):
        super(CompareController, self).__before__()

    def __get_rev_or_redirect(self, ref, repo, redirect_after=True,
                              partial=False):
        """
        Safe way to get changeset if error occur it redirects to changeset with
        proper message. If partial is set then don't do redirect raise Exception
        instead

        :param ref:
        :param repo:
        :param redirect_after:
        :param partial:
        """
        rev = ref[1] # default and used for git
        if repo.scm_instance.alias == 'hg':
            # lookup up the exact node id
            _revset_predicates = {
                    'branch': 'branch',
                    'book': 'bookmark',
                    'tag': 'tag',
                    'rev': 'id',
                }
            rev_spec = "max(%s(%%s))" % _revset_predicates[ref[0]]
            revs = repo.scm_instance._repo.revs(rev_spec, safe_str(ref[1]))
            if revs:
                rev = revs[-1]
            # else: TODO: just report 'not found'

        try:
            return repo.scm_instance.get_changeset(rev).raw_id
        except EmptyRepositoryError, e:
            if not redirect_after:
                return None
            h.flash(h.literal(_('There are no changesets yet')),
                    category='warning')
            redirect(url('summary_home', repo_name=repo.repo_name))

        except RepositoryError, e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='warning')
            if not partial:
                redirect(h.url('summary_home', repo_name=repo.repo_name))
            raise HTTPBadRequest()

    def _get_changesets(self, alias, org_repo, org_rev, other_repo, other_rev):
        """
        Returns lists of changesets that can be merged from org_repo@org_rev
        to other_repo@other_rev
        ... and the other way
        ... and the ancestor that would be used for merge

        :param org_repo: repo object, that is most likely the orginal repo we forked from
        :param org_rev: the revision we want our compare to be made
        :param other_repo: repo object, mostl likely the fork of org_repo. It hass
            all changesets that we need to obtain
        :param other_rev: revision we want out compare to be made on other_repo
        """
        ancestor = None
        if org_rev == other_rev:
            org_changesets = []
            other_changesets = []
            ancestor = org_rev

        elif alias == 'hg':
            #case two independent repos
            if org_repo != other_repo:
                hgrepo = unionrepo.unionrepository(other_repo.baseui,
                                                   other_repo.path,
                                                   org_repo.path)
                # all ancestors of other_rev will be in other_repo and
                # rev numbers from hgrepo can be used in other_repo - org_rev ancestors cannot

            #no remote compare do it on the same repository
            else:
                hgrepo = other_repo._repo

            ancestors = hgrepo.revs("ancestor(id(%s), id(%s))", org_rev, other_rev)
            if ancestors:
                # pick arbitrary ancestor - but there is usually only one
                ancestor = hgrepo[ancestors[0]].hex()

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
                SubprocessGitClient(thin_packs=False).fetch(other_repo.path, gitrepo)

                gitrepo_remote = Repo(other_repo.path)
                SubprocessGitClient(thin_packs=False).fetch(org_repo.path, gitrepo_remote)

                revs = []
                for x in gitrepo_remote.get_walker(include=[other_rev],
                                                   exclude=[org_rev]):
                    revs.append(x.commit.id)

                other_changesets = [other_repo.get_changeset(rev) for rev in reversed(revs)]
                if other_changesets:
                    ancestor = other_changesets[0].parents[0].raw_id
                else:
                    # no changesets from other repo, ancestor is the other_rev
                    ancestor = other_rev

            else:
                so, se = org_repo.run_git_command(
                    'log --reverse --pretty="format: %%H" -s %s..%s'
                        % (org_rev, other_rev)
                )
                other_changesets = [org_repo.get_changeset(cs)
                              for cs in re.findall(r'[0-9a-fA-F]{40}', so)]
            org_changesets = []

        else:
            raise Exception('Bad alias only git and hg is allowed')

        return other_changesets, org_changesets, ancestor

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self, repo_name):
        c.compare_home = True
        org_repo = c.db_repo.repo_name
        other_repo = request.GET.get('other_repo', org_repo)
        c.org_repo = Repository.get_by_repo_name(org_repo)
        c.other_repo = Repository.get_by_repo_name(other_repo)
        c.org_ref_name = c.other_ref_name = _('Select changeset')
        return render('compare/compare_diff.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def compare(self, repo_name, org_ref_type, org_ref_name, other_ref_type, other_ref_name):
        # org_ref will be evaluated in org_repo
        org_repo = c.db_repo.repo_name
        org_ref = (org_ref_type, org_ref_name)
        # other_ref will be evaluated in other_repo
        other_ref = (other_ref_type, other_ref_name)
        other_repo = request.GET.get('other_repo', org_repo)
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
        c.fulldiff = request.GET.get('fulldiff')
        # partial uses compare_cs.html template directly
        partial = request.environ.get('HTTP_X_PARTIAL_XHR')
        # as_form puts hidden input field with changeset revisions
        c.as_form = partial and request.GET.get('as_form')
        # swap url for compare_diff page - never partial and never as_form
        c.swap_url = h.url('compare_url',
            repo_name=other_repo,
            org_ref_type=other_ref_type, org_ref_name=other_ref_name,
            other_repo=org_repo,
            other_ref_type=org_ref_type, other_ref_name=org_ref_name,
            merge=merge or '')

        org_repo = Repository.get_by_repo_name(org_repo)
        other_repo = Repository.get_by_repo_name(other_repo)

        if org_repo is None:
            msg = 'Could not find org repo %s' % org_repo
            log.error(msg)
            h.flash(msg, category='error')
            return redirect(url('compare_home', repo_name=c.repo_name))

        if other_repo is None:
            msg = 'Could not find other repo %s' % other_repo
            log.error(msg)
            h.flash(msg, category='error')
            return redirect(url('compare_home', repo_name=c.repo_name))

        if org_repo.scm_instance.alias != other_repo.scm_instance.alias:
            msg = 'compare of two different kind of remote repos not available'
            log.error(msg)
            h.flash(msg, category='error')
            return redirect(url('compare_home', repo_name=c.repo_name))

        c.org_rev = self.__get_rev_or_redirect(ref=org_ref, repo=org_repo, partial=partial)
        c.other_rev = self.__get_rev_or_redirect(ref=other_ref, repo=other_repo, partial=partial)

        c.compare_home = False
        c.org_repo = org_repo
        c.other_repo = other_repo
        c.org_ref_name = org_ref_name
        c.other_ref_name = other_ref_name
        c.org_ref_type = org_ref_type
        c.other_ref_type = other_ref_type

        c.cs_ranges, c.cs_ranges_org, c.ancestor = self._get_changesets(
            org_repo.scm_instance.alias, org_repo.scm_instance, c.org_rev,
            other_repo.scm_instance, c.other_rev)
        c.statuses = c.db_repo.statuses(
            [x.raw_id for x in c.cs_ranges])

        if partial:
            return render('compare/compare_cs.html')
        if merge and c.ancestor:
            # case we want a simple diff without incoming changesets,
            # previewing what will be merged.
            # Make the diff on the other repo (which is known to have other_rev)
            log.debug('Using ancestor %s as rev1 instead of %s'
                      % (c.ancestor, c.org_rev))
            rev1 = c.ancestor
            org_repo = other_repo
        else: # comparing tips, not necessarily linearly related
            if merge:
                log.error('Unable to find ancestor revision')
            if org_repo != other_repo:
                log.error('cannot compare across repos %s and %s', org_repo, other_repo)
                raise HTTPNotFound
            rev1 = c.org_rev

        diff_limit = self.cut_off_limit if not c.fulldiff else None

        log.debug('running diff between %s and %s in %s'
                  % (rev1, c.other_rev, org_repo.scm_instance.path))
        txtdiff = org_repo.scm_instance.get_diff(rev1=rev1, rev2=c.other_rev)

        diff_processor = diffs.DiffProcessor(txtdiff or '', format='gitdiff',
                                             diff_limit=diff_limit)
        _parsed = diff_processor.prepare()

        c.limited_diff = False
        if isinstance(_parsed, LimitedDiffContainer):
            c.limited_diff = True

        c.files = []
        c.changes = {}
        c.lines_added = 0
        c.lines_deleted = 0
        for f in _parsed:
            st = f['stats']
            if not st['binary']:
                c.lines_added += st['added']
                c.lines_deleted += st['deleted']
            fid = h.FID('', f['filename'])
            c.files.append([fid, f['operation'], f['filename'], f['stats']])
            htmldiff = diff_processor.as_html(enable_comments=False, parsed_lines=[f])
            c.changes[fid] = [f['operation'], f['filename'], htmldiff]

        return render('compare/compare_diff.html')
