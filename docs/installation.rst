.. _installation:

==========================
Installation on Unix/Linux
==========================

The following describes three different ways of installing Kallithea:

- :ref:`installation-source`: The simplest way to keep the installation
  up-to-date and track any local customizations is to run directly from
  source in a Kallithea repository clone, preferably inside a virtualenv
  virtual Python environment.

- :ref:`installation-virtualenv`: If you prefer to only use released versions
  of Kallithea, the recommended method is to install Kallithea in a virtual
  Python environment using `virtualenv`. The advantages of this method over
  direct installation is that Kallithea and its dependencies are completely
  contained inside the virtualenv (which also means you can have multiple
  installations side by side or remove it entirely by just removing the
  virtualenv directory) and does not require root privileges.

- :ref:`installation-without-virtualenv`: The alternative method of installing
  a Kallithea release is using standard pip. The package will be installed in
  the same location as all other Python packages you have ever installed. As a
  result, removing it is not as straightforward as with a virtualenv, as you'd
  have to remove its dependencies manually and make sure that they are not
  needed by other packages.

Regardless of the installation method you may need to make sure you have
appropriate development packages installed, as installation of some of the
Kallithea dependencies requires a working C compiler and libffi library
headers. Depending on your configuration, you may also need to install
Git and development packages for the database of your choice.

For Debian and Ubuntu, the following command will ensure that a reasonable
set of dependencies is installed::

    sudo apt-get install build-essential git python-pip python-virtualenv libffi-dev python-dev

For Fedora and RHEL-derivatives, the following command will ensure that a
reasonable set of dependencies is installed::

    sudo yum install gcc git python-pip python-virtualenv libffi-devel python-devel

.. _installation-source:


Installation from repository source
-----------------------------------

To install Kallithea in a virtualenv_ using the stable branch of the development
repository, follow the instructions below::

        hg clone https://kallithea-scm.org/repos/kallithea -u stable
        cd kallithea
        virtualenv ../kallithea-venv
        . ../kallithea-venv/bin/activate
        pip install --upgrade pip setuptools
        pip install --upgrade -e .
        python2 setup.py compile_catalog   # for translation of the UI

You can now proceed to :ref:`setup`.

.. _installation-virtualenv:


Installing a released version in a virtualenv
---------------------------------------------

It is highly recommended to use a separate virtualenv_ for installing Kallithea.
This way, all libraries required by Kallithea will be installed separately from your
main Python installation and other applications and things will be less
problematic when upgrading the system or Kallithea.
An additional benefit of virtualenv_ is that it doesn't require root privileges.

- Assuming you have installed virtualenv_, create a new virtual environment
  for example, in `/srv/kallithea/venv`, using the virtualenv command::

    virtualenv /srv/kallithea/venv

- Activate the virtualenv_ in your current shell session and make sure the
  basic requirements are up-to-date by running::

    . /srv/kallithea/venv/bin/activate
    pip install --upgrade pip setuptools

.. note:: You can't use UNIX ``sudo`` to source the ``virtualenv`` script; it
   will "activate" a shell that terminates immediately. It is also perfectly
   acceptable (and desirable) to create a virtualenv as a normal user.

- Make a folder for Kallithea data files, and configuration somewhere on the
  filesystem. For example::

    mkdir /srv/kallithea

- Go into the created directory and run this command to install Kallithea::

    pip install --upgrade kallithea

.. note:: Some dependencies are optional. If you need them, install them in
   the virtualenv too::

     pip install --upgrade kallithea python-ldap python-pam psycopg2

   This might require installation of development packages using your
   distribution's package manager.

  Alternatively, download a .tar.gz from http://pypi.python.org/pypi/Kallithea,
  extract it and install from source by running::

    pip install --upgrade .

- This will install Kallithea together with all other required
  Python libraries into the activated virtualenv.

You can now proceed to :ref:`setup`.

.. _installation-without-virtualenv:


Installing a released version without virtualenv
------------------------------------------------

For installation without virtualenv, 'just' use::

    pip install kallithea

Note that this method requires root privileges and will install packages
globally without using the system's package manager.

To install as a regular user in ``~/.local``, you can use::

    pip install --user kallithea

You can now proceed to :ref:`setup`.


.. _virtualenv: http://pypi.python.org/pypi/virtualenv
