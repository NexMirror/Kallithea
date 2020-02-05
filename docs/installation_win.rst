.. _installation_win:

.. warning:: This section is outdated and needs updating for Python 3.

====================================================
Installation on Windows (7/Server 2008 R2 and newer)
====================================================


First time install
------------------

Target OS: Windows 7 and newer or Windows Server 2008 R2 and newer

Tested on Windows 8.1, Windows Server 2008 R2 and Windows Server 2012

To install on an older version of Windows, see `<installation_win_old.html>`_

Step 1 -- Install Python
^^^^^^^^^^^^^^^^^^^^^^^^

Install Python 3. Latest version is recommended. If you need another version, they can run side by side.

- Download Python 3 from http://www.python.org/download/
- Choose and click on the version
- Click on "Windows X86-64 Installer" for x64 or "Windows x86 MSI installer" for Win32.
- Disable UAC or run the installer with admin privileges. If you chose to disable UAC, do not forget to reboot afterwards.

While writing this guide, the latest version was v3.8.1.
Remember the specific major and minor versions installed, because they will
be needed in the next step. In this case, it is "3.8".

Step 2 -- Python BIN
^^^^^^^^^^^^^^^^^^^^

Add Python BIN folder to the path. This can be done manually (editing
"PATH" environment variable) or by using Windows Support Tools that
come pre-installed in Windows Vista/7 and later.

Open a CMD and type::

  SETX PATH "%PATH%;[your-python-path]" /M

Please substitute [your-python-path] with your Python installation
path. Typically this is ``C:\\Python38``.

Step 3 -- Install pywin32 extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download pywin32 from:
http://sourceforge.net/projects/pywin32/files/

- Click on "pywin32" folder
- Click on the first folder (in this case, Build 219, maybe newer when you try)
- Choose the file ending with ".amd64-py3.x.exe" (".win32-py3.x.exe"
  for Win32) where x is the minor version of Python you installed.
  When writing this guide, the file was:
  http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win-amd64-py3.8.exe/download
  (x64)
  http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/pywin32-219.win32-py3.8.exe/download
  (Win32)

Step 5 -- Kallithea folder structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a Kallithea folder structure.

This is only an example to install Kallithea. Of course, you can
change it. However, this guide will follow the proposed structure, so
please later adapt the paths if you change them. Folders without
spaces are recommended.

Create the following folder structure::

  C:\Kallithea
  C:\Kallithea\Bin
  C:\Kallithea\Env
  C:\Kallithea\Repos

Step 6 -- Install virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   A python virtual environment will allow for isolation between the Python packages of your system and those used for Kallithea.
   It is strongly recommended to use it to ensure that Kallithea does not change a dependency that other software uses or vice versa.

To create a virtual environment, run::

  python3 -m venv C:\Kallithea\Env

Step 7 -- Install Kallithea
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to install Kallithea, you need to be able to run "pip install kallithea". It will use pip to install the Kallithea Python package and its dependencies.
Some Python packages use managed code and need to be compiled.
This can be done on Linux without any special steps. On Windows, you will need to install Microsoft Visual C++ compiler for Python 3.8.

Download and install "Microsoft Visual C++ Compiler for Python 3.8" from http://aka.ms/vcpython27

.. note::
  You can also install the dependencies using already compiled Windows binaries packages. A good source of compiled Python packages is http://www.lfd.uci.edu/~gohlke/pythonlibs/. However, not all of the necessary packages for Kallithea are on this site and some are hard to find, so we will stick with using the compiler.

In a command prompt type (adapting paths if necessary)::

  cd C:\Kallithea\Env\Scripts
  activate
  pip install --upgrade pip setuptools

The prompt will change into "(Env) C:\\Kallithea\\Env\\Scripts" or similar
(depending of your folder structure). Then type::

  pip install kallithea

.. note:: This will take some time. Please wait patiently until it is fully
          complete. Some warnings will appear. Don't worry, they are
          normal.

Step 8 -- Install Git (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mercurial being a python package, was installed automatically when doing ``pip install kallithea``.

You need to install Git manually if you want Kallithea to be able to host Git repositories.
See http://git-scm.com/book/en/v2/Getting-Started-Installing-Git#Installing-on-Windows for instructions.
The location of the Git binaries (like ``c:\path\to\git\bin``) must be
added to the ``PATH`` environment variable so ``git.exe`` and other tools like
``gzip.exe`` are available.

Step 9 -- Configuring Kallithea
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Steps taken from `<setup.html>`_

You have to use the same command prompt as in Step 7, so if you closed
it, reopen it following the same commands (including the "activate"
one). When ready, type::

  cd C:\Kallithea\Bin
  kallithea-cli config-create my.ini

Then you must edit my.ini to fit your needs (IP address, IP
port, mail settings, database, etc.). `NotePad++`__ or a similar text
editor is recommended to properly handle the newline character
differences between Unix and Windows.

__ http://notepad-plus-plus.org/

For the sake of simplicity, run it with the default settings. After your edits (if any) in the previous command prompt, type::

  kallithea-cli db-create -c my.ini

.. warning:: This time a *new* database will be installed. You must
             follow a different process to later :ref:`upgrade <upgrade>`
             to a newer Kallithea version.

The script will ask you for confirmation about creating a new database, answer yes (y)

The script will ask you for the repository path, answer C:\\Kallithea\\Repos (or similar).

The script will ask you for the admin username and password, answer "admin" + "123456" (or whatever you want)

The script will ask you for admin mail, answer "admin@xxxx.com" (or whatever you want).

If you make a mistake and the script doesn't end, don't worry: start it again.

If you decided not to install Git, you will get errors about it that you can ignore.

Step 10 -- Running Kallithea
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the previous command prompt, being in the C:\\Kallithea\\Bin folder, type::

  gearbox serve -c my.ini

Open your web server, and go to http://127.0.0.1:5000

It works!! :-)

Remark:
If it does not work the first time, Ctrl-C the CMD process and start it again. Don't forget the "http://" in Internet Explorer.

What this guide does not cover:

- Installing Celery
- Running Kallithea as a Windows Service. You can investigate here:

  - http://pypi.python.org/pypi/wsgisvc
  - http://ryrobes.com/python/running-python-scripts-as-a-windows-service/
  - http://wiki.pylonshq.com/display/pylonscookbook/How+to+run+Pylons+as+a+Windows+service

- Using Apache. You can investigate here:

  - https://groups.google.com/group/rhodecode/msg/c433074e813ffdc4
