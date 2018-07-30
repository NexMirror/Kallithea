.. _vcs_setup:

=============================
Version control systems setup
=============================

Kallithea supports Git and Mercurial repositories out-of-the-box.
For Git, you do need the ``git`` command line client installed on the server.

You can always disable Git or Mercurial support by editing the
file ``kallithea/__init__.py`` and commenting out the backend. For example, to
disable Git but keep Mercurial enabled:

.. code-block:: python

   BACKENDS = {
       'hg': 'Mercurial repository',
       #'git': 'Git repository',
   }


Git-specific setup
------------------


Web server with chunked encoding
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Large Git pushes require an HTTP server with support for
chunked encoding for POST. The Python web servers waitress_ and
gunicorn_ (Linux only) can be used. By default, Kallithea uses
waitress_ for `gearbox serve` instead of the built-in `paste` WSGI
server.

The web server used by gearbox is controlled in the .ini file::

    use = egg:waitress#main

or::

    use = egg:gunicorn#main

Also make sure to comment out the following options::

    threadpool_workers =
    threadpool_max_requests =
    use_threadpool =

Increasing Git HTTP POST buffer size
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Git pushes fail with HTTP error code 411 (Length Required), you may need to
increase the Git HTTP POST buffer. Run the following command as the user that
runs Kallithea to set a global Git variable to this effect::

    git config --global http.postBuffer 524288000


.. _waitress: http://pypi.python.org/pypi/waitress
.. _gunicorn: http://pypi.python.org/pypi/gunicorn
.. _subrepositories: http://mercurial.aragost.com/kick-start/en/subrepositories/
