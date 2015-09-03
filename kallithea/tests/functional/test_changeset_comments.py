from kallithea.tests import *
from kallithea.model.db import ChangesetComment, Notification, \
    UserNotification
from kallithea.model.meta import Session


class TestChangeSetCommentsController(TestController):

    def setUp(self):
        for x in ChangesetComment.query().all():
            Session().delete(x)
        Session().commit()

        self.remove_all_notifications()

    def test_create(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'CommentOnRevision'

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params)
        # Test response...
        self.assertEqual(response.status, '302 Found')
        response.follow()

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        # test DB
        self.assertEqual(ChangesetComment.query().count(), 1)
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )

        self.assertEqual(Notification.query().count(), 1)
        self.assertEqual(ChangesetComment.query().count(), 1)

        notification = Notification.query().all()[0]

        ID = ChangesetComment.query().first().comment_id
        self.assertEqual(notification.type_,
                         Notification.TYPE_CHANGESET_COMMENT)
        sbj = (u'/%s/changeset/'
               '27cd5cce30c96924232dffcd24178a07ffeb5dfc#comment-%s' % (HG_REPO, ID))
        print "%s vs %s" % (sbj, notification.subject)
        self.assertTrue(sbj in notification.subject)

    def test_create_inline(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'CommentOnRevision'
        f_path = 'vcs/web/simplevcs/views/repository.py'
        line = 'n1'

        params = {'text': text, 'f_path': f_path, 'line': line, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params)
        # Test response...
        self.assertEqual(response.status, '302 Found')
        response.follow()

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        #test DB
        self.assertEqual(ChangesetComment.query().count(), 1)
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (1 inline, 0 general)'''
        )
        response.mustcontain(
            '''<div class="comments-list-chunk" '''
            '''data-f_path="vcs/web/simplevcs/views/repository.py" '''
            '''data-line_no="n1" data-target-id="vcswebsimplevcsviewsrepositorypy_n1">'''
        )

        self.assertEqual(Notification.query().count(), 1)
        self.assertEqual(ChangesetComment.query().count(), 1)

        notification = Notification.query().all()[0]
        ID = ChangesetComment.query().first().comment_id
        self.assertEqual(notification.type_,
                         Notification.TYPE_CHANGESET_COMMENT)
        sbj = (u'/%s/changeset/'
               '27cd5cce30c96924232dffcd24178a07ffeb5dfc#comment-%s' % (HG_REPO, ID))
        print "%s vs %s" % (sbj, notification.subject)
        self.assertTrue(sbj in notification.subject)

    def test_create_with_mention(self):
        self.log_user()

        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'@%s check CommentOnRevision' % TEST_USER_REGULAR_LOGIN

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params)
        # Test response...
        self.assertEqual(response.status, '302 Found')
        response.follow()

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        # test DB
        self.assertEqual(ChangesetComment.query().count(), 1)
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 1 comment (0 inline, 1 general)'''
        )

        self.assertEqual(Notification.query().count(), 2)
        users = [x.user.username for x in UserNotification.query().all()]

        # test_regular gets notification by @mention
        self.assertEqual(sorted(users), [TEST_USER_ADMIN_LOGIN, TEST_USER_REGULAR_LOGIN])

    def test_delete(self):
        self.log_user()
        rev = '27cd5cce30c96924232dffcd24178a07ffeb5dfc'
        text = u'CommentOnRevision'

        params = {'text': text, '_authentication_token': self.authentication_token()}
        response = self.app.post(url(controller='changeset', action='comment',
                                     repo_name=HG_REPO, revision=rev),
                                     params=params)

        comments = ChangesetComment.query().all()
        self.assertEqual(len(comments), 1)
        comment_id = comments[0].comment_id

        self.app.post(url(controller='changeset',
                                    action='delete_comment',
                                    repo_name=HG_REPO,
                                    comment_id=comment_id),
            params={'_method': 'delete', '_authentication_token': self.authentication_token()})

        comments = ChangesetComment.query().all()
        self.assertEqual(len(comments), 0)

        response = self.app.get(url(controller='changeset', action='index',
                                repo_name=HG_REPO, revision=rev))
        response.mustcontain(
            '''<div class="comments-number">'''
            ''' 0 comments (0 inline, 0 general)'''
        )
