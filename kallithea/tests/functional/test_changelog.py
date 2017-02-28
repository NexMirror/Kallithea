from kallithea.tests.base import *


class TestChangelogController(TestController):

    def test_index_hg(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO))

        response.mustcontain('''id="chg_20" class="container mergerow"''')
        response.mustcontain(
            """<input class="changeset_range" """
            """id="7b22a518347bb9bc19679f6af07cd0a61bfe16e7" """
            """name="7b22a518347bb9bc19679f6af07cd0a61bfe16e7" """
            """type="checkbox" value="1" />"""
        )
        #rev 640: code garden
        response.mustcontain(
            """<a class="changeset_hash" href="/%s/changeset/0a4e54a4460401d6dbbd6a3604b17cd2b3606b82">r640:0a4e54a44604</a>""" % HG_REPO
        )
        response.mustcontain("""code garden""")

        response.mustcontain("""var jsdata = ([[[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 1, 2, 0], [0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0], [1, 1, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 3, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0, 0, 0, 0, 0], [[1, 3], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0, 0, 0, 0, 0], [[1, 3], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 4, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 5, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 5, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 5, 0]], 0, 0, 0, 0, 0, 0], [[1, 5], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 6, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 1, 6, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 7, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 7, 0]], 0, 0, 0, 0, 0, 0], [[1, 7], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 8, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 8, 0]], 0, 0, 0, 0, 0, 0], [[1, 8], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 9, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 10, 0], [0, 0, 2, 0], [1, 2, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 10, 0], [2, 2, 9, 0]], 0, 0, 0, 0, 0, 0], [[2, 9], [[0, 0, 2, 0], [1, 1, 10, 0], [2, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0, 0, 0, 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[1, 11], [[0, 0, 2, 0], [1, 1, 11, 0]], 1, 0, 0, 0, 0, 0], [[2, 12], [[0, 0, 2, 0], [2, 1, 12, 0]], 1, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 13, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0, 0, 0, 0, 0], [[1, 13], [[0, 0, 2, 0], [1, 1, 13, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0, 0, 0, 0, 0], [[1, 13], [[0, 0, 2, 0], [1, 1, 13, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 14, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0, 0, 0, 0, 0]]);""")

    def test_index_pagination_hg(self):
        self.log_user()
        #pagination
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 1})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 2})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 3})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 4})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 5})
        response = self.app.get(url(controller='changelog', action='index',
                                    repo_name=HG_REPO), {'page': 6, 'size': 20})

        # Test response after pagination...
        response.mustcontain(
            """<input class="changeset_range" """
            """id="22baf968d547386b9516965ce89d189665003a31" """
            """name="22baf968d547386b9516965ce89d189665003a31" """
            """type="checkbox" value="1" />"""
        )

        response.mustcontain(
            """<a class="changeset_hash" href="/vcs_test_hg/changeset/22baf968d547386b9516965ce89d189665003a31">r539:22baf968d547</a>"""
        )

    def test_index_git(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO))

        response.mustcontain('''id="chg_20" class="container "''') # why no mergerow for git?
        response.mustcontain(
            """<input class="changeset_range" """
            """id="95f9a91d775b0084b2368ae7779e44931c849c0e" """
            """name="95f9a91d775b0084b2368ae7779e44931c849c0e" """
            """type="checkbox" value="1" />"""
        )

        response.mustcontain(
            """<a class="changeset_hash" href="/vcs_test_git/changeset/95f9a91d775b0084b2368ae7779e44931c849c0e">r613:95f9a91d775b</a>"""
        )

        response.mustcontain("""fixing stupid typo in context for mercurial""")

        response.mustcontain("""var jsdata = ([[[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 1, 2, 0], [0, 0, 1, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 1, 0], [1, 1, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 1], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 3, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0, 0, 0, 0, 0], [[1, 3], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 1, 4, 0], [0, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0], [1, 0, 2, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 2], [[0, 0, 4, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 1, 5, 0], [0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 5, 0]], 0, 0, 0, 0, 0, 0], [[1, 5], [[0, 0, 4, 0], [1, 1, 5, 0]], 0, 0, 0, 0, 0, 0], [[1, 5], [[0, 0, 4, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 1, 6, 0], [0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 4, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 4, 0], [1, 1, 6, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 6, 0]], 0, 0, 0, 0, 0, 0], [[1, 6], [[0, 0, 4, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 1, 7, 0], [0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 7, 0]], 0, 0, 0, 0, 0, 0], [[1, 7], [[0, 0, 4, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 1, 8, 0], [0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 8, 0]], 0, 0, 0, 0, 0, 0], [[1, 8], [[0, 0, 4, 0], [1, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 1, 9, 0], [0, 0, 4, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[1, 9], [[0, 0, 4, 0], [1, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[1, 9], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 4, 0], [1, 1, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 4], [[0, 0, 9, 0], [1, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 1, 10, 0], [0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 1, 11, 0], [0, 0, 9, 0], [1, 2, 10, 0]], 0, 0, 0, 0, 0, 0], [[2, 10], [[0, 0, 9, 0], [1, 1, 11, 0], [2, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[1, 11], [[0, 0, 9, 0], [1, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[1, 11], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 1, 11, 0], [0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0], [1, 1, 11, 0]], 0, 0, 0, 0, 0, 0], [[1, 11], [[0, 0, 9, 0], [1, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0], [[0, 9], [[0, 0, 9, 0]], 0, 0, 0, 0, 0, 0]]);""")

#        response.mustcontain(
#            """<div id="changed_total_5e204e7583b9c8e7b93a020bd036564b1e731dae" """
#            """style="float:right;" class="changed_total" data-toggle="tooltip" """
#            """title="Affected number of files, click to show """
#            """more details">3</div>"""
#        )

    def test_index_pagination_git(self):
        self.log_user()
        #pagination
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 1})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 2})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 3})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 4})
        self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 5})
        response = self.app.get(url(controller='changelog', action='index',
                                    repo_name=GIT_REPO), {'page': 6, 'size': 20})

        # Test response after pagination...
        response.mustcontain(
            """<input class="changeset_range" """
            """id="636ed213f2f11ef91071b9c24f2d5e6bd01a6ed5" """
            """name="636ed213f2f11ef91071b9c24f2d5e6bd01a6ed5" """
            """type="checkbox" value="1" />"""
        )

        response.mustcontain(
            """<a class="changeset_hash" href="/vcs_test_git/changeset/636ed213f2f11ef91071b9c24f2d5e6bd01a6ed5">r515:636ed213f2f1</a>"""
        )

    def test_index_hg_with_filenode(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/vcs/exceptions.py',
                                    repo_name=HG_REPO))
        #history commits messages
        response.mustcontain('Added exceptions module, this time for real')
        response.mustcontain('Added not implemented hg backend test case')
        response.mustcontain('Added BaseChangeset class')
        # Test response...

    def test_index_git_with_filenode(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/vcs/exceptions.py',
                                    repo_name=GIT_REPO))
        #history commits messages
        response.mustcontain('Added exceptions module, this time for real')
        response.mustcontain('Added not implemented hg backend test case')
        response.mustcontain('Added BaseChangeset class')

    def test_index_hg_with_filenode_that_is_dirnode(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/tests',
                                    repo_name=HG_REPO))
        assert response.status == '302 Found'

    def test_index_git_with_filenode_that_is_dirnode(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/tests',
                                    repo_name=GIT_REPO))
        assert response.status == '302 Found'

    def test_index_hg_with_filenode_not_existing(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/wrong_path',
                                    repo_name=HG_REPO))
        assert response.status == '302 Found'

    def test_index_git_with_filenode_not_existing(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/wrong_path',
                                    repo_name=GIT_REPO))
        assert response.status == '302 Found'
