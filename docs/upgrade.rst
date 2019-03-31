.. _upgrade:

===================
Upgrading Kallithea
===================

This describes the process for upgrading Kallithea, independently of the
Kallithea installation method.

.. note::
    If you are upgrading from a RhodeCode installation, you must first
    install Kallithea 0.3.2 and follow the instructions in the 0.3.2
    README to perform a one-time conversion of the database from
    RhodeCode to Kallithea, before upgrading to the latest version
    of Kallithea.


1. Stop the Kallithea web application
-------------------------------------

This step depends entirely on the web server software used to serve
Kallithea, but in any case, Kallithea should not be running during
the upgrade.

.. note::
    If you're using Celery, make sure you stop all instances during the
    upgrade.


2. Create a backup of both database and configuration
-----------------------------------------------------

You are of course strongly recommended to make backups regularly, but it
is *especially* important to make a full database and configuration
backup before performing a Kallithea upgrade.

Back up your configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Make a copy of your Kallithea configuration (``.ini``) file.

If you are using :ref:`rcextensions <customization>`, you should also
make a copy of the entire ``rcextensions`` directory.

Back up your database
^^^^^^^^^^^^^^^^^^^^^

If using SQLite, simply make a copy of the Kallithea database (``.db``)
file.

If using PostgreSQL, please consult the documentation for the ``pg_dump``
utility.

If using MySQL, please consult the documentation for the ``mysqldump``
utility.

Look for ``sqlalchemy.url`` in your configuration file to determine
database type, settings, location, etc. If you were running Kallithea 0.3.x or
older, this was ``sqlalchemy.db1.url``.


3. Activate or recreate the Kallithea virtual environment (if any)
------------------------------------------------------------------

.. note::
    If you did not install Kallithea in a virtual environment, skip this step.

For major upgrades, e.g. from 0.3.x to 0.4.x, it is recommended to create a new
virtual environment, rather than reusing the old. For minor upgrades, e.g.
within the 0.4.x range, this is not really necessary (but equally fine).

To create a new virtual environment, please refer to the appropriate
installation page for details. After creating and activating the new virtual
environment, proceed with the rest of the upgrade process starting from the next
section.

To reuse the same virtual environment, first activate it, then verify that you
are using the correct environment by running::

    pip freeze

This will list all packages installed in the current environment. If
Kallithea isn't listed, deactivate the environment and then activate the correct
one, or recreate a new environment. See the appropriate installation page for
details.


4. Install new version of Kallithea
-----------------------------------

Please refer to the instructions for the installation method you
originally used to install Kallithea.

If you originally installed using pip, it is as simple as::

    pip install --upgrade kallithea

If you originally installed from version control, assuming you did not make
private changes (in which case you should adapt the instructions accordingly)::

    cd my-kallithea-clone
    hg parent   # make a note of the original revision
    hg pull
    hg update
    hg parent   # make a note of the new revision
    pip install --upgrade -e .

.. _upgrade_config:


5. Upgrade your configuration
-----------------------------

Run the following command to create a new configuration (``.ini``) file::

    kallithea-cli config-create new.ini

Then compare it with your old config file and copy over the required
configuration values from the old to the new file.

.. note::
    Please always make sure your ``.ini`` files are up to date. Errors
    can often be caused by missing parameters added in new versions.

.. _upgrade_db:


6. Upgrade your database
------------------------

.. note::
    If you are *downgrading* Kallithea, you should perform the database
    migration step *before* installing the older version. (That is,
    always perform migrations using the most recent of the two versions
    you're migrating between.)

First, run the following command to see your current database version::

    alembic -c new.ini current

Typical output will be something like "9358dc3d6828 (head)", which is
the current Alembic database "revision ID". Write down the entire output
for troubleshooting purposes.

The output will be empty if you're upgrading from Kallithea 0.3.x or
older. That's expected. If you get an error that the config file was not
found or has no ``[alembic]`` section, see the next section.

Next, if you are performing an *upgrade*: Run the following command to
upgrade your database to the current Kallithea version::

    alembic -c new.ini upgrade head

If you are performing a *downgrade*: Run the following command to
downgrade your database to the given version::

    alembic -c new.ini downgrade 0.4

Alembic will show the necessary migrations (if any) as it executes them.
If no "ERROR" is displayed, the command was successful.

Should an error occur, the database may be "stranded" half-way
through the migration, and you should restore it from backup.

Enabling old Kallithea config files for Alembic use
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Kallithea configuration files created before the introduction of Alembic
(i.e. predating Kallithea 0.4) need to be updated for use with Alembic.
Without this, Alembic will fail with an error like this::

    FAILED: No config file 'my.ini' found, or file has no '[alembic]' section

.. note::
    If you followed this upgrade guide correctly, you will have created a
    new configuration file in section :ref:`Upgrading your configuration
    <upgrade_config>`. When calling Alembic, make
    sure to use this new config file. In this case, you should not get any
    errors and the below manual steps should not be needed.

If Alembic complains specifically about a missing ``alembic.ini``, it is
likely because you did not specify a config file using the ``-c`` option.
On the other hand, if the mentioned config file actually exists, you
need to append the following lines to it::

    [alembic]
    script_location = kallithea:alembic

Your config file should now work with Alembic.


7. Prepare the front-end
------------------------

Starting with Kallithea 0.4, external front-end dependencies are no longer
shipped but need to be downloaded and/or generated at installation time. Run the
following command::

    kallithea-cli front-end-build


8. Rebuild the Whoosh full-text index
-------------------------------------

It is recommended that you rebuild the Whoosh index after upgrading since
new Whoosh versions can introduce incompatible index changes.


9. Start the Kallithea web application
--------------------------------------

This step once again depends entirely on the web server software used to
serve Kallithea.

If you were running Kallithea 0.3.x or older and were using ``paster serve
my.ini`` before, then the corresponding command in Kallithea 0.4 and later is::

    gearbox serve -c new.ini

Before starting the new version of Kallithea, you may find it helpful to
clear out your log file so that new errors are readily apparent.

.. note::
    If you're using Celery, make sure you restart all instances of it after
    upgrade.


10. Update Git repository hooks
-------------------------------

It is possible that an upgrade involves changes to the Git hooks installed by
Kallithea. As these hooks are created inside the repositories on the server
filesystem, they are not updated automatically when upgrading Kallithea itself.

To update the hooks of your Git repositories:

* Go to *Admin > Settings > Remap and Rescan*
* Select the checkbox *Install Git hooks*
* Click the button *Rescan repositories*

.. note::
    Kallithea does not use hooks on Mercurial repositories. This step is thus
    not necessary if you only have Mercurial repositories.


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
