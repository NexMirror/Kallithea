.. _installation_iis:

=====================================================================
Installing Kallithea on Microsoft Internet Information Services (IIS)
=====================================================================

The following is documented using IIS 7/8 terminology. There should be nothing
preventing you from applying this on IIS 6 well.

.. note::

    Installing Kallithea under IIS can enable Single Sign-On to the Kallithea
    web interface from web browsers that can authenticate to the web server.
    (As an alternative to IIS, SSO is also possible with for example Apache and
    mod_sspi.)

    Mercurial and Git do however by default not support SSO on the client side
    and will still require some other kind of authentication.
    (An extension like hgssoauthentication_ might solve that.)

.. note::

    For the best security, it is strongly recommended to only host the site over
    a secure connection, e.g. using TLS.


Prerequisites
-------------

Apart from the normal requirements for Kallithea, it is also necessary to get an
ISAPI-WSGI bridge module, e.g. isapi-wsgi.


Installation
------------

The following assumes that your Kallithea is at ``c:\inetpub\kallithea``, and
will be served from the root of its own website. The changes to serve it in its
own virtual folder will be noted where appropriate.

Application pool
^^^^^^^^^^^^^^^^

Make sure that there is a unique application pool for the Kallithea application
with an identity that has read access to the Kallithea distribution.

The application pool does not need to be able to run any managed code. If you
are using a 32-bit Python installation, then you must enable 32-bit program in
the advanced settings for the application pool; otherwise Python will not be able
to run on the website and neither will Kallithea.

.. note::

    The application pool can be the same as an existing application pool,
    as long as the Kallithea requirements are met by the existing pool.

ISAPI handler
^^^^^^^^^^^^^

The ISAPI handler can be generated using::

    kallithea-cli iis-install -c my.ini --virtualdir=/

This will generate a ``dispatch.py`` file in the current directory that contains
the necessary components to finalize an installation into IIS. Once this file
has been generated, it is necessary to run the following command due to the way
that ISAPI-WSGI is made::

    python2 dispatch.py install

This accomplishes two things: generating an ISAPI compliant DLL file,
``_dispatch.dll``, and installing a script map handler into IIS for the
``--virtualdir`` specified above pointing to ``_dispatch.dll``.

The ISAPI handler is registered to all file extensions, so it will automatically
be the one handling all requests to the specified virtual directory. When the website starts
the ISAPI handler, it will start a thread pool managed wrapper around the
middleware WSGI handler that Kallithea runs within and each HTTP request to the
site will be processed through this logic henceforth.

Authentication with Kallithea using IIS authentication modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended way to handle authentication with Kallithea using IIS is to let
IIS handle all the authentication and just pass it to Kallithea.

.. note::

    As an alternative without SSO, you can also use LDAP authentication with
    Active Directory, see :ref:`ldap-setup`.

To move responsibility into IIS from Kallithea, we need to configure Kallithea
to let external systems handle authentication and then let Kallithea create the
user automatically. To do this, access the administration's authentication page
and enable the ``kallithea.lib.auth_modules.auth_container`` plugin. Once it is
added, enable it with the ``REMOTE_USER`` header and check *Clean username*.
Finally, save the changes on this page.

Switch to the administration's permissions page and disable anonymous access,
otherwise Kallithea will not attempt to use the authenticated user name. By
default, Kallithea will populate the list of users lazily as they log in. Either
disable external auth account activation and ensure that you pre-populate the
user database with an external tool, or set it to *Automatic activation of
external account*. Finally, save the changes.

The last necessary step is to enable the relevant authentication in IIS, e.g.
Windows authentication.


Troubleshooting
---------------

Typically, any issues in this setup will either be entirely in IIS or entirely
in Kallithea (or Kallithea's WSGI middleware). Consequently, two
different options for finding issues exist: IIS' failed request tracking which
is great at finding issues until they exist inside Kallithea, at which point the
ISAPI-WSGI wrapper above uses ``win32traceutil``, which is part of ``pywin32``.

In order to dump output from WSGI using ``win32traceutil`` it is sufficient to
type the following in a console window::

    python2 -m win32traceutil

and any exceptions occurring in the WSGI layer and below (i.e. in the Kallithea
application itself) that are uncaught, will be printed here complete with stack
traces, making it a lot easier to identify issues.


.. _hgssoauthentication: https://bitbucket.org/domruf/hgssoauthentication
