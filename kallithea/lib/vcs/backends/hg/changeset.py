import os
import posixpath

from kallithea.lib.vcs.conf import settings
from kallithea.lib.vcs.backends.base import BaseChangeset
from kallithea.lib.vcs.exceptions import (
    ChangesetDoesNotExistError, ChangesetError, ImproperArchiveTypeError,
    NodeDoesNotExistError, VCSError
)
from kallithea.lib.vcs.nodes import (
    AddedFileNodesGenerator, ChangedFileNodesGenerator, DirNode, FileNode,
    NodeKind, RemovedFileNodesGenerator, RootNode, SubModuleNode
)
from kallithea.lib.vcs.utils import safe_str, safe_unicode, date_fromtimestamp
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.lib.vcs.utils.paths import get_dirs_for_path
from kallithea.lib.vcs.utils.hgcompat import archival, hex

from mercurial import obsolete


class MercurialChangeset(BaseChangeset):
    """
    Represents state of the repository at the single revision.
    """

    def __init__(self, repository, revision):
        self.repository = repository
        assert isinstance(revision, basestring), repr(revision)
        self.raw_id = revision
        self._ctx = repository._repo[revision]
        self.revision = self._ctx._rev
        self.nodes = {}

    @LazyProperty
    def tags(self):
        return map(safe_unicode, self._ctx.tags())

    @LazyProperty
    def branch(self):
        return safe_unicode(self._ctx.branch())

    @LazyProperty
    def branches(self):
        return [safe_unicode(self._ctx.branch())]

    @LazyProperty
    def closesbranch(self):
        return self._ctx.closesbranch()

    @LazyProperty
    def obsolete(self):
        return self._ctx.obsolete()

    @LazyProperty
    def bumped(self):
        try:
            return self._ctx.phasedivergent()
        except AttributeError: # renamed in Mercurial 4.6 (9fa874fb34e1)
            return self._ctx.bumped()

    @LazyProperty
    def divergent(self):
        try:
            return self._ctx.contentdivergent()
        except AttributeError: # renamed in Mercurial 4.6 (8b2d7684407b)
            return self._ctx.divergent()

    @LazyProperty
    def extinct(self):
        return self._ctx.extinct()

    @LazyProperty
    def unstable(self):
        try:
            return self._ctx.orphan()
        except AttributeError: # renamed in Mercurial 4.6 (03039ff3082b)
            return self._ctx.unstable()

    @LazyProperty
    def phase(self):
        if(self._ctx.phase() == 1):
            return 'Draft'
        elif(self._ctx.phase() == 2):
            return 'Secret'
        else:
            return ''

    @LazyProperty
    def successors(self):
        try:
            # This works starting from Mercurial 4.3: the function `successorssets` was moved to the mercurial.obsutil module and gained the `closest` parameter.
            from mercurial import obsutil
            successors = obsutil.successorssets(self._ctx._repo, self._ctx.node(), closest=True)
        except ImportError:
            # fallback for older versions
            successors = obsolete.successorssets(self._ctx._repo, self._ctx.node())
        if successors:
            # flatten the list here handles both divergent (len > 1)
            # and the usual case (len = 1)
            successors = [hex(n)[:12] for sub in successors for n in sub if n != self._ctx.node()]

        return successors

    @LazyProperty
    def predecessors(self):
        try:
            # This works starting from Mercurial 4.3: the function `closestpredecessors` was added.
            from mercurial import obsutil
            return [hex(n)[:12] for n in obsutil.closestpredecessors(self._ctx._repo, self._ctx.node())]
        except ImportError:
            # fallback for older versions
            predecessors = set()
            nm = self._ctx._repo.changelog.nodemap
            for p in self._ctx._repo.obsstore.precursors.get(self._ctx.node(), ()):
                pr = nm.get(p[0])
                if pr is not None:
                    predecessors.add(hex(p[0])[:12])
            return predecessors

    @LazyProperty
    def bookmarks(self):
        return map(safe_unicode, self._ctx.bookmarks())

    @LazyProperty
    def message(self):
        return safe_unicode(self._ctx.description())

    @LazyProperty
    def committer(self):
        return safe_unicode(self.author)

    @LazyProperty
    def author(self):
        return safe_unicode(self._ctx.user())

    @LazyProperty
    def date(self):
        return date_fromtimestamp(*self._ctx.date())

    @LazyProperty
    def _timestamp(self):
        return self._ctx.date()[0]

    @LazyProperty
    def status(self):
        """
        Returns modified, added, removed, deleted files for current changeset
        """
        return self.repository._repo.status(self._ctx.p1().node(),
                                            self._ctx.node())

    @LazyProperty
    def _file_paths(self):
        return list(self._ctx)

    @LazyProperty
    def _dir_paths(self):
        p = list(set(get_dirs_for_path(*self._file_paths)))
        p.insert(0, '')
        return p

    @LazyProperty
    def _paths(self):
        return self._dir_paths + self._file_paths

    @LazyProperty
    def id(self):
        if self.last:
            return u'tip'
        return self.short_id

    @LazyProperty
    def short_id(self):
        return self.raw_id[:12]

    @LazyProperty
    def parents(self):
        """
        Returns list of parents changesets.
        """
        return [self.repository.get_changeset(parent.rev())
                for parent in self._ctx.parents() if parent.rev() >= 0]

    @LazyProperty
    def children(self):
        """
        Returns list of children changesets.
        """
        return [self.repository.get_changeset(child.rev())
                for child in self._ctx.children() if child.rev() >= 0]

    def next(self, branch=None):
        if branch and self.branch != branch:
            raise VCSError('Branch option used on changeset not belonging '
                           'to that branch')

        cs = self
        while True:
            try:
                next_ = cs.repository.revisions.index(cs.raw_id) + 1
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
                prev_ = cs.repository.revisions.index(cs.raw_id) - 1
                if prev_ < 0:
                    raise IndexError
                prev_rev = cs.repository.revisions[prev_]
            except IndexError:
                raise ChangesetDoesNotExistError
            cs = cs.repository.get_changeset(prev_rev)

            if not branch or branch == cs.branch:
                return cs

    def diff(self):
        # Only used for feed diffstat
        return ''.join(self._ctx.diff())

    def _fix_path(self, path):
        """
        Paths are stored without trailing slash so we need to get rid off it if
        needed. Also mercurial keeps filenodes as str so we need to decode
        from unicode to str
        """
        if path.endswith('/'):
            path = path.rstrip('/')

        return safe_str(path)

    def _get_kind(self, path):
        path = self._fix_path(path)
        if path in self._file_paths:
            return NodeKind.FILE
        elif path in self._dir_paths:
            return NodeKind.DIR
        else:
            raise ChangesetError("Node does not exist at the given path '%s'"
                % (path))

    def _get_filectx(self, path):
        path = self._fix_path(path)
        if self._get_kind(path) != NodeKind.FILE:
            raise ChangesetError("File does not exist for revision %s at "
                " '%s'" % (self.raw_id, path))
        return self._ctx.filectx(path)

    def _extract_submodules(self):
        """
        returns a dictionary with submodule information from substate file
        of hg repository
        """
        return self._ctx.substate

    def get_file_mode(self, path):
        """
        Returns stat mode of the file at the given ``path``.
        """
        fctx = self._get_filectx(path)
        if 'x' in fctx.flags():
            return 0100755
        else:
            return 0100644

    def get_file_content(self, path):
        """
        Returns content of the file at given ``path``.
        """
        fctx = self._get_filectx(path)
        return fctx.data()

    def get_file_size(self, path):
        """
        Returns size of the file at given ``path``.
        """
        fctx = self._get_filectx(path)
        return fctx.size()

    def get_file_changeset(self, path):
        """
        Returns last commit of the file at the given ``path``.
        """
        return self.get_file_history(path, limit=1)[0]

    def get_file_history(self, path, limit=None):
        """
        Returns history of file as reversed list of ``Changeset`` objects for
        which file at given ``path`` has been modified.
        """
        fctx = self._get_filectx(path)
        hist = []
        cnt = 0
        for cs in reversed([x for x in fctx.filelog()]):
            cnt += 1
            hist.append(hex(fctx.filectx(cs).node()))
            if limit is not None and cnt == limit:
                break

        return [self.repository.get_changeset(node) for node in hist]

    def get_file_annotate(self, path):
        """
        Returns a generator of four element tuples with
            lineno, sha, changeset lazy loader and line
        """
        annotations = self._get_filectx(path).annotate()
        try:
            annotation_lines = [(annotateline.fctx, annotateline.text) for annotateline in annotations]
        except AttributeError: # annotateline was introduced in Mercurial 4.6 (b33b91ca2ec2)
            try:
                annotation_lines = [(aline.fctx, l) for aline, l in annotations]
            except AttributeError: # aline.fctx was introduced in Mercurial 4.4
                annotation_lines = [(aline[0], l) for aline, l in annotations]
        for i, (fctx, l) in enumerate(annotation_lines):
            sha = fctx.hex()
            yield (i + 1, sha, lambda sha=sha, l=l: self.repository.get_changeset(sha), l)

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

        allowed_kinds = settings.ARCHIVE_SPECS.keys()
        if kind not in allowed_kinds:
            raise ImproperArchiveTypeError('Archive kind not supported use one'
                'of %s', allowed_kinds)

        if stream is None:
            raise VCSError('You need to pass in a valid stream for filling'
                           ' with archival data')

        if prefix is None:
            prefix = '%s-%s' % (self.repository.name, self.short_id)
        elif prefix.startswith('/'):
            raise VCSError("Prefix cannot start with leading slash")
        elif prefix.strip() == '':
            raise VCSError("Prefix cannot be empty")

        archival.archive(self.repository._repo, stream, self.raw_id,
                         kind, prefix=prefix, subrepos=subrepos)

    def get_nodes(self, path):
        """
        Returns combined ``DirNode`` and ``FileNode`` objects list representing
        state of changeset at the given ``path``. If node at the given ``path``
        is not instance of ``DirNode``, ChangesetError would be raised.
        """

        if self._get_kind(path) != NodeKind.DIR:
            raise ChangesetError("Directory does not exist for revision %s at "
                " '%s'" % (self.revision, path))
        path = self._fix_path(path)

        filenodes = [FileNode(f, changeset=self) for f in self._file_paths
            if os.path.dirname(f) == path]
        dirs = path == '' and '' or [d for d in self._dir_paths
            if d and posixpath.dirname(d) == path]
        dirnodes = [DirNode(d, changeset=self) for d in dirs
            if os.path.dirname(d) == path]

        als = self.repository.alias
        for k, vals in self._extract_submodules().iteritems():
            #vals = url,rev,type
            loc = vals[0]
            cs = vals[1]
            dirnodes.append(SubModuleNode(k, url=loc, changeset=cs,
                                          alias=als))
        nodes = dirnodes + filenodes
        # cache nodes
        for node in nodes:
            self.nodes[node.path] = node
        nodes.sort()

        return nodes

    def get_node(self, path):
        """
        Returns ``Node`` object from the given ``path``. If there is no node at
        the given ``path``, ``ChangesetError`` would be raised.
        """

        path = self._fix_path(path)

        if path not in self.nodes:
            if path in self._file_paths:
                node = FileNode(path, changeset=self)
            elif path in self._dir_paths or path in self._dir_paths:
                if path == '':
                    node = RootNode(changeset=self)
                else:
                    node = DirNode(path, changeset=self)
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
        return self._ctx.files()

    @property
    def added(self):
        """
        Returns list of added ``FileNode`` objects.
        """
        return AddedFileNodesGenerator([n for n in self.status[1]], self)

    @property
    def changed(self):
        """
        Returns list of modified ``FileNode`` objects.
        """
        return ChangedFileNodesGenerator([n for n in self.status[0]], self)

    @property
    def removed(self):
        """
        Returns list of removed ``FileNode`` objects.
        """
        return RemovedFileNodesGenerator([n for n in self.status[2]], self)

    @LazyProperty
    def extra(self):
        return self._ctx.extra()
