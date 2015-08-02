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
