import mock

import kallithea
from kallithea.tests import *
from kallithea.model.db import User

class smtplib_mock(object):

    @classmethod
    def SMTP(cls, server, port, local_hostname):
        return smtplib_mock()

    def ehlo(self):
        pass
    def quit(self):
        pass
    def sendmail(self, sender, dest, msg):
        smtplib_mock.lastsender = sender
        smtplib_mock.lastdest = dest
        smtplib_mock.lastmsg = msg
        pass

@mock.patch('kallithea.lib.rcmail.smtp_mailer.smtplib', smtplib_mock)
class TestMail(BaseTestCase):

    def test_send_mail_trivial(self):
        mailserver = 'smtp.mailserver.org'
        recipients = ['rcpt1', 'rcpt2']
        envelope_from = 'noreply@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body)

        self.assertSetEqual(smtplib_mock.lastdest, set(recipients))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn('From: %s' % envelope_from, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)

    def test_send_mail_no_recipients(self):
        mailserver = 'smtp.mailserver.org'
        recipients = []
        envelope_from = 'noreply@mailserver.org'
        email_to = 'admin@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
            'email_to': email_to,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body)

        self.assertSetEqual(smtplib_mock.lastdest, set([TEST_USER_ADMIN_EMAIL, email_to]))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn('From: %s' % envelope_from, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)

    def test_send_mail_no_recipients_no_email_to(self):
        mailserver = 'smtp.mailserver.org'
        recipients = []
        envelope_from = 'noreply@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body)

        self.assertSetEqual(smtplib_mock.lastdest, set([TEST_USER_ADMIN_EMAIL]))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn('From: %s' % envelope_from, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)

    def test_send_mail_with_author(self):
        mailserver = 'smtp.mailserver.org'
        recipients = ['rcpt1', 'rcpt2']
        envelope_from = 'noreply@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'
        author = User.get_by_username(TEST_USER_REGULAR_LOGIN)

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body, author=author)

        self.assertSetEqual(smtplib_mock.lastdest, set(recipients))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn('From: "Kallithea Admin (no-reply)" <%s>' % envelope_from, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)

    def test_send_mail_with_author_full_mail_from(self):
        mailserver = 'smtp.mailserver.org'
        recipients = ['rcpt1', 'rcpt2']
        envelope_addr = 'noreply@mailserver.org'
        envelope_from = 'Some Name <%s>' % envelope_addr
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'
        author = User.get_by_username(TEST_USER_REGULAR_LOGIN)

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body, author=author)

        self.assertSetEqual(smtplib_mock.lastdest, set(recipients))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn('From: "Kallithea Admin (no-reply)" <%s>' % envelope_addr, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)

    def test_send_mail_extra_headers(self):
        mailserver = 'smtp.mailserver.org'
        recipients = ['rcpt1', 'rcpt2']
        envelope_from = 'noreply@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'
        author = User(name='foo', lastname='(fubar) "baz"')
        headers = {'extra': 'yes'}

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body,
                                                     author=author, headers=headers)

        self.assertSetEqual(smtplib_mock.lastdest, set(recipients))
        self.assertEqual(smtplib_mock.lastsender, envelope_from)
        self.assertIn(r'From: "foo (fubar) \"baz\" (no-reply)" <%s>' % envelope_from, smtplib_mock.lastmsg)
        self.assertIn('Subject: %s' % subject, smtplib_mock.lastmsg)
        self.assertIn(body, smtplib_mock.lastmsg)
        self.assertIn(html_body, smtplib_mock.lastmsg)
        self.assertIn('Extra: yes', smtplib_mock.lastmsg)
        # verify that headers dict hasn't mutated by send_email
        self.assertDictEqual(headers, {'extra': 'yes'})
