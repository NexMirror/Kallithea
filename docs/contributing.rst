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

To get started with development::

        hg clone https://kallithea-scm.org/repos/kallithea
        cd kallithea
        virtualenv ../kallithea-venv
        source ../kallithea-venv/bin/activate
        pip install --upgrade pip setuptools
        python2 setup.py develop
        paster make-config Kallithea my.ini
        paster setup-db my.ini --user=user --email=user@example.com --password=password --repos=/tmp
        paster serve my.ini --reload &
        firefox http://127.0.0.1:5000/

You can also start out by forking https://bitbucket.org/conservancy/kallithea
on Bitbucket_ and create a local clone of your own fork.


Running tests
-------------

After finishing your changes make sure all tests pass cleanly. You can run
the testsuite running ``nosetests`` from the project root, or if you use tox
run ``tox`` for Python 2.6--2.7 with multiple database test.

When running tests, Kallithea uses `kallithea/tests/test.ini` and populates the
SQLite database specified there.

It is possible to avoid recreating the full test database on each invocation of
the tests, thus eliminating the initial delay. To achieve this, run the tests as::

    paster serve kallithea/tests/test.ini --pid-file=test.pid --daemon
    KALLITHEA_WHOOSH_TEST_DISABLE=1 KALLITHEA_NO_TMP_PATH=1 nosetests
    kill -9 $(cat test.pid)

You can run individual tests by specifying their path as argument to nosetests.
nosetests also has many more options, see `nosetests -h`. Some useful options
are::

    -x, --stop            Stop running tests after the first error or failure
    -s, --nocapture       Don't capture stdout (any stdout output will be
                          printed immediately) [NOSE_NOCAPTURE]
    --failed              Run the tests that failed in the last test run.


Coding/contribution guidelines
------------------------------

Kallithea is GPLv3 and we assume all contributions are made by the
committer/contributor and under GPLv3 unless explicitly stated. We do care a
lot about preservation of copyright and license information for existing code
that is brought into the project.

We don't have a formal coding/formatting standard. We are currently using a mix
of Mercurial (http://mercurial.selenic.com/wiki/CodingStyle), pep8, and
consistency with existing code. Run whitespacecleanup.sh to avoid stupid
whitespace noise in your patches.

We support both Python 2.6.x and 2.7.x and nothing else. For now we don't care
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

Contributions will be accepted in most formats -- such as pull requests on
bitbucket, something hosted on your own Kallithea instance, or patches sent by
email to the `kallithea-general`_ mailing list.

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

For now we just have one official branch ("default") and will keep it so stable
that it can be (and is) used in production. Experimental changes should live
elsewhere (for example in a pull request) until they are ready.

.. _translations:
.. include:: ./../kallithea/i18n/how_to


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
