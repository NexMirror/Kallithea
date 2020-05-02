# -*- coding: utf-8 -*-
"""
    vcs.backends.git.repository
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Git repository implementation.

    :created_on: Apr 8, 2010
    :copyright: (c) 2010-2011 by Marcin Kuzminski, Lukasz Balcerzak.
"""

import errno
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict

import mercurial.url  # import httpbasicauthhandler, httpdigestauthhandler
import mercurial.util  # import url as hg_url
from dulwich.config import ConfigFile
from dulwich.objects import Tag
from dulwich.repo import NotGitRepository, Repo

from kallithea.lib.vcs import subprocessio
from kallithea.lib.vcs.backends.base import BaseRepository, CollectionGenerator
from kallithea.lib.vcs.conf import settings
from kallithea.lib.vcs.exceptions import (BranchDoesNotExistError, ChangesetDoesNotExistError, EmptyRepositoryError, RepositoryError, TagAlreadyExistError,
                                          TagDoesNotExistError)
from kallithea.lib.vcs.utils import ascii_str, date_fromtimestamp, makedate, safe_bytes, safe_str
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.lib.vcs.utils.paths import abspath, get_user_home

from .changeset import GitChangeset
from .inmemory import GitInMemoryChangeset
from .workdir import GitWorkdir


SHA_PATTERN = re.compile(r'^([0-9a-fA-F]{12}|[0-9a-fA-F]{40})$')

log = logging.getLogger(__name__)


class GitRepository(BaseRepository):
    """
    Git repository backend.
    """
    DEFAULT_BRANCH_NAME = 'master'
    scm = 'git'

    def __init__(self, repo_path, create=False, src_url=None,
                 update_after_clone=False, bare=False):

        self.path = abspath(repo_path)
        self.repo = self._get_repo(create, src_url, update_after_clone, bare)
        self.bare = self.repo.bare

    @property
    def _config_files(self):
        return [
            self.bare and abspath(self.path, 'config')
                      or abspath(self.path, '.git', 'config'),
             abspath(get_user_home(), '.gitconfig'),
         ]

    @property
    def _repo(self):
        return self.repo

    @property
    def head(self):
        try:
            return self._repo.head()
        except KeyError:
            return None

    @property
    def _empty(self):
        """
        Checks if repository is empty ie. without any changesets
        """

        try:
            self.revisions[0]
        except (KeyError, IndexError):
            return True
        return False

    @LazyProperty
    def revisions(self):
        """
        Returns list of revisions' ids, in ascending order.  Being lazy
        attribute allows external tools to inject shas from cache.
        """
        return self._get_all_revisions()

    @classmethod
    def _run_git_command(cls, cmd, cwd=None):
        """
        Runs given ``cmd`` as git command and returns output bytes in a tuple
        (stdout, stderr) ... or raise RepositoryError.

        :param cmd: git command to be executed
        :param cwd: passed directly to subprocess
        """
        # need to clean fix GIT_DIR !
        gitenv = dict(os.environ)
        gitenv.pop('GIT_DIR', None)
        gitenv['GIT_CONFIG_NOGLOBAL'] = '1'

        assert isinstance(cmd, list), cmd
        cmd = [settings.GIT_EXECUTABLE_PATH, '-c', 'core.quotepath=false'] + cmd
        try:
            p = subprocessio.SubprocessIOChunker(cmd, cwd=cwd, env=gitenv, shell=False)
        except (EnvironmentError, OSError) as err:
            # output from the failing process is in str(EnvironmentError)
            msg = ("Couldn't run git command %s.\n"
                   "Subprocess failed with '%s': %s\n" %
                   (cmd, type(err).__name__, err)
            ).strip()
            log.error(msg)
            raise RepositoryError(msg)

        try:
            stdout = b''.join(p.output)
            stderr = b''.join(p.error)
        finally:
            p.close()
        # TODO: introduce option to make commands fail if they have any stderr output?
        if stderr:
            log.debug('stderr from %s:\n%s', cmd, stderr)
        else:
            log.debug('stderr from %s: None', cmd)
        return stdout, stderr

    def run_git_command(self, cmd):
        """
        Runs given ``cmd`` as git command with cwd set to current repo.
        Returns stdout as unicode str ... or raise RepositoryError.
        """
        cwd = None
        if os.path.isdir(self.path):
            cwd = self.path
        stdout, _stderr = self._run_git_command(cmd, cwd=cwd)
        return safe_str(stdout)

    @classmethod
    def _check_url(cls, url):
        """
        Function will check given url and try to verify if it's a valid
        link. Sometimes it may happened that git will issue basic
        auth request that can cause whole API to hang when used from python
        or other external calls.

        On failures it'll raise urllib2.HTTPError, exception is also thrown
        when the return code is non 200
        """
        # check first if it's not an local url
        if os.path.isdir(url) or url.startswith('file:'):
            return True

        if url.startswith('git://'):
            return True

        if '+' in url[:url.find('://')]:
            url = url[url.find('+') + 1:]

        handlers = []
        url_obj = mercurial.util.url(safe_bytes(url))
        test_uri, authinfo = url_obj.authinfo()
        if not test_uri.endswith(b'info/refs'):
            test_uri = test_uri.rstrip(b'/') + b'/info/refs'

        url_obj.passwd = b'*****'
        cleaned_uri = str(url_obj)

        if authinfo:
            # create a password manager
            passmgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            passmgr.add_password(*authinfo)

            handlers.extend((mercurial.url.httpbasicauthhandler(passmgr),
                             mercurial.url.httpdigestauthhandler(passmgr)))

        o = urllib.request.build_opener(*handlers)
        o.addheaders = [('User-Agent', 'git/1.7.8.0')]  # fake some git

        req = urllib.request.Request(
            "%s?%s" % (
                safe_str(test_uri),
                urllib.parse.urlencode({"service": 'git-upload-pack'})
            ))

        try:
            resp = o.open(req)
            if resp.code != 200:
                raise Exception('Return Code is not 200')
        except Exception as e:
            # means it cannot be cloned
            raise urllib.error.URLError("[%s] org_exc: %s" % (cleaned_uri, e))

        # now detect if it's proper git repo
        gitdata = resp.read()
        if b'service=git-upload-pack' not in gitdata:
            raise urllib.error.URLError(
                "url [%s] does not look like an git" % cleaned_uri)

        return True

    def _get_repo(self, create, src_url=None, update_after_clone=False,
                  bare=False):
        if create and os.path.exists(self.path):
            raise RepositoryError("Location already exist")
        if src_url and not create:
            raise RepositoryError("Create should be set to True if src_url is "
                                  "given (clone operation creates repository)")
        try:
            if create and src_url:
                GitRepository._check_url(src_url)
                self.clone(src_url, update_after_clone, bare)
                return Repo(self.path)
            elif create:
                os.makedirs(self.path)
                if bare:
                    return Repo.init_bare(self.path)
                else:
                    return Repo.init(self.path)
            else:
                return Repo(self.path)
        except (NotGitRepository, OSError) as err:
            raise RepositoryError(err)

    def _get_all_revisions(self):
        # we must check if this repo is not empty, since later command
        # fails if it is. And it's cheaper to ask than throw the subprocess
        # errors
        try:
            self._repo.head()
        except KeyError:
            return []

        rev_filter = settings.GIT_REV_FILTER
        cmd = ['rev-list', rev_filter, '--reverse', '--date-order']
        try:
            so = self.run_git_command(cmd)
        except RepositoryError:
            # Can be raised for empty repositories
            return []
        return so.splitlines()

    def _get_all_revisions2(self):
        # alternate implementation using dulwich
        includes = [ascii_str(sha) for key, (sha, type_) in self._parsed_refs.items()
                    if type_ != b'T']
        return [c.commit.id for c in self._repo.get_walker(include=includes)]

    def _get_revision(self, revision):
        """
        Given any revision identifier, returns a 40 char string with revision hash.
        """
        if self._empty:
            raise EmptyRepositoryError("There are no changesets yet")

        if revision in (None, '', 'tip', 'HEAD', 'head', -1):
            revision = -1

        if isinstance(revision, int):
            try:
                return self.revisions[revision]
            except IndexError:
                msg = "Revision %r does not exist for %s" % (revision, self.name)
                raise ChangesetDoesNotExistError(msg)

        if isinstance(revision, str):
            if revision.isdigit() and (len(revision) < 12 or len(revision) == revision.count('0')):
                try:
                    return self.revisions[int(revision)]
                except IndexError:
                    msg = "Revision %r does not exist for %s" % (revision, self)
                    raise ChangesetDoesNotExistError(msg)

            # get by branch/tag name
            _ref_revision = self._parsed_refs.get(safe_bytes(revision))
            if _ref_revision:  # and _ref_revision[1] in [b'H', b'RH', b'T']:
                return ascii_str(_ref_revision[0])

            if revision in self.revisions:
                return revision

            # maybe it's a tag ? we don't have them in self.revisions
            if revision in self.tags.values():
                return revision

            if SHA_PATTERN.match(revision):
                msg = "Revision %r does not exist for %s" % (revision, self.name)
                raise ChangesetDoesNotExistError(msg)

        raise ChangesetDoesNotExistError("Given revision %r not recognized" % revision)

    def get_ref_revision(self, ref_type, ref_name):
        """
        Returns ``GitChangeset`` object representing repository's
        changeset at the given ``revision``.
        """
        return self._get_revision(ref_name)

    def _get_archives(self, archive_name='tip'):

        for i in [('zip', '.zip'), ('gz', '.tar.gz'), ('bz2', '.tar.bz2')]:
            yield {"type": i[0], "extension": i[1], "node": archive_name}

    def _get_url(self, url):
        """
        Returns normalized url. If schema is not given, would fall to
        filesystem (``file:///``) schema.
        """
        if url != 'default' and '://' not in url:
            url = ':///'.join(('file', url))
        return url

    @LazyProperty
    def name(self):
        return os.path.basename(self.path)

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
            idx_loc = '' if self.bare else '.git'
            # fallback to filesystem
            in_path = os.path.join(self.path, idx_loc, "index")
            he_path = os.path.join(self.path, idx_loc, "HEAD")
            if os.path.exists(in_path):
                return os.stat(in_path).st_mtime
            else:
                return os.stat(he_path).st_mtime

    @LazyProperty
    def description(self):
        return safe_str(self._repo.get_description() or b'unknown')

    @LazyProperty
    def contact(self):
        undefined_contact = 'Unknown'
        return undefined_contact

    @property
    def branches(self):
        if not self.revisions:
            return {}
        _branches = [(safe_str(key), ascii_str(sha))
                     for key, (sha, type_) in self._parsed_refs.items() if type_ == b'H']
        return OrderedDict(sorted(_branches, key=(lambda ctx: ctx[0]), reverse=False))

    @LazyProperty
    def closed_branches(self):
        return {}

    @LazyProperty
    def tags(self):
        return self._get_tags()

    def _get_tags(self):
        if not self.revisions:
            return {}
        _tags = [(safe_str(key), ascii_str(sha))
                 for key, (sha, type_) in self._parsed_refs.items() if type_ == b'T']
        return OrderedDict(sorted(_tags, key=(lambda ctx: ctx[0]), reverse=True))

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
        message = message or "Added tag %s for commit %s" % (name,
            changeset.raw_id)
        self._repo.refs[b"refs/tags/%s" % safe_bytes(name)] = changeset._commit.id

        self._parsed_refs = self._get_parsed_refs()
        self.tags = self._get_tags()
        return changeset

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
        # self._repo.refs is a DiskRefsContainer, and .path gives the full absolute path of '.git'
        tagpath = os.path.join(safe_str(self._repo.refs.path), 'refs', 'tags', name)
        try:
            os.remove(tagpath)
            self._parsed_refs = self._get_parsed_refs()
            self.tags = self._get_tags()
        except OSError as e:
            raise RepositoryError(e.strerror)

    @LazyProperty
    def bookmarks(self):
        """
        Gets bookmarks for this repository
        """
        return {}

    @LazyProperty
    def _parsed_refs(self):
        return self._get_parsed_refs()

    def _get_parsed_refs(self):
        """Return refs as a dict, like:
        { b'v0.2.0': [b'599ba911aa24d2981225f3966eb659dfae9e9f30', b'T'] }
        """
        _repo = self._repo
        refs = _repo.get_refs()
        keys = [(b'refs/heads/', b'H'),
                (b'refs/remotes/origin/', b'RH'),
                (b'refs/tags/', b'T')]
        _refs = {}
        for ref, sha in refs.items():
            for k, type_ in keys:
                if ref.startswith(k):
                    _key = ref[len(k):]
                    if type_ == b'T':
                        obj = _repo.get_object(sha)
                        if isinstance(obj, Tag):
                            sha = _repo.get_object(sha).object[1]
                    _refs[_key] = [sha, type_]
                    break
        return _refs

    def _heads(self, reverse=False):
        refs = self._repo.get_refs()
        heads = {}

        for key, val in refs.items():
            for ref_key in [b'refs/heads/', b'refs/remotes/origin/']:
                if key.startswith(ref_key):
                    n = key[len(ref_key):]
                    if n not in [b'HEAD']:
                        heads[n] = val

        return heads if reverse else dict((y, x) for x, y in heads.items())

    def get_changeset(self, revision=None):
        """
        Returns ``GitChangeset`` object representing commit from git repository
        at the given revision or head (most recent commit) if None given.
        """
        if isinstance(revision, GitChangeset):
            return revision
        return GitChangeset(repository=self, revision=self._get_revision(revision))

    def get_changesets(self, start=None, end=None, start_date=None,
           end_date=None, branch_name=None, reverse=False, max_revisions=None):
        """
        Returns iterator of ``GitChangeset`` objects from start to end (both
        are inclusive), in ascending date order (unless ``reverse`` is set).

        :param start: changeset ID, as str; first returned changeset
        :param end: changeset ID, as str; last returned changeset
        :param start_date: if specified, changesets with commit date less than
          ``start_date`` would be filtered out from returned set
        :param end_date: if specified, changesets with commit date greater than
          ``end_date`` would be filtered out from returned set
        :param branch_name: if specified, changesets not reachable from given
          branch would be filtered out from returned set
        :param reverse: if ``True``, returned generator would be reversed
          (meaning that returned changesets would have descending date order)

        :raise BranchDoesNotExistError: If given ``branch_name`` does not
            exist.
        :raise ChangesetDoesNotExistError: If changeset for given ``start`` or
          ``end`` could not be found.

        """
        if branch_name and branch_name not in self.branches:
            raise BranchDoesNotExistError("Branch '%s' not found"
                                          % branch_name)
        # actually we should check now if it's not an empty repo to not spaw
        # subprocess commands
        if self._empty:
            raise EmptyRepositoryError("There are no changesets yet")

        # %H at format means (full) commit hash, initial hashes are retrieved
        # in ascending date order
        cmd = ['log', '--date-order', '--reverse', '--pretty=format:%H']
        if max_revisions:
            cmd += ['--max-count=%s' % max_revisions]
        if start_date:
            cmd += ['--since', start_date.strftime('%m/%d/%y %H:%M:%S')]
        if end_date:
            cmd += ['--until', end_date.strftime('%m/%d/%y %H:%M:%S')]
        if branch_name:
            cmd.append(branch_name)
        else:
            cmd.append(settings.GIT_REV_FILTER)

        revs = self.run_git_command(cmd).splitlines()
        start_pos = 0
        end_pos = len(revs)
        if start:
            _start = self._get_revision(start)
            try:
                start_pos = revs.index(_start)
            except ValueError:
                pass

        if end is not None:
            _end = self._get_revision(end)
            try:
                end_pos = revs.index(_end)
            except ValueError:
                pass

        if None not in [start, end] and start_pos > end_pos:
            raise RepositoryError('start cannot be after end')

        if end_pos is not None:
            end_pos += 1

        revs = revs[start_pos:end_pos]
        if reverse:
            revs.reverse()

        return CollectionGenerator(self, revs)

    def get_diff(self, rev1, rev2, path=None, ignore_whitespace=False,
                 context=3):
        """
        Returns (git like) *diff*, as plain bytes text. Shows changes
        introduced by ``rev2`` since ``rev1``.

        :param rev1: Entry point from which diff is shown. Can be
          ``self.EMPTY_CHANGESET`` - in this case, patch showing all
          the changes since empty state of the repository until ``rev2``
        :param rev2: Until which revision changes should be shown.
        :param ignore_whitespace: If set to ``True``, would not show whitespace
          changes. Defaults to ``False``.
        :param context: How many lines before/after changed lines should be
          shown. Defaults to ``3``. Due to limitations in Git, if
          value passed-in is greater than ``2**31-1``
          (``2147483647``), it will be set to ``2147483647``
          instead. If negative value is passed-in, it will be set to
          ``0`` instead.
        """

        # Git internally uses a signed long int for storing context
        # size (number of lines to show before and after the
        # differences). This can result in integer overflow, so we
        # ensure the requested context is smaller by one than the
        # number that would cause the overflow. It is highly unlikely
        # that a single file will contain that many lines, so this
        # kind of change should not cause any realistic consequences.
        overflowed_long_int = 2**31

        if context >= overflowed_long_int:
            context = overflowed_long_int - 1

        # Negative context values make no sense, and will result in
        # errors. Ensure this does not happen.
        if context < 0:
            context = 0

        flags = ['-U%s' % context, '--full-index', '--binary', '-p', '-M', '--abbrev=40']
        if ignore_whitespace:
            flags.append('-w')

        if hasattr(rev1, 'raw_id'):
            rev1 = getattr(rev1, 'raw_id')

        if hasattr(rev2, 'raw_id'):
            rev2 = getattr(rev2, 'raw_id')

        if rev1 == self.EMPTY_CHANGESET:
            rev2 = self.get_changeset(rev2).raw_id
            cmd = ['show'] + flags + [rev2]
        else:
            rev1 = self.get_changeset(rev1).raw_id
            rev2 = self.get_changeset(rev2).raw_id
            cmd = ['diff'] + flags + [rev1, rev2]

        if path:
            cmd += ['--', path]

        stdout, stderr = self._run_git_command(cmd, cwd=self.path)
        # If we used 'show' command, strip first few lines (until actual diff
        # starts)
        if rev1 == self.EMPTY_CHANGESET:
            parts = stdout.split(b'\ndiff ', 1)
            if len(parts) > 1:
                stdout = b'diff ' + parts[1]
        return stdout

    @LazyProperty
    def in_memory_changeset(self):
        """
        Returns ``GitInMemoryChangeset`` object for this repository.
        """
        return GitInMemoryChangeset(self)

    def clone(self, url, update_after_clone=True, bare=False):
        """
        Tries to clone changes from external location.

        :param update_after_clone: If set to ``False``, git won't checkout
          working directory
        :param bare: If set to ``True``, repository would be cloned into
          *bare* git repository (no working directory at all).
        """
        url = self._get_url(url)
        cmd = ['clone', '-q']
        if bare:
            cmd.append('--bare')
        elif not update_after_clone:
            cmd.append('--no-checkout')
        cmd += ['--', url, self.path]
        # If error occurs run_git_command raises RepositoryError already
        self.run_git_command(cmd)

    def pull(self, url):
        """
        Tries to pull changes from external location.
        """
        url = self._get_url(url)
        cmd = ['pull', '--ff-only', url]
        # If error occurs run_git_command raises RepositoryError already
        self.run_git_command(cmd)

    def fetch(self, url):
        """
        Tries to pull changes from external location.
        """
        url = self._get_url(url)
        so = self.run_git_command(['ls-remote', '-h', url])
        cmd = ['fetch', url, '--']
        for line in (x for x in so.splitlines()):
            sha, ref = line.split('\t')
            cmd.append('+%s:%s' % (ref, ref))
        self.run_git_command(cmd)

    def _update_server_info(self):
        """
        runs gits update-server-info command in this repo instance
        """
        from dulwich.server import update_server_info
        try:
            update_server_info(self._repo)
        except OSError as e:
            if e.errno not in [errno.ENOENT, errno.EROFS]:
                raise
            # Workaround for dulwich crashing on for example its own dulwich/tests/data/repos/simple_merge.git/info/refs.lock
            log.error('Ignoring %s running update-server-info: %s', type(e).__name__, e)

    @LazyProperty
    def workdir(self):
        """
        Returns ``Workdir`` instance for this repository.
        """
        return GitWorkdir(self)

    def get_config_value(self, section, name, config_file=None):
        """
        Returns configuration value for a given [``section``] and ``name``.

        :param section: Section we want to retrieve value from
        :param name: Name of configuration we want to retrieve
        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        if config_file is None:
            config_file = []
        elif isinstance(config_file, str):
            config_file = [config_file]

        def gen_configs():
            for path in config_file + self._config_files:
                try:
                    yield ConfigFile.from_path(path)
                except (IOError, OSError, ValueError):
                    continue

        for config in gen_configs():
            try:
                value = config.get(section, name)
            except KeyError:
                continue
            return None if value is None else safe_str(value)
        return None

    def get_user_name(self, config_file=None):
        """
        Returns user's name from global configuration file.

        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        return self.get_config_value('user', 'name', config_file)

    def get_user_email(self, config_file=None):
        """
        Returns user's email from global configuration file.

        :param config_file: A path to file which should be used to retrieve
          configuration from (might also be a list of file paths)
        """
        return self.get_config_value('user', 'email', config_file)
