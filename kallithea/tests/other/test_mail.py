import mock

import kallithea
from kallithea.model.db import User
from kallithea.tests.base import *


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
class TestMail(TestController):

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

        assert smtplib_mock.lastdest == set(recipients)
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: %s' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

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

        assert smtplib_mock.lastdest == set([TEST_USER_ADMIN_EMAIL, email_to])
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: %s' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

    def test_send_mail_no_recipients_multiple_email_to(self):
        mailserver = 'smtp.mailserver.org'
        recipients = []
        envelope_from = 'noreply@mailserver.org'
        email_to = 'admin@mailserver.org,admin2@example.com'
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

        assert smtplib_mock.lastdest == set([TEST_USER_ADMIN_EMAIL] + email_to.split(','))
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: %s' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

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

        assert smtplib_mock.lastdest == set([TEST_USER_ADMIN_EMAIL])
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: %s' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

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

        assert smtplib_mock.lastdest == set(recipients)
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: "Kallithea Admin (no-reply)" <%s>' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

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

        assert smtplib_mock.lastdest == set(recipients)
        assert smtplib_mock.lastsender == envelope_from
        assert 'From: "Kallithea Admin (no-reply)" <%s>' % envelope_addr in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg

    def test_send_mail_extra_headers(self):
        mailserver = 'smtp.mailserver.org'
        recipients = ['rcpt1', 'rcpt2']
        envelope_from = 'noreply@mailserver.org'
        subject = 'subject'
        body = 'body'
        html_body = 'html_body'
        author = User(name='foo', lastname=u'(fubar) "baz"')
        headers = {'extra': 'yes'}

        config_mock = {
            'smtp_server': mailserver,
            'app_email_from': envelope_from,
        }
        with mock.patch('kallithea.lib.celerylib.tasks.config', config_mock):
            kallithea.lib.celerylib.tasks.send_email(recipients, subject, body, html_body,
                                                     author=author, headers=headers)

        assert smtplib_mock.lastdest == set(recipients)
        assert smtplib_mock.lastsender == envelope_from
        assert r'From: "foo (fubar) \"baz\" (no-reply)" <%s>' % envelope_from in smtplib_mock.lastmsg
        assert 'Subject: %s' % subject in smtplib_mock.lastmsg
        assert body in smtplib_mock.lastmsg
        assert html_body in smtplib_mock.lastmsg
        assert 'Extra: yes' in smtplib_mock.lastmsg
        # verify that headers dict hasn't mutated by send_email
        assert headers == {'extra': 'yes'}
