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
kallithea.controllers.files
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Files controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 21, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement
import os
import logging
import traceback
import tempfile
import shutil

from pylons import request, response, tmpl_context as c, url
from pylons.i18n.translation import _
from pylons.controllers.util import redirect
from kallithea.lib.utils import jsonify, action_logger

from kallithea.lib import diffs
from kallithea.lib import helpers as h

from kallithea.lib.compat import OrderedDict
from kallithea.lib.utils2 import convert_line_endings, detect_mode, safe_str,\
    str2bool
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.vcs.backends.base import EmptyChangeset
from kallithea.lib.vcs.conf import settings
from kallithea.lib.vcs.exceptions import RepositoryError, \
    ChangesetDoesNotExistError, EmptyRepositoryError, \
    ImproperArchiveTypeError, VCSError, NodeAlreadyExistsError,\
    NodeDoesNotExistError, ChangesetError, NodeError
from kallithea.lib.vcs.nodes import FileNode

from kallithea.model.repo import RepoModel
from kallithea.model.scm import ScmModel
from kallithea.model.db import Repository

from kallithea.controllers.changeset import anchor_url, _ignorews_url,\
    _context_url, get_line_ctx, get_ignore_ws
from webob.exc import HTTPNotFound
from kallithea.lib.exceptions import NonRelativePathError


log = logging.getLogger(__name__)


class FilesController(BaseRepoController):

    def __before__(self):
        super(FilesController, self).__before__()
        c.cut_off_limit = self.cut_off_limit

    def __get_cs(self, rev, silent_empty=False):
        """
        Safe way to get changeset if error occur it redirects to tip with
        proper message

        :param rev: revision to fetch
        :silent_empty: return None if repository is empty
        """

        try:
            return c.db_repo_scm_instance.get_changeset(rev)
        except EmptyRepositoryError, e:
            if silent_empty:
                return None
            url_ = url('files_add_home',
                       repo_name=c.repo_name,
                       revision=0, f_path='', anchor='edit')
            add_new = h.link_to(_('Click here to add new file'), url_, class_="alert-link")
            h.flash(h.literal(_('There are no files yet. %s') % add_new),
                    category='warning')
            raise HTTPNotFound()
        except(ChangesetDoesNotExistError, LookupError), e:
            msg = _('Such revision does not exist for this repository')
            h.flash(msg, category='error')
            raise HTTPNotFound()
        except RepositoryError, e:
            h.flash(safe_str(e), category='error')
            raise HTTPNotFound()

    def __get_filenode(self, cs, path):
        """
        Returns file_node or raise HTTP error.

        :param cs: given changeset
        :param path: path to lookup
        """

        try:
            file_node = cs.get_node(path)
            if file_node.is_dir():
                raise RepositoryError('given path is a directory')
        except(ChangesetDoesNotExistError,), e:
            msg = _('Such revision does not exist for this repository')
            h.flash(msg, category='error')
            raise HTTPNotFound()
        except RepositoryError, e:
            h.flash(safe_str(e), category='error')
            raise HTTPNotFound()

        return file_node

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self, repo_name, revision, f_path, annotate=False):
        # redirect to given revision from form if given
        post_revision = request.POST.get('at_rev', None)
        if post_revision:
            cs = self.__get_cs(post_revision) # FIXME - unused!

        c.revision = revision
        c.changeset = self.__get_cs(revision)
        c.branch = request.GET.get('branch', None)
        c.f_path = f_path
        c.annotate = annotate
        cur_rev = c.changeset.revision

        # prev link
        try:
            prev_rev = c.db_repo_scm_instance.get_changeset(cur_rev).prev(c.branch)
            c.url_prev = url('files_home', repo_name=c.repo_name,
                         revision=prev_rev.raw_id, f_path=f_path)
            if c.branch:
                c.url_prev += '?branch=%s' % c.branch
        except (ChangesetDoesNotExistError, VCSError):
            c.url_prev = '#'

        # next link
        try:
            next_rev = c.db_repo_scm_instance.get_changeset(cur_rev).next(c.branch)
            c.url_next = url('files_home', repo_name=c.repo_name,
                     revision=next_rev.raw_id, f_path=f_path)
            if c.branch:
                c.url_next += '?branch=%s' % c.branch
        except (ChangesetDoesNotExistError, VCSError):
            c.url_next = '#'

        # files or dirs
        try:
            c.file = c.changeset.get_node(f_path)

            if c.file.is_file():
                c.load_full_history = False
                file_last_cs = c.file.last_changeset
                c.file_changeset = (c.changeset
                                    if c.changeset.revision < file_last_cs.revision
                                    else file_last_cs)
                #determine if we're on branch head
                _branches = c.db_repo_scm_instance.branches
                c.on_branch_head = revision in _branches.keys() + _branches.values()
                _hist = []
                c.file_history = []
                if c.load_full_history:
                    c.file_history, _hist = self._get_node_history(c.changeset, f_path)

                c.authors = []
                for a in set([x.author for x in _hist]):
                    c.authors.append((h.email(a), h.person(a)))
            else:
                c.authors = c.file_history = []
        except RepositoryError, e:
            h.flash(safe_str(e), category='error')
            raise HTTPNotFound()

        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            return render('files/files_ypjax.html')

        # TODO: tags and bookmarks?
        c.revision_options = [(c.changeset.raw_id,
                              _('%s at %s') % (c.changeset.branch, h.short_id(c.changeset.raw_id)))] + \
            [(n, b) for b, n in c.db_repo_scm_instance.branches.items()]
        if c.db_repo_scm_instance.closed_branches:
            prefix = _('(closed)') + ' '
            c.revision_options += [('-', '-')] + \
                [(n, prefix + b) for b, n in c.db_repo_scm_instance.closed_branches.items()]

        return render('files/files.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def history(self, repo_name, revision, f_path):
        changeset = self.__get_cs(revision)
        f_path = f_path
        _file = changeset.get_node(f_path)
        if _file.is_file():
            file_history, _hist = self._get_node_history(changeset, f_path)

            res = []
            for obj in file_history:
                res.append({
                    'text': obj[1],
                    'children': [{'id': o[0], 'text': o[1]} for o in obj[0]]
                })

            data = {
                'more': False,
                'results': res
            }
            return data

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def authors(self, repo_name, revision, f_path):
        changeset = self.__get_cs(revision)
        f_path = f_path
        _file = changeset.get_node(f_path)
        if _file.is_file():
            file_history, _hist = self._get_node_history(changeset, f_path)
            c.authors = []
            for a in set([x.author for x in _hist]):
                c.authors.append((h.email(a), h.person(a)))
            return render('files/files_history_box.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def rawfile(self, repo_name, revision, f_path):
        cs = self.__get_cs(revision)
        file_node = self.__get_filenode(cs, f_path)

        response.content_disposition = 'attachment; filename=%s' % \
            safe_str(f_path.split(Repository.url_sep())[-1])

        response.content_type = file_node.mimetype
        return file_node.content

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def raw(self, repo_name, revision, f_path):
        cs = self.__get_cs(revision)
        file_node = self.__get_filenode(cs, f_path)

        raw_mimetype_mapping = {
            # map original mimetype to a mimetype used for "show as raw"
            # you can also provide a content-disposition to override the
            # default "attachment" disposition.
            # orig_type: (new_type, new_dispo)

            # show images inline:
            'image/x-icon': ('image/x-icon', 'inline'),
            'image/png': ('image/png', 'inline'),
            'image/gif': ('image/gif', 'inline'),
            'image/jpeg': ('image/jpeg', 'inline'),
            'image/svg+xml': ('image/svg+xml', 'inline'),
        }

        mimetype = file_node.mimetype
        try:
            mimetype, dispo = raw_mimetype_mapping[mimetype]
        except KeyError:
            # we don't know anything special about this, handle it safely
            if file_node.is_binary:
                # do same as download raw for binary files
                mimetype, dispo = 'application/octet-stream', 'attachment'
            else:
                # do not just use the original mimetype, but force text/plain,
                # otherwise it would serve text/html and that might be unsafe.
                # Note: underlying vcs library fakes text/plain mimetype if the
                # mimetype can not be determined and it thinks it is not
                # binary.This might lead to erroneous text display in some
                # cases, but helps in other cases, like with text files
                # without extension.
                mimetype, dispo = 'text/plain', 'inline'

        if dispo == 'attachment':
            dispo = 'attachment; filename=%s' % \
                        safe_str(f_path.split(os.sep)[-1])

        response.content_disposition = dispo
        response.content_type = mimetype
        return file_node.content

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.write', 'repository.admin')
    def delete(self, repo_name, revision, f_path):
        repo = c.db_repo
        if repo.enable_locking and repo.locked[0]:
            h.flash(_('This repository has been locked by %s on %s')
                % (h.person_by_id(repo.locked[0]),
                   h.fmt_date(h.time_to_datetime(repo.locked[1]))),
                'warning')
            return redirect(h.url('files_home',
                                  repo_name=repo_name, revision='tip'))

        # check if revision is a branch identifier- basically we cannot
        # create multiple heads via file editing
        _branches = repo.scm_instance.branches
        # check if revision is a branch name or branch hash
        if revision not in _branches.keys() + _branches.values():
            h.flash(_('You can only delete files with revision '
                      'being a valid branch '), category='warning')
            return redirect(h.url('files_home',
                                  repo_name=repo_name, revision='tip',
                                  f_path=f_path))

        r_post = request.POST

        c.cs = self.__get_cs(revision)
        c.file = self.__get_filenode(c.cs, f_path)

        c.default_message = _('Deleted file %s via Kallithea') % (f_path)
        c.f_path = f_path
        node_path = f_path
        author = self.authuser.full_contact

        if r_post:
            message = r_post.get('message') or c.default_message

            try:
                nodes = {
                    node_path: {
                        'content': ''
                    }
                }
                self.scm_model.delete_nodes(
                    user=c.authuser.user_id, repo=c.db_repo,
                    message=message,
                    nodes=nodes,
                    parent_cs=c.cs,
                    author=author,
                )

                h.flash(_('Successfully deleted file %s') % f_path,
                        category='success')
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during commit'), category='error')
            return redirect(url('changeset_home',
                                repo_name=c.repo_name, revision='tip'))

        return render('files/files_delete.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.write', 'repository.admin')
    def edit(self, repo_name, revision, f_path):
        repo = c.db_repo
        if repo.enable_locking and repo.locked[0]:
            h.flash(_('This repository has been locked by %s on %s')
                % (h.person_by_id(repo.locked[0]),
                   h.fmt_date(h.time_to_datetime(repo.locked[1]))),
                'warning')
            return redirect(h.url('files_home',
                                  repo_name=repo_name, revision='tip'))

        # check if revision is a branch identifier- basically we cannot
        # create multiple heads via file editing
        _branches = repo.scm_instance.branches
        # check if revision is a branch name or branch hash
        if revision not in _branches.keys() + _branches.values():
            h.flash(_('You can only edit files with revision '
                      'being a valid branch '), category='warning')
            return redirect(h.url('files_home',
                                  repo_name=repo_name, revision='tip',
                                  f_path=f_path))

        r_post = request.POST

        c.cs = self.__get_cs(revision)
        c.file = self.__get_filenode(c.cs, f_path)

        if c.file.is_binary:
            return redirect(url('files_home', repo_name=c.repo_name,
                            revision=c.cs.raw_id, f_path=f_path))
        c.default_message = _('Edited file %s via Kallithea') % (f_path)
        c.f_path = f_path

        if r_post:

            old_content = c.file.content
            sl = old_content.splitlines(1)
            first_line = sl[0] if sl else ''
            # modes:  0 - Unix, 1 - Mac, 2 - DOS
            mode = detect_mode(first_line, 0)
            content = convert_line_endings(r_post.get('content', ''), mode)

            message = r_post.get('message') or c.default_message
            author = self.authuser.full_contact

            if content == old_content:
                h.flash(_('No changes'), category='warning')
                return redirect(url('changeset_home', repo_name=c.repo_name,
                                    revision='tip'))
            try:
                self.scm_model.commit_change(repo=c.db_repo_scm_instance,
                                             repo_name=repo_name, cs=c.cs,
                                             user=self.authuser.user_id,
                                             author=author, message=message,
                                             content=content, f_path=f_path)
                h.flash(_('Successfully committed to %s') % f_path,
                        category='success')
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during commit'), category='error')
            return redirect(url('changeset_home',
                                repo_name=c.repo_name, revision='tip'))

        return render('files/files_edit.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.write', 'repository.admin')
    def add(self, repo_name, revision, f_path):

        repo = Repository.get_by_repo_name(repo_name)
        if repo.enable_locking and repo.locked[0]:
            h.flash(_('This repository has been locked by %s on %s')
                % (h.person_by_id(repo.locked[0]),
                   h.fmt_date(h.time_to_datetime(repo.locked[1]))),
                  'warning')
            return redirect(h.url('files_home',
                                  repo_name=repo_name, revision='tip'))

        r_post = request.POST
        c.cs = self.__get_cs(revision, silent_empty=True)
        if c.cs is None:
            c.cs = EmptyChangeset(alias=c.db_repo_scm_instance.alias)
        c.default_message = (_('Added file via Kallithea'))
        c.f_path = f_path

        if r_post:
            unix_mode = 0
            content = convert_line_endings(r_post.get('content', ''), unix_mode)

            message = r_post.get('message') or c.default_message
            filename = r_post.get('filename')
            location = r_post.get('location', '')
            file_obj = r_post.get('upload_file', None)

            if file_obj is not None and hasattr(file_obj, 'filename'):
                filename = file_obj.filename
                content = file_obj.file

                if hasattr(content, 'file'):
                    # non posix systems store real file under file attr
                    content = content.file

            if not content:
                h.flash(_('No content'), category='warning')
                return redirect(url('changeset_home', repo_name=c.repo_name,
                                    revision='tip'))
            if not filename:
                h.flash(_('No filename'), category='warning')
                return redirect(url('changeset_home', repo_name=c.repo_name,
                                    revision='tip'))
            #strip all crap out of file, just leave the basename
            filename = os.path.basename(filename)
            node_path = os.path.join(location, filename)
            author = self.authuser.full_contact

            try:
                nodes = {
                    node_path: {
                        'content': content
                    }
                }
                self.scm_model.create_nodes(
                    user=c.authuser.user_id, repo=c.db_repo,
                    message=message,
                    nodes=nodes,
                    parent_cs=c.cs,
                    author=author,
                )

                h.flash(_('Successfully committed to %s') % node_path,
                        category='success')
            except NonRelativePathError, e:
                h.flash(_('Location must be relative path and must not '
                          'contain .. in path'), category='warning')
                return redirect(url('changeset_home', repo_name=c.repo_name,
                                    revision='tip'))
            except (NodeError, NodeAlreadyExistsError), e:
                h.flash(_(e), category='error')
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during commit'), category='error')
            return redirect(url('changeset_home',
                                repo_name=c.repo_name, revision='tip'))

        return render('files/files_add.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def archivefile(self, repo_name, fname):

        fileformat = None
        revision = None
        ext = None
        subrepos = request.GET.get('subrepos') == 'true'

        for a_type, ext_data in settings.ARCHIVE_SPECS.items():
            archive_spec = fname.split(ext_data[1])
            if len(archive_spec) == 2 and archive_spec[1] == '':
                fileformat = a_type or ext_data[1]
                revision = archive_spec[0]
                ext = ext_data[1]

        try:
            dbrepo = RepoModel().get_by_repo_name(repo_name)
            if not dbrepo.enable_downloads:
                return _('Downloads disabled')

            if c.db_repo_scm_instance.alias == 'hg':
                # patch and reset hooks section of UI config to not run any
                # hooks on fetching archives with subrepos
                for k, v in c.db_repo_scm_instance._repo.ui.configitems('hooks'):
                    c.db_repo_scm_instance._repo.ui.setconfig('hooks', k, None)

            cs = c.db_repo_scm_instance.get_changeset(revision)
            content_type = settings.ARCHIVE_SPECS[fileformat][0]
        except ChangesetDoesNotExistError:
            return _('Unknown revision %s') % revision
        except EmptyRepositoryError:
            return _('Empty repository')
        except (ImproperArchiveTypeError, KeyError):
            return _('Unknown archive type')
        # archive cache
        from kallithea import CONFIG
        rev_name = cs.raw_id[:12]
        archive_name = '%s-%s%s' % (safe_str(repo_name.replace('/', '_')),
                                    safe_str(rev_name), ext)

        use_cached_archive = False  # defines if we use cached version of archive
        archive_cache_enabled = CONFIG.get('archive_cache_dir')
        if not subrepos and archive_cache_enabled:
            #check if we it's ok to write
            if not os.path.isdir(CONFIG['archive_cache_dir']):
                os.makedirs(CONFIG['archive_cache_dir'])
            cached_archive_path = os.path.join(CONFIG['archive_cache_dir'], archive_name)
            if os.path.isfile(cached_archive_path):
                log.debug('Found cached archive in %s' % cached_archive_path)
                fd, archive = None, cached_archive_path
                use_cached_archive = True
            else:
                log.debug('Archive %s is not yet cached' % (archive_name))

        if not use_cached_archive:
            # generate new archive
            fd, archive = tempfile.mkstemp()
            temp_stream = open(archive, 'wb')
            log.debug('Creating new temp archive in %s' % archive)
            cs.fill_archive(stream=temp_stream, kind=fileformat, subrepos=subrepos)
            temp_stream.close()
            if not subrepos and archive_cache_enabled:
                #if we generated the archive and use cache rename that
                log.debug('Storing new archive in %s' % cached_archive_path)
                shutil.move(archive, cached_archive_path)
                archive = cached_archive_path

        def get_chunked_archive(archive):
            stream = open(archive, 'rb')
            while True:
                data = stream.read(16 * 1024)
                if not data:
                    stream.close()
                    if fd:  # fd means we used temporary file
                        os.close(fd)
                    if not archive_cache_enabled:
                        log.debug('Destroying temp archive %s' % archive)
                        os.remove(archive)
                    break
                yield data
        # store download action
        action_logger(user=c.authuser,
                      action='user_downloaded_archive:%s' % (archive_name),
                      repo=repo_name, ipaddr=self.ip_addr, commit=True)
        response.content_disposition = str('attachment; filename=%s' % (archive_name))
        response.content_type = str(content_type)
        return get_chunked_archive(archive)

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def diff(self, repo_name, f_path):
        ignore_whitespace = request.GET.get('ignorews') == '1'
        line_context = request.GET.get('context', 3)
        diff2 = request.GET.get('diff2', '')
        diff1 = request.GET.get('diff1', '') or diff2
        c.action = request.GET.get('diff')
        c.no_changes = diff1 == diff2
        c.f_path = f_path
        c.big_diff = False
        c.anchor_url = anchor_url
        c.ignorews_url = _ignorews_url
        c.context_url = _context_url
        c.changes = OrderedDict()
        c.changes[diff2] = []

        #special case if we want a show rev only, it's impl here
        #to reduce JS and callbacks

        if request.GET.get('show_rev'):
            if str2bool(request.GET.get('annotate', 'False')):
                _url = url('files_annotate_home', repo_name=c.repo_name,
                           revision=diff1, f_path=c.f_path)
            else:
                _url = url('files_home', repo_name=c.repo_name,
                           revision=diff1, f_path=c.f_path)

            return redirect(_url)
        try:
            if diff1 not in ['', None, 'None', '0' * 12, '0' * 40]:
                c.changeset_1 = c.db_repo_scm_instance.get_changeset(diff1)
                try:
                    node1 = c.changeset_1.get_node(f_path)
                    if node1.is_dir():
                        raise NodeError('%s path is a %s not a file'
                                        % (node1, type(node1)))
                except NodeDoesNotExistError:
                    c.changeset_1 = EmptyChangeset(cs=diff1,
                                                   revision=c.changeset_1.revision,
                                                   repo=c.db_repo_scm_instance)
                    node1 = FileNode(f_path, '', changeset=c.changeset_1)
            else:
                c.changeset_1 = EmptyChangeset(repo=c.db_repo_scm_instance)
                node1 = FileNode(f_path, '', changeset=c.changeset_1)

            if diff2 not in ['', None, 'None', '0' * 12, '0' * 40]:
                c.changeset_2 = c.db_repo_scm_instance.get_changeset(diff2)
                try:
                    node2 = c.changeset_2.get_node(f_path)
                    if node2.is_dir():
                        raise NodeError('%s path is a %s not a file'
                                        % (node2, type(node2)))
                except NodeDoesNotExistError:
                    c.changeset_2 = EmptyChangeset(cs=diff2,
                                                   revision=c.changeset_2.revision,
                                                   repo=c.db_repo_scm_instance)
                    node2 = FileNode(f_path, '', changeset=c.changeset_2)
            else:
                c.changeset_2 = EmptyChangeset(repo=c.db_repo_scm_instance)
                node2 = FileNode(f_path, '', changeset=c.changeset_2)
        except (RepositoryError, NodeError):
            log.error(traceback.format_exc())
            return redirect(url('files_home', repo_name=c.repo_name,
                                f_path=f_path))

        if c.action == 'download':
            _diff = diffs.get_gitdiff(node1, node2,
                                      ignore_whitespace=ignore_whitespace,
                                      context=line_context)
            diff = diffs.DiffProcessor(_diff, format='gitdiff')

            diff_name = '%s_vs_%s.diff' % (diff1, diff2)
            response.content_type = 'text/plain'
            response.content_disposition = (
                'attachment; filename=%s' % diff_name
            )
            return diff.as_raw()

        elif c.action == 'raw':
            _diff = diffs.get_gitdiff(node1, node2,
                                      ignore_whitespace=ignore_whitespace,
                                      context=line_context)
            diff = diffs.DiffProcessor(_diff, format='gitdiff')
            response.content_type = 'text/plain'
            return diff.as_raw()

        else:
            fid = h.FID(diff2, node2.path)
            line_context_lcl = get_line_ctx(fid, request.GET)
            ign_whitespace_lcl = get_ignore_ws(fid, request.GET)

            lim = request.GET.get('fulldiff') or self.cut_off_limit
            _, cs1, cs2, diff, st = diffs.wrapped_diff(filenode_old=node1,
                                         filenode_new=node2,
                                         cut_off_limit=lim,
                                         ignore_whitespace=ign_whitespace_lcl,
                                         line_context=line_context_lcl,
                                         enable_comments=False)
            op = ''
            filename = node1.path
            cs_changes = {
                'fid': [cs1, cs2, op, filename, diff, st]
            }
            c.changes = cs_changes

        return render('files/file_diff.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def diff_2way(self, repo_name, f_path):
        diff1 = request.GET.get('diff1', '')
        diff2 = request.GET.get('diff2', '')
        try:
            if diff1 not in ['', None, 'None', '0' * 12, '0' * 40]:
                c.changeset_1 = c.db_repo_scm_instance.get_changeset(diff1)
                try:
                    node1 = c.changeset_1.get_node(f_path)
                    if node1.is_dir():
                        raise NodeError('%s path is a %s not a file'
                                        % (node1, type(node1)))
                except NodeDoesNotExistError:
                    c.changeset_1 = EmptyChangeset(cs=diff1,
                                                   revision=c.changeset_1.revision,
                                                   repo=c.db_repo_scm_instance)
                    node1 = FileNode(f_path, '', changeset=c.changeset_1)
            else:
                c.changeset_1 = EmptyChangeset(repo=c.db_repo_scm_instance)
                node1 = FileNode(f_path, '', changeset=c.changeset_1)

            if diff2 not in ['', None, 'None', '0' * 12, '0' * 40]:
                c.changeset_2 = c.db_repo_scm_instance.get_changeset(diff2)
                try:
                    node2 = c.changeset_2.get_node(f_path)
                    if node2.is_dir():
                        raise NodeError('%s path is a %s not a file'
                                        % (node2, type(node2)))
                except NodeDoesNotExistError:
                    c.changeset_2 = EmptyChangeset(cs=diff2,
                                                   revision=c.changeset_2.revision,
                                                   repo=c.db_repo_scm_instance)
                    node2 = FileNode(f_path, '', changeset=c.changeset_2)
            else:
                c.changeset_2 = EmptyChangeset(repo=c.db_repo_scm_instance)
                node2 = FileNode(f_path, '', changeset=c.changeset_2)
        except ChangesetDoesNotExistError as e:
            msg = _('Such revision does not exist for this repository')
            h.flash(msg, category='error')
            raise HTTPNotFound()
        c.node1 = node1
        c.node2 = node2
        c.cs1 = c.changeset_1
        c.cs2 = c.changeset_2

        return render('files/diff_2way.html')

    def _get_node_history(self, cs, f_path, changesets=None):
        """
        get changesets history for given node

        :param cs: changeset to calculate history
        :param f_path: path for node to calculate history for
        :param changesets: if passed don't calculate history and take
            changesets defined in this list
        """
        # calculate history based on tip
        tip_cs = c.db_repo_scm_instance.get_changeset()
        if changesets is None:
            try:
                changesets = tip_cs.get_file_history(f_path)
            except (NodeDoesNotExistError, ChangesetError):
                #this node is not present at tip !
                changesets = cs.get_file_history(f_path)
        hist_l = []

        changesets_group = ([], _("Changesets"))
        branches_group = ([], _("Branches"))
        tags_group = ([], _("Tags"))
        for chs in changesets:
            #_branch = '(%s)' % chs.branch if (cs.repository.alias == 'hg') else ''
            _branch = chs.branch
            n_desc = '%s (%s)' % (h.show_id(chs), _branch)
            changesets_group[0].append((chs.raw_id, n_desc,))
        hist_l.append(changesets_group)

        for name, chs in c.db_repo_scm_instance.branches.items():
            branches_group[0].append((chs, name),)
        hist_l.append(branches_group)

        for name, chs in c.db_repo_scm_instance.tags.items():
            tags_group[0].append((chs, name),)
        hist_l.append(tags_group)

        return hist_l, changesets

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def nodelist(self, repo_name, revision, f_path):
        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            cs = self.__get_cs(revision)
            _d, _f = ScmModel().get_nodes(repo_name, cs.raw_id, f_path,
                                          flat=False)
            return {'nodes': _d + _f}
