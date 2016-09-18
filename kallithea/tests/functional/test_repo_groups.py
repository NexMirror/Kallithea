from kallithea.tests.base import *


class TestRepoGroupsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('repos_groups'))
        response.mustcontain('{"totalRecords": 0, "sort": null, "startIndex": 0, "dir": "asc", "records": []};')

    def test_new(self):
        self.log_user()
        response = self.app.get(url('new_repos_group'))

    def test_new_by_regular_user(self):
        self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        response = self.app.get(url('new_repos_group'), status=403)
