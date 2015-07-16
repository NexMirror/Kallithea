.. _email:

===============
E-mail settings
===============

The Kallithea configuration file has several e-mail related settings. When
these contain correct values, Kallithea will send e-mail in the situations
described below. If the e-mail configuration is not correct so that e-mails
cannot be sent, all mails will show up in the log output.

Before any e-mail can be sent, an SMTP server has to be configured using the
configuration file setting ``smtp_server``. If required for that server, specify
a username (``smtp_username``) and password (``smtp_password``), a non-standard
port (``smtp_port``), encryption settings (``smtp_use_tls`` or ``smtp_use_ssl``)
and/or specific authentication parameters (``smtp_auth``).

Application e-mails
-------------------

Kallithea sends an e-mail to `users` on several occasions:

- when comments are given on one of their changesets
- when comments are given on changesets they are reviewer on or on which they
  commented regardless
- when they are invited as reviewer in pull requests
- when they request a password reset

Kallithea sends an e-mail to all `administrators` upon new account registration.
Administrators are users with the ``Admin`` flag set in the ``Admin->Users``
section.

When Kallithea wants to send an e-mail but due to an error cannot correctly
determine the intended recipients, the administrators and the addresses
specified in ``email_to`` in the configuration file are used as fallback.

Recipients will see these e-mails originating from the sender specified in the
``app_email_from`` setting in the configuration file. This setting can either
contain only an e-mail address, like `kallithea-noreply@example.com`, or both
a name and an address in the following format: `Kallithea
<kallithea-noreply@example.com>`. The subject of these e-mails can
optionally be prefixed with the value of ``email_prefix`` in the configuration
file.

Error e-mails
-------------

When an exception occurs in Kallithea -- and unless interactive debugging is
enabled using ``set debug = true`` in the ``[app:main]`` section of the
configuration file -- an e-mail with exception details is sent by WebError_'s
``ErrorMiddleware`` to the addresses specified in ``email_to`` in the
configuration file.

Recipients will see these e-mails originating from the sender specified in the
``error_email_from`` setting in the configuration file. This setting can either
contain only an e-mail address, like `kallithea-noreply@example.com`, or both
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
