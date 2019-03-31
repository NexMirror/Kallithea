.. _vcs_notes:

===================================
Version control systems usage notes
===================================

.. _importing:


Importing existing repositories
-------------------------------

There are two main methods to import repositories in Kallithea: via the web
interface or via the filesystem. If you have a large number of repositories to
import, importing them via the filesystem is more convenient.

Importing via web interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a small number of repositories, it may be easier to create the target
repositories through the Kallithea web interface, via *Admin > Repositories* or
via the *Add Repository* button on the entry page of the web interface.

Repositories can be nested in repository groups by first creating the group (via
*Admin > Repository Groups* or via the *Add Repository Group* button on the
entry page of the web interface) and then selecting the appropriate group when
adding the repository.

After creation of the (empty) repository, push the existing commits to the
*Clone URL* displayed on the repository summary page. For Git repositories,
first add the *Clone URL* as remote, then push the commits to that remote.  The
specific commands to execute are shown under the *Existing repository?* section
of the new repository's summary page.

A benefit of this method particular for Git repositories, is that the
Kallithea-specific Git hooks are installed automatically.  For Mercurial, no
hooks are required anyway.

Importing via the filesystem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The alternative method of importing repositories consists of creating the
repositories in the desired hierarchy on the filesystem and letting Kallithea
scan that location.

All repositories are stored in a central location on the filesystem. This
location is specified during installation (via ``db-create``) and can be reviewed
at *Admin > Settings > VCS > Location of repositories*. Repository groups
(defined in *Admin > Repository Groups*) are represented by a directory in that
repository location. Repositories of the repository group are nested under that
directory.

To import a set of repositories and organize them in a certain repository group
structure, first place clones in the desired hierarchy at the configured
repository location.
These clones should be created without working directory. For Mercurial, this is
done with ``hg clone -U``, for Git with ``git clone --bare``.

When the repositories are added correctly on the filesystem:

* go to *Admin > Settings > Remap and Rescan* in the Kallithea web interface
* select the *Install Git hooks* checkbox when importing Git repositories
* click *Rescan Repositories*

This step will scan the filesystem and create the appropriate repository groups
and repositories in Kallithea.

*Note*: Once repository groups have been created this way, manage their access
permissions through the Kallithea web interface.


Mercurial-specific notes
------------------------


Working with subrepositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section explains how to use Mercurial subrepositories_ in Kallithea.

Example usage::

    ## init a simple repo
    hg init mainrepo
    cd mainrepo
    echo "file" > file
    hg add file
    hg ci --message "initial file"

    # clone subrepo we want to add from Kallithea
    hg clone http://kallithea.local/subrepo

    ## specify URL to existing repo in Kallithea as subrepository path
    echo "subrepo = http://kallithea.local/subrepo" > .hgsub
    hg add .hgsub
    hg ci --message "added remote subrepo"

In the file list of a clone of ``mainrepo`` you will see a connected
subrepository at the revision it was cloned with. Clicking on the
subrepository link sends you to the proper repository in Kallithea.

Cloning ``mainrepo`` will also clone the attached subrepository.

Next we can edit the subrepository data, and push back to Kallithea. This will
update both repositories.


.. _subrepositories: http://mercurial.aragost.com/kick-start/en/subrepositories/
