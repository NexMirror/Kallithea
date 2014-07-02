from kallithea.tests import *
from kallithea.model.db import Notification, User

from kallithea.model.user import UserModel
from kallithea.model.notification import NotificationModel
from kallithea.model.meta import Session


class TestNotificationsController(TestController):

    def tearDown(self):
        for n in Notification.query().all():
            inst = Notification.get(n.notification_id)
            Session().delete(inst)
        Session().commit()

    def test_index(self):
        self.log_user()

        u1 = UserModel().create_or_update(username='u1', password='qweqwe',
                                          email='u1@example.com',
                                          firstname='u1', lastname='u1')
        u1 = u1.user_id

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
                                               firstname='u1', lastname='u1')
        u2 = UserModel().create_or_update(username='u2', password='qweqwe',
                                               email='u2@example.com',
                                               firstname='u2', lastname='u2')

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
        self.assertEqual(get_notif(cur_user.notifications), [notification])
        self.assertEqual(get_notif(u1.notifications), [notification])
        self.assertEqual(get_notif(u2.notifications), [notification])
        cur_usr_id = cur_user.user_id

        response = self.app.delete(url('notification',
                                       notification_id=
                                       notification.notification_id))
        self.assertEqual(response.body, 'ok')

        cur_user = User.get(cur_usr_id)
        self.assertEqual(cur_user.notifications, [])

    def test_show(self):
        self.log_user()
        cur_user = self._get_logged_user()
        u1 = UserModel().create_or_update(username='u1', password='qweqwe',
                                          email='u1@example.com',
                                          firstname='u1', lastname='u1')
        u2 = UserModel().create_or_update(username='u2', password='qweqwe',
                                          email='u2@example.com',
                                          firstname='u2', lastname='u2')

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
