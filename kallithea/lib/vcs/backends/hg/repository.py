# -*- coding: utf-8 -*-
"""
    vcs.backends.hg.repository
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Mercurial repository implementation.

    :created_on: Apr 8, 2010
    :copyright: (c) 2010-2011 by Marcin Kuzminski, Lukasz Balcerzak.
"""

import os
import time
import urllib
import urllib2
import logging
import datetime

from kallithea.lib.vcs.backends.base import BaseRepository, CollectionGenerator

from kallithea.lib.vcs.exceptions import (
    BranchDoesNotExistError, ChangesetDoesNotExistError, EmptyRepositoryError,
    RepositoryError, VCSError, TagAlreadyExistError, TagDoesNotExistError
)
from kallithea.lib.vcs.utils import (
    author_email, author_name, date_fromtimestamp, makedate, safe_unicode, safe_str,
)
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.lib.vcs.utils.ordered_dict import OrderedDict
from kallithea.lib.vcs.utils.paths import abspath
from kallithea.lib.vcs.utils.hgcompat import (
    ui, nullid, match, patch, diffopts, clone, get_contact, pull,
    localrepository, RepoLookupError, Abort, RepoError, hex, scmutil, hg_url,
    httpbasicauthhandler, httpdigestauthhandler, peer, httppeer, sshpeer
)

from .changeset import MercurialChangeset
from .inmemory import MercurialInMemoryChangeset
from .workdir import MercurialWorkdir

log = logging.getLogger(__name__)


class MercurialRepository(BaseRepository):
    """
    Mercurial repository backend
    """
    DEFAULT_BRANCH_NAME = 'default'
    scm = 'hg'

    def __init__(self, repo_path, create=False, baseui=None, src_url=None,
                 update_after_clone=False):
        """
        Raises RepositoryError if repository could not be find at the given
        ``repo_path``.

        :param repo_path: local path of the repository
        :param create=False: if set to True, would try to create repository if
           it does not exist rather than raising exception
        :param baseui=None: user data
        :param src_url=None: would try to clone repository from given location
        :param update_after_clone=False: sets update of working copy after
          making a clone
        """

        if not isinstance(repo_path, str):
            raise VCSError('Mercurial backend requires repository path to '
                           'be instance of <str> got %s instead' %
                           type(repo_path))

        self.path = abspath(repo_path)
        self.baseui = baseui or ui.ui()
        # We've set path and ui, now we can set _repo itself
        self._repo = self._get_repo(create, src_url, update_after_clone)

    @property
    def _empty(self):
        """
        Checks if repository is empty ie. without any changesets
        """
        # TODO: Following raises errors when using InMemoryChangeset...
        # return len(self._repo.changelog) == 0
        return len(self.revisions) == 0

    @LazyProperty
    def revisions(self):
        """
        Returns list of revisions' ids, in ascending order.  Being lazy
        attribute allows external tools to inject shas from cache.
        """
        return self._get_all_revisions()

    @LazyProperty
    def name(self):
        return os.path.basename(self.path)

    @LazyProperty
    def branches(self):
        return self._get_branches()

    @LazyProperty
    def closed_branches(self):
        return self._get_branches(normal=False, closed=True)

    @LazyProperty
    def allbranches(self):
        """
        List all branches, including closed branches.
        """
        return self._get_branches(closed=True)

    def _get_branches(self, normal=True, closed=False):
        """
        Gets branches for this repository
        Returns only not closed branches by default

        :param closed: return also closed branches for mercurial
        :param normal: return also normal branches
        """

        if self._empty:
            return {}

        bt = OrderedDict()
        for bn, _heads, tip, isclosed in sorted(self._repo.branchmap().iterbranches()):
            if isclosed:
                if closed:
                    bt[safe_unicode(bn)] = hex(tip)
            else:
                if normal:
                    bt[safe_unicode(bn)] = hex(tip)

        return bt

    @LazyProperty
    def tags(self):
        """
        Gets tags for this repository
        """
        return self._get_tags()

    def _get_tags(self):
        if self._empty:
            return {}

        sortkey = lambda ctx: ctx[0]  # sort by name
        _tags = [(safe_unicode(n), hex(h),) for n, h in
                 self._repo.tags().items()]

        return OrderedDict(sorted(_tags, key=sortkey, reverse=True))

    def tag(self, name, user, revision=None, message=None, date=None,
            **kwargs):
        """
        Creates and returns a tag for the given ``revision``.

        :param name: name for new tag
        :param user: full username, i.e.: "Joe Doe <joe.doe@example.com>"
        :param revision: changeset id for which new tag would be created
        :param message: message of the tag's commit
        :param date: date of tag's commit

        :raises TagAlreadyExistError: if tag with same name already exists
        """
        if name in self.tags:
            raise TagAlreadyExistError("Tag %s already exists" % name)
        changeset = self.get_changeset(revision)
        local = kwargs.setdefault('local', False)

        if message is None:
            message = "Added tag %s for changeset %s" % (name,
                changeset.short_id)

        if date is None:
            date = datetime.datetime.now().ctime()

        try:
            self._repo.tag(name, changeset._ctx.node(), message, local, user,
                date)
        except Abort, e:
            raise RepositoryError(e.message)

        # Reinitialize tags
        self.tags = self._get_tags()
        tag_id = self.tags[name]

        return self.get_changeset(revision=tag_id)

    def remove_tag(self, name, user, message=None, date=None):
        """
        Removes tag with the given ``name``.

        :param name: name of the tag to be removed
        :param user: full username, i.e.: "Joe Doe <joe.doe@example.com>"
        :param message: message of the tag's removal commit
        :param date: date of tag's removal commit

        :raises TagDoesNotExistError: if tag with given name does not exists
        """
        if name not in self.tags:
            raise TagDoesNotExistError("Tag %s does not exist" % name)
        if message is None:
            message = "Removed tag %s" % name
        if date is None:
            date = datetime.datetime.now().ctime()
        local = False

        try:
            self._repo.tag(name, nullid, message, local, user, date)
            self.tags = self._get_tags()
        except Abort, e:
            raise RepositoryError(e.message)

    @LazyProperty
    def bookmarks(self):
        """
        Gets bookmarks for this repository
        """
        return self._get_bookmarks()

    def _get_bookmarks(self):
        if self._empty:
            return {}

        sortkey = lambda ctx: ctx[0]  # sort by name
        _bookmarks = [(safe_unicode(n), hex(h),) for n, h in
                 self._repo._bookmarks.items()]
        return OrderedDict(sorted(_bookmarks, key=sortkey, reverse=True))

    def _get_all_revisions(self):

        return map(lambda x: hex(x[7]), self._repo.changelog.index)[:-1]

    def get_diff(self, rev1, rev2, path='', ignore_whitespace=False,
                  context=3):
        """
        Returns (git like) *diff*, as plain text. Shows changes introduced by
        ``rev2`` since ``rev1``.

        :param rev1: Entry point from which diff is shown. Can be
          ``self.EMPTY_CHANGESET`` - in this case, patch showing all
          the changes since empty state of the repository until ``rev2``
        :param rev2: Until which revision changes should be shown.
        :param ignore_whitespace: If set to ``True``, would not show whitespace
          changes. Defaults to ``False``.
        :param context: How many lines before/after changed lines should be
          shown. Defaults to ``3``.
        """
        if hasattr(rev1, 'raw_id'):
            rev1 = getattr(rev1, 'raw_id')

        if hasattr(rev2, 'raw_id'):
            rev2 = getattr(rev2, 'raw_id')

        # Check if given revisions are present at repository (may raise
        # ChangesetDoesNotExistError)
        if rev1 != self.EMPTY_CHANGESET:
            self.get_changeset(rev1)
        self.get_changeset(rev2)
        if path:
            file_filter = match(self.path, '', [path])
        else:
            file_filter = None

        return ''.join(patch.diff(self._repo, rev1, rev2, match=file_filter,
                          opts=diffopts(git=True,
                                        ignorews=ignore_whitespace,
                                        context=context)))

    @classmethod
    def _check_url(cls, url, repoui=None):
        """
        Function will check given url and try to verify if it's a valid
        link. Sometimes it may happened that mercurial will issue basic
        auth request that can cause whole API to hang when used from python
        or other external calls.

        On failures it'll raise urllib2.HTTPError, exception is also thrown
        when the return code is non 200
        """
        # check first if it's not an local url
        if os.path.isdir(url) or url.startswith('file:'):
            return True

        if url.startswith('ssh:'):
            # in case of invalid uri or authentication issues, sshpeer will
            # throw an exception.
            sshpeer(repoui or ui.ui(), url).lookup('tip')
            return True

        url_prefix = None
        if '+' in url[:url.find('://')]:
            url_prefix, url = url.split('+', 1)

        handlers = []
        url_obj = hg_url(url)
        test_uri, authinfo = url_obj.authinfo()
        url_obj.passwd = '*****'
        cleaned_uri = str(url_obj)

        if authinfo:
            #create a password manager
            passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passmgr.add_password(*authinfo)

            handlers.extend((httpbasicauthhandler(passmgr),
                             httpdigestauthhandler(passmgr)))

        o = urllib2.build_opener(*handlers)
        o.addheaders = [('Content-Type', 'application/mercurial-0.1'),
                        ('Accept', 'application/mercurial-0.1')]

        q = {"cmd": 'between'}
        q.update({'pairs': "%s-%s" % ('0' * 40, '0' * 40)})
        qs = '?%s' % urllib.urlencode(q)
        cu = "%s%s" % (test_uri, qs)
        req = urllib2.Request(cu, None, {})

        try:
            resp = o.open(req)
            if resp.code != 200:
                raise Exception('Return Code is not 200')
        except Exception, e:
            # means it cannot be cloned
            raise urllib2.URLError("[%s] org_exc: %s" % (cleaned_uri, e))

        if not url_prefix: # skip svn+http://... (and git+... too)
            # now check if it's a proper hg repo
            try:
                httppeer(repoui or ui.ui(), url).lookup('tip')
            except Exception, e:
                raise urllib2.URLError(
                    "url [%s] does not look like an hg repo org_exc: %s"
                    % (cleaned_uri, e))

        return True

    def _get_repo(self, create, src_url=None, update_after_clone=False):
        """
        Function will check for mercurial repository in given path and return
        a localrepo object. If there is no repository in that path it will
        raise an exception unless ``create`` parameter is set to True - in
        that case repository would be created and returned.
        If ``src_url`` is given, would try to clone repository from the
        location at given clone_point. Additionally it'll make update to
        working copy accordingly to ``update_after_clone`` flag
        """

        try:
            if src_url:
                url = str(self._get_url(src_url))
                opts = {}
                if not update_after_clone:
                    opts.update({'noupdate': True})
                MercurialRepository._check_url(url, self.baseui)
                clone(self.baseui, url, self.path, **opts)

                # Don't try to create if we've already cloned repo
                create = False
            return localrepository(self.baseui, self.path, create=create)
        except (Abort, RepoError), err:
            if create:
                msg = "Cannot create repository at %s. Original error was %s"\
                    % (self.path, err)
            else:
                msg = "Not valid repository at %s. Original error was %s"\
                    % (self.path, err)
            raise RepositoryError(msg)

    @LazyProperty
    def in_memory_changeset(self):
        return MercurialInMemoryChangeset(self)

    @LazyProperty
    def description(self):
        undefined_description = u'unknown'
        _desc = self._repo.ui.config('web', 'description', None, untrusted=True)
        return safe_unicode(_desc or undefined_description)

    @LazyProperty
    def contact(self):
        undefined_contact = u'Unknown'
        return safe_unicode(get_contact(self._repo.ui.config)
                            or undefined_contact)

    @LazyProperty
    def last_change(self):
        """
        Returns last change made on this repository as datetime object
        """
        return date_fromtimestamp(self._get_mtime(), makedate()[1])

    def _get_mtime(self):
        try:
            return time.mktime(self.get_changeset().date.timetuple())
        except RepositoryError:
            #fallback to filesystem
            cl_path = os.path.join(self.path, '.hg', "00changelog.i")
            st_path = os.path.join(self.path, '.hg', "store")
            if os.path.exists(cl_path):
                return os.stat(cl_path).st_mtime
            else:
                return os.stat(st_path).st_mtime

    def _get_revision(self, revision):
        """
        Gets an ID revision given as str. This will always return a fill
        40 char revision number

        :param revision: str or int or None
        """
        if isinstance(revision, unicode):
            revision = safe_str(revision)

        if self._empty:
            raise EmptyRepositoryError("There are no changesets yet")

        if revision in [-1, 'tip', None]:
            revision = 'tip'

        try:
            revision = hex(self._repo.lookup(revision))
        except (LookupError, ):
            msg = ("Ambiguous identifier `%s` for %s" % (revision, self))
            raise ChangesetDoesNotExistError(msg)
        except (IndexError, ValueError, RepoLookupError, TypeError):
            msg = ("Revision %s does not exist for %s" % (revision, self))
            raise ChangesetDoesNotExistError(msg)

        return revision

    def get_ref_revision(self, ref_type, ref_name):
        """
        Returns revision number for the given reference.
        """
        ref_name = safe_str(ref_name)
        if ref_type == 'rev' and not ref_name.strip('0'):
            return self.EMPTY_CHANGESET
        # lookup up the exact node id
        _revset_predicates = {
                'branch': 'branch',
                'book': 'bookmark',
                'tag': 'tag',
                'rev': 'id',
            }
        # avoid expensive branch(x) iteration over whole repo
        rev_spec = "%%s & %s(%%s)" % _revset_predicates[ref_type]
        try:
            revs = self._repo.revs(rev_spec, ref_name, ref_name)
        except LookupError:
            msg = ("Ambiguous identifier %s:%s for %s" % (ref_type, ref_name, self.name))
            raise ChangesetDoesNotExistError(msg)
        except RepoLookupError:
            msg = ("Revision %s:%s does not exist for %s" % (ref_type, ref_name, self.name))
            raise ChangesetDoesNotExistError(msg)
        if revs:
            try:
                revision = revs.last()
            except AttributeError:
                # removed in hg 3.2
                revision = revs[-1]
        else:
            # TODO: just report 'not found'?
            revision = ref_name

        return self._get_revision(revision)

    def _get_archives(self, archive_name='tip'):
        allowed = self.baseui.configlist("web", "allow_archive",
                                         untrusted=True)
        for i in [('zip', '.zip'), ('gz', '.tar.gz'), ('bz2', '.tar.bz2')]:
            if i[0] in allowed or self._repo.ui.configbool("web",
                                                           "allow" + i[0],
                                                           untrusted=True):
                yield {"type": i[0], "extension": i[1], "node": archive_name}

    def _get_url(self, url):
        """
        Returns normalized url. If schema is not given, would fall
        to filesystem
        (``file:///``) schema.
        """
        url = str(url)
        if url != 'default' and not '://' in url:
            url = "file:" + urllib.pathname2url(url)
        return url

    def get_hook_location(self):
        """
        returns absolute path to location where hooks are stored
        """
        return os.path.join(self.path, '.hg', '.hgrc')

    def get_changeset(self, revision=None):
        """
        Returns ``MercurialChangeset`` object representing repository's
        changeset at the given ``revision``.
        """
        revision = self._get_revision(revision)
        changeset = MercurialChangeset(repository=self, revision=revision)
        return changeset

    def get_changesets(self, start=None, end=None, start_date=None,
                       end_date=None, branch_name=None, reverse=False):
        """
        Returns iterator of ``MercurialChangeset`` objects from start to end
        (both are inclusive)

        :param start: None, str, int or mercurial lookup format
        :param end:  None, str, int or mercurial lookup format
        :param start_date:
        :param end_date:
        :param branch_name:
        :param reversed: return changesets in reversed order
        """

        start_raw_id = self._get_revision(start)
        start_pos = self.revisions.index(start_raw_id) if start else None
        end_raw_id = self._get_revision(end)
        end_pos = self.revisions.index(end_raw_id) if end else None

        if None not in [start, end] and start_pos > end_pos:
            raise RepositoryError("Start revision '%s' cannot be "
                                  "after end revision '%s'" % (start, end))

        if branch_name and branch_name not in self.allbranches.keys():
            msg = ("Branch %s not found in %s" % (branch_name, self))
            raise BranchDoesNotExistError(msg)
        if end_pos is not None:
            end_pos += 1
        #filter branches
        filter_ = []
        if branch_name:
            filter_.append('branch("%s")' % (branch_name))

        if start_date and not end_date:
            filter_.append('date(">%s")' % start_date)
        if end_date and not start_date:
            filter_.append('date("<%s")' % end_date)
        if start_date and end_date:
            filter_.append('date(">%s") and date("<%s")' % (start_date, end_date))
        if filter_:
            revisions = scmutil.revrange(self._repo, filter_)
        else:
            revisions = self.revisions

        # this is very much a hack to turn this into a list; a better solution
        # would be to get rid of this function entirely and use revsets
        revs = list(revisions)[start_pos:end_pos]
        if reverse:
            revs = reversed(revs)

        return CollectionGenerator(self, revs)

    def pull(self, url):
        """
        Tries to pull changes from external location.
        """
        url = self._get_url(url)
        other = peer(self._repo, {}, url)
        try:
            # hg 3.2 moved push / pull to exchange module
            from mercurial import exchange
            exchange.pull(self._repo, other, heads=None, force=None)
        except ImportError:
            self._repo.pull(other, heads=None, force=None)
        except Abort, err:
            # Propagate error but with vcs's type
            raise RepositoryError(str(err))

    @LazyProperty
    def workdir(self):
        """
        Returns ``Workdir`` instance for this repository.
        """
        return MercurialWorkdir(self)

    def get_config_value(self, section, name=None, config_file=None):
        """
        Returns configuration value for a given [``section``] and ``name``.

        :param section: Section we want to retrieve value from
        :param name: Name of configuration we want to retrieve
        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        if config_file is None:
            config_file = []
        elif isinstance(config_file, basestring):
            config_file = [config_file]

        config = self._repo.ui
        for path in config_file:
            config.readconfig(path)
        return config.config(section, name)

    def get_user_name(self, config_file=None):
        """
        Returns user's name from global configuration file.

        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        username = self.get_config_value('ui', 'username')
        if username:
            return author_name(username)
        return None

    def get_user_email(self, config_file=None):
        """
        Returns user's email from global configuration file.

        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        username = self.get_config_value('ui', 'username')
        if username:
            return author_email(username)
        return None
