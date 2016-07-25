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

Look for ``sqlalchemy.db1.url`` in your configuration file to determine
database type, settings, location, etc.


3. Activate the Kallithea virtual environment (if any)
------------------------------------------------------

Verify that you are using the Python environment that you originally
installed Kallithea in by running::

    pip freeze

This will list all packages installed in the current environment. If
Kallithea isn't listed, activate the correct virtual environment.
See the appropriate installation page for details.


4. Install new version of Kallithea
-----------------------------------

Please refer to the instructions for the installation method you
originally used to install Kallithea.

If you originally installed using pip, it is as simple as::

    pip install --upgrade kallithea

If you originally installed from version control, it is as simple as::

    cd my-kallithea-clone
    hg pull -u
    pip install -e .


5. Upgrade your configuration
-----------------------------

Run the following command to upgrade your configuration (``.ini``) file::

    paster make-config Kallithea my.ini

This will display any changes made by the new version of Kallithea to your
current configuration, and attempt an automatic merge. It is recommended
that you check the contents after the merge.

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

    alembic -c my.ini current

Typical output will be something like "9358dc3d6828 (head)", which is
the current Alembic database "revision ID". Write down the entire output
for troubleshooting purposes.

The output will be empty if you're upgrading from Kallithea 0.3.x or
older. That's expected. If you get an error that the config file was not
found or has no ``[alembic]`` section, see the next section.

Next, if you are performing an *upgrade*: Run the following command to
upgrade your database to the current Kallithea version::

    alembic -c my.ini upgrade head

If you are performing a *downgrade*: Run the following command to
downgrade your database to the given version::

    alembic -c my.ini downgrade 0.4

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

If Alembic complains specifically about a missing ``alembic.ini``, it is
likely because you did not specify a config file using the ``-c`` option.
On the other hand, if the mentioned config file actually exists, you
need to append the following lines to it::

    [alembic]
    script_location = kallithea:alembic

Your config file should now work with Alembic.


7. Rebuild the Whoosh full-text index
-------------------------------------

It is recommended that you rebuild the Whoosh index after upgrading since
new Whoosh versions can introduce incompatible index changes.


8. Start the Kallithea web application
--------------------------------------

This step once again depends entirely on the web server software used to
serve Kallithea.

Before starting the new version of Kallithea, you may find it helpful to
clear out your log file so that new errors are readily apparent.

.. note::
    If you're using Celery, make sure you restart all instances of it after
    upgrade.


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
