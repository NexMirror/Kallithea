from kallithea.tests import *


class TestChangelogController(TestControllerPytest):

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
            """<span class="changeset_hash">r640:0a4e54a44604</span>"""
        )
        response.mustcontain("""code garden""")

        response.mustcontain("""var jsdata = [[[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 1, 2, 0], [0, 0, 1, 0]], 0, 0], [[0, 1], [[0, 0, 1, 0], [1, 1, 2, 0]], 0, 0], [[0, 1], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 3, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0], [[1, 3], [[0, 0, 2, 0], [1, 1, 3, 0]], 0, 0], [[1, 3], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 4, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 1, 4, 0]], 0, 0], [[1, 4], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 5, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 5, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 5, 0]], 0, 0], [[1, 5], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 6, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 1, 6, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 6, 0]], 0, 0], [[1, 6], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 7, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 7, 0]], 0, 0], [[1, 7], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 8, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 8, 0]], 0, 0], [[1, 8], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 9, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 10, 0], [0, 0, 2, 0], [1, 2, 9, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 10, 0], [2, 2, 9, 0]], 0, 0], [[2, 9], [[0, 0, 2, 0], [1, 1, 10, 0], [2, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 1, 10, 0]], 0, 0], [[1, 10], [[0, 0, 2, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[1, 11], [[0, 0, 2, 0], [1, 1, 11, 0]], 1, 0], [[2, 12], [[0, 0, 2, 0], [2, 1, 12, 0]], 1, 0], [[0, 2], [[0, 1, 13, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0], [[1, 13], [[0, 0, 2, 0], [1, 1, 13, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0], [1, 1, 13, 0]], 0, 0], [[1, 13], [[0, 0, 2, 0], [1, 1, 13, 0], [1, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 1, 14, 0], [0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 2, 0]], 0, 0]];""")

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
            """<span class="changeset_hash">r539:22baf968d547</span>"""
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
            """<span class="changeset_hash">r613:95f9a91d775b</span>"""
        )

        response.mustcontain("""fixing stupid typo in context for mercurial""")

        response.mustcontain("""var jsdata = [[[0, 1], [[0, 0, 2, 0]], 0, 0], [[0, 2], [[0, 0, 3, 0]], 0, 0], [[0, 3], [[0, 0, 4, 0]], 0, 0], [[0, 4], [[0, 0, 5, 0]], 0, 0], [[0, 5], [[0, 0, 6, 0]], 0, 0], [[0, 6], [[0, 0, 7, 0]], 0, 0], [[0, 7], [[0, 0, 8, 0]], 0, 0], [[0, 8], [[0, 0, 9, 0]], 0, 0], [[0, 9], [[0, 1, 11, 0], [0, 0, 10, 0]], 0, 0], [[0, 10], [[0, 0, 12, 0], [1, 1, 11, 0]], 0, 0], [[0, 12], [[0, 0, 11, 0], [1, 0, 11, 0]], 0, 0], [[0, 11], [[0, 1, 14, 0], [0, 0, 13, 0]], 0, 0], [[0, 13], [[0, 0, 15, 0], [1, 1, 14, 0]], 0, 0], [[0, 15], [[0, 0, 16, 0], [1, 1, 14, 0]], 0, 0], [[1, 14], [[0, 0, 16, 0], [1, 0, 16, 0]], 0, 0], [[0, 16], [[0, 1, 18, 0], [0, 0, 17, 0]], 0, 0], [[0, 17], [[0, 0, 19, 0], [1, 1, 18, 0]], 0, 0], [[0, 19], [[0, 0, 20, 0], [1, 1, 18, 0]], 0, 0], [[0, 20], [[0, 0, 21, 0], [1, 1, 18, 0]], 0, 0], [[0, 21], [[0, 0, 22, 0], [1, 1, 18, 0]], 0, 0], [[0, 22], [[0, 0, 23, 0], [1, 1, 18, 0]], 0, 0], [[0, 23], [[0, 0, 24, 0], [1, 1, 18, 0]], 0, 0], [[1, 18], [[0, 0, 24, 0], [1, 1, 25, 0]], 0, 0], [[1, 25], [[0, 0, 24, 0], [1, 1, 26, 0], [1, 0, 24, 0]], 0, 0], [[0, 24], [[0, 0, 27, 0], [1, 1, 26, 0]], 0, 0], [[1, 26], [[0, 0, 27, 0], [1, 1, 28, 0]], 0, 0], [[1, 28], [[0, 0, 27, 0], [1, 1, 29, 0]], 0, 0], [[1, 29], [[0, 0, 27, 0], [1, 1, 30, 0]], 0, 0], [[1, 30], [[0, 0, 27, 0], [1, 0, 27, 0], [1, 1, 31, 0]], 0, 0], [[1, 31], [[0, 0, 27, 0], [1, 1, 32, 0]], 0, 0], [[1, 32], [[0, 0, 27, 0], [1, 1, 33, 0]], 0, 0], [[0, 27], [[0, 0, 33, 0], [1, 0, 33, 0]], 0, 0], [[0, 33], [[0, 0, 34, 0]], 0, 0], [[0, 34], [[0, 0, 35, 0]], 0, 0], [[0, 35], [[0, 0, 36, 0]], 0, 0], [[0, 36], [[0, 0, 37, 0]], 0, 0], [[0, 37], [[0, 0, 38, 0]], 0, 0], [[0, 38], [[0, 1, 40, 0], [0, 0, 39, 0]], 0, 0], [[0, 39], [[0, 0, 41, 0], [1, 1, 40, 0]], 0, 0], [[1, 40], [[0, 0, 41, 0], [1, 1, 42, 0]], 0, 0], [[1, 42], [[0, 0, 41, 0], [1, 0, 41, 0]], 0, 0], [[0, 41], [[0, 0, 43, 0]], 0, 0], [[0, 43], [[0, 1, 45, 0], [0, 0, 44, 0]], 0, 0], [[0, 44], [[0, 0, 46, 0], [1, 1, 45, 0]], 0, 0], [[1, 45], [[0, 0, 46, 0], [1, 1, 47, 0]], 0, 0], [[1, 47], [[0, 0, 46, 0], [1, 1, 48, 0], [1, 0, 46, 0]], 0, 0], [[0, 46], [[0, 0, 49, 0], [1, 1, 48, 0]], 0, 0], [[1, 48], [[0, 0, 49, 0], [1, 0, 49, 0]], 0, 0], [[0, 49], [[0, 1, 51, 0], [0, 0, 50, 0]], 0, 0], [[0, 50], [[0, 0, 52, 0], [1, 1, 51, 0]], 0, 0], [[1, 51], [[0, 0, 52, 0], [1, 0, 52, 0]], 0, 0], [[0, 52], [[0, 0, 53, 0]], 0, 0], [[0, 53], [[0, 0, 54, 0]], 0, 0], [[0, 54], [[0, 0, 55, 0]], 0, 0], [[0, 55], [[0, 1, 57, 0], [0, 0, 56, 0]], 0, 0], [[0, 56], [[0, 0, 58, 0], [1, 1, 57, 0]], 0, 0], [[1, 57], [[0, 0, 58, 0], [1, 0, 58, 0]], 0, 0], [[0, 58], [[0, 0, 59, 0]], 0, 0], [[0, 59], [[0, 0, 60, 0]], 0, 0], [[0, 60], [[0, 0, 61, 0]], 0, 0], [[0, 61], [[0, 1, 63, 0], [0, 0, 62, 0]], 0, 0], [[0, 62], [[0, 0, 64, 0], [1, 1, 63, 0]], 0, 0], [[1, 63], [[0, 0, 64, 0], [1, 0, 64, 0], [1, 1, 65, 0]], 0, 0], [[1, 65], [[0, 0, 64, 0], [1, 1, 66, 0]], 0, 0], [[0, 64], [[0, 0, 67, 0], [1, 1, 66, 0]], 0, 0], [[0, 67], [[0, 0, 68, 0], [1, 1, 66, 0]], 0, 0], [[0, 68], [[0, 0, 69, 0], [1, 1, 66, 0]], 0, 0], [[0, 69], [[0, 0, 70, 0], [1, 1, 66, 0]], 0, 0], [[0, 70], [[0, 0, 71, 0], [1, 1, 66, 0]], 0, 0], [[0, 71], [[0, 0, 72, 0], [1, 1, 66, 0]], 0, 0], [[0, 72], [[0, 0, 66, 0], [1, 0, 66, 0]], 0, 0], [[0, 66], [[0, 0, 73, 0]], 0, 0], [[0, 73], [[0, 0, 74, 0]], 0, 0], [[0, 74], [[0, 0, 75, 0]], 0, 0], [[0, 75], [[0, 1, 77, 0], [0, 0, 76, 0]], 0, 0], [[0, 76], [[0, 1, 79, 0], [0, 0, 78, 0], [1, 2, 77, 0]], 0, 0], [[2, 77], [[0, 0, 78, 0], [1, 1, 79, 0], [2, 0, 78, 0]], 0, 0], [[0, 78], [[0, 0, 80, 0], [1, 1, 79, 0]], 0, 0], [[0, 80], [[0, 0, 81, 0], [1, 1, 79, 0]], 0, 0], [[0, 81], [[0, 0, 82, 0], [1, 1, 79, 0]], 0, 0], [[1, 79], [[0, 0, 82, 0], [1, 0, 82, 0], [1, 1, 83, 0]], 0, 0], [[1, 83], [[0, 0, 82, 0], [1, 1, 84, 0]], 0, 0], [[0, 82], [[0, 0, 85, 0], [1, 1, 84, 0]], 0, 0], [[0, 85], [[0, 0, 86, 0], [1, 1, 84, 0]], 0, 0], [[0, 86], [[0, 0, 87, 0], [1, 1, 84, 0]], 0, 0], [[0, 87], [[0, 0, 88, 0], [1, 1, 84, 0]], 0, 0], [[0, 88], [[0, 1, 84, 0], [0, 0, 89, 0], [1, 1, 84, 0]], 0, 0], [[0, 89], [[0, 0, 90, 0], [1, 1, 84, 0]], 0, 0], [[1, 84], [[0, 0, 90, 0], [1, 0, 90, 0]], 0, 0], [[0, 90], [[0, 0, 91, 0]], 0, 0], [[0, 91], [[0, 0, 92, 0]], 0, 0], [[0, 92], [[0, 0, 93, 0]], 0, 0], [[0, 93], [[0, 0, 94, 0]], 0, 0], [[0, 94], [[0, 0, 95, 0]], 0, 0], [[0, 95], [[0, 0, 96, 0]], 0, 0], [[0, 96], [[0, 0, 97, 0]], 0, 0], [[0, 97], [[0, 0, 98, 0]], 0, 0], [[0, 98], [[0, 0, 99, 0]], 0, 0], [[0, 99], [[0, 0, 100, 0]], 0, 0], [[0, 100], [[0, 0, 101, 0]], 0, 0]];""")

#        response.mustcontain(
#            """<div id="changed_total_5e204e7583b9c8e7b93a020bd036564b1e731dae" """
#            """style="float:right;" class="changed_total tooltip" """
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
            """<span class="changeset_hash">r515:636ed213f2f1</span>"""
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
        self.assertEqual(response.status, '302 Found')

    def test_index_git_with_filenode_that_is_dirnode(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/tests',
                                    repo_name=GIT_REPO))
        self.assertEqual(response.status, '302 Found')

    def test_index_hg_with_filenode_not_existing(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/wrong_path',
                                    repo_name=HG_REPO))
        self.assertEqual(response.status, '302 Found')

    def test_index_git_with_filenode_not_existing(self):
        self.log_user()
        response = self.app.get(url(controller='changelog', action='index',
                                    revision='tip', f_path='/wrong_path',
                                    repo_name=GIT_REPO))
        self.assertEqual(response.status, '302 Found')
