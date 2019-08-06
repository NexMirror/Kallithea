from kallithea.tests.base import *


class TestRepoGroupsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('repos_groups'))
        response.mustcontain('"records": []')

    def test_new(self):
        self.log_user()
        response = self.app.get(url('new_repos_group'))

    def test_create(self):
        self.log_user()

        group_name = 'foo'

        # creation with form error
        response = self.app.post(url('repos_groups'),
                                         {'group_name': group_name,
                                          '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.mustcontain('name="group_name" type="text" value="%s"' % group_name)
        response.mustcontain('<!-- for: group_description -->')

        # creation
        response = self.app.post(url('repos_groups'),
                                         {'group_name': group_name,
                                         'group_description': 'lala',
                                         'parent_group_id': '-1',
                                         'group_copy_permissions': 'True',
                                          '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Created repository group %s' % group_name)

        # edit form
        response = self.app.get(url('edit_repo_group', group_name=group_name))
        response.mustcontain('>lala<')

        # edit with form error
        response = self.app.post(url('update_repos_group', group_name=group_name),
                                         {'group_name': group_name,
                                          '_session_csrf_secret_token': self.session_csrf_secret_token()})
        response.mustcontain('name="group_name" type="text" value="%s"' % group_name)
        response.mustcontain('<!-- for: group_description -->')

        # edit
        response = self.app.post(url('update_repos_group', group_name=group_name),
                                         {'group_name': group_name,
                                         'group_description': 'lolo',
                                          '_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Updated repository group %s' % group_name)
        response = response.follow()
        response.mustcontain('name="group_name" type="text" value="%s"' % group_name)
        response.mustcontain(no='<!-- for: group_description -->')
        response.mustcontain('>lolo<')

        # listing
        response = self.app.get(url('repos_groups'))
        response.mustcontain('raw_name": "%s"' % group_name)

        # show
        response = self.app.get(url('repos_group', group_name=group_name))
        response.mustcontain('href="/_admin/repo_groups/%s/edit"' % group_name)

        # show ignores extra trailing slashes in the URL
        response = self.app.get(url('repos_group', group_name='%s//' % group_name))
        response.mustcontain('href="/_admin/repo_groups/%s/edit"' % group_name)

        # delete
        response = self.app.post(url('delete_repo_group', group_name=group_name),
                                 {'_session_csrf_secret_token': self.session_csrf_secret_token()})
        self.checkSessionFlash(response, 'Removed repository group %s' % group_name)

    def test_new_by_regular_user(self):
        self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        response = self.app.get(url('new_repos_group'), status=403)
