# -*- coding: utf-8 -*-
from kallithea.tests import *

class TestCompareController(TestController):

    def test_compare_tag_hg(self):
        self.log_user()
        tag1 = 'v0.1.2'
        tag2 = 'v0.1.3'
        response = self.app.get(url('compare_url',
                                    repo_name=HG_REPO,
                                    org_ref_type="tag",
                                    org_ref_name=tag1,
                                    other_ref_type="tag",
                                    other_ref_name=tag2,
                                    ), status=200)
        response.mustcontain('%s@%s' % (HG_REPO, tag1))
        response.mustcontain('%s@%s' % (HG_REPO, tag2))

        ## outgoing changesets between tags
        response.mustcontain('''<a href="/%s/changeset/c5ddebc06eaaba3010c2d66ea6ec9d074eb0f678">r112:c5ddebc06eaa</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/70d4cef8a37657ee4cf5aabb3bd9f68879769816">r115:70d4cef8a376</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/9749bfbfc0d2eba208d7947de266303b67c87cda">r116:9749bfbfc0d2</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/41fda979f02fda216374bf8edac4e83f69e7581c">r117:41fda979f02f</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/bb1a3ab98cc45cb934a77dcabf87a5a598b59e97">r118:bb1a3ab98cc4</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/36e0fc9d2808c5022a24f49d6658330383ed8666">r119:36e0fc9d2808</a>''' % HG_REPO)
        response.mustcontain('''<a href="/%s/changeset/17544fbfcd33ffb439e2b728b5d526b1ef30bfcf">r120:17544fbfcd33</a>''' % HG_REPO)

        response.mustcontain('11 files changed with 94 insertions and 64 deletions')

        ## files diff
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-A"></i>
                             <a href="#C--1c5cf9e91c12">docs/api/utils/index.rst</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-A"></i>
                             <a href="#C--e3305437df55">test_and_report.sh</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--c8e92ef85cd1">.hgignore</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--6e08b694d687">.hgtags</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--2c14b00f3393">docs/api/index.rst</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--430ccbc82bdf">vcs/__init__.py</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--9c390eb52cd6">vcs/backends/hg.py</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--ebb592c595c0">vcs/utils/__init__.py</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--7abc741b5052">vcs/utils/annotate.py</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--2ef0ef106c56">vcs/utils/diffs.py</a>''')
        response.mustcontain('''<div class="node">
                             <i class="icon-diff-M"></i>
                             <a href="#C--3150cb87d4b7">vcs/utils/lazy.py</a>''')

    def test_compare_tag_git(self):
        self.log_user()
        tag1 = 'v0.1.2'
        tag2 = 'v0.1.3'
        response = self.app.get(url('compare_url',
                                    repo_name=GIT_REPO,
                                    org_ref_type="tag",
                                    org_ref_name=tag1,
                                    other_ref_type="tag",
                                    other_ref_name=tag2,
                                    ), status=200)
        response.mustcontain('%s@%s' % (GIT_REPO, tag1))
        response.mustcontain('%s@%s' % (GIT_REPO, tag2))

        ## outgoing changesets between tags
        response.mustcontain('''<a href="/%s/changeset/794bbdd31545c199f74912709ea350dedcd189a2">r113:794bbdd31545</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/e36d8c5025329bdd4212bd53d4ed8a70ff44985f">r115:e36d8c502532</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/5c9ff4f6d7508db0e72b1d2991c357d0d8e07af2">r116:5c9ff4f6d750</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/b7187fa2b8c1d773ec35e9dee12f01f74808c879">r117:b7187fa2b8c1</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/5f3b74262014a8de2dc7dade1152de9fd0c8efef">r118:5f3b74262014</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/17438a11f72b93f56d0e08e7d1fa79a378578a82">r119:17438a11f72b</a>''' % GIT_REPO)
        response.mustcontain('''<a href="/%s/changeset/5a3a8fb005554692b16e21dee62bf02667d8dc3e">r120:5a3a8fb00555</a>''' % GIT_REPO)

        response.mustcontain('11 files changed with 94 insertions and 64 deletions')

        #files
        response.mustcontain('''<a href="#C--1c5cf9e91c12">docs/api/utils/index.rst</a>''')
        response.mustcontain('''<a href="#C--e3305437df55">test_and_report.sh</a>''')
        response.mustcontain('''<a href="#C--c8e92ef85cd1">.hgignore</a>''')
        response.mustcontain('''<a href="#C--6e08b694d687">.hgtags</a>''')
        response.mustcontain('''<a href="#C--2c14b00f3393">docs/api/index.rst</a>''')
        response.mustcontain('''<a href="#C--430ccbc82bdf">vcs/__init__.py</a>''')
        response.mustcontain('''<a href="#C--9c390eb52cd6">vcs/backends/hg.py</a>''')
        response.mustcontain('''<a href="#C--ebb592c595c0">vcs/utils/__init__.py</a>''')
        response.mustcontain('''<a href="#C--7abc741b5052">vcs/utils/annotate.py</a>''')
        response.mustcontain('''<a href="#C--2ef0ef106c56">vcs/utils/diffs.py</a>''')
        response.mustcontain('''<a href="#C--3150cb87d4b7">vcs/utils/lazy.py</a>''')

    def test_index_branch_hg(self):
        self.log_user()
        response = self.app.get(url('compare_url',
                                    repo_name=HG_REPO,
                                    org_ref_type="branch",
                                    org_ref_name='default',
                                    other_ref_type="branch",
                                    other_ref_name='default',
                                    ))

        response.mustcontain('%s@default' % (HG_REPO))
        response.mustcontain('%s@default' % (HG_REPO))
        # branch are equal
        response.mustcontain('<span class="empty_data">No files</span>')
        response.mustcontain('<span class="empty_data">No changesets</span>')

    def test_index_branch_git(self):
        self.log_user()
        response = self.app.get(url('compare_url',
                                    repo_name=GIT_REPO,
                                    org_ref_type="branch",
                                    org_ref_name='master',
                                    other_ref_type="branch",
                                    other_ref_name='master',
                                    ))

        response.mustcontain('%s@master' % (GIT_REPO))
        response.mustcontain('%s@master' % (GIT_REPO))
        # branch are equal
        response.mustcontain('<span class="empty_data">No files</span>')
        response.mustcontain('<span class="empty_data">No changesets</span>')

    def test_compare_revisions_hg(self):
        self.log_user()
        rev1 = 'b986218ba1c9'
        rev2 = '3d8f361e72ab'

        response = self.app.get(url('compare_url',
                                    repo_name=HG_REPO,
                                    org_ref_type="rev",
                                    org_ref_name=rev1,
                                    other_ref_type="rev",
                                    other_ref_name=rev2,
                                    ))
        response.mustcontain('%s@%s' % (HG_REPO, rev1))
        response.mustcontain('%s@%s' % (HG_REPO, rev2))

        ## outgoing changesets between those revisions
        response.mustcontain("""<a href="/%s/changeset/3d8f361e72ab303da48d799ff1ac40d5ac37c67e">r1:%s</a>""" % (HG_REPO, rev2))

        response.mustcontain('1 file changed with 7 insertions and 0 deletions')
        ## files
        response.mustcontain("""<a href="#C--c8e92ef85cd1">.hgignore</a>""")

    def test_compare_revisions_git(self):
        self.log_user()
        rev1 = 'c1214f7e79e02fc37156ff215cd71275450cffc3'
        rev2 = '38b5fe81f109cb111f549bfe9bb6b267e10bc557'

        response = self.app.get(url('compare_url',
                                    repo_name=GIT_REPO,
                                    org_ref_type="rev",
                                    org_ref_name=rev1,
                                    other_ref_type="rev",
                                    other_ref_name=rev2,
                                    ))
        response.mustcontain('%s@%s' % (GIT_REPO, rev1))
        response.mustcontain('%s@%s' % (GIT_REPO, rev2))

        ## outgoing changesets between those revisions
        response.mustcontain("""<a href="/%s/changeset/38b5fe81f109cb111f549bfe9bb6b267e10bc557">r1:%s</a>""" % (GIT_REPO, rev2[:12]))
        response.mustcontain('1 file changed with 7 insertions and 0 deletions')

        ## files
        response.mustcontain("""<a href="#C--c8e92ef85cd1">.hgignore</a>""")

    def test_compare_revisions_hg_as_form(self):
        self.log_user()
        rev1 = 'b986218ba1c9'
        rev2 = '3d8f361e72ab'

        response = self.app.get(url('compare_url',
                                    repo_name=HG_REPO,
                                    org_ref_type="rev",
                                    org_ref_name=rev1,
                                    other_ref_type="rev",
                                    other_ref_name=rev2,
                                    as_form=True,
                                    ),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'},)

        ## outgoing changesets between those revisions
        response.mustcontain("""<a href="/%s/changeset/3d8f361e72ab303da48d799ff1ac40d5ac37c67e">r1:%s</a>""" % (HG_REPO, rev2))

        response.mustcontain('Common ancestor')
        response.mustcontain("""<a href="/%s/changeset/b986218ba1c9b0d6a259fac9b050b1724ed8e545">%s</a>""" % (HG_REPO, rev1))

    def test_compare_revisions_git_as_form(self):
        self.log_user()
        rev1 = 'c1214f7e79e02fc37156ff215cd71275450cffc3'
        rev2 = '38b5fe81f109cb111f549bfe9bb6b267e10bc557'

        response = self.app.get(url('compare_url',
                                    repo_name=GIT_REPO,
                                    org_ref_type="rev",
                                    org_ref_name=rev1,
                                    other_ref_type="rev",
                                    other_ref_name=rev2,
                                    as_form=True,
                                    ),
                                extra_environ={'HTTP_X_PARTIAL_XHR': '1'},)
        ## outgoing changesets between those revisions
        response.mustcontain("""<a href="/%s/changeset/38b5fe81f109cb111f549bfe9bb6b267e10bc557">r1:%s</a>""" % (GIT_REPO, rev2[:12]))

        response.mustcontain('Common ancestor')
        response.mustcontain("""<a href="/%s/changeset/c1214f7e79e02fc37156ff215cd71275450cffc3">%s</a>""" % (GIT_REPO, rev1[:12]))
