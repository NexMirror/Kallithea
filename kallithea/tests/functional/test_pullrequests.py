import re

from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.model.meta import Session

from kallithea.controllers.pullrequests import PullrequestsController

fixture = Fixture()

class TestPullrequestsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='pullrequests', action='index',
                                    repo_name=HG_REPO))

    def test_create_trivial(self):
        self.log_user()
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                 }
                                )
        self.assertEqual(response.status, '302 Found')
        response = response.follow()
        self.assertEqual(response.status, '200 OK')
        response.mustcontain('This pull request has already been merged to default.')

    def test_create_with_existing_reviewer(self):
        self.log_user()
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': TEST_USER_ADMIN_LOGIN,
                                 }
                                )
        self.assertEqual(response.status, '302 Found')
        response = response.follow()
        self.assertEqual(response.status, '200 OK')
        response.mustcontain('This pull request has already been merged to default.')

    def test_create_with_invalid_reviewer(self):
        invalid_user_name = 'invalid_user'
        self.log_user()
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {
                                  'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': invalid_user_name,
                                 },
                                 status=400)
        response.mustcontain('Invalid reviewer &#34;%s&#34; specified' % invalid_user_name)

    def test_update_with_invalid_reviewer(self):
        invalid_user_id = 99999
        self.log_user()
        # create a valid pull request
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {
                                  'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                 }
                                )
        self.assertEqual(response.status, '302 Found')
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        self.assertNotEqual(m, None)
        pull_request_id = m.group(1)

        # update it
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request_id),
                                 {
                                  'updaterev': 'default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': invalid_user_id,
                                 },
                                 status=400)
        response.mustcontain('Invalid reviewer &#34;%s&#34; specified' % invalid_user_id)

    def test_edit_with_invalid_reviewer(self):
        invalid_user_id = 99999
        self.log_user()
        # create a valid pull request
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {
                                  'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                 }
                                )
        self.assertEqual(response.status, '302 Found')
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        self.assertNotEqual(m, None)
        pull_request_id = m.group(1)

        # edit it
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request_id),
                                 {
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': invalid_user_id,
                                 },
                                 status=400)
        response.mustcontain('Invalid reviewer &#34;%s&#34; specified' % invalid_user_id)

class TestPullrequestsGetRepoRefs(TestController):

    def setUp(self):
        self.main = fixture.create_repo('main', repo_type='hg')
        Session.add(self.main)
        Session.commit()
        self.c = PullrequestsController()

    def tearDown(self):
        fixture.destroy_repo('main')
        Session.commit()
        Session.remove()

    def test_repo_refs_empty_repo(self):
        # empty repo with no commits, no branches, no bookmarks, just one tag
        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        self.assertEqual(default, 'tag:null:0000000000000000000000000000000000000000')

    def test_repo_refs_one_commit_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        self.assertEqual(default, 'branch:default:%s' % cs0.raw_id)
        self.assertIn(([('branch:default:%s' % cs0.raw_id, 'default (current tip)')],
                'Branches'), refs)

    def test_repo_refs_one_commit_rev_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'branch:default:%s' % cs0.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_rev_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'rev:%s:%s' % (cs0.raw_id, cs0.raw_id)
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'Changeset: %s' % cs0.raw_id[0:12])], 'Special'), refs)
        self.assertIn(([('branch:default:%s' % cs1.raw_id, 'default (current tip)')], 'Branches'), refs)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs1.raw_id)
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_branch_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, branch='default')
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_one_branch_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        # TODO
