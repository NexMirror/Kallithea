.. _contributing:

=========================
Contributing to Kallithea
=========================

Kallithea is developed and maintained by its users. Please join us and scratch
your own itch.


Infrastructure
--------------

The main repository is hosted on Our Own Kallithea (aka OOK) at
https://kallithea-scm.org/repos/kallithea/, our self-hosted instance
of Kallithea.

For now, we use Bitbucket_ for `pull requests`_ and `issue tracking`_. The
issue tracker is for tracking bugs, not for support, discussion, or ideas --
please use the `mailing list`_ or :ref:`IRC <readme>` to reach the community.

We use Weblate_ to translate the user interface messages into languages other
than English. Join our project on `Hosted Weblate`_ to help us.
To register, you can use your Bitbucket or GitHub account. See :ref:`translations`
for more details.


Getting started
---------------

To get started with Kallithea development::

        hg clone https://kallithea-scm.org/repos/kallithea
        cd kallithea
        virtualenv ../kallithea-venv
        source ../kallithea-venv/bin/activate
        pip install --upgrade pip setuptools
        pip install --upgrade -e . -r dev_requirements.txt python-ldap python-pam
        kallithea-cli config-create my.ini
        kallithea-cli db-create -c my.ini --user=user --email=user@example.com --password=password --repos=/tmp
        kallithea-cli front-end-build
        gearbox serve -c my.ini --reload &
        firefox http://127.0.0.1:5000/

If you plan to use Bitbucket_ for sending contributions, you can also fork
Kallithea on Bitbucket_ first (https://bitbucket.org/conservancy/kallithea) and
then replace the clone step above by a clone of your fork. In this case, please
see :ref:`contributing-guidelines` below for configuring your fork correctly.


Contribution flow
-----------------

Starting from an existing Kallithea clone, make sure it is up to date with the
latest upstream changes::

        hg pull
        hg update

Review the :ref:`contributing-guidelines` and :ref:`coding-guidelines`.

If you are new to Mercurial, refer to Mercurial `Quick Start`_ and `Beginners
Guide`_ on the Mercurial wiki.

Now, make some changes and test them (see :ref:`contributing-tests`). Don't
forget to add new tests to cover new functionality or bug fixes.

For documentation changes, run ``make html`` from the ``docs`` directory to
generate the HTML result, then review them in your browser.

Before submitting any changes, run the cleanup script::

        ./scripts/run-all-cleanup

When you are completely ready, you can send your changes to the community for
review and inclusion. Most commonly used methods are sending patches to the
mailing list (via ``hg email``) or by creating a pull request on Bitbucket_.

.. _contributing-tests:


Running tests
-------------

After finishing your changes make sure all tests pass cleanly. Run the testsuite
by invoking ``py.test`` from the project root::

    py.test

Note that on unix systems, the temporary directory (``/tmp`` or where
``$TMPDIR`` points) must allow executable files; Git hooks must be executable,
and the test suite creates repositories in the temporary directory. Linux
systems with /tmp mounted noexec will thus fail.

You can also use ``tox`` to run the tests with all supported Python versions
(currently only Python 2.7).

When running tests, Kallithea generates a `test.ini` based on template values
in `kallithea/tests/conftest.py` and populates the SQLite database specified
there.

It is possible to avoid recreating the full test database on each invocation of
the tests, thus eliminating the initial delay. To achieve this, run the tests as::

    gearbox serve -c /tmp/kallithea-test-XXX/test.ini --pid-file=test.pid --daemon
    KALLITHEA_WHOOSH_TEST_DISABLE=1 KALLITHEA_NO_TMP_PATH=1 py.test
    kill -9 $(cat test.pid)

In these commands, the following variables are used::

    KALLITHEA_WHOOSH_TEST_DISABLE=1 - skip whoosh index building and tests
    KALLITHEA_NO_TMP_PATH=1 - disable new temp path for tests, used mostly for testing_vcs_operations

You can run individual tests by specifying their path as argument to py.test.
py.test also has many more options, see `py.test -h`. Some useful options
are::

    -k EXPRESSION         only run tests which match the given substring
                          expression. An expression is a python evaluable
                          expression where all names are substring-matched
                          against test names and their parent classes. Example:
    -x, --exitfirst       exit instantly on first error or failed test.
    --lf                  rerun only the tests that failed at the last run (or
                          all if none failed)
    --ff                  run all tests but run the last failures first. This
                          may re-order tests and thus lead to repeated fixture
                          setup/teardown
    --pdb                 start the interactive Python debugger on errors.
    -s, --capture=no      don't capture stdout (any stdout output will be
                          printed immediately)

Performance tests
^^^^^^^^^^^^^^^^^

A number of performance tests are present in the test suite, but they are
not run in a standard test run. These tests are useful to
evaluate the impact of certain code changes with respect to performance.

To run these tests::

    env TEST_PERFORMANCE=1 py.test kallithea/tests/performance

To analyze performance, you could install pytest-profiling_, which enables the
--profile and --profile-svg options to py.test.

.. _pytest-profiling: https://github.com/manahl/pytest-plugins/tree/master/pytest-profiling

.. _contributing-guidelines:


Contribution guidelines
-----------------------

Kallithea is GPLv3 and we assume all contributions are made by the
committer/contributor and under GPLv3 unless explicitly stated. We do care a
lot about preservation of copyright and license information for existing code
that is brought into the project.

Contributions will be accepted in most formats -- such as pull requests on
Bitbucket, something hosted on your own Kallithea instance, or patches sent by
email to the `kallithea-general`_ mailing list.

When contributing via Bitbucket, please make your fork of
https://bitbucket.org/conservancy/kallithea/ `non-publishing`_ -- it is one of
the settings on "Repository details" page. This ensures your commits are in
"draft" phase and makes it easier for you to address feedback and for project
maintainers to integrate your changes.

.. _non-publishing: https://www.mercurial-scm.org/wiki/Phases#Publishing_Repository

Make sure to test your changes both manually and with the automatic tests
before posting.

We care about quality and review and keeping a clean repository history. We
might give feedback that requests polishing contributions until they are
"perfect". We might also rebase and collapse and make minor adjustments to your
changes when we apply them.

We try to make sure we have consensus on the direction the project is taking.
Everything non-sensitive should be discussed in public -- preferably on the
mailing list.  We aim at having all non-trivial changes reviewed by at least
one other core developer before pushing. Obvious non-controversial changes will
be handled more casually.

There is a main development branch ("default") which is generally stable so that
it can be (and is) used in production. There is also a "stable" branch that is
almost exclusively reserved for bug fixes or trivial changes. Experimental
changes should live elsewhere (for example in a pull request) until they are
ready.

.. _coding-guidelines:


Coding guidelines
-----------------

We don't have a formal coding/formatting standard. We are currently using a mix
of Mercurial's (https://www.mercurial-scm.org/wiki/CodingStyle), pep8, and
consistency with existing code. Run ``scripts/run-all-cleanup`` before
committing to ensure some basic code formatting consistency.

We currently only support Python 2.7.x and nothing else. For now we don't care
about Python 3 compatibility.

We try to support the most common modern web browsers. IE9 is still supported
to the extent it is feasible, IE8 is not.

We primarily support Linux and OS X on the server side but Windows should also work.

HTML templates should use 2 spaces for indentation ... but be pragmatic. We
should use templates cleverly and avoid duplication. We should use reasonable
semantic markup with element classes and IDs that can be used for styling and testing.
We should only use inline styles in places where it really is semantic (such as
``display: none``).

JavaScript must use ``;`` between/after statements. Indentation 4 spaces. Inline
multiline functions should be indented two levels -- one for the ``()`` and one for
``{}``.
Variables holding jQuery objects should be named with a leading ``$``.

Commit messages should have a leading short line summarizing the changes. For
bug fixes, put ``(Issue #123)`` at the end of this line.

Use American English grammar and spelling overall. Use `English title case`_ for
page titles, button labels, headers, and 'labels' for fields in forms.

.. _English title case: https://en.wikipedia.org/wiki/Capitalization#Title_case

Template helpers (that is, everything in ``kallithea.lib.helpers``)
should only be referenced from templates. If you need to call a
helper from the Python code, consider moving the function somewhere
else (e.g. to the model).

Notes on the SQLAlchemy session
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each HTTP request runs inside an independent SQLAlchemy session (as well
as in an independent database transaction). ``Session`` is the session manager
and factory. ``Session()`` will create a new session on-demand or return the
current session for the active thread. Many database operations are methods on
such session instances - only ``Session.remove()`` should be called directly on
the manager.

Database model objects
(almost) always belong to a particular SQLAlchemy session, which means
that SQLAlchemy will ensure that they're kept in sync with the database
(but also means that they cannot be shared across requests).

Objects can be added to the session using ``Session().add``, but this is
rarely needed:

* When creating a database object by calling the constructor directly,
  it must explicitly be added to the session.

* When creating an object using a factory function (like
  ``create_repo``), the returned object has already (by convention)
  been added to the session, and should not be added again.

* When getting an object from the session (via ``Session().query`` or
  any of the utility functions that look up objects in the database),
  it's already part of the session, and should not be added again.
  SQLAlchemy monitors attribute modifications automatically for all
  objects it knows about and syncs them to the database.

SQLAlchemy also flushes changes to the database automatically; manually
calling ``Session().flush`` is usually only necessary when the Python
code needs the database to assign an "auto-increment" primary key ID to
a freshly created model object (before flushing, the ID attribute will
be ``None``).

TurboGears2 DebugBar
^^^^^^^^^^^^^^^^^^^^

It is possible to enable the TurboGears2-provided DebugBar_, a toolbar overlayed
over the Kallithea web interface, allowing you to see:

* timing information of the current request, including profiling information
* request data, including GET data, POST data, cookies, headers and environment
  variables
* a list of executed database queries, including timing and result values

DebugBar is only activated when ``debug = true`` is set in the configuration
file. This is important, because the DebugBar toolbar will be visible for all
users, and allow them to see information they should not be allowed to see. Like
is anyway the case for ``debug = true``, do not use this in production!

To enable DebugBar, install ``tgext.debugbar`` and ``kajiki`` (typically via
``pip``) and restart Kallithea (in debug mode).


"Roadmap"
---------

We do not have a road map but are waiting for your contributions. Refer to the
wiki_ for some ideas of places we might want to go -- contributions in these
areas are very welcome.


Thank you for your contribution!
--------------------------------


.. _Weblate: http://weblate.org/
.. _issue tracking: https://bitbucket.org/conservancy/kallithea/issues?status=new&status=open
.. _pull requests: https://bitbucket.org/conservancy/kallithea/pull-requests
.. _bitbucket: http://bitbucket.org/
.. _mailing list: http://lists.sfconservancy.org/mailman/listinfo/kallithea-general
.. _kallithea-general: http://lists.sfconservancy.org/mailman/listinfo/kallithea-general
.. _Hosted Weblate: https://hosted.weblate.org/projects/kallithea/kallithea/
.. _wiki: https://bitbucket.org/conservancy/kallithea/wiki/Home
.. _DebugBar: https://github.com/TurboGears/tgext.debugbar
.. _Quick Start: https://www.mercurial-scm.org/wiki/QuickStart
.. _Beginners Guide: https://www.mercurial-scm.org/wiki/BeginnersGuides
