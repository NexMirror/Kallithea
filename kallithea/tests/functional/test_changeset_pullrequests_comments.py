import re

from kallithea.tests.base import *
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.db import ChangesetComment, Notification, \
    UserNotification
from kallithea.model.meta import Session


class TestChangeSetCommentsController(TestController):

    def setup_method(self, method):
        for x in ChangesetComment.query().all():
            Session().delete(x)
        Session().commit()

        self.remove_all_notifications()

    def test_create(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'general comment on changeset'

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 1
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]

        comment_id = ChangesetComment.query().first().comment_id
        assert notification.type_ == Notification.TYPE_CHANGESET_COMMENT
        sbj = (u'/%s/changeset/'
               '27cd5cce30c96924232dffcd24178a07ffeb5dfc#comment-%s'
               % (HG_REPO, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

    def test_create_inline(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'inline comment on changeset'
        f_path = 'vcs/web/simplevcs/views/repository.py'
        line = 'n1'

        params = {'text': text, 'f_path': f_path, 'line': line, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (1 inline, 0 general)'''
        )
        response.mustcontain(
            '''<div class="comments-list-chunk" '''
            '''data-f_path="vcs/web/simplevcs/views/repository.py" '''
            '''data-line_no="n1" data-target-id="vcswebsimplevcsviewsrepositorypy_n1">'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 1
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]
        comment_id = ChangesetComment.query().first().comment_id
        assert notification.type_ == Notification.TYPE_CHANGESET_COMMENT
        sbj = (u'/%s/changeset/'
               '27cd5cce30c96924232dffcd24178a07ffeb5dfc#comment-%s'
               % (HG_REPO, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

    def test_create_with_mention(self):
        self.log_user()

        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'@%s check CommentOnRevision' % TEST_USER_REGULAR_LOGIN

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )
        response.mustcontain('<b>@%s</b> check CommentOnRevision' % TEST_USER_REGULAR_LOGIN)

        # test DB
        assert ChangesetComment.query().count() == 1
        assert Notification.query().count() == 2
        users = [x.user.username for x in UserNotification.query().all()]

        # test_regular gets notification by @mention
        assert sorted(users) == [TEST_USER_ADMIN_LOGIN, TEST_USER_REGULAR_LOGIN]

    def test_create_status_change(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'general comment on changeset'

        params = {'text': text, 'changeset_status': 'rejected',
                '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 1
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]

        comment_id = ChangesetComment.query().first().comment_id
        assert notification.type_ == Notification.TYPE_CHANGESET_COMMENT
        sbj = (u'/%s/changeset/'
               '27cd5cce30c96924232dffcd24178a07ffeb5dfc#comment-%s'
               % (HG_REPO, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

        # check status
        status = ChangesetStatusModel().get_status(repo=HG_REPO, revision=rev)
        assert status == 'rejected'

    def test_delete(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'general comment on changeset to be deleted'

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})

        comments = ChangesetComment.query().all()
        assert len(comments) == 1
        comment_id = comments[0].comment_id

        self.app.post(url("changeset_comment_delete",
                                    repo_name=HG_REPO,
                                    comment_id=comment_id),
            params={'_authentication_token': self.authentication_token()})

        comments = ChangesetComment.query().all()
        assert len(comments) == 0

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 0 comments (0 inline, 0 general)'''
        )
        response.mustcontain(no=text)


class TestPullrequestsCommentsController(TestController):

    def setup_method(self, method):
        for x in ChangesetComment.query().all():
            Session().delete(x)
        Session().commit()

        self.remove_all_notifications()

    def _create_pr(self):
        response = self.app.post(url(controller='pullrequests', action='create',
                                     repo_name=HG_REPO),
                                 {'org_repo': HG_REPO,
                                  'org_ref': 'branch:stable:4f7e2131323e0749a740c0a56ab68ae9269c562a',
                                  'other_repo': HG_REPO,
                                  'other_ref': 'branch:default:96507bd11ecc815ebc6270fdf6db110928c09c1e',
                                  'pullrequest_title': 'title',
                                  'pullrequest_desc': 'description',
                                  '_authentication_token': self.authentication_token(),
                                 },
                                 status=302)
        pr_id = int(re.search('/pull-request/(\d+)/', response.location).group(1))
        return pr_id

    def test_create(self):
        self.log_user()
        pr_id = self._create_pr()

        text = u'general comment on pullrequest'
        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='pullrequests', action='comment',
                                     repo_name=HG_REPO, pull_request_id=pr_id),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='pullrequests', action='show',
                                repo_name=HG_REPO, pull_request_id=pr_id, extra=''))
        # PRs currently always have an initial 'Under Review' status change
        # that counts as a general comment, hence '2' in the test below. That
        # could be counted as a misfeature, to be reworked later.
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 2 comments (0 inline, 2 general)'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 2
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]
        comment_id = ChangesetComment.query().order_by(ChangesetComment.comment_id.desc()).first().comment_id
        assert notification.type_ == Notification.TYPE_PULL_REQUEST_COMMENT
        sbj = (u'/%s/pull-request/%s/_/stable#comment-%s'
               % (HG_REPO, pr_id, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

    def test_create_inline(self):
        self.log_user()
        pr_id = self._create_pr()

        text = u'inline comment on changeset'
        f_path = 'vcs/web/simplevcs/views/repository.py'
        line = 'n1'
        params = {'text': text, 'f_path': f_path, 'line': line, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='pullrequests', action='comment',
                                     repo_name=HG_REPO, pull_request_id=pr_id),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='pullrequests', action='show',
                                repo_name=HG_REPO, pull_request_id=pr_id, extra=''))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 2 comments (1 inline, 1 general)'''
        )
        response.mustcontain(
            '''<div class="comments-list-chunk" '''
            '''data-f_path="vcs/web/simplevcs/views/repository.py" '''
            '''data-line_no="n1" data-target-id="vcswebsimplevcsviewsrepositorypy_n1">'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 2
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]
        comment_id = ChangesetComment.query().order_by(ChangesetComment.comment_id.desc()).first().comment_id
        assert notification.type_ == Notification.TYPE_PULL_REQUEST_COMMENT
        sbj = (u'/%s/pull-request/%s/_/stable#comment-%s'
               % (HG_REPO, pr_id, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

    def test_create_with_mention(self):
        self.log_user()
        pr_id = self._create_pr()

        text = u'@%s check CommentOnRevision' % TEST_USER_REGULAR_LOGIN
        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='pullrequests', action='comment',
                                     repo_name=HG_REPO, pull_request_id=pr_id),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='pullrequests', action='show',
                                repo_name=HG_REPO, pull_request_id=pr_id, extra=''))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 2 comments (0 inline, 2 general)'''
        )
        response.mustcontain('<b>@%s</b> check CommentOnRevision' % TEST_USER_REGULAR_LOGIN)

        # test DB
        assert ChangesetComment.query().count() == 2
        assert Notification.query().count() == 2
        users = [x.user.username for x in UserNotification.query().all()]

        # test_regular gets notification by @mention
        assert sorted(users) == [TEST_USER_ADMIN_LOGIN, TEST_USER_REGULAR_LOGIN]

    def test_create_status_change(self):
        self.log_user()
        pr_id = self._create_pr()

        text = u'general comment on pullrequest'
        params = {'text': text, 'changeset_status': 'rejected',
                '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='pullrequests', action='comment',
                                     repo_name=HG_REPO, pull_request_id=pr_id),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})
        # Test response...
        assert response.status == '200 OK'

        response = self.app.get(url(controller='pullrequests', action='show',
                                repo_name=HG_REPO, pull_request_id=pr_id, extra=''))
        # PRs currently always have an initial 'Under Review' status change
        # that counts as a general comment, hence '2' in the test below. That
        # could be counted as a misfeature, to be reworked later.
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 2 comments (0 inline, 2 general)'''
        )
        response.mustcontain(text)

        # test DB
        assert ChangesetComment.query().count() == 2
        assert Notification.query().count() == 1

        notification = Notification.query().all()[0]
        comment_id = ChangesetComment.query().order_by(ChangesetComment.comment_id.desc()).first().comment_id
        assert notification.type_ == Notification.TYPE_PULL_REQUEST_COMMENT
        sbj = (u'/%s/pull-request/%s/_/stable#comment-%s'
               % (HG_REPO, pr_id, comment_id))
        print "%s vs %s" % (sbj, notification.subject)
        assert sbj in notification.subject

        # check status
        status = ChangesetStatusModel().get_status(repo=HG_REPO, pull_request=pr_id)
        assert status == 'rejected'

    def test_delete(self):
        self.log_user()
        pr_id = self._create_pr()

        text = u'general comment on changeset to be deleted'
        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='pullrequests', action='comment',
                                     repo_name=HG_REPO, pull_request_id=pr_id),
                                     params=params, extra_environ={'HTTP_X_PARTIAL_XHR': '1'})

        comments = ChangesetComment.query().all()
        assert len(comments) == 2
        comment_id = comments[-1].comment_id

        self.app.post(url("pullrequest_comment_delete",
                                    repo_name=HG_REPO,
                                    comment_id=comment_id),
            params={'_authentication_token': self.authentication_token()})

        comments = ChangesetComment.query().all()
        assert len(comments) == 1

        response = self.app.get(url(controller='pullrequests', action='show',
                                repo_name=HG_REPO, pull_request_id=pr_id, extra=''))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )
        response.mustcontain(no=text)