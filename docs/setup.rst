.. _setup:

=====
Setup
=====


Setting up Kallithea
--------------------

First, you will need to create a Kallithea configuration file. Run the
following command to do so::

    kallithea-cli config-create my.ini

This will create the file ``my.ini`` in the current directory. This
configuration file contains the various settings for Kallithea, e.g.
proxy port, email settings, usage of static files, cache, Celery
settings, and logging. Extra settings can be specified like::

    kallithea-cli config-create my.ini host=8.8.8.8 "[handler_console]" formatter=color_formatter

Next, you need to create the databases used by Kallithea. It is recommended to
use PostgreSQL or SQLite (default). If you choose a database other than the
default, ensure you properly adjust the database URL in your ``my.ini``
configuration file to use this other database. Kallithea currently supports
PostgreSQL, SQLite and MySQL databases. Create the database by running
the following command::

    kallithea-cli db-create -c my.ini

This will prompt you for a "root" path. This "root" path is the location where
Kallithea will store all of its repositories on the current machine. After
entering this "root" path ``db-create`` will also prompt you for a username
and password for the initial admin account which ``db-create`` sets
up for you.

The ``db-create`` values can also be given on the command line.
Example::

    kallithea-cli db-create -c my.ini --user=nn --password=secret --email=nn@example.com --repos=/srv/repos

The ``db-create`` command will create all needed tables and an
admin account. When choosing a root path you can either use a new
empty location, or a location which already contains existing
repositories. If you choose a location which contains existing
repositories Kallithea will add all of the repositories at the chosen
location to its database.  (Note: make sure you specify the correct
path to the root).

.. note:: the given path for Mercurial_ repositories **must** be write
          accessible for the application. It's very important since
          the Kallithea web interface will work without write access,
          but when trying to do a push it will fail with permission
          denied errors unless it has write access.

Finally, prepare the front-end by running::

    kallithea-cli front-end-build

You are now ready to use Kallithea. To run it simply execute::

    gearbox serve -c my.ini

- This command runs the Kallithea server. The web app should be available at
  http://127.0.0.1:5000. The IP address and port is configurable via the
  configuration file created in the previous step.
- Log in to Kallithea using the admin account created when running ``db-create``.
- The default permissions on each repository is read, and the owner is admin.
  Remember to update these if needed.
- In the admin panel you can toggle LDAP, anonymous, and permissions
  settings, as well as edit more advanced options on users and
  repositories.


Internationalization (i18n support)
-----------------------------------

The Kallithea web interface is automatically displayed in the user's preferred
language, as indicated by the browser. Thus, different users may see the
application in different languages. If the requested language is not available
(because the translation file for that language does not yet exist or is
incomplete), English is used.

If you want to disable automatic language detection and instead configure a
fixed language regardless of user preference, set ``i18n.enabled = false`` and
specify another language by setting ``i18n.lang`` in the Kallithea
configuration file.


Using Kallithea with SSH
------------------------

Kallithea supports repository access via SSH key based authentication.
This means:

- repository URLs like ``ssh://kallithea@example.com/name/of/repository``

- all network traffic for both read and write happens over the SSH protocol on
  port 22, without using HTTP/HTTPS nor the Kallithea WSGI application

- encryption and authentication protocols are managed by the system's ``sshd``
  process, with all users using the same Kallithea system user (e.g.
  ``kallithea``) when connecting to the SSH server, but with users' public keys
  in the Kallithea system user's `.ssh/authorized_keys` file granting each user
  sandboxed access to the repositories.

- users and admins can manage SSH public keys in the web UI

- in their SSH client configuration, users can configure how the client should
  control access to their SSH key - without passphrase, with passphrase, and
  optionally with passphrase caching in the local shell session (``ssh-agent``).
  This is standard SSH functionality, not something Kallithea provides or
  interferes with.

- network communication between client and server happens in a bidirectional
  stateful stream, and will in some cases be faster than HTTP/HTTPS with several
  stateless round-trips.

.. note:: At this moment, repository access via SSH has been tested on Unix
    only. Windows users that care about SSH are invited to test it and report
    problems, ideally contributing patches that solve these problems.

Users and admins can upload SSH public keys (e.g. ``.ssh/id_rsa.pub``) through
the web interface. The server's ``.ssh/authorized_keys`` file is automatically
maintained with an entry for each SSH key. Each entry will tell ``sshd`` to run
``kallithea-cli`` with the ``ssh-serve`` sub-command and the right Kallithea user ID
when encountering the corresponding SSH key.

To enable SSH repository access, Kallithea must be configured with the path to
the ``.ssh/authorized_keys`` file for the Kallithea user, and the path to the
``kallithea-cli`` command. Put something like this in the ``.ini`` file::

    ssh_enabled = true
    ssh_authorized_keys = /home/kallithea/.ssh/authorized_keys
    kallithea_cli_path = /srv/kallithea/venv/bin/kallithea-cli

The SSH service must be running, and the Kallithea user account must be active
(not necessarily with password access, but public key access must be enabled),
all file permissions must be set as sshd wants it, and ``authorized_keys`` must
be writeable by the Kallithea user.

.. note:: The ``authorized_keys`` file will be rewritten from scratch on
    each update. If it already exists with other data, Kallithea will not
    overwrite the existing ``authorized_keys``, and the server process will
    instead throw an exception. The system administrator thus cannot ssh
    directly to the Kallithea user but must use su/sudo from another account.

    If ``/home/kallithea/.ssh/`` (the directory of the path specified in the
    ``ssh_authorized_keys`` setting of the ``.ini`` file) does not exist as a
    directory, Kallithea will attempt to create it. If that path exists but is
    *not* a directory, or is not readable-writable-executable by the server
    process, the server process will raise an exception each time it attempts to
    write the ``authorized_keys`` file.

.. warning:: The handling of SSH access is steered directly by the command
    specified in the ``authorized_keys`` file. There is no interaction with the
    web UI.  Once SSH access is correctly configured and enabled, it will work
    regardless of whether the Kallithea web process is actually running. Hence,
    if you want to perform repository or server maintenance and want to fully
    disable all access to the repositories, disable SSH access by setting
    ``ssh_enabled = false`` in the correct ``.ini`` file (i.e. the ``.ini`` file
    specified in the ``authorized_keys`` file.)

The ``authorized_keys`` file can be updated manually with ``kallithea-cli
ssh-update-authorized-keys -c my.ini``. This command is not needed in normal
operation but is for example useful after changing SSH-related settings in the
``.ini`` file or renaming that file. (The path to the ``.ini`` file is used in
the generated ``authorized_keys`` file).


Setting up Whoosh full text search
----------------------------------

Kallithea provides full text search of repositories using `Whoosh`__.

.. __: https://whoosh.readthedocs.io/en/latest/

For an incremental index build, run::

    kallithea-cli index-create -c my.ini

For a full index rebuild, run::

    kallithea-cli index-create -c my.ini --full

The ``--repo-location`` option allows the location of the repositories to be overridden;
usually, the location is retrieved from the Kallithea database.

The ``--index-only`` option can be used to limit the indexed repositories to a comma-separated list::

    kallithea-cli index-create -c my.ini --index-only=vcs,kallithea

To keep your index up-to-date it is necessary to do periodic index builds;
for this, it is recommended to use a crontab entry. Example::

    0  3  *  *  *  /path/to/virtualenv/bin/kallithea-cli index-create -c /path/to/kallithea/my.ini

When using incremental mode (the default), Whoosh will check the last
modification date of each file and add it to be reindexed if a newer file is
available. The indexing daemon checks for any removed files and removes them
from index.

If you want to rebuild the index from scratch, you can use the ``-f`` flag as above,
or in the admin panel you can check the "build from scratch" checkbox.


Integration with issue trackers
-------------------------------

Kallithea provides a simple integration with issue trackers. It's possible
to define a regular expression that will match an issue ID in commit messages,
and have that replaced with a URL to the issue.

This is achieved with following three variables in the ini file::

    issue_pat = #(\d+)
    issue_server_link = https://issues.example.com/{repo}/issue/\1
    issue_sub =

``issue_pat`` is the regular expression describing which strings in
commit messages will be treated as issue references. The expression can/should
have one or more parenthesized groups that can later be referred to in
``issue_server_link`` and ``issue_sub`` (see below). If you prefer, named groups
can be used instead of simple parenthesized groups.

If the pattern should only match if it is preceded by whitespace, add the
following string before the actual pattern: ``(?:^|(?<=\s))``.
If the pattern should only match if it is followed by whitespace, add the
following string after the actual pattern: ``(?:$|(?=\s))``.
These expressions use lookbehind and lookahead assertions of the Python regular
expression module to avoid the whitespace to be part of the actual pattern,
otherwise the link text will also contain that whitespace.

Matched issue references are replaced with the link specified in
``issue_server_link``, in which any backreferences are resolved. Backreferences
can be ``\1``, ``\2``, ... or for named groups ``\g<groupname>``.
The special token ``{repo}`` is replaced with the full repository path
(including repository groups), while token ``{repo_name}`` is replaced with the
repository name (without repository groups).

The link text is determined by ``issue_sub``, which can be a string containing
backreferences to the groups specified in ``issue_pat``. If ``issue_sub`` is
empty, then the text matched by ``issue_pat`` is used verbatim.

The example settings shown above match issues in the format ``#<number>``.
This will cause the text ``#300`` to be transformed into a link:

.. code-block:: html

  <a href="https://issues.example.com/example_repo/issue/300">#300</a>

The following example transforms a text starting with either of 'pullrequest',
'pull request' or 'PR', followed by an optional space, then a pound character
(#) and one or more digits, into a link with the text 'PR #' followed by the
digits::

    issue_pat = (pullrequest|pull request|PR) ?#(\d+)
    issue_server_link = https://issues.example.com/\2
    issue_sub = PR #\2

The following example demonstrates how to require whitespace before the issue
reference in order for it to be recognized, such that the text ``issue#123`` will
not cause a match, but ``issue #123`` will::

    issue_pat = (?:^|(?<=\s))#(\d+)
    issue_server_link = https://issues.example.com/\1
    issue_sub =

If needed, more than one pattern can be specified by appending a unique suffix to
the variables. For example, also demonstrating the use of named groups::

    issue_pat_wiki = wiki-(?P<pagename>\S+)
    issue_server_link_wiki = https://wiki.example.com/\g<pagename>
    issue_sub_wiki = WIKI-\g<pagename>

With these settings, wiki pages can be referenced as wiki-some-id, and every
such reference will be transformed into:

.. code-block:: html

  <a href="https://wiki.example.com/some-id">WIKI-some-id</a>

Refer to the `Python regular expression documentation`_ for more details about
the supported syntax in ``issue_pat``, ``issue_server_link`` and ``issue_sub``.


Hook management
---------------

Hooks can be managed in similar way to that used in ``.hgrc`` files.
To manage hooks, choose *Admin > Settings > Hooks*.

The built-in hooks cannot be modified, though they can be enabled or disabled in the *VCS* section.

To add another custom hook simply fill in the first textbox with
``<name>.<hook_type>`` and the second with the hook path. Example hooks
can be found in ``kallithea.lib.hooks``.


Changing default encoding
-------------------------

By default, Kallithea uses UTF-8 encoding.
This is configurable as ``default_encoding`` in the .ini file.
This affects many parts in Kallithea including user names, filenames, and
encoding of commit messages. In addition Kallithea can detect if the ``chardet``
library is installed. If ``chardet`` is detected Kallithea will fallback to it
when there are encode/decode errors.

The Mercurial encoding is configurable as ``hgencoding``. It is similar to
setting the ``HGENCODING`` environment variable, but will override it.


Celery configuration
--------------------

Kallithea can use the distributed task queue system Celery_ to run tasks like
cloning repositories or sending emails.

Kallithea will in most setups work perfectly fine out of the box (without
Celery), executing all tasks in the web server process. Some tasks can however
take some time to run and it can be better to run such tasks asynchronously in
a separate process so the web server can focus on serving web requests.

For installation and configuration of Celery, see the `Celery documentation`_.
Note that Celery requires a message broker service like RabbitMQ_ (recommended)
or Redis_.

The use of Celery is configured in the Kallithea ini configuration file.
To enable it, simply set::

  use_celery = true

and add or change the ``celery.*`` and ``broker.*`` configuration variables.

Remember that the ini files use the format with '.' and not with '_' like
Celery. So for example setting `BROKER_HOST` in Celery means setting
`broker.host` in the configuration file.

To start the Celery process, run::

  kallithea-cli celery-run -c my.ini

Extra options to the Celery worker can be passed after ``--`` - see ``-- -h``
for more info.

.. note::
   Make sure you run this command from the same virtualenv, and with the same
   user that Kallithea runs.


HTTPS support
-------------

Kallithea will by default generate URLs based on the WSGI environment.

Alternatively, you can use some special configuration settings to control
directly which scheme/protocol Kallithea will use when generating URLs:

- With ``https_fixup = true``, the scheme will be taken from the
  ``X-Url-Scheme``, ``X-Forwarded-Scheme`` or ``X-Forwarded-Proto`` HTTP header
  (default ``http``).
- With ``force_https = true`` the default will be ``https``.
- With ``use_htsts = true``, Kallithea will set ``Strict-Transport-Security`` when using https.

.. _nginx_virtual_host:


Nginx virtual host example
--------------------------

Sample config for Nginx using proxy:

.. code-block:: nginx

    upstream kallithea {
        server 127.0.0.1:5000;
        # add more instances for load balancing
        #server 127.0.0.1:5001;
        #server 127.0.0.1:5002;
    }

    ## gist alias
    server {
       listen          443;
       server_name     gist.example.com;
       access_log      /var/log/nginx/gist.access.log;
       error_log       /var/log/nginx/gist.error.log;

       ssl on;
       ssl_certificate     gist.your.kallithea.server.crt;
       ssl_certificate_key gist.your.kallithea.server.key;

       ssl_session_timeout 5m;

       ssl_protocols SSLv3 TLSv1;
       ssl_ciphers DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:EDH-RSA-DES-CBC3-SHA:AES256-SHA:DES-CBC3-SHA:AES128-SHA:RC4-SHA:RC4-MD5;
       ssl_prefer_server_ciphers on;

       rewrite ^/(.+)$ https://kallithea.example.com/_admin/gists/$1;
       rewrite (.*)    https://kallithea.example.com/_admin/gists;
    }

    server {
       listen          443;
       server_name     kallithea.example.com
       access_log      /var/log/nginx/kallithea.access.log;
       error_log       /var/log/nginx/kallithea.error.log;

       ssl on;
       ssl_certificate     your.kallithea.server.crt;
       ssl_certificate_key your.kallithea.server.key;

       ssl_session_timeout 5m;

       ssl_protocols SSLv3 TLSv1;
       ssl_ciphers DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:EDH-RSA-DES-CBC3-SHA:AES256-SHA:DES-CBC3-SHA:AES128-SHA:RC4-SHA:RC4-MD5;
       ssl_prefer_server_ciphers on;

       ## uncomment root directive if you want to serve static files by nginx
       ## requires static_files = false in .ini file
       #root /srv/kallithea/kallithea/kallithea/public;
       include         /etc/nginx/proxy.conf;
       location / {
            try_files $uri @kallithea;
       }

       location @kallithea {
            proxy_pass      http://127.0.0.1:5000;
       }

    }

Here's the proxy.conf. It's tuned so it will not timeout on long
pushes or large pushes::

    proxy_redirect              off;
    proxy_set_header            Host $host;
    ## needed for container auth
    #proxy_set_header            REMOTE_USER $remote_user;
    #proxy_set_header            X-Forwarded-User $remote_user;
    proxy_set_header            X-Url-Scheme $scheme;
    proxy_set_header            X-Host $http_host;
    proxy_set_header            X-Real-IP $remote_addr;
    proxy_set_header            X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header            Proxy-host $proxy_host;
    proxy_buffering             off;
    proxy_connect_timeout       7200;
    proxy_send_timeout          7200;
    proxy_read_timeout          7200;
    proxy_buffers               8 32k;
    client_max_body_size        1024m;
    client_body_buffer_size     128k;
    large_client_header_buffers 8 64k;

.. _apache_virtual_host_reverse_proxy:


Apache virtual host reverse proxy example
-----------------------------------------

Here is a sample configuration file for Apache using proxy:

.. code-block:: apache

    <VirtualHost *:80>
            ServerName kallithea.example.com

            <Proxy *>
              # For Apache 2.4 and later:
              Require all granted

              # For Apache 2.2 and earlier, instead use:
              # Order allow,deny
              # Allow from all
            </Proxy>

            #important !
            #Directive to properly generate url (clone url) for Kallithea
            ProxyPreserveHost On

            #kallithea instance
            ProxyPass / http://127.0.0.1:5000/
            ProxyPassReverse / http://127.0.0.1:5000/

            #to enable https use line below
            #SetEnvIf X-Url-Scheme https HTTPS=1
    </VirtualHost>

Additional tutorial
http://pylonsbook.com/en/1.1/deployment.html#using-apache-to-proxy-requests-to-pylons

.. _apache_subdirectory:


Apache as subdirectory
----------------------

Apache subdirectory part:

.. code-block:: apache

    <Location /PREFIX >
      ProxyPass http://127.0.0.1:5000/PREFIX
      ProxyPassReverse http://127.0.0.1:5000/PREFIX
      SetEnvIf X-Url-Scheme https HTTPS=1
    </Location>

Besides the regular apache setup you will need to add the following line
into ``[app:main]`` section of your .ini file::

    filter-with = proxy-prefix

Add the following at the end of the .ini file::

    [filter:proxy-prefix]
    use = egg:PasteDeploy#prefix
    prefix = /PREFIX

then change ``PREFIX`` into your chosen prefix

.. _apache_mod_wsgi:


Apache with mod_wsgi
--------------------

Alternatively, Kallithea can be set up with Apache under mod_wsgi. For
that, you'll need to:

- Install mod_wsgi. If using a Debian-based distro, you can install
  the package libapache2-mod-wsgi::

    aptitude install libapache2-mod-wsgi

- Enable mod_wsgi::

    a2enmod wsgi

- Add global Apache configuration to tell mod_wsgi that Python only will be
  used in the WSGI processes and shouldn't be initialized in the Apache
  processes::

    WSGIRestrictEmbedded On

- Create a WSGI dispatch script, like the one below. Make sure you
  check that the paths correctly point to where you installed Kallithea
  and its Python Virtual Environment.

  .. code-block:: python

      import os
      os.environ['PYTHON_EGG_CACHE'] = '/srv/kallithea/.egg-cache'

      # sometimes it's needed to set the current dir
      os.chdir('/srv/kallithea/')

      import site
      site.addsitedir("/srv/kallithea/venv/lib/python2.7/site-packages")

      ini = '/srv/kallithea/my.ini'
      from logging.config import fileConfig
      fileConfig(ini, {'__file__': ini, 'here': '/srv/kallithea'})
      from paste.deploy import loadapp
      application = loadapp('config:' + ini)

  Or using proper virtualenv activation:

  .. code-block:: python

      activate_this = '/srv/kallithea/venv/bin/activate_this.py'
      execfile(activate_this, dict(__file__=activate_this))

      import os
      os.environ['HOME'] = '/srv/kallithea'

      ini = '/srv/kallithea/kallithea.ini'
      from logging.config import fileConfig
      fileConfig(ini, {'__file__': ini, 'here': '/srv/kallithea'})
      from paste.deploy import loadapp
      application = loadapp('config:' + ini)

- Add the necessary ``WSGI*`` directives to the Apache Virtual Host configuration
  file, like in the example below. Notice that the WSGI dispatch script created
  above is referred to with the ``WSGIScriptAlias`` directive.
  The default locale settings Apache provides for web services are often not
  adequate, with `C` as the default language and `ASCII` as the encoding.
  Instead, use the ``lang`` parameter of ``WSGIDaemonProcess`` to specify a
  suitable locale. See also the :ref:`overview` section and the
  `WSGIDaemonProcess documentation`_.

  Apache will by default run as a special Apache user, on Linux systems
  usually ``www-data`` or ``apache``. If you need to have the repositories
  directory owned by a different user, use the user and group options to
  WSGIDaemonProcess to set the name of the user and group.

  Once again, check that all paths are correctly specified.

  .. code-block:: apache

      WSGIDaemonProcess kallithea processes=5 threads=1 maximum-requests=100 \
          python-home=/srv/kallithea/venv lang=C.UTF-8
      WSGIProcessGroup kallithea
      WSGIScriptAlias / /srv/kallithea/dispatch.wsgi
      WSGIPassAuthorization On

  Or if using a dispatcher WSGI script with proper virtualenv activation:

  .. code-block:: apache

      WSGIDaemonProcess kallithea processes=5 threads=1 maximum-requests=100 lang=en_US.utf8
      WSGIProcessGroup kallithea
      WSGIScriptAlias / /srv/kallithea/dispatch.wsgi
      WSGIPassAuthorization On


Other configuration files
-------------------------

A number of `example init.d scripts`__ can be found in
the ``init.d`` directory of the Kallithea source.

.. __: https://kallithea-scm.org/repos/kallithea/files/tip/init.d/ .


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _Python regular expression documentation: https://docs.python.org/2/library/re.html
.. _Mercurial: https://www.mercurial-scm.org/
.. _Celery: http://celeryproject.org/
.. _Celery documentation: http://docs.celeryproject.org/en/latest/getting-started/index.html
.. _RabbitMQ: http://www.rabbitmq.com/
.. _Redis: http://redis.io/
.. _mercurial-server: http://www.lshift.net/mercurial-server.html
.. _PublishingRepositories: https://www.mercurial-scm.org/wiki/PublishingRepositories
.. _WSGIDaemonProcess documentation: https://modwsgi.readthedocs.io/en/develop/configuration-directives/WSGIDaemonProcess.html
