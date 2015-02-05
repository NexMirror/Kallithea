.. _installation:

==========================
Installation on Unix/Linux
==========================

``Kallithea`` is written entirely in Python. Before posting any issues make
sure, your not missing any system libraries and using right version of
libraries required by Kallithea. There's also restriction in terms of mercurial
clients. Minimal version of hg client known working fine with Kallithea is
**1.6**. If you're using older client, please upgrade.


Installing Kallithea from PyPI (aka "Cheeseshop")
-------------------------------------------------

Kallithea requires python version 2.6 or higher.

The easiest way to install ``kallithea`` is to run::

    easy_install kallithea

Or::

    pip install kallithea

If you prefer to install Kallithea manually simply grab latest release from
http://pypi.python.org/pypi/Kallithea, decompress the archive and run::

    python setup.py install

Step by step installation example for Windows
---------------------------------------------

:ref:`installation_win`


Step by step installation example for Linux
-------------------------------------------


For installing Kallithea i highly recommend using separate virtualenv_. This
way many required by Kallithea libraries will remain sandboxed from your main
python and making things less problematic when doing system python updates.

Alternative very detailed installation instructions for Ubuntu Server with
celery, indexer and daemon scripts: https://gist.github.com/4546398


- Assuming you have installed virtualenv_ create a new virtual environment
  using virtualenv command::

    virtualenv --no-site-packages /opt/kallithea-venv


.. note:: Using ``--no-site-packages`` when generating your
   virtualenv is **very important**. This flag provides the necessary
   isolation for running the set of packages required by
   Kallithea.  If you do not specify ``--no-site-packages``,
   it's possible that Kallithea will not install properly into
   the virtualenv, or, even if it does, may not run properly,
   depending on the packages you've already got installed into your
   Python's "main" site-packages dir.


- this will install new virtualenv_ into `/opt/kallithea-venv`.
- Activate the virtualenv_ by running::

    source /opt/kallithea-venv/bin/activate

.. note:: If you're using UNIX, *do not* use ``sudo`` to run the
   ``virtualenv`` script.  It's perfectly acceptable (and desirable)
   to create a virtualenv as a normal user.

- Make a folder for Kallithea data files, and configuration somewhere on the
  filesystem. For example::

    mkdir /opt/kallithea


- Go into the created directory run this command to install kallithea::

    easy_install kallithea

  or::

    pip install kallithea

- This will install Kallithea together with pylons and all other required
  python libraries into activated virtualenv

Requirements for Celery (optional)
----------------------------------

In order to gain maximum performance
there are some third-party you must install. When Kallithea is used
together with celery you have to install some kind of message broker,
recommended one is rabbitmq_ to make the async tasks work.

Of course Kallithea works in sync mode also and then you do not have to install
any third party applications. However, using Celery_ will give you a large
speed improvement when using many big repositories. If you plan to use
Kallithea for say 7 to 10 repositories, Kallithea will perform perfectly well
without celery running.

If you make the decision to run Kallithea with celery make sure you run
celeryd using paster and message broker together with the application.

.. note::
   Installing message broker and using celery is optional, Kallithea will
   work perfectly fine without them.


**Message Broker**

- preferred is `RabbitMq <http://www.rabbitmq.com/>`_
- A possible alternative is `Redis <http://code.google.com/p/redis/>`_

For installation instructions you can visit:
http://ask.github.com/celery/getting-started/index.html.
This is a very nice tutorial on how to start using celery_ with rabbitmq_


You can now proceed to :ref:`setup`
-----------------------------------



.. _virtualenv: http://pypi.python.org/pypi/virtualenv
.. _python: http://www.python.org/
.. _mercurial: http://mercurial.selenic.com/
.. _celery: http://celeryproject.org/
.. _rabbitmq: http://www.rabbitmq.com/
