=======================
Database schema changes
=======================

Kallithea uses Alembic for :ref:`database migrations <upgrade_db>`
(upgrades and downgrades).

If you are developing a Kallithea feature that requires database schema
changes, you should make a matching Alembic database migration script:

1. :ref:`Create a Kallithea configuration and database <setup>` for testing
   the migration script, or use existing ``development.ini`` setup.

   Ensure that this database is up to date with the latest database
   schema *before* the changes you're currently developing. (Do not
   create the database while your new schema changes are applied.)

2. Create a separate throwaway configuration for iterating on the actual
   database changes::

    kallithea-cli config-create temp.ini

   Edit the file to change database settings. SQLite is typically fine,
   but make sure to change the path to e.g. ``temp.db``, to avoid
   clobbering any existing database file.

3. Make your code changes (including database schema changes in ``db.py``).

4. After every database schema change, recreate the throwaway database
   to test the changes::

    rm temp.db
    kallithea-cli db-create -c temp.ini --repos=/var/repos --user=doe --email doe@example.com --password=123456 --no-public-access --force-yes
    kallithea-cli repo-scan -c temp.ini

5. Once satisfied with the schema changes, auto-generate a draft Alembic
   script using the development database that has *not* been upgraded.
   (The generated script will upgrade the database to match the code.)

   ::

    alembic -c development.ini revision -m "area: add cool feature" --autogenerate

6. Edit the script to clean it up and fix any problems.

   Note that for changes that simply add columns, it may be appropriate
   to not remove them in the downgrade script (and instead do nothing),
   to avoid the loss of data. Unknown columns will simply be ignored by
   Kallithea versions predating your changes.

7. Run ``alembic -c development.ini upgrade head`` to apply changes to
   the (non-throwaway) database, and test the upgrade script. Also test
   downgrades.

   The included ``development.ini`` has full SQL logging enabled. If
   you're using another configuration file, you may want to enable it
   by setting ``level = DEBUG`` in section ``[handler_console_sql]``.

The Alembic migration script should be committed in the same revision as
the database schema (``db.py``) changes.

See the `Alembic documentation`__ for more information, in particular
the tutorial and the section about auto-generating migration scripts.

.. __: http://alembic.zzzcomputing.com/en/latest/


Troubleshooting
---------------

* If ``alembic --autogenerate`` responds "Target database is not up to
  date", you need to either first use Alembic to upgrade the database
  to the most recent version (before your changes), or recreate the
  database from scratch (without your schema changes applied).
