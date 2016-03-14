.. _customization:

=============
Customization
=============

There are several ways to customize Kallithea to your needs depending on what
you want to achieve.


HTML/JavaScript/CSS customization
---------------------------------

To customize the look-and-feel of the web interface (for example to add a
company banner or some JavaScript widget or to tweak the CSS style definitions)
you can enter HTML code (possibly with JavaScript and/or CSS) directly via the
*Admin > Settings > Global > HTML/JavaScript customization
block*.


Behavioral customization: rcextensions
--------------------------------------

Some behavioral customization can be done in Python using ``rcextensions``, a
custom Python package that can extend Kallithea functionality.

With ``rcextensions`` it's possible to add additional mappings for Whoosh
indexing and statistics, to add additional code into the push/pull/create/delete
repository hooks (for example to send signals to build bots such as Jenkins) and
even to monkey-patch certain parts of the Kallithea source code (for example
overwrite an entire function, change a global variable, ...).

To generate a skeleton extensions package, run::

    paster make-rcext my.ini

This will create an ``rcextensions`` package next to the specified ``ini`` file.
See the ``__init__.py`` file inside the generated ``rcextensions`` package
for more details.


Behavioral customization: code changes
--------------------------------------

As Kallithea is open-source software, you can make any changes you like directly
in the source code.

We encourage you to send generic improvements back to the
community so that Kallithea can become better. See :ref:`contributing` for more
details.
