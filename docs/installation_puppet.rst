.. _installation_puppet:

===================================
Installation and setup using Puppet
===================================

The whole installation and setup process of Kallithea can be simplified by
using Puppet and the `rauch/kallithea
<https://forge.puppetlabs.com/rauch/kallithea>`_ Puppet module. This is
especially useful for getting started quickly, without having to deal with all
the Python specialities.

.. note:: The following instructions assume you are not familiar with Puppet at
          all. If this is not the case, you should probably skip directly to the
          `Kallithea Puppet module documentation
          <https://forge.puppetlabs.com/rauch/kallithea#puppet-kallithea>`_.


Installing Puppet
-----------------

This installation variant requires a Unix/Linux type server with Puppet 3.0+
installed. Many major distributions have Puppet in their standard repositories.
Thus, you will probably be ready to go by running, e.g. ``apt-get install
puppet`` or ``yum install puppet``, depending on your distro's favoured package
manager. Afterwards, check the Puppet version by running ``puppet --version``
and ensure you have at least 3.0.

If your distribution does not provide Puppet packages or you need a
newer version, please see the `Puppet Reference Manual
<https://docs.puppetlabs.com/puppet/4.2/reference/install_linux.html>`_ for
instructions on how to install Puppet on your target platform.


Installing the Puppet module
----------------------------

To install the latest version of the Kallithea Puppet module from the Puppet
Forge, run the following as ``root``:

.. code-block:: bash

    puppet module install rauch/kallithea

This will install both the Kallithea Puppet module and its dependency modules.

.. warning::  Be aware that Puppet can do all kinds of things to your systems.
              Third-party modules (like the ``kallithea`` module) may run
              arbitrary commands on your system (most of the time as the
              ``root`` user), so do not apply them on production machines if
              you don't know what you are doing. Instead, use a test system
              (e.g. a virtual machine) for evaluation purposes.


Applying the module
-------------------

To trigger the actual installation process, we have to *apply* the
``kallithea`` Puppet class, which is provided by the module we have just
installed, to our system. For this, create a file named e.g. ``kallithea.pp``,
a *Puppet manifest*, with the following content:

.. _simple_manifest:
.. code-block:: puppet

    class { 'kallithea':
      seed_db    => true,
      manage_git => true,
    }

To apply the manifest, simply run the following (preferably as root):

.. code-block:: bash

    puppet apply kallithea.pp

This will basically run through the usual Kallithea :ref:`installation` and
:ref:`setup` steps, as documented. Consult the module documentation for details
on `what the module affects
<https://forge.puppetlabs.com/rauch/kallithea#what-kallithea-affects>`_. You
can also do a *dry run* by adding the ``--noop`` option to the command.


Using parameters for customizing the setup process
--------------------------------------------------

The ``kallithea`` Puppet class provides a number of `parameters
<https://forge.puppetlabs.com/rauch/kallithea#class-kallithea>`_ for
customizing the setup process. You have seen the usage of the ``seed_db``
parameter in the :ref:`example above <simple_manifest>`, but there are more.
For example, you can specify the installation directory, the name of the user
under which Kallithea gets installed, the initial admin password, etc.
Notably, you can provide arbitrary modifications to Kallithea's configuration
file by means of the ``config_hash`` parameter.

Parameters, which have not been set explicitly, will be set to default values,
which are defined inside the ``kallithea`` Puppet module. For example, if you
just stick to the defaults as in the :ref:`example above <simple_manifest>`,
you will end up with a Kallithea instance, which

- is installed in ``/srv/kallithea``, owned by the user ``kallithea``
- uses the Kallithea default configuration
- uses the admin user ``admin`` with password ``adminpw``
- is started automatically and enabled on boot

As of Kallithea 0.3.0, this in particular means that Kallithea will use an
SQLite database and listen on ``http://localhost:5000``.

See also the `full parameters list
<https://forge.puppetlabs.com/rauch/kallithea#class-kallithea>`_ for more
information.


Making your Kallithea instance publicly available
-------------------------------------------------

If you followed the instructions above, the Kallithea instance will be
listening on ``http://localhost:5000`` and therefore not publicly available.
There are several ways to change this.

The direct way
^^^^^^^^^^^^^^

The simplest setup is to instruct Kallithea to listen on another IP address
and/or port by using the ``config_hash`` parameter of the Kallithea Puppet
class. For example, assume we want to listen on all interfaces on port 80:

.. code-block:: puppet

    class { 'kallithea':
      seed_db => true,
      config_hash => {
        "server:main" => {
          'host' => '0.0.0.0',
          'port' => '80',
        }
      }
    }

Using Apache as reverse proxy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In a more advanced setup, you might instead want use a full-blown web server
like Apache HTTP Server as the public web server, configured such that requests
are internally forwarded to the local Kallithea instance (a so called *reverse
proxy setup*). This can be easily done with Puppet as well:

First, install the `puppetlabs/apache
<https://forge.puppetlabs.com/puppetlabs/apache>`_ Puppet module as above by running the following as root:

.. code-block:: bash

    puppet module install puppetlabs/apache

Then, append the following to your manifest:

.. code-block:: puppet

    include apache

    apache::vhost { 'kallithea.example.com':
      docroot             => '/var/www/html',
      manage_docroot      => false,
      port                => 80,
      proxy_preserve_host => true,
      proxy_pass          => [
        {
          path => '/',
          url  => 'http://localhost:5000/',
        },
      ],
    }

Applying the resulting manifest will install the Apache web server and setup a
virtual host acting as a reverse proxy for your local Kallithea instance.
