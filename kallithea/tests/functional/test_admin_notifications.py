from kallithea.tests import *
from kallithea.model.db import User

from kallithea.model.user import UserModel
from kallithea.model.notification import NotificationModel
from kallithea.model.meta import Session
from kallithea.lib import helpers as h


class TestNotificationsController(TestController):
    def setup_method(self, method):
        self.remove_all_notifications()

    def test_index(self):
        self.log_user()

        u1 = UserModel().create_or_update(username='u1', password='qweqwe',
                                          email='u1@example.com',
                                          firstname=u'u1', lastname=u'u1')
        u1 = u1.user_id
        Session().commit()

        response = self.app.get(url('notifications'))
        response.mustcontain('<div class="table">No notifications here yet</div>')

        cur_user = self._get_logged_user()
        notif = NotificationModel().create(created_by=u1, subject=u'test_notification_1',
                                           body=u'notification_1', recipients=[cur_user])
        Session().commit()
        response = self.app.get(url('notifications'))
        response.mustcontain('id="notification_%s"' % notif.notification_id)

    def test_delete(self):
        self.log_user()
        cur_user = self._get_logged_user()

        u1 = UserModel().create_or_update(username='u1', password='qweqwe',
                                               email='u1@example.com',
                                               firstname=u'u1', lastname=u'u1')
        u2 = UserModel().create_or_update(username='u2', password='qweqwe',
                                               email='u2@example.com',
                                               firstname=u'u2', lastname=u'u2')

        # make notifications
        notification = NotificationModel().create(created_by=cur_user,
                                                  subject=u'test',
                                                  body=u'hi there',
                                                  recipients=[cur_user, u1, u2])
        Session().commit()
        u1 = User.get(u1.user_id)
        u2 = User.get(u2.user_id)

        # check DB
        get_notif = lambda un: [x.notification for x in un]
        assert get_notif(cur_user.notifications) == [notification]
        assert get_notif(u1.notifications) == [notification]
        assert get_notif(u2.notifications) == [notification]
        cur_usr_id = cur_user.user_id

        response = self.app.post(
            url('notification', notification_id=notification.notification_id),
            params={'_method': 'delete', '_authentication_token': self.authentication_token()})
        assert response.body == 'ok'

        cur_user = User.get(cur_usr_id)
        assert cur_user.notifications == []

    def test_show(self):
        self.log_user()
        cur_user = self._get_logged_user()
        u1 = UserModel().create_or_update(username='u1', password='qweqwe',
                                          email='u1@example.com',
                                          firstname=u'u1', lastname=u'u1')
        u2 = UserModel().create_or_update(username='u2', password='qweqwe',
                                          email='u2@example.com',
                                          firstname=u'u2', lastname=u'u2')

        subject = u'test'
        notif_body = u'hi there'
        notification = NotificationModel().create(created_by=cur_user,
                                                  subject=subject,
                                                  body=notif_body,
                                                  recipients=[cur_user, u1, u2])

        response = self.app.get(url('notification',
                                    notification_id=notification.notification_id))

        response.mustcontain(subject)
        response.mustcontain(notif_body)

    def test_description_with_age(self):
        self.log_user()
        cur_user = self._get_logged_user()
        subject = u'test'
        notify_body = u'hi there'
        notification = NotificationModel().create(created_by = cur_user,
                                                  subject    = subject,
                                                  body       = notify_body)

        description = NotificationModel().make_description(notification)
        assert description == "{0} sent message {1}".format(
                cur_user.username,
                h.age(notification.created_on)
                )

    def test_description_with_datetime(self):
        self.log_user()
        cur_user = self._get_logged_user()
        subject = u'test'
        notify_body = u'hi there'
        notification = NotificationModel().create(created_by = cur_user,
                                                  subject    = subject,
                                                  body       = notify_body)

        description = NotificationModel().make_description(notification, False)
        assert description == "{0} sent message at {1}".format(
                cur_user.username,
                h.fmt_date(notification.created_on)
                )
