.. _installation_win_old:


Step by step Installation for Windows
=====================================


Kallithea step-by-step install Guide for Windows

Target OS: Windows XP SP3 32bit English (Clean installation)
+ All Windows Updates until 24-may-2012

.. note::

   This installation is for 32bit systems, for 64bit windows you might need
   to download proper 64bit versions of the different packages(Windows Installer, Win32py extensions)
   plus some extra tweaks.
   These extra steps haven been marked as "64bit".
   Tested on Windows Server 2008 R2 SP1, 9-feb-2013.
   If you run into any 64bit related problems, please check these pages:
   - http://blog.victorjabur.com/2011/06/05/compiling-python-2-7-modules-on-windows-32-and-64-using-msvc-2008-express/
   - http://bugs.python.org/issue7511

Step1 - Install Visual Studio 2008 Express
------------------------------------------


Optional: You can also install MinGW, but VS2008 installation is easier.

Download "Visual C++ 2008 Express Edition with SP1" from:
http://www.microsoft.com/visualstudio/en-us/products/2008-editions/express
(if not found or relocated, google for "visual studio 2008 express" for
updated link)

You can also download full ISO file for offline installation, just
choose "All - Offline Install ISO image file" in the previous page and
choose "Visual C++ 2008 Express" when installing.

.. note::

   Using other versions of Visual Studio will lead to random crashes.
   You must use Visual Studio 2008!"

.. note::

   Silverlight Runtime and SQL Server 2008 Express Edition are not
   required, you can uncheck them

.. note::

   64bit: You also need to install the Microsoft Windows SDK for .NET 3.5 SP1 (.NET 4.0 won't work).
   Download from: http://www.microsoft.com/en-us/download/details.aspx?id=3138

.. note::

   64bit: You also need to copy and rename a .bat file to make the Visual C++ compiler work.
   I am not sure why this is not necessary for 32bit.
   Copy C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\bin\vcvars64.bat to C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\bin\amd64\vcvarsamd64.bat


Step2 - Install Python
----------------------

Install Python 2.x.y (x = 6 or 7) x86 version (32bit). DO NOT USE A 3.x version.
Download Python 2.x.y from:
http://www.python.org/download/

Choose "Windows Installer" (32bit version) not "Windows X86-64
Installer". While writing this guide, the latest version was v2.7.3.
Remember the specific major and minor version installed, because it will
be needed in the next step. In this case, it is "2.7".

.. note::

   64bit: Just download and install the 64bit version of python.

Step3 - Install Win32py extensions
----------------------------------

Download pywin32 from:
http://sourceforge.net/projects/pywin32/files/

- Click on "pywin32" folder
- Click on the first folder (in this case, Build 217, maybe newer when you try)
- Choose the file ending with ".win32-py2.x.exe" -> x being the minor
  version of Python you installed (in this case, 7)
  When writing this guide, the file was:
  http://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/pywin32-217.win32-py2.7.exe/download

  .. note::

     64bit: Download and install the 64bit version.
     At the time of writing you can find this at:
     http://sourceforge.net/projects/pywin32/files/pywin32/Build%20218/pywin32-218.win-amd64-py2.7.exe/download

Step4 - Python BIN
------------------

Add Python BIN folder to the path

You have to add the Python folder to the path, you can do it manually
(editing "PATH" environment variable) or using Windows Support Tools
that came preinstalled in Vista/7 and can be installed in Windows XP.

- Using support tools on WINDOWS XP:
  If you use Windows XP you can install them using Windows XP CD and
  navigating to \SUPPORT\TOOLS. There, execute Setup.EXE (not MSI).
  Afterwards, open a CMD and type::

    SETX PATH "%PATH%;[your-python-path]" -M

  Close CMD (the path variable will be updated then)

- Using support tools on WINDOWS Vista/7:

  Open a CMD and type::

    SETX PATH "%PATH%;[your-python-path]" /M

  Please substitute [your-python-path] with your Python installation path.
  Typically: C:\\Python27


Step5 - Kallithea folder structure
----------------------------------

Create a Kallithea folder structure

This is only a example to install Kallithea, you can of course change
it. However, this guide will follow the proposed structure, so please
later adapt the paths if you change them. My recommendation is to use
folders with NO SPACES. But you can try if you are brave...

Create the following folder structure::

  C:\Kallithea
  C:\Kallithea\Bin
  C:\Kallithea\Env
  C:\Kallithea\Repos


Step6 - Install virtualenv
---------------------------

Install Virtual Env for Python

Navigate to: http://www.virtualenv.org/en/latest/index.html#installation
Right click on "virtualenv.py" file and choose "Save link as...".
Download to C:\\Kallithea (or whatever you want)
(the file is located at
https://raw.github.com/pypa/virtualenv/master/virtualenv.py)

Create a virtual Python environment in C:\\Kallithea\\Env (or similar). To
do so, open a CMD (Python Path should be included in Step3), navigate
where you downloaded "virtualenv.py", and write::

 python virtualenv.py C:\Kallithea\Env

(--no-site-packages is now the default behaviour of virtualenv, no need
to include it)


Step7 - Install Kallithea
-------------------------

Finally, install Kallithea

Close previously opened command prompt/s, and open a Visual Studio 2008
Command Prompt (**IMPORTANT!!**). To do so, go to Start Menu, and then open
"Microsoft Visual C++ 2008 Express Edition" -> "Visual Studio Tools" ->
"Visual Studio 2008 Command Prompt"

.. note::

   64bit: For 64bit you need to modify the shortcut that is used to start the
   Visual Studio 2008 Command Prompt. Use right-mouse click to open properties.

Change commandline from::

%comspec% /k ""C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"" x86

to::

%comspec% /k ""C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\vcvarsall.bat"" amd64


In that CMD (loaded with VS2008 PATHs) type::

  cd C:\Kallithea\Env\Scripts (or similar)
  activate

The prompt will change into "(Env) C:\\Kallithea\\Env\\Scripts" or similar
(depending of your folder structure). Then type::

 pip install kallithea

(long step, please wait until fully complete)

Some warnings will appear, don't worry as they are normal.


Step8 - Configuring Kallithea
-----------------------------


steps taken from http://packages.python.org/Kallithea/setup.html

You have to use the same Visual Studio 2008 command prompt as Step7, so
if you closed it reopen it following the same commands (including the
"activate" one). When ready, just type::

  cd C:\Kallithea\Bin
  paster make-config Kallithea production.ini

Then, you must edit production.ini to fit your needs (ip address, ip
port, mail settings, database, whatever). I recommend using NotePad++
(free) or similar text editor, as it handles well the EndOfLine
character differences between Unix and Windows
(http://notepad-plus-plus.org/)

For the sake of simplicity lets run it with the default settings. After
your edits (if any), in the previous Command Prompt, type::

 paster setup-db production.ini

(this time a NEW database will be installed, you must follow a different
step to later UPGRADE to a newer Kallithea version)

The script will ask you for confirmation about creating a NEW database,
answer yes (y)
The script will ask you for repository path, answer C:\\Kallithea\\Repos
(or similar)
The script will ask you for admin username and password, answer "admin"
+ "123456" (or whatever you want)
The script will ask you for admin mail, answer "admin@xxxx.com" (or
whatever you want)

If you make some mistake and the script does not end, don't worry, start
it again.


Step9 - Running Kallithea
-------------------------


In the previous command prompt, being in the C:\\Kallithea\\Bin folder,
just type::

 paster serve production.ini

Open yout web server, and go to http://127.0.0.1:5000

It works!! :-)

Remark:
If it does not work first time, just Ctrl-C the CMD process and start it
again. Don't forget the "http://" in Internet Explorer



What this Guide does not cover:

- Installing Celery
- Running Kallithea as Windows Service. You can investigate here:

  - http://pypi.python.org/pypi/wsgisvc
  - http://ryrobes.com/python/running-python-scripts-as-a-windows-service/
  - http://wiki.pylonshq.com/display/pylonscookbook/How+to+run+Pylons+as+a+Windows+service

- Using Apache. You can investigate here:

  - https://groups.google.com/group/rhodecode/msg/c433074e813ffdc4


Upgrading
=========

Stop running Kallithea
Open a CommandPrompt like in Step7 (VS2008 path + activate) and type::

 easy_install -U kallithea
 cd \Kallithea\Bin

{ backup your production.ini file now} ::

 paster make-config Kallithea production.ini

(check changes and update your production.ini accordingly) ::

 paster upgrade-db production.ini (update database)

Full steps in http://packages.python.org/Kallithea/upgrade.html
