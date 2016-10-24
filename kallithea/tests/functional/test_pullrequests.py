import re

from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture
from kallithea.model.db import User
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
                                 },
                                 status=302)
        response = response.follow()
        assert response.status == '200 OK'
        response.mustcontain('This pull request has already been merged to default.')

    def test_update_reviewers(self):
        self.log_user()
        regular_user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        regular_user2 = User.get_by_username(TEST_USER_REGULAR2_LOGIN)
        admin_user = User.get_by_username(TEST_USER_ADMIN_LOGIN)

        # create initial PR
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'branch:default:default',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                 },
                                 status=302)
        pull_request1_id = re.search('/pull-request/(\d+)/', response.location).group(1)
        assert response.location == 'http://localhost/%s/pull-request/%s/_/title' % (HG_REPO, pull_request1_id)

        # create new iteration
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request1_id),
                                 {
                                  'updaterev': 'default',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': [regular_user.user_id],
                                 },
                                 status=302)
        pull_request2_id = re.search('/pull-request/(\d+)/', response.location).group(1)
        assert pull_request2_id != pull_request1_id
        assert response.location == 'http://localhost/%s/pull-request/%s/_/title_v2' % (HG_REPO, pull_request2_id)
        response = response.follow()
        # verify reviewer was added
        response.mustcontain('<input type="hidden" value="%s" name="review_members" />' % regular_user.user_id)

        # update without creating new iteration
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request2_id),
                                 {
                                  'pullrequest_title': 'Title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_authentication_token': self.authentication_token(),
                                  'org_review_members': [admin_user.user_id], # fake - just to get some 'meanwhile' warning ... but it is also added ...
                                  'review_members': [regular_user2.user_id, admin_user.user_id],
                                 },
                                 status=302)
        assert response.location == 'http://localhost/%s/pull-request/%s/_/Title' % (HG_REPO, pull_request2_id)
        response = response.follow()
        # verify reviewers were added / removed
        response.mustcontain('Meanwhile, the following reviewers have been added: test_regular')
        response.mustcontain('Meanwhile, the following reviewers have been removed: test_admin')
        response.mustcontain('<input type="hidden" value="%s" name="review_members" />' % regular_user.user_id)
        response.mustcontain('<input type="hidden" value="%s" name="review_members" />' % regular_user2.user_id)
        response.mustcontain(no='<input type="hidden" value="%s" name="review_members" />' % admin_user.user_id)

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
                                 },
                                status=302)
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        assert m != None
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
                                  'review_members': [str(invalid_user_id)],
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
                                 },
                                status=302)
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        assert m != None
        pull_request_id = m.group(1)

        # edit it
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request_id),
                                 {
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_authentication_token': self.authentication_token(),
                                  'review_members': [str(invalid_user_id)],
                                 },
                                 status=400)
        response.mustcontain('Invalid reviewer &#34;%s&#34; specified' % invalid_user_id)

class TestPullrequestsGetRepoRefs(TestController):

    def setup_method(self, method):
        self.main = fixture.create_repo(u'main', repo_type='hg')
        Session.commit()
        self.c = PullrequestsController()

    def teardown_method(self, method):
        fixture.destroy_repo(u'main')
        Session.commit()
        Session.remove()

    def test_repo_refs_empty_repo(self):
        # empty repo with no commits, no branches, no bookmarks, just one tag
        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        assert default == 'tag:null:0000000000000000000000000000000000000000'

    def test_repo_refs_one_commit_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        assert default == 'branch:default:%s' % cs0.raw_id
        assert ([('branch:default:%s' % cs0.raw_id, 'default (current tip)')],
                'Branches') in refs

    def test_repo_refs_one_commit_rev_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'branch:default:%s' % cs0.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_rev_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'rev:%s:%s' % (cs0.raw_id, cs0.raw_id)
        assert default == expected
        assert ([(expected, 'Changeset: %s' % cs0.raw_id[0:12])], 'Special') in refs
        assert ([('branch:default:%s' % cs1.raw_id, 'default (current tip)')], 'Branches') in refs

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs1.raw_id)
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_branch_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, branch='default')
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_one_branch_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        # TODO
