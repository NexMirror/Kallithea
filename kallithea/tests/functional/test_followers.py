from kallithea.tests import base


class TestFollowersController(base.TestController):

    def test_index_hg(self):
        self.log_user()
        repo_name = base.HG_REPO
        response = self.app.get(base.url(controller='followers',
                                    action='followers',
                                    repo_name=repo_name))

        response.mustcontain(base.TEST_USER_ADMIN_LOGIN)
        response.mustcontain("""Started following""")

    def test_index_git(self):
        self.log_user()
        repo_name = base.GIT_REPO
        response = self.app.get(base.url(controller='followers',
                                    action='followers',
                                    repo_name=repo_name))

        response.mustcontain(base.TEST_USER_ADMIN_LOGIN)
        response.mustcontain("""Started following""")
