.. _authentication:

====================
Authentication setup
====================

Users can be authenticated in different ways. By default, Kallithea
uses its internal user database. Alternative authentication
methods include LDAP, PAM, Crowd, and container-based authentication.

.. _ldap-setup:


LDAP Authentication
-------------------

Kallithea supports LDAP authentication. In order
to use LDAP, you have to install the python-ldap_ package. This package is
available via PyPI, so you can install it by running::

    pip install python-ldap

.. note:: ``python-ldap`` requires some libraries to be installed on
          your system, so before installing it check that you have at
          least the ``openldap`` and ``sasl`` libraries.

Choose *Admin > Authentication*, click the ``kallithea.lib.auth_modules.auth_ldap`` button
and then *Save*, to enable the LDAP plugin and configure its settings.

Here's a typical LDAP setup::

 Connection settings
 Enable LDAP          = checked
 Host                 = host.example.com
 Account              = <account>
 Password             = <password>
 Connection Security  = LDAPS
 Certificate Checks   = DEMAND

 Search settings
 Base DN              = CN=users,DC=host,DC=example,DC=org
 LDAP Filter          = (&(objectClass=user)(!(objectClass=computer)))
 LDAP Search Scope    = SUBTREE

 Attribute mappings
 Login Attribute      = uid
 First Name Attribute = firstName
 Last Name Attribute  = lastName
 Email Attribute      = mail

If your user groups are placed in an Organisation Unit (OU) structure, the Search Settings configuration differs::

 Search settings
 Base DN              = DC=host,DC=example,DC=org
 LDAP Filter          = (&(memberOf=CN=your user group,OU=subunit,OU=unit,DC=host,DC=example,DC=org)(objectClass=user))
 LDAP Search Scope    = SUBTREE

.. _enable_ldap:

Enable LDAP : required
    Whether to use LDAP for authenticating users.

.. _ldap_host:

Host : required
    LDAP server hostname or IP address. Can be also a comma separated
    list of servers to support LDAP fail-over.

.. _Port:

Port : optional
    Defaults to 389 for PLAIN un-encrypted LDAP and START_TLS.
    Defaults to 636 for LDAPS.

.. _ldap_account:

Account : optional
    Only required if the LDAP server does not allow anonymous browsing of
    records.  This should be a special account for record browsing.  This
    will require `LDAP Password`_ below.

.. _LDAP Password:

Password : optional
    Only required if the LDAP server does not allow anonymous browsing of
    records.

.. _Enable LDAPS:

Connection Security : required
    Defines the connection to LDAP server

    PLAIN
        Plain unencrypted LDAP connection.
        This will by default use `Port`_ 389.

    LDAPS
        Use secure LDAPS connections according to `Certificate
        Checks`_ configuration.
        This will by default use `Port`_ 636.

    START_TLS
        Use START TLS according to `Certificate Checks`_ configuration on an
        apparently "plain" LDAP connection.
        This will by default use `Port`_ 389.

.. _Certificate Checks:

Certificate Checks : optional
    How SSL certificates verification is handled -- this is only useful when
    `Enable LDAPS`_ is enabled.  Only DEMAND or HARD offer full SSL security
    with mandatory certificate validation, while the other options are
    susceptible to man-in-the-middle attacks.

    NEVER
        A serve certificate will never be requested or checked.

    ALLOW
        A server certificate is requested.  Failure to provide a
        certificate or providing a bad certificate will not terminate the
        session.

    TRY
        A server certificate is requested.  Failure to provide a
        certificate does not halt the session; providing a bad certificate
        halts the session.

    DEMAND
        A server certificate is requested and must be provided and
        authenticated for the session to proceed.

    HARD
        The same as DEMAND.

.. _Custom CA Certificates:

Custom CA Certificates : optional
    Directory used by OpenSSL to find CAs for validating the LDAP server certificate.
    Python 2.7.10 and later default to using the system certificate store, and
    this should thus not be necessary when using certificates signed by a CA
    trusted by the system.
    It can be set to something like `/etc/openldap/cacerts` on older systems or
    if using self-signed certificates.

.. _Base DN:

Base DN : required
    The Distinguished Name (DN) where searches for users will be performed.
    Searches can be controlled by `LDAP Filter`_ and `LDAP Search Scope`_.

.. _LDAP Filter:

LDAP Filter : optional
    A LDAP filter defined by RFC 2254.  This is more useful when `LDAP
    Search Scope`_ is set to SUBTREE.  The filter is useful for limiting
    which LDAP objects are identified as representing Users for
    authentication.  The filter is augmented by `Login Attribute`_ below.
    This can commonly be left blank.

.. _LDAP Search Scope:

LDAP Search Scope : required
    This limits how far LDAP will search for a matching object.

    BASE
        Only allows searching of `Base DN`_ and is usually not what you
        want.

    ONELEVEL
        Searches all entries under `Base DN`_, but not Base DN itself.

    SUBTREE
        Searches all entries below `Base DN`_, but not Base DN itself.
        When using SUBTREE `LDAP Filter`_ is useful to limit object
        location.

.. _Login Attribute:

Login Attribute : required
    The LDAP record attribute that will be matched as the USERNAME or
    ACCOUNT used to connect to Kallithea.  This will be added to `LDAP
    Filter`_ for locating the User object.  If `LDAP Filter`_ is specified as
    "LDAPFILTER", `Login Attribute`_ is specified as "uid" and the user has
    connected as "jsmith" then the `LDAP Filter`_ will be augmented as below
    ::

        (&(LDAPFILTER)(uid=jsmith))

.. _ldap_attr_firstname:

First Name Attribute : required
    The LDAP record attribute which represents the user's first name.

.. _ldap_attr_lastname:

Last Name Attribute : required
    The LDAP record attribute which represents the user's last name.

.. _ldap_attr_email:

Email Attribute : required
    The LDAP record attribute which represents the user's email address.

If all data are entered correctly, and python-ldap_ is properly installed
users should be granted access to Kallithea with LDAP accounts.  At this
time user information is copied from LDAP into the Kallithea user database.
This means that updates of an LDAP user object may not be reflected as a
user update in Kallithea.

If You have problems with LDAP access and believe You entered correct
information check out the Kallithea logs, any error messages sent from LDAP
will be saved there.

Active Directory
^^^^^^^^^^^^^^^^

Kallithea can use Microsoft Active Directory for user authentication.  This
is done through an LDAP or LDAPS connection to Active Directory.  The
following LDAP configuration settings are typical for using Active
Directory ::

 Base DN              = OU=SBSUsers,OU=Users,OU=MyBusiness,DC=v3sys,DC=local
 Login Attribute      = sAMAccountName
 First Name Attribute = givenName
 Last Name Attribute  = sn
 Email Attribute     = mail

All other LDAP settings will likely be site-specific and should be
appropriately configured.


Authentication by container or reverse-proxy
--------------------------------------------

Kallithea supports delegating the authentication
of users to its WSGI container, or to a reverse-proxy server through which all
clients access the application.

When these authentication methods are enabled in Kallithea, it uses the
username that the container/proxy (Apache or Nginx, etc.) provides and doesn't
perform the authentication itself. The authorization, however, is still done by
Kallithea according to its settings.

When a user logs in for the first time using these authentication methods,
a matching user account is created in Kallithea with default permissions. An
administrator can then modify it using Kallithea's admin interface.

It's also possible for an administrator to create accounts and configure their
permissions before the user logs in for the first time, using the :ref:`create-user` API.

Container-based authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In a container-based authentication setup, Kallithea reads the user name from
the ``REMOTE_USER`` server variable provided by the WSGI container.

After setting up your container (see :ref:`apache_mod_wsgi`), you'll need
to configure it to require authentication on the location configured for
Kallithea.

Proxy pass-through authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In a proxy pass-through authentication setup, Kallithea reads the user name
from the ``X-Forwarded-User`` request header, which should be configured to be
sent by the reverse-proxy server.

After setting up your proxy solution (see :ref:`apache_virtual_host_reverse_proxy`,
:ref:`apache_subdirectory` or :ref:`nginx_virtual_host`), you'll need to
configure the authentication and add the username in a request header named
``X-Forwarded-User``.

For example, the following config section for Apache sets a subdirectory in a
reverse-proxy setup with basic auth:

.. code-block:: apache

    <Location /someprefix>
      ProxyPass http://127.0.0.1:5000/someprefix
      ProxyPassReverse http://127.0.0.1:5000/someprefix
      SetEnvIf X-Url-Scheme https HTTPS=1

      AuthType Basic
      AuthName "Kallithea authentication"
      AuthUserFile /srv/kallithea/.htpasswd
      Require valid-user

      RequestHeader unset X-Forwarded-User

      RewriteEngine On
      RewriteCond %{LA-U:REMOTE_USER} (.+)
      RewriteRule .* - [E=RU:%1]
      RequestHeader set X-Forwarded-User %{RU}e
    </Location>

Setting metadata in container/reverse-proxy
"""""""""""""""""""""""""""""""""""""""""""
When a new user account is created on the first login, Kallithea has no information about
the user's email and full name. So you can set some additional request headers like in the
example below. In this example the user is authenticated via Kerberos and an Apache
mod_python fixup handler is used to get the user information from a LDAP server. But you
could set the request headers however you want.

.. code-block:: apache

    <Location /someprefix>
      ProxyPass http://127.0.0.1:5000/someprefix
      ProxyPassReverse http://127.0.0.1:5000/someprefix
      SetEnvIf X-Url-Scheme https HTTPS=1

      AuthName "Kerberos Login"
      AuthType Kerberos
      Krb5Keytab /etc/apache2/http.keytab
      KrbMethodK5Passwd off
      KrbVerifyKDC on
      Require valid-user

      PythonFixupHandler ldapmetadata

      RequestHeader set X_REMOTE_USER %{X_REMOTE_USER}e
      RequestHeader set X_REMOTE_EMAIL %{X_REMOTE_EMAIL}e
      RequestHeader set X_REMOTE_FIRSTNAME %{X_REMOTE_FIRSTNAME}e
      RequestHeader set X_REMOTE_LASTNAME %{X_REMOTE_LASTNAME}e
    </Location>

.. code-block:: python

    from mod_python import apache
    import ldap

    LDAP_SERVER = "ldaps://server.mydomain.com:636"
    LDAP_USER = ""
    LDAP_PASS = ""
    LDAP_ROOT = "dc=mydomain,dc=com"
    LDAP_FILTER = "sAMAccountName=%s"
    LDAP_ATTR_LIST = ['sAMAccountName','givenname','sn','mail']

    def fixuphandler(req):
        if req.user is None:
            # no user to search for
            return apache.OK
        else:
            try:
                if('\\' in req.user):
                    username = req.user.split('\\')[1]
                elif('@' in req.user):
                    username = req.user.split('@')[0]
                else:
                    username = req.user
                l = ldap.initialize(LDAP_SERVER)
                l.simple_bind_s(LDAP_USER, LDAP_PASS)
                r = l.search_s(LDAP_ROOT, ldap.SCOPE_SUBTREE, LDAP_FILTER % username, attrlist=LDAP_ATTR_LIST)

                req.subprocess_env['X_REMOTE_USER'] = username
                req.subprocess_env['X_REMOTE_EMAIL'] = r[0][1]['mail'][0].lower()
                req.subprocess_env['X_REMOTE_FIRSTNAME'] = "%s" % r[0][1]['givenname'][0]
                req.subprocess_env['X_REMOTE_LASTNAME'] = "%s" % r[0][1]['sn'][0]
            except Exception, e:
                apache.log_error("error getting data from ldap %s" % str(e), apache.APLOG_ERR)

            return apache.OK

.. note::
   If you enable proxy pass-through authentication, make sure your server is
   only accessible through the proxy. Otherwise, any client would be able to
   forge the authentication header and could effectively become authenticated
   using any account of their liking.


.. _python-ldap: http://www.python-ldap.org/
