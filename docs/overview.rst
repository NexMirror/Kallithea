.. _overview:

=====================
Installation overview
=====================

Some overview and some details that can help understanding the options when
installing Kallithea.


Python environment
------------------

**Kallithea** is written entirely in Python_ and requires Python version
2.7 or higher. Python 3.x is currently not supported.

Given a Python installation, there are different ways of providing the
environment for running Python applications. Each of them pretty much
corresponds to a ``site-packages`` directory somewhere where packages can be
installed.

Kallithea itself can be run from source or be installed, but even when running
from source, there are some dependencies that must be installed in the Python
environment used for running Kallithea.

- Packages *could* be installed in Python's ``site-packages`` directory ... but
  that would require running pip_ as root and it would be hard to uninstall or
  upgrade and is probably not a good idea unless using a package manager.

- Packages could also be installed in ``~/.local`` ... but that is probably
  only a good idea if using a dedicated user per application or instance.

- Finally, it can be installed in a virtualenv_. That is a very lightweight
  "container" where each Kallithea instance can get its own dedicated and
  self-contained virtual environment.

We recommend using virtualenv for installing Kallithea.


Locale environment
------------------

In order to ensure a correct functioning of Kallithea with respect to non-ASCII
characters in user names, file paths, commit messages, etc., it is very
important that Kallithea is run with a correct `locale` configuration.

On Unix, environment variables like ``LANG`` or ``LC_ALL`` can specify a language (like
``en_US``) and encoding (like ``UTF-8``) to use for code points outside the ASCII
range. The flexibility of supporting multiple encodings of Unicode has the flip
side of having to specify which encoding to use - especially for Mercurial.

It depends on the OS distribution and system configuration which locales are
available. For example, some Docker containers based on Debian default to only
supporting the ``C`` language, while other Linux environments have ``en_US`` but not
``C``. The ``locale -a`` command will show which values are available on the
current system. Regardless of the actual language, you should normally choose a
locale that has the ``UTF-8`` encoding (note that spellings ``utf8``, ``utf-8``,
``UTF8``, ``UTF-8`` are all referring to the same thing)

For technical reasons, the locale configuration **must** be provided in the
environment in which Kallithea runs - it cannot be specified in the ``.ini`` file.
How to practically do this depends on the web server that is used and the way it
is started. For example, gearbox is often started by a normal user, either
manually or via a script. In this case, the required locale environment
variables can be provided directly in that user's environment or in the script.
However, web servers like Apache are often started at boot via an init script or
service file. Modifying the environment for this case would thus require
root/administrator privileges. Moreover, that environment would dictate the
settings for all web services running under that web server, Kallithea being
just one of them. Specifically in the case of Apache with ``mod_wsgi``, the
locale can be set for a specific service in its ``WSGIDaemonProcess`` directive,
using the ``lang`` parameter.


Installation methods
--------------------

Kallithea must be installed on a server. Kallithea is installed in a Python
environment so it can use packages that are installed there and make itself
available for other packages.

Two different cases will pretty much cover the options for how it can be
installed.

- The Kallithea source repository can be cloned and used -- it is kept stable and
  can be used in production. The Kallithea maintainers use the development
  branch in production. The advantage of installation from source and regularly
  updating it is that you take advantage of the most recent improvements. Using
  it directly from a DVCS also means that it is easy to track local customizations.

  Running ``pip install -e .`` in the source will use pip to install the
  necessary dependencies in the Python environment and create a
  ``.../site-packages/Kallithea.egg-link`` file there that points at the Kallithea
  source.

- Kallithea can also be installed from ready-made packages using a package manager.
  The official released versions are available on PyPI_ and can be downloaded and
  installed with all dependencies using ``pip install kallithea``.

  With this method, Kallithea is installed in the Python environment as any
  other package, usually as a ``.../site-packages/Kallithea-X-py2.7.egg/``
  directory with Python files and everything else that is needed.

  (``pip install kallithea`` from a source tree will do pretty much the same
  but build the Kallithea package itself locally instead of downloading it.)

.. note::
   Kallithea includes front-end code that needs to be processed first.
   The tool npm_ is used to download external dependencies and orchestrate the
   processing. The ``npm`` binary must thus be available.


Web server
----------

Kallithea is (primarily) a WSGI_ application that must be run from a web
server that serves WSGI applications over HTTP.

Kallithea itself is not serving HTTP (or HTTPS); that is the web server's
responsibility. Kallithea does however need to know its own user facing URL
(protocol, address, port and path) for each HTTP request. Kallithea will
usually use its own HTML/cookie based authentication but can also be configured
to use web server authentication.

There are several web server options:

- Kallithea uses the Gearbox_ tool as command line interface. Gearbox provides
  ``gearbox serve`` as a convenient way to launch a Python WSGI / web server
  from the command line. That is perfect for development and evaluation.
  Actual use in production might have different requirements and need extra
  work to make it manageable as a scalable system service.

  Gearbox comes with its own built-in web server but Kallithea defaults to use
  Waitress_. Gunicorn_ is also an option. These web servers have different
  limited feature sets.

  The web server used by ``gearbox`` is configured in the ``.ini`` file passed
  to it. The entry point for the WSGI application is configured
  in ``setup.py`` as ``kallithea.config.middleware:make_app``.

- `Apache httpd`_ can serve WSGI applications directly using mod_wsgi_ and a
  simple Python file with the necessary configuration. This is a good option if
  Apache is an option.

- uWSGI_ is also a full web server with built-in WSGI module.

- IIS_ can also server WSGI applications directly using isapi-wsgi_.

- A `reverse HTTP proxy <https://en.wikipedia.org/wiki/Reverse_proxy>`_
  can be put in front of another web server which has WSGI support.
  Such a layered setup can be complex but might in some cases be the right
  option, for example to standardize on one internet-facing web server, to add
  encryption or special authentication or for other security reasons, to
  provide caching of static files, or to provide load balancing or fail-over.
  Nginx_, Varnish_ and HAProxy_ are often used for this purpose, often in front
  of a ``gearbox serve`` that somehow is wrapped as a service.

The best option depends on what you are familiar with and the requirements for
performance and stability. Also, keep in mind that Kallithea mainly is serving
dynamically generated pages from a relatively slow Python process. Kallithea is
also often used inside organizations with a limited amount of users and thus no
continuous hammering from the internet.


.. _Python: http://www.python.org/
.. _Gunicorn: http://gunicorn.org/
.. _Waitress: http://waitress.readthedocs.org/en/latest/
.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _Gearbox: http://turbogears.readthedocs.io/en/latest/turbogears/gearbox.html
.. _PyPI: https://pypi.python.org/pypi
.. _Apache httpd: http://httpd.apache.org/
.. _mod_wsgi: https://code.google.com/p/modwsgi/
.. _isapi-wsgi: https://github.com/hexdump42/isapi-wsgi
.. _uWSGI: https://uwsgi-docs.readthedocs.org/en/latest/
.. _nginx: http://nginx.org/en/
.. _iis: http://en.wikipedia.org/wiki/Internet_Information_Services
.. _pip: http://en.wikipedia.org/wiki/Pip_%28package_manager%29
.. _WSGI: http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
.. _HAProxy: http://www.haproxy.org/
.. _Varnish: https://www.varnish-cache.org/
.. _npm: https://www.npmjs.com/
