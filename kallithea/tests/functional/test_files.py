# -*- coding: utf-8 -*-
import mimetypes
import posixpath

from kallithea.model.db import Repository
from kallithea.model.meta import Session
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()

ARCHIVE_SPECS = {
    '.tar.bz2': ('application/x-bzip2', 'tbz2', ''),
    '.tar.gz': ('application/x-gzip', 'tgz', ''),
    '.zip': ('application/zip', 'zip', ''),
}

HG_NODE_HISTORY = fixture.load_resource('hg_node_history_response.json')
GIT_NODE_HISTORY = fixture.load_resource('git_node_history_response.json')


def _set_downloads(repo_name, set_to):
    repo = Repository.get_by_repo_name(repo_name)
    repo.enable_downloads = set_to
    Session().commit()


class TestFilesController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='/'))
        # Test response...
        response.mustcontain('<a class="browser-dir ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/docs"><i class="icon-folder-open"></i><span>docs</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-dir ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/vcs"><i class="icon-folder-open"></i><span>vcs</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/.gitignore"><i class="icon-doc"></i><span>.gitignore</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/.hgignore"><i class="icon-doc"></i><span>.hgignore</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/.hgtags"><i class="icon-doc"></i><span>.hgtags</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/.travis.yml"><i class="icon-doc"></i><span>.travis.yml</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/MANIFEST.in"><i class="icon-doc"></i><span>MANIFEST.in</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/README.rst"><i class="icon-doc"></i><span>README.rst</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/run_test_and_report.sh"><i class="icon-doc"></i><span>run_test_and_report.sh</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/setup.cfg"><i class="icon-doc"></i><span>setup.cfg</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/setup.py"><i class="icon-doc"></i><span>setup.py</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/test_and_report.sh"><i class="icon-doc"></i><span>test_and_report.sh</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/96507bd11ecc815ebc6270fdf6db110928c09c1e/tox.ini"><i class="icon-doc"></i><span>tox.ini</span></a>' % HG_REPO)

    def test_index_revision(self):
        self.log_user()

        response = self.app.get(
            url(controller='files', action='index',
                repo_name=HG_REPO,
                revision='7ba66bec8d6dbba14a2155be32408c435c5f4492',
                f_path='/')
        )

        # Test response...

        response.mustcontain('<a class="browser-dir ypjax-link" href="/%s/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/docs"><i class="icon-folder-open"></i><span>docs</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-dir ypjax-link" href="/%s/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/tests"><i class="icon-folder-open"></i><span>tests</span></a>' % HG_REPO)
        response.mustcontain('<a class="browser-file ypjax-link" href="/%s/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/README.rst"><i class="icon-doc"></i><span>README.rst</span></a>' % HG_REPO)
        response.mustcontain('1.1 KiB')

    def test_index_different_branch(self):
        self.log_user()

        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='97e8b885c04894463c51898e14387d80c30ed1ee',
                                    f_path='/'))

        response.mustcontain("""<option selected="selected" value="97e8b885c04894463c51898e14387d80c30ed1ee">git at 97e8b885c048</option>""")

    def test_index_paging(self):
        self.log_user()

        for r in [(73, 'a066b25d5df7016b45a41b7e2a78c33b57adc235'),
                  (92, 'cc66b61b8455b264a7a8a2d8ddc80fcfc58c221e'),
                  (109, '75feb4c33e81186c87eac740cee2447330288412'),
                  (1, '3d8f361e72ab303da48d799ff1ac40d5ac37c67e'),
                  (0, 'b986218ba1c9b0d6a259fac9b050b1724ed8e545')]:

            response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision=r[1],
                                    f_path='/'))

            response.mustcontain("""@ r%s:%s""" % (r[0], r[1][:12]))

    def test_file_source(self):
        # Force the global cache to be populated now when we know the right .ini has been loaded.
        # (Without this, the test would fail.)
        import kallithea.lib.helpers
        kallithea.lib.helpers._urlify_issues_f = None
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='8911406ad776fdd3d0b9932a2e89677e57405a48',
                                    f_path='vcs/nodes.py'))

        response.mustcontain("""<div class="formatted-fixed">Partially implemented <a class="issue-tracker-link" href="https://issues.example.com/vcs_test_hg/issue/16">#16</a>. filecontent/commit message/author/node name are safe_unicode now.<br/>"""
"""In addition some other __str__ are unicode as well<br/>"""
"""Added test for unicode<br/>"""
"""Improved test to clone into uniq repository.<br/>"""
"""removed extra unicode conversion in diff.</div>
""")

        response.mustcontain("""<option selected="selected" value="8911406ad776fdd3d0b9932a2e89677e57405a48">default at 8911406ad776</option>""")

    def test_file_source_history(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='history',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='vcs/nodes.py'),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'},)
        assert response.body == HG_NODE_HISTORY

    def test_file_source_history_git(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='history',
                                    repo_name=GIT_REPO,
                                    revision='master',
                                    f_path='vcs/nodes.py'),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'},)
        assert response.body == GIT_NODE_HISTORY

    def test_file_annotation(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='vcs/nodes.py',
                                    annotate=True))

        response.mustcontain("""r356:25213a5fbb04""")

    def test_file_annotation_git(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=GIT_REPO,
                                    revision='master',
                                    f_path='vcs/nodes.py',
                                    annotate=True))
        response.mustcontain("""r345:c994f0de03b2""")

    def test_file_annotation_history(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='history',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='vcs/nodes.py',
                                    annotate=True),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'})

        assert response.body == HG_NODE_HISTORY

    def test_file_annotation_history_git(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='history',
                                    repo_name=GIT_REPO,
                                    revision='master',
                                    f_path='vcs/nodes.py',
                                    annotate=True),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'})

        assert response.body == GIT_NODE_HISTORY

    def test_file_authors(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='authors',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='vcs/nodes.py',
                                    annotate=True))
        response.mustcontain('Marcin Kuzminski')
        response.mustcontain('Lukasz Balcerzak')

    def test_file_authors_git(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='authors',
                                    repo_name=GIT_REPO,
                                    revision='master',
                                    f_path='vcs/nodes.py',
                                    annotate=True))
        response.mustcontain('Marcin Kuzminski')
        response.mustcontain('Lukasz Balcerzak')

    def test_archival(self):
        self.log_user()
        _set_downloads(HG_REPO, set_to=True)
        for arch_ext, info in ARCHIVE_SPECS.items():
            short = '27cd5cce30c9%s' % arch_ext
            fname = '27cd5cce30c96924232dffcd24178a07ffeb5dfc%s' % arch_ext
            filename = '%s-%s' % (HG_REPO, short)
            response = self.app.get(url(controller='files',
                                        action='archivefile',
                                        repo_name=HG_REPO,
                                        fname=fname))

            assert response.status == '200 OK'
            heads = [
                ('Pragma', 'no-cache'),
                ('Cache-Control', 'no-cache'),
                ('Content-Disposition', 'attachment; filename=%s' % filename),
                ('Content-Type', info[0]),
            ]
            assert response.response._headers.items() == heads

    def test_archival_wrong_ext(self):
        self.log_user()
        _set_downloads(HG_REPO, set_to=True)
        for arch_ext in ['tar', 'rar', 'x', '..ax', '.zipz']:
            fname = '27cd5cce30c96924232dffcd24178a07ffeb5dfc%s' % arch_ext

            response = self.app.get(url(controller='files',
                                        action='archivefile',
                                        repo_name=HG_REPO,
                                        fname=fname))
            response.mustcontain('Unknown archive type')

    def test_archival_wrong_revision(self):
        self.log_user()
        _set_downloads(HG_REPO, set_to=True)
        for rev in ['00x000000', 'tar', 'wrong', '@##$@$42413232', '232dffcd']:
            fname = '%s.zip' % rev

            response = self.app.get(url(controller='files',
                                        action='archivefile',
                                        repo_name=HG_REPO,
                                        fname=fname))
            response.mustcontain('Unknown revision')

    #==========================================================================
    # RAW FILE
    #==========================================================================
    def test_raw_file_ok(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='rawfile',
                                    repo_name=HG_REPO,
                                    revision='27cd5cce30c96924232dffcd24178a07ffeb5dfc',
                                    f_path='vcs/nodes.py'))

        assert response.content_disposition == "attachment; filename=nodes.py"
        assert response.content_type == mimetypes.guess_type("nodes.py")[0]

    def test_raw_file_wrong_cs(self):
        self.log_user()
        rev = u'ERRORce30c96924232dffcd24178a07ffeb5dfc'
        f_path = 'vcs/nodes.py'

        response = self.app.get(url(controller='files', action='rawfile',
                                    repo_name=HG_REPO,
                                    revision=rev,
                                    f_path=f_path), status=404)

        msg = """Such revision does not exist for this repository"""
        response.mustcontain(msg)

    def test_raw_file_wrong_f_path(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        f_path = 'vcs/ERRORnodes.py'
        response = self.app.get(url(controller='files', action='rawfile',
                                    repo_name=HG_REPO,
                                    revision=rev,
                                    f_path=f_path), status=404)

        msg = "There is no file nor directory at the given path: &#39;%s&#39; at revision %s" % (f_path, rev[:12])
        response.mustcontain(msg)

    #==========================================================================
    # RAW RESPONSE - PLAIN
    #==========================================================================
    def test_raw_ok(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='raw',
                                    repo_name=HG_REPO,
                                    revision='27cd5cce30c96924232dffcd24178a07ffeb5dfc',
                                    f_path='vcs/nodes.py'))

        assert response.content_type == "text/plain"

    def test_raw_wrong_cs(self):
        self.log_user()
        rev = u'ERRORcce30c96924232dffcd24178a07ffeb5dfc'
        f_path = 'vcs/nodes.py'

        response = self.app.get(url(controller='files', action='raw',
                                    repo_name=HG_REPO,
                                    revision=rev,
                                    f_path=f_path), status=404)

        msg = """Such revision does not exist for this repository"""
        response.mustcontain(msg)

    def test_raw_wrong_f_path(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        f_path = 'vcs/ERRORnodes.py'
        response = self.app.get(url(controller='files', action='raw',
                                    repo_name=HG_REPO,
                                    revision=rev,
                                    f_path=f_path), status=404)
        msg = "There is no file nor directory at the given path: &#39;%s&#39; at revision %s" % (f_path, rev[:12])
        response.mustcontain(msg)

    def test_ajaxed_files_list(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        response = self.app.get(
            url('files_nodelist_home', repo_name=HG_REPO, f_path='/',
                revision=rev),
            extra_environ={'HTTP_X_PARTIAL_XHR': '1'},
        )
        response.mustcontain("vcs/web/simplevcs/views/repository.py")

    # Hg - ADD FILE
    def test_add_file_view_hg(self):
        self.log_user()
        response = self.app.get(url('files_add_home',
                                      repo_name=HG_REPO,
                                      revision='tip', f_path='/'))

    def test_add_file_into_hg_missing_content(self):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=HG_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': '',
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)

        self.checkSessionFlash(response, 'No content')

    def test_add_file_into_hg_missing_filename(self):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=HG_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)

        self.checkSessionFlash(response, 'No filename')

    @parametrize('location,filename', [
        ('/abs', 'foo'),
        ('../rel', 'foo'),
        ('file/../foo', 'foo'),
    ])
    def test_add_file_into_hg_bad_filenames(self, location, filename):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=HG_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)

        self.checkSessionFlash(response, 'Location must be relative path and must not contain .. in path')

    @parametrize('cnt,location,filename', [
        (1, '', 'foo.txt'),
        (2, 'dir', 'foo.rst'),
        (3, 'rel/dir', 'foo.bar'),
    ])
    def test_add_file_into_hg(self, cnt, location, filename):
        self.log_user()
        repo = fixture.create_repo(u'commit-test-%s' % cnt, repo_type='hg')
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    # Git - add file
    def test_add_file_view_git(self):
        self.log_user()
        response = self.app.get(url('files_add_home',
                                      repo_name=GIT_REPO,
                                      revision='tip', f_path='/'))

    def test_add_file_into_git_missing_content(self):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=GIT_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                     'content': '',
                                     '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        self.checkSessionFlash(response, 'No content')

    def test_add_file_into_git_missing_filename(self):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=GIT_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)

        self.checkSessionFlash(response, 'No filename')

    @parametrize('location,filename', [
        ('/abs', 'foo'),
        ('../rel', 'foo'),
        ('file/../foo', 'foo'),
    ])
    def test_add_file_into_git_bad_filenames(self, location, filename):
        self.log_user()
        response = self.app.post(url('files_add_home',
                                      repo_name=GIT_REPO,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)

        self.checkSessionFlash(response, 'Location must be relative path and must not contain .. in path')

    @parametrize('cnt,location,filename', [
        (1, '', 'foo.txt'),
        (2, 'dir', 'foo.rst'),
        (3, 'rel/dir', 'foo.bar'),
    ])
    def test_add_file_into_git(self, cnt, location, filename):
        self.log_user()
        repo = fixture.create_repo(u'commit-test-%s' % cnt, repo_type='git')
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "foo",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    # Hg - EDIT
    def test_edit_file_view_hg(self):
        self.log_user()
        response = self.app.get(url('files_edit_home',
                                      repo_name=HG_REPO,
                                      revision='tip', f_path='vcs/nodes.py'))

    def test_edit_file_view_not_on_branch_hg(self):
        self.log_user()
        repo = fixture.create_repo(u'test-edit-repo', repo_type='hg')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.get(url('files_edit_home',
                                          repo_name=repo.repo_name,
                                          revision='tip', f_path=posixpath.join(location, filename)),
                                    status=302)
            self.checkSessionFlash(response,
                'You can only edit files with revision being a valid branch')
        finally:
            fixture.destroy_repo(repo.repo_name)

    def test_edit_file_view_commit_changes_hg(self):
        self.log_user()
        repo = fixture.create_repo(u'test-edit-repo', repo_type='hg')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip',
                                      f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.post(url('files_edit_home',
                                          repo_name=repo.repo_name,
                                          revision=repo.scm_instance.DEFAULT_BRANCH_NAME,
                                          f_path=posixpath.join(location, filename)),
                                     params={
                                        'content': "def py():\n print 'hello world'\n",
                                        'message': 'i committed',
                                        '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                     },
                                    status=302)
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    # Git - edit
    def test_edit_file_view_git(self):
        self.log_user()
        response = self.app.get(url('files_edit_home',
                                      repo_name=GIT_REPO,
                                      revision='tip', f_path='vcs/nodes.py'))

    def test_edit_file_view_not_on_branch_git(self):
        self.log_user()
        repo = fixture.create_repo(u'test-edit-repo', repo_type='git')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.get(url('files_edit_home',
                                          repo_name=repo.repo_name,
                                          revision='tip', f_path=posixpath.join(location, filename)),
                                    status=302)
            self.checkSessionFlash(response,
                'You can only edit files with revision being a valid branch')
        finally:
            fixture.destroy_repo(repo.repo_name)

    def test_edit_file_view_commit_changes_git(self):
        self.log_user()
        repo = fixture.create_repo(u'test-edit-repo', repo_type='git')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip',
                                      f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.post(url('files_edit_home',
                                          repo_name=repo.repo_name,
                                          revision=repo.scm_instance.DEFAULT_BRANCH_NAME,
                                          f_path=posixpath.join(location, filename)),
                                     params={
                                        'content': "def py():\n print 'hello world'\n",
                                        'message': 'i committed',
                                        '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                     },
                                    status=302)
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    # Hg - delete
    def test_delete_file_view_hg(self):
        self.log_user()
        response = self.app.get(url('files_delete_home',
                                     repo_name=HG_REPO,
                                     revision='tip', f_path='vcs/nodes.py'))

    def test_delete_file_view_not_on_branch_hg(self):
        self.log_user()
        repo = fixture.create_repo(u'test-delete-repo', repo_type='hg')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.get(url('files_delete_home',
                                          repo_name=repo.repo_name,
                                          revision='tip', f_path=posixpath.join(location, filename)),
                                    status=302)
            self.checkSessionFlash(response,
                'You can only delete files with revision being a valid branch')
        finally:
            fixture.destroy_repo(repo.repo_name)

    def test_delete_file_view_commit_changes_hg(self):
        self.log_user()
        repo = fixture.create_repo(u'test-delete-repo', repo_type='hg')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip',
                                      f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.post(url('files_delete_home',
                                          repo_name=repo.repo_name,
                                          revision=repo.scm_instance.DEFAULT_BRANCH_NAME,
                                          f_path=posixpath.join(location, filename)),
                                     params={
                                        'message': 'i committed',
                                        '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                     },
                                    status=302)
            self.checkSessionFlash(response,
                                   'Successfully deleted file %s' % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    # Git - delete
    def test_delete_file_view_git(self):
        self.log_user()
        response = self.app.get(url('files_delete_home',
                                     repo_name=HG_REPO,
                                     revision='tip', f_path='vcs/nodes.py'))

    def test_delete_file_view_not_on_branch_git(self):
        self.log_user()
        repo = fixture.create_repo(u'test-delete-repo', repo_type='git')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip', f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.get(url('files_delete_home',
                                          repo_name=repo.repo_name,
                                          revision='tip', f_path=posixpath.join(location, filename)),
                                    status=302)
            self.checkSessionFlash(response,
                'You can only delete files with revision being a valid branch')
        finally:
            fixture.destroy_repo(repo.repo_name)

    def test_delete_file_view_commit_changes_git(self):
        self.log_user()
        repo = fixture.create_repo(u'test-delete-repo', repo_type='git')

        ## add file
        location = 'vcs'
        filename = 'nodes.py'
        response = self.app.post(url('files_add_home',
                                      repo_name=repo.repo_name,
                                      revision='tip',
                                      f_path='/'),
                                 params={
                                    'content': "def py():\n print 'hello'\n",
                                    'filename': filename,
                                    'location': location,
                                    '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response.follow()
        try:
            self.checkSessionFlash(response, 'Successfully committed to %s'
                                   % posixpath.join(location, filename))
            response = self.app.post(url('files_delete_home',
                                          repo_name=repo.repo_name,
                                          revision=repo.scm_instance.DEFAULT_BRANCH_NAME,
                                          f_path=posixpath.join(location, filename)),
                                     params={
                                        'message': 'i committed',
                                        '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                     },
                                    status=302)
            self.checkSessionFlash(response,
                                   'Successfully deleted file %s' % posixpath.join(location, filename))
        finally:
            fixture.destroy_repo(repo.repo_name)

    def test_png_diff_no_crash_hg(self):
        self.log_user()
        response = self.app.get(url('files_diff_home',
                                    repo_name=HG_REPO,
                                    f_path='docs/theme/ADC/static/documentation.png',
                                    diff1='tip', diff2='tip'))
        response.mustcontain("""<pre>Binary file</pre>""")

    def test_png_diff_no_crash_git(self):
        self.log_user()
        response = self.app.get(url('files_diff_home',
                                    repo_name=GIT_REPO,
                                    f_path='docs/theme/ADC/static/documentation.png',
                                    diff1='master', diff2='master'))
        response.mustcontain("""<pre>Binary file</pre>""")
