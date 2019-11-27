# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.model.notification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Model for notifications


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 20, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import datetime
import logging

from tg import app_globals
from tg import tmpl_context as c
from tg.i18n import ugettext as _

import kallithea
from kallithea.lib import helpers as h
from kallithea.lib.utils2 import safe_unicode
from kallithea.model.db import User


log = logging.getLogger(__name__)


class NotificationModel(object):

    TYPE_CHANGESET_COMMENT = u'cs_comment'
    TYPE_MESSAGE = u'message'
    TYPE_MENTION = u'mention' # not used
    TYPE_REGISTRATION = u'registration'
    TYPE_PULL_REQUEST = u'pull_request'
    TYPE_PULL_REQUEST_COMMENT = u'pull_request_comment'

    def create(self, created_by, subject, body, recipients=None,
               type_=TYPE_MESSAGE, with_email=True,
               email_kwargs=None, repo_name=None):
        """

        Creates notification of given type

        :param created_by: int, str or User instance. User who created this
            notification
        :param subject:
        :param body:
        :param recipients: list of int, str or User objects, when None
            is given send to all admins
        :param type_: type of notification
        :param with_email: send email with this notification
        :param email_kwargs: additional dict to pass as args to email template
        """
        from kallithea.lib.celerylib import tasks
        email_kwargs = email_kwargs or {}
        if recipients and not getattr(recipients, '__iter__', False):
            raise Exception('recipients must be a list or iterable')

        created_by_obj = User.guess_instance(created_by)

        recipients_objs = set()
        if recipients:
            for u in recipients:
                obj = User.guess_instance(u)
                if obj is not None:
                    recipients_objs.add(obj)
                else:
                    # TODO: inform user that requested operation couldn't be completed
                    log.error('cannot email unknown user %r', u)
            log.debug('sending notifications %s to %s',
                type_, recipients_objs
            )
        elif recipients is None:
            # empty recipients means to all admins
            recipients_objs = User.query().filter(User.admin == True).all()
            log.debug('sending notifications %s to admins: %s',
                type_, recipients_objs
            )
        #else: silently skip notification mails?

        if not with_email:
            return

        headers = {}
        headers['X-Kallithea-Notification-Type'] = type_
        if 'threading' in email_kwargs:
            headers['References'] = ' '.join('<%s>' % x for x in email_kwargs['threading'])

        # this is passed into template
        created_on = h.fmt_date(datetime.datetime.now())
        html_kwargs = {
                  'subject': subject,
                  'body': h.render_w_mentions(body, repo_name),
                  'when': created_on,
                  'user': created_by_obj.username,
                  }

        txt_kwargs = {
                  'subject': subject,
                  'body': body,
                  'when': created_on,
                  'user': created_by_obj.username,
                  }

        html_kwargs.update(email_kwargs)
        txt_kwargs.update(email_kwargs)
        email_subject = EmailNotificationModel() \
                            .get_email_description(type_, **txt_kwargs)
        email_txt_body = EmailNotificationModel() \
                            .get_email_tmpl(type_, 'txt', **txt_kwargs)
        email_html_body = EmailNotificationModel() \
                            .get_email_tmpl(type_, 'html', **html_kwargs)

        # don't send email to person who created this comment
        rec_objs = set(recipients_objs).difference(set([created_by_obj]))

        # send email with notification to all other participants
        for rec in rec_objs:
            tasks.send_email([rec.email], email_subject, email_txt_body,
                     email_html_body, headers, author=created_by_obj)


class EmailNotificationModel(object):

    TYPE_CHANGESET_COMMENT = NotificationModel.TYPE_CHANGESET_COMMENT
    TYPE_MESSAGE = NotificationModel.TYPE_MESSAGE # only used for testing
    # NotificationModel.TYPE_MENTION is not used
    TYPE_PASSWORD_RESET = 'password_link'
    TYPE_REGISTRATION = NotificationModel.TYPE_REGISTRATION
    TYPE_PULL_REQUEST = NotificationModel.TYPE_PULL_REQUEST
    TYPE_PULL_REQUEST_COMMENT = NotificationModel.TYPE_PULL_REQUEST_COMMENT
    TYPE_DEFAULT = 'default'

    def __init__(self):
        super(EmailNotificationModel, self).__init__()
        self._template_root = kallithea.CONFIG['paths']['templates'][0]
        self._tmpl_lookup = app_globals.mako_lookup
        self.email_types = {
            self.TYPE_CHANGESET_COMMENT: 'changeset_comment',
            self.TYPE_PASSWORD_RESET: 'password_reset',
            self.TYPE_REGISTRATION: 'registration',
            self.TYPE_DEFAULT: 'default',
            self.TYPE_PULL_REQUEST: 'pull_request',
            self.TYPE_PULL_REQUEST_COMMENT: 'pull_request_comment',
        }
        self._subj_map = {
            self.TYPE_CHANGESET_COMMENT: _('[Comment] %(repo_name)s changeset %(short_id)s "%(message_short)s" on %(branch)s'),
            self.TYPE_MESSAGE: 'Test Message',
            # self.TYPE_PASSWORD_RESET
            self.TYPE_REGISTRATION: _('New user %(new_username)s registered'),
            # self.TYPE_DEFAULT
            self.TYPE_PULL_REQUEST: _('[Review] %(repo_name)s PR %(pr_nice_id)s "%(pr_title_short)s" from %(pr_source_branch)s by %(pr_owner_username)s'),
            self.TYPE_PULL_REQUEST_COMMENT: _('[Comment] %(repo_name)s PR %(pr_nice_id)s "%(pr_title_short)s" from %(pr_source_branch)s by %(pr_owner_username)s'),
        }

    def get_email_description(self, type_, **kwargs):
        """
        return subject for email based on given type
        """
        tmpl = self._subj_map[type_]
        try:
            subj = tmpl % kwargs
        except KeyError as e:
            log.error('error generating email subject for %r from %s: %s', type_, ','.join(self._subj_map.keys()), e)
            raise
        l = [safe_unicode(x) for x in [kwargs.get('status_change'), kwargs.get('closing_pr') and _('Closing')] if x]
        if l:
            if subj.startswith('['):
                subj = '[' + ', '.join(l) + ': ' + subj[1:]
            else:
                subj = '[' + ', '.join(l) + '] ' + subj
        return subj

    def get_email_tmpl(self, type_, content_type, **kwargs):
        """
        return generated template for email based on given type
        """

        base = 'email_templates/' + self.email_types.get(type_, self.email_types[self.TYPE_DEFAULT]) + '.' + content_type
        email_template = self._tmpl_lookup.get_template(base)
        # translator and helpers inject
        _kwargs = {'_': _,
                   'h': h,
                   'c': c}
        _kwargs.update(kwargs)
        if content_type == 'html':
            _kwargs.update({
                "color_text": "#202020",
                "color_emph": "#395fa0",
                "color_link": "#395fa0",
                "color_border": "#ddd",
                "color_background_grey": "#f9f9f9",
                "color_button": "#395fa0",
                "monospace_style": "font-family:Lucida Console,Consolas,Monaco,Inconsolata,Liberation Mono,monospace",
                "sans_style": "font-family:Helvetica,Arial,sans-serif",
                })
            _kwargs.update({
                "default_style": "%(sans_style)s;font-weight:200;font-size:14px;line-height:17px;color:%(color_text)s" % _kwargs,
                "comment_style": "%(monospace_style)s;white-space:pre-wrap" % _kwargs,
                "data_style": "border:%(color_border)s 1px solid;background:%(color_background_grey)s" % _kwargs,
                "emph_style": "font-weight:600;color:%(color_emph)s" % _kwargs,
                "link_style": "color:%(color_link)s;text-decoration:none" % _kwargs,
                "link_text_style": "color:%(color_text)s;text-decoration:none;border:%(color_border)s 1px solid;background:%(color_background_grey)s" % _kwargs,
                })

        log.debug('rendering tmpl %s with kwargs %s', base, _kwargs)
        return email_template.render_unicode(**_kwargs)
