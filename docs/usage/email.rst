.. _email:

==============
Email settings
==============

The Kallithea configuration file has several email related settings. When
these contain correct values, Kallithea will send email in the situations
described below. If the email configuration is not correct so that emails
cannot be sent, all mails will show up in the log output.

Before any email can be sent, an SMTP server has to be configured using the
configuration file setting ``smtp_server``. If required for that server, specify
a username (``smtp_username``) and password (``smtp_password``), a non-standard
port (``smtp_port``), encryption settings (``smtp_use_tls`` or ``smtp_use_ssl``)
and/or specific authentication parameters (``smtp_auth``).


Application emails
------------------

Kallithea sends an email to `users` on several occasions:

- when comments are given on one of their changesets
- when comments are given on changesets they are reviewer on or on which they
  commented regardless
- when they are invited as reviewer in pull requests
- when they request a password reset

Kallithea sends an email to all `administrators` upon new account registration.
Administrators are users with the ``Admin`` flag set on the *Admin > Users*
page.

When Kallithea wants to send an email but due to an error cannot correctly
determine the intended recipients, the administrators and the addresses
specified in ``email_to`` in the configuration file are used as fallback.

Recipients will see these emails originating from the sender specified in the
``app_email_from`` setting in the configuration file. This setting can either
contain only an email address, like `kallithea-noreply@example.com`, or both
a name and an address in the following format: `Kallithea
<kallithea-noreply@example.com>`. However, if the email is sent due to an
action of a particular user, for example when a comment is given or a pull
request created, the name of that user will be combined with the email address
specified in ``app_email_from`` to form the sender (and any name part in that
configuration setting disregarded).

The subject of these emails can optionally be prefixed with the value of
``email_prefix`` in the configuration file.


Error emails
------------

When an exception occurs in Kallithea -- and unless interactive debugging is
enabled using ``set debug = true`` in the ``[app:main]`` section of the
configuration file -- an email with exception details is sent by WebError_'s
``ErrorMiddleware`` to the addresses specified in ``email_to`` in the
configuration file.

Recipients will see these emails originating from the sender specified in the
``error_email_from`` setting in the configuration file. This setting can either
contain only an email address, like `kallithea-noreply@example.com`, or both
a name and an address in the following format: `Kallithea Errors
<kallithea-noreply@example.com>`.

*Note:* The WebError_ package does not respect ``smtp_port`` and assumes the
standard SMTP port (25). If you have a remote SMTP server with a different port,
you could set up a local forwarding SMTP server on port 25.


References
----------

- `Error Middleware (Pylons documentation) <http://pylons-webframework.readthedocs.org/en/latest/debugging.html#error-middleware>`_
- `ErrorHandler (Pylons modules documentation) <http://pylons-webframework.readthedocs.org/en/latest/modules/middleware.html#pylons.middleware.ErrorHandler>`_


.. _WebError: https://pypi.python.org/pypi/WebError
