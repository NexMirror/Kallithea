import datetime
import os
import StringIO
import tarfile
import tempfile
import zipfile

import pytest

from kallithea.lib.vcs.exceptions import VCSError
from kallithea.lib.vcs.nodes import FileNode
from kallithea.tests.vcs.base import _BackendTestMixin
from kallithea.tests.vcs.conf import TESTS_TMP_PATH


class ArchivesTestCaseMixin(_BackendTestMixin):

    @classmethod
    def _get_commits(cls):
        start_date = datetime.datetime(2010, 1, 1, 20)
        for x in xrange(5):
            yield {
                'message': 'Commit %d' % x,
                'author': 'Joe Doe <joe.doe@example.com>',
                'date': start_date + datetime.timedelta(hours=12 * x),
                'added': [
                    FileNode('%d/file_%d.txt' % (x, x),
                        content='Foobar %d' % x),
                ],
            }

    def test_archive_zip(self):
        path = tempfile.mkstemp(dir=TESTS_TMP_PATH, prefix='test_archive_zip-')[1]
        with open(path, 'wb') as f:
            self.tip.fill_archive(stream=f, kind='zip', prefix='repo')
        out = zipfile.ZipFile(path)

        for x in xrange(5):
            node_path = '%d/file_%d.txt' % (x, x)
            decompressed = StringIO.StringIO()
            decompressed.write(out.read('repo/' + node_path))
            assert decompressed.getvalue() == self.tip.get_node(node_path).content

    def test_archive_tgz(self):
        path = tempfile.mkstemp(dir=TESTS_TMP_PATH, prefix='test_archive_tgz-')[1]
        with open(path, 'wb') as f:
            self.tip.fill_archive(stream=f, kind='tgz', prefix='repo')
        outdir = tempfile.mkdtemp(dir=TESTS_TMP_PATH, prefix='test_archive_tgz-', suffix='-outdir')

        outfile = tarfile.open(path, 'r|gz')
        outfile.extractall(outdir)

        for x in xrange(5):
            node_path = '%d/file_%d.txt' % (x, x)
            assert open(os.path.join(outdir, 'repo/' + node_path)).read() == self.tip.get_node(node_path).content

    def test_archive_tbz2(self):
        path = tempfile.mkstemp(dir=TESTS_TMP_PATH, prefix='test_archive_tbz2-')[1]
        with open(path, 'w+b') as f:
            self.tip.fill_archive(stream=f, kind='tbz2', prefix='repo')
        outdir = tempfile.mkdtemp(dir=TESTS_TMP_PATH, prefix='test_archive_tbz2-', suffix='-outdir')

        outfile = tarfile.open(path, 'r|bz2')
        outfile.extractall(outdir)

        for x in xrange(5):
            node_path = '%d/file_%d.txt' % (x, x)
            assert open(os.path.join(outdir, 'repo/' + node_path)).read() == self.tip.get_node(node_path).content

    def test_archive_default_stream(self):
        tmppath = tempfile.mkstemp(dir=TESTS_TMP_PATH, prefix='test_archive_default_stream-')[1]
        with open(tmppath, 'wb') as stream:
            self.tip.fill_archive(stream=stream)
        mystream = StringIO.StringIO()
        self.tip.fill_archive(stream=mystream)
        mystream.seek(0)
        with open(tmppath, 'rb') as f:
            file_content = f.read()
            stringio_content = mystream.read()
            # the gzip header contains a MTIME header
            # because is takes a little bit of time from one fill_archive call to the next
            # this part may differ so don't include that part in the comparison
            assert file_content[:4] == stringio_content[:4]
            assert file_content[8:] == stringio_content[8:]

    def test_archive_wrong_kind(self):
        with pytest.raises(VCSError):
            self.tip.fill_archive(kind='wrong kind')

    def test_archive_empty_prefix(self):
        with pytest.raises(VCSError):
            self.tip.fill_archive(prefix='')

    def test_archive_prefix_with_leading_slash(self):
        with pytest.raises(VCSError):
            self.tip.fill_archive(prefix='/any')


class TestGitArchive(ArchivesTestCaseMixin):
    backend_alias = 'git'


class TestHgArchive(ArchivesTestCaseMixin):
    backend_alias = 'hg'
