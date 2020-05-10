import re
from io import BytesIO
from itertools import chain
from subprocess import PIPE, Popen

from dulwich import objects
from dulwich.config import ConfigFile

from kallithea.lib.vcs.backends.base import BaseChangeset, EmptyChangeset
from kallithea.lib.vcs.conf import settings
from kallithea.lib.vcs.exceptions import ChangesetDoesNotExistError, ChangesetError, ImproperArchiveTypeError, NodeDoesNotExistError, RepositoryError, VCSError
from kallithea.lib.vcs.nodes import (AddedFileNodesGenerator, ChangedFileNodesGenerator, DirNode, FileNode, NodeKind, RemovedFileNodesGenerator, RootNode,
                                     SubModuleNode)
from kallithea.lib.vcs.utils import ascii_bytes, ascii_str, date_fromtimestamp, safe_int, safe_str
from kallithea.lib.vcs.utils.lazy import LazyProperty


class GitChangeset(BaseChangeset):
    """
    Represents state of the repository at a revision.
    """

    def __init__(self, repository, revision):
        self._stat_modes = {}
        self.repository = repository
        try:
            commit = self.repository._repo[ascii_bytes(revision)]
            if isinstance(commit, objects.Tag):
                revision = safe_str(commit.object[1])
                commit = self.repository._repo.get_object(commit.object[1])
        except KeyError:
            raise RepositoryError("Cannot get object with id %s" % revision)
        self.raw_id = ascii_str(commit.id)
        self.short_id = self.raw_id[:12]
        self._commit = commit  # a Dulwich Commmit with .id
        self._tree_id = commit.tree
        self._committer_property = 'committer'
        self._author_property = 'author'
        self._date_property = 'commit_time'
        self._date_tz_property = 'commit_timezone'
        self.revision = repository.revisions.index(self.raw_id)

        self.nodes = {}
        self._paths = {}

    @LazyProperty
    def bookmarks(self):
        return ()

    @LazyProperty
    def message(self):
        return safe_str(self._commit.message)

    @LazyProperty
    def committer(self):
        return safe_str(getattr(self._commit, self._committer_property))

    @LazyProperty
    def author(self):
        return safe_str(getattr(self._commit, self._author_property))

    @LazyProperty
    def date(self):
        return date_fromtimestamp(getattr(self._commit, self._date_property),
                                  getattr(self._commit, self._date_tz_property))

    @LazyProperty
    def _timestamp(self):
        return getattr(self._commit, self._date_property)

    @LazyProperty
    def status(self):
        """
        Returns modified, added, removed, deleted files for current changeset
        """
        return self.changed, self.added, self.removed

    @LazyProperty
    def tags(self):
        _tags = []
        for tname, tsha in self.repository.tags.items():
            if tsha == self.raw_id:
                _tags.append(tname)
        return _tags

    @LazyProperty
    def branch(self):
        # Note: This function will return one branch name for the changeset -
        # that might not make sense in Git where branches() is a better match
        # for the basic model
        heads = self.repository._heads(reverse=False)
        ref = heads.get(self._commit.id)
        if ref:
            return safe_str(ref)

    @LazyProperty
    def branches(self):
        heads = self.repository._heads(reverse=True)
        return [safe_str(b) for b in heads if heads[b] == self._commit.id] # FIXME: Inefficient ... and returning None!

    def _get_id_for_path(self, path):
        # FIXME: Please, spare a couple of minutes and make those codes cleaner;
        if path not in self._paths:
            path = path.strip('/')
            # set root tree
            tree = self.repository._repo[self._tree_id]
            if path == '':
                self._paths[''] = tree.id
                return tree.id
            splitted = path.split('/')
            dirs, name = splitted[:-1], splitted[-1]
            curdir = ''

            # initially extract things from root dir
            for item, stat, id in tree.items():
                name = safe_str(item)
                if curdir:
                    name = '/'.join((curdir, name))
                self._paths[name] = id
                self._stat_modes[name] = stat

            for dir in dirs:
                if curdir:
                    curdir = '/'.join((curdir, dir))
                else:
                    curdir = dir
                dir_id = None
                for item, stat, id in tree.items():
                    name = safe_str(item)
                    if dir == name:
                        dir_id = id
                if dir_id:
                    # Update tree
                    tree = self.repository._repo[dir_id]
                    if not isinstance(tree, objects.Tree):
                        raise ChangesetError('%s is not a directory' % curdir)
                else:
                    raise ChangesetError('%s have not been found' % curdir)

                # cache all items from the given traversed tree
                for item, stat, id in tree.items():
                    name = safe_str(item)
                    if curdir:
                        name = '/'.join((curdir, name))
                    self._paths[name] = id
                    self._stat_modes[name] = stat
            if path not in self._paths:
                raise NodeDoesNotExistError("There is no file nor directory "
                    "at the given path '%s' at revision %s"
                    % (path, self.short_id))
        return self._paths[path]

    def _get_kind(self, path):
        obj = self.repository._repo[self._get_id_for_path(path)]
        if isinstance(obj, objects.Blob):
            return NodeKind.FILE
        elif isinstance(obj, objects.Tree):
            return NodeKind.DIR

    def _get_filectx(self, path):
        path = path.rstrip('/')
        if self._get_kind(path) != NodeKind.FILE:
            raise ChangesetError("File does not exist for revision %s at "
                " '%s'" % (self.raw_id, path))
        return path

    def _get_file_nodes(self):
        return chain(*(t[2] for t in self.walk()))

    @LazyProperty
    def parents(self):
        """
        Returns list of parents changesets.
        """
        return [self.repository.get_changeset(ascii_str(parent_id))
                for parent_id in self._commit.parents]

    @LazyProperty
    def children(self):
        """
        Returns list of children changesets.
        """
        rev_filter = settings.GIT_REV_FILTER
        so = self.repository.run_git_command(
            ['rev-list', rev_filter, '--children']
        )
        return [
            self.repository.get_changeset(cs)
            for parts in (l.split(' ') for l in so.splitlines())
            if parts[0] == self.raw_id
            for cs in parts[1:]
        ]

    def next(self, branch=None):
        if branch and self.branch != branch:
            raise VCSError('Branch option used on changeset not belonging '
                           'to that branch')

        cs = self
        while True:
            try:
                next_ = cs.revision + 1
                next_rev = cs.repository.revisions[next_]
            except IndexError:
                raise ChangesetDoesNotExistError
            cs = cs.repository.get_changeset(next_rev)

            if not branch or branch == cs.branch:
                return cs

    def prev(self, branch=None):
        if branch and self.branch != branch:
            raise VCSError('Branch option used on changeset not belonging '
                           'to that branch')

        cs = self
        while True:
            try:
                prev_ = cs.revision - 1
                if prev_ < 0:
                    raise IndexError
                prev_rev = cs.repository.revisions[prev_]
            except IndexError:
                raise ChangesetDoesNotExistError
            cs = cs.repository.get_changeset(prev_rev)

            if not branch or branch == cs.branch:
                return cs

    def diff(self, ignore_whitespace=True, context=3):
        # Only used to feed diffstat
        rev1 = self.parents[0] if self.parents else self.repository.EMPTY_CHANGESET
        rev2 = self
        return self.repository.get_diff(rev1, rev2,
                                    ignore_whitespace=ignore_whitespace,
                                    context=context)

    def get_file_mode(self, path):
        """
        Returns stat mode of the file at the given ``path``.
        """
        # ensure path is traversed
        self._get_id_for_path(path)
        return self._stat_modes[path]

    def get_file_content(self, path):
        """
        Returns content of the file at given ``path``.
        """
        id = self._get_id_for_path(path)
        blob = self.repository._repo[id]
        return blob.as_pretty_string()

    def get_file_size(self, path):
        """
        Returns size of the file at given ``path``.
        """
        id = self._get_id_for_path(path)
        blob = self.repository._repo[id]
        return blob.raw_length()

    def get_file_changeset(self, path):
        """
        Returns last commit of the file at the given ``path``.
        """
        return self.get_file_history(path, limit=1)[0]

    def get_file_history(self, path, limit=None):
        """
        Returns history of file as reversed list of ``Changeset`` objects for
        which file at given ``path`` has been modified.

        TODO: This function now uses os underlying 'git' and 'grep' commands
        which is generally not good. Should be replaced with algorithm
        iterating commits.
        """
        self._get_filectx(path)

        if limit is not None:
            cmd = ['log', '-n', str(safe_int(limit, 0)),
                   '--pretty=format:%H', '-s', self.raw_id, '--', path]

        else:
            cmd = ['log',
                   '--pretty=format:%H', '-s', self.raw_id, '--', path]
        so = self.repository.run_git_command(cmd)
        ids = re.findall(r'[0-9a-fA-F]{40}', so)
        return [self.repository.get_changeset(sha) for sha in ids]

    def get_file_history_2(self, path):
        """
        Returns history of file as reversed list of ``Changeset`` objects for
        which file at given ``path`` has been modified.

        """
        self._get_filectx(path)
        from dulwich.walk import Walker
        include = [self.raw_id]
        walker = Walker(self.repository._repo.object_store, include,
                        paths=[path], max_entries=1)
        return [self.repository.get_changeset(ascii_str(x.commit.id.decode))
                for x in walker]

    def get_file_annotate(self, path):
        """
        Returns a generator of four element tuples with
            lineno, sha, changeset lazy loader and line
        """
        # TODO: This function now uses os underlying 'git' command which is
        # generally not good. Should be replaced with algorithm iterating
        # commits.
        cmd = ['blame', '-l', '--root', '-r', self.raw_id, '--', path]
        # -l     ==> outputs long shas (and we need all 40 characters)
        # --root ==> doesn't put '^' character for boundaries
        # -r sha ==> blames for the given revision
        so = self.repository.run_git_command(cmd)

        for i, blame_line in enumerate(so.split('\n')[:-1]):
            sha, line = re.split(r' ', blame_line, 1)
            yield (i + 1, sha, lambda sha=sha: self.repository.get_changeset(sha), line)

    def fill_archive(self, stream=None, kind='tgz', prefix=None,
                     subrepos=False):
        """
        Fills up given stream.

        :param stream: file like object.
        :param kind: one of following: ``zip``, ``tgz`` or ``tbz2``.
            Default: ``tgz``.
        :param prefix: name of root directory in archive.
            Default is repository name and changeset's raw_id joined with dash
            (``repo-tip.<KIND>``).
        :param subrepos: include subrepos in this archive.

        :raise ImproperArchiveTypeError: If given kind is wrong.
        :raise VcsError: If given stream is None
        """
        allowed_kinds = settings.ARCHIVE_SPECS
        if kind not in allowed_kinds:
            raise ImproperArchiveTypeError('Archive kind not supported use one'
                'of %s' % ' '.join(allowed_kinds))

        if stream is None:
            raise VCSError('You need to pass in a valid stream for filling'
                           ' with archival data')

        if prefix is None:
            prefix = '%s-%s' % (self.repository.name, self.short_id)
        elif prefix.startswith('/'):
            raise VCSError("Prefix cannot start with leading slash")
        elif prefix.strip() == '':
            raise VCSError("Prefix cannot be empty")

        if kind == 'zip':
            frmt = 'zip'
        else:
            frmt = 'tar'
        _git_path = settings.GIT_EXECUTABLE_PATH
        cmd = '%s archive --format=%s --prefix=%s/ %s' % (_git_path,
                                                frmt, prefix, self.raw_id)
        if kind == 'tgz':
            cmd += ' | gzip -9'
        elif kind == 'tbz2':
            cmd += ' | bzip2 -9'

        if stream is None:
            raise VCSError('You need to pass in a valid stream for filling'
                           ' with archival data')
        popen = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True,
                      cwd=self.repository.path)

        buffer_size = 1024 * 8
        chunk = popen.stdout.read(buffer_size)
        while chunk:
            stream.write(chunk)
            chunk = popen.stdout.read(buffer_size)
        # Make sure all descriptors would be read
        popen.communicate()

    def get_nodes(self, path):
        """
        Returns combined ``DirNode`` and ``FileNode`` objects list representing
        state of changeset at the given ``path``. If node at the given ``path``
        is not instance of ``DirNode``, ChangesetError would be raised.
        """

        if self._get_kind(path) != NodeKind.DIR:
            raise ChangesetError("Directory does not exist for revision %s at "
                " '%s'" % (self.revision, path))
        path = path.rstrip('/')
        id = self._get_id_for_path(path)
        tree = self.repository._repo[id]
        dirnodes = []
        filenodes = []
        als = self.repository.alias
        for name, stat, id in tree.items():
            obj_path = safe_str(name)
            if path != '':
                obj_path = '/'.join((path, obj_path))
            if objects.S_ISGITLINK(stat):
                root_tree = self.repository._repo[self._tree_id]
                cf = ConfigFile.from_file(BytesIO(self.repository._repo.get_object(root_tree[b'.gitmodules'][1]).data))
                url = ascii_str(cf.get(('submodule', obj_path), 'url'))
                dirnodes.append(SubModuleNode(obj_path, url=url, changeset=ascii_str(id),
                                              alias=als))
                continue

            obj = self.repository._repo.get_object(id)
            if obj_path not in self._stat_modes:
                self._stat_modes[obj_path] = stat
            if isinstance(obj, objects.Tree):
                dirnodes.append(DirNode(obj_path, changeset=self))
            elif isinstance(obj, objects.Blob):
                filenodes.append(FileNode(obj_path, changeset=self, mode=stat))
            else:
                raise ChangesetError("Requested object should be Tree "
                                     "or Blob, is %r" % type(obj))
        nodes = dirnodes + filenodes
        for node in nodes:
            if node.path not in self.nodes:
                self.nodes[node.path] = node
        nodes.sort()
        return nodes

    def get_node(self, path):
        """
        Returns ``Node`` object from the given ``path``. If there is no node at
        the given ``path``, ``ChangesetError`` would be raised.
        """
        path = path.rstrip('/')
        if path not in self.nodes:
            try:
                id_ = self._get_id_for_path(path)
            except ChangesetError:
                raise NodeDoesNotExistError("Cannot find one of parents' "
                    "directories for a given path: %s" % path)

            stat = self._stat_modes.get(path)
            if stat and objects.S_ISGITLINK(stat):
                tree = self.repository._repo[self._tree_id]
                cf = ConfigFile.from_file(BytesIO(self.repository._repo.get_object(tree[b'.gitmodules'][1]).data))
                url = ascii_str(cf.get(('submodule', path), 'url'))
                node = SubModuleNode(path, url=url, changeset=ascii_str(id_),
                                     alias=self.repository.alias)
            else:
                obj = self.repository._repo.get_object(id_)

                if isinstance(obj, objects.Tree):
                    if path == '':
                        node = RootNode(changeset=self)
                    else:
                        node = DirNode(path, changeset=self)
                    node._tree = obj
                elif isinstance(obj, objects.Blob):
                    node = FileNode(path, changeset=self)
                    node._blob = obj
                else:
                    raise NodeDoesNotExistError("There is no file nor directory "
                        "at the given path: '%s' at revision %s"
                        % (path, self.short_id))
            # cache node
            self.nodes[path] = node
        return self.nodes[path]

    @LazyProperty
    def affected_files(self):
        """
        Gets a fast accessible file changes for given changeset
        """
        added, modified, deleted = self._changes_cache
        return list(added.union(modified).union(deleted))

    @LazyProperty
    def _changes_cache(self):
        added = set()
        modified = set()
        deleted = set()
        _r = self.repository._repo

        parents = self.parents
        if not self.parents:
            parents = [EmptyChangeset()]
        for parent in parents:
            if isinstance(parent, EmptyChangeset):
                oid = None
            else:
                oid = _r[parent._commit.id].tree
            changes = _r.object_store.tree_changes(oid, _r[self._commit.id].tree)
            for (oldpath, newpath), (_, _), (_, _) in changes:
                if newpath and oldpath:
                    modified.add(safe_str(newpath))
                elif newpath and not oldpath:
                    added.add(safe_str(newpath))
                elif not newpath and oldpath:
                    deleted.add(safe_str(oldpath))
        return added, modified, deleted

    def _get_paths_for_status(self, status):
        """
        Returns sorted list of paths for given ``status``.

        :param status: one of: *added*, *modified* or *deleted*
        """
        added, modified, deleted = self._changes_cache
        return sorted({
            'added': list(added),
            'modified': list(modified),
            'deleted': list(deleted)}[status]
        )

    @LazyProperty
    def added(self):
        """
        Returns list of added ``FileNode`` objects.
        """
        if not self.parents:
            return list(self._get_file_nodes())
        return AddedFileNodesGenerator([n for n in
                                self._get_paths_for_status('added')], self)

    @LazyProperty
    def changed(self):
        """
        Returns list of modified ``FileNode`` objects.
        """
        if not self.parents:
            return []
        return ChangedFileNodesGenerator([n for n in
                                self._get_paths_for_status('modified')], self)

    @LazyProperty
    def removed(self):
        """
        Returns list of removed ``FileNode`` objects.
        """
        if not self.parents:
            return []
        return RemovedFileNodesGenerator([n for n in
                                self._get_paths_for_status('deleted')], self)

    extra = {}
