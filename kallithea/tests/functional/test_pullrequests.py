import re

import pytest

from kallithea.controllers.pullrequests import PullrequestsController
from kallithea.model.db import PullRequest, User
from kallithea.model.meta import Session
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


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
                                  'org_ref': 'branch:stable:4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response = response.follow()
        assert response.status == '200 OK'
        response.mustcontain('Successfully opened new pull request')
        response.mustcontain('No additional changesets found for iterating on this pull request')
        response.mustcontain('href="/vcs_test_hg/changeset/4f7e2131323e0749a740c0a56ab68ae9269c562a"')

    def test_available(self):
        self.log_user()
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'rev:94f45ed825a1:94f45ed825a113e61af7e141f44ca578374abef0',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response = response.follow()
        assert response.status == '200 OK'
        response.mustcontain(no='No additional changesets found for iterating on this pull request')
        response.mustcontain('The following additional changes are available on stable:')
        response.mustcontain('<input id="updaterev_4f7e2131323e0749a740c0a56ab68ae9269c562a" name="updaterev" type="radio" value="4f7e2131323e0749a740c0a56ab68ae9269c562a" />')
        response.mustcontain('href="/vcs_test_hg/changeset/4f7e2131323e0749a740c0a56ab68ae9269c562a"') # as update

    def test_range(self):
        self.log_user()
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'branch:stable:4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'rev:94f45ed825a1:94f45ed825a113e61af7e141f44ca578374abef0',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        response = response.follow()
        assert response.status == '200 OK'
        response.mustcontain('No additional changesets found for iterating on this pull request')
        response.mustcontain('href="/vcs_test_hg/changeset/4f7e2131323e0749a740c0a56ab68ae9269c562a"')

    def test_update_reviewers(self):
        self.log_user()
        regular_user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
        regular_user2 = User.get_by_username(TEST_USER_REGULAR2_LOGIN)
        admin_user = User.get_by_username(TEST_USER_ADMIN_LOGIN)

        # create initial PR
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'rev:94f45ed825a1:94f45ed825a113e61af7e141f44ca578374abef0',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                 status=302)
        pull_request1_id = re.search('/pull-request/(\d+)/', response.location).group(1)
        assert response.location == 'http://localhost/%s/pull-request/%s/_/stable' % (HG_REPO, pull_request1_id)

        # create new iteration
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request1_id),
                                 {
                                  'updaterev': '4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                  'review_members': [regular_user.user_id],
                                 },
                                 status=302)
        pull_request2_id = re.search('/pull-request/(\d+)/', response.location).group(1)
        assert pull_request2_id != pull_request1_id
        assert response.location == 'http://localhost/%s/pull-request/%s/_/stable' % (HG_REPO, pull_request2_id)
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
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                  'org_review_members': [admin_user.user_id], # fake - just to get some 'meanwhile' warning ... but it is also added ...
                                  'review_members': [regular_user2.user_id, admin_user.user_id],
                                 },
                                 status=302)
        assert response.location == 'http://localhost/%s/pull-request/%s/_/stable' % (HG_REPO, pull_request2_id)
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
                                  'org_ref': 'rev:94f45ed825a1:94f45ed825a113e61af7e141f44ca578374abef0',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                status=302)
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        assert m is not None
        pull_request_id = m.group(1)

        # update it
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request_id),
                                 {
                                  'updaterev': '4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
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
                                  'org_ref': 'branch:stable:4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                 },
                                status=302)
        # location is of the form:
        # http://localhost/vcs_test_hg/pull-request/54/_/title
        m = re.search('/pull-request/(\d+)/', response.location)
        assert m is not None
        pull_request_id = m.group(1)

        # edit it
        response = self.app.post(url(controller='pullrequests', action='post',
                                     repo_name=HG_REPO, pull_request_id=pull_request_id),
                                 {
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  'owner': TEST_USER_ADMIN_LOGIN,
                                  '_session_csrf_secret_token': self.session_csrf_secret_token(),
                                  'review_members': [str(invalid_user_id)],
                                 },
                                 status=400)
        response.mustcontain('Invalid reviewer &#34;%s&#34; specified' % invalid_user_id)

    def test_iteration_refs(self):
        # Repo graph excerpt:
        #   o   fb95b340e0d0 webvcs
        #  /:
        # o :   41d2568309a0 default
        # : :
        # : o   5ec21f21aafe webvcs
        # : :
        # : o   9e6119747791 webvcs
        # : :
        # o :   3d1091ee5a53 default
        # :/
        # o     948da46b29c1 default

        self.log_user()

        # create initial PR
        response = self.app.post(
            url(controller='pullrequests', action='create', repo_name=HG_REPO),
            {
                'org_repo': HG_REPO,
                'org_ref': 'rev:9e6119747791:9e6119747791ff886a5abe1193a730b6bf874e1c',
                'other_repo': HG_REPO,
                'other_ref': 'branch:default:3d1091ee5a533b1f4577ec7d8a226bb315fb1336',
                'pullrequest_title': 'title',
                'pullrequest_desc': 'description',
                '_session_csrf_secret_token': self.session_csrf_secret_token(),
            },
            status=302)
        pr1_id = int(re.search('/pull-request/(\d+)/', response.location).group(1))
        pr1 = PullRequest.get(pr1_id)

        assert pr1.org_ref == 'branch:webvcs:9e6119747791ff886a5abe1193a730b6bf874e1c'
        assert pr1.other_ref == 'branch:default:948da46b29c125838a717f6a8496eb409717078d'

        Session().rollback() # invalidate loaded PR objects before issuing next request.

        # create PR 2 (new iteration with same ancestor)
        response = self.app.post(
            url(controller='pullrequests', action='post', repo_name=HG_REPO, pull_request_id=pr1_id),
            {
                'updaterev': '5ec21f21aafe95220f1fc4843a4a57c378498b71',
                'pullrequest_title': 'title',
                'pullrequest_desc': 'description',
                'owner': TEST_USER_REGULAR_LOGIN,
                '_session_csrf_secret_token': self.session_csrf_secret_token(),
             },
             status=302)
        pr2_id = int(re.search('/pull-request/(\d+)/', response.location).group(1))
        pr1 = PullRequest.get(pr1_id)
        pr2 = PullRequest.get(pr2_id)

        assert pr2_id != pr1_id
        assert pr1.status == PullRequest.STATUS_CLOSED
        assert pr2.org_ref == 'branch:webvcs:5ec21f21aafe95220f1fc4843a4a57c378498b71'
        assert pr2.other_ref == pr1.other_ref

        Session().rollback() # invalidate loaded PR objects before issuing next request.

        # create PR 3 (new iteration with new ancestor)
        response = self.app.post(
            url(controller='pullrequests', action='post', repo_name=HG_REPO, pull_request_id=pr2_id),
            {
                'updaterev': 'fb95b340e0d03fa51f33c56c991c08077c99303e',
                'pullrequest_title': 'title',
                'pullrequest_desc': 'description',
                'owner': TEST_USER_REGULAR_LOGIN,
                '_session_csrf_secret_token': self.session_csrf_secret_token(),
             },
             status=302)
        pr3_id = int(re.search('/pull-request/(\d+)/', response.location).group(1))
        pr2 = PullRequest.get(pr2_id)
        pr3 = PullRequest.get(pr3_id)

        assert pr3_id != pr2_id
        assert pr2.status == PullRequest.STATUS_CLOSED
        assert pr3.org_ref == 'branch:webvcs:fb95b340e0d03fa51f33c56c991c08077c99303e'
        assert pr3.other_ref == 'branch:default:41d2568309a05f422cffb8008e599d385f8af439'


@pytest.mark.usefixtures("test_context_fixture") # apply fixture for all test methods
class TestPullrequestsGetRepoRefs(TestController):

    def setup_method(self, method):
        self.repo_name = u'main'
        repo = fixture.create_repo(self.repo_name, repo_type='hg')
        self.repo_scm_instance = repo.scm_instance
        Session().commit()
        self.c = PullrequestsController()

    def teardown_method(self, method):
        fixture.destroy_repo(u'main')
        Session().commit()
        Session.remove()

    def test_repo_refs_empty_repo(self):
        # empty repo with no commits, no branches, no bookmarks, just one tag
        refs, default = self.c._get_repo_refs(self.repo_scm_instance)
        assert default == 'tag:null:0000000000000000000000000000000000000000'

    def test_repo_refs_one_commit_no_hints(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.repo_scm_instance)
        assert default == 'branch:default:%s' % cs0.raw_id
        assert ([('branch:default:%s' % cs0.raw_id, 'default (current tip)')],
                'Branches') in refs

    def test_repo_refs_one_commit_rev_hint(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.repo_scm_instance, rev=cs0.raw_id)
        expected = 'branch:default:%s' % cs0.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_no_hints(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.repo_scm_instance)
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_rev_hints(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.repo_scm_instance, rev=cs0.raw_id)
        expected = 'rev:%s:%s' % (cs0.raw_id, cs0.raw_id)
        assert default == expected
        assert ([(expected, 'Changeset: %s' % cs0.raw_id[0:12])], 'Special') in refs
        assert ([('branch:default:%s' % cs1.raw_id, 'default (current tip)')], 'Branches') in refs

        refs, default = self.c._get_repo_refs(self.repo_scm_instance, rev=cs1.raw_id)
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_two_commits_branch_hint(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.repo_scm_instance, branch='default')
        expected = 'branch:default:%s' % cs1.raw_id
        assert default == expected
        assert ([(expected, 'default (current tip)')], 'Branches') in refs

    def test_repo_refs_one_branch_no_hints(self):
        cs0 = fixture.commit_change(self.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        # TODO
