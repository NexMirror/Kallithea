.. _changelog:

=========
Changelog
=========


1.4.1 (**2012-09-04**)
----------------------

:status: in-progress
:branch: beta

news
++++

- always put a comment about code-review status change even if user send
  empty data 
- modified_on column saves repository update and it's going to be used
  later for light version of main page ref #500
- pull request notifications send much nicer emails with details about pull
  request

fixes
+++++

- fixed migrations of permissions that can lead to inconsistency.
  Some users sent feedback that after upgrading from older versions issues 
  with updating default permissions occurred. RhodeCode detects that now and
  resets default user permission to initial state if there is a need for that.
  Also forces users to set the default value for new forking permission. 
- #535 improved apache wsgi example configuration in docs


1.4.0 (**2012-09-03**)
----------------------

news
++++
 
- new codereview system
- email map, allowing users to have multiple email addresses mapped into
  their accounts
- improved git-hook system. Now all actions for git are logged into journal
  including pushed revisions, user and IP address
- changed setup-app into setup-rhodecode and added default options to it.
- new git repos are created as bare now by default
- #464 added links to groups in permission box
- #465 mentions autocomplete inside comments boxes
- #469 added --update-only option to whoosh to re-index only given list
  of repos in index 
- rhodecode-api CLI client
- new git http protocol replaced buggy dulwich implementation.
  Now based on pygrack & gitweb
- Improved RSS/ATOM feeds. Discoverable by browsers using proper headers, and 
  reformated based on user suggestions. Additional rss/atom feeds for user
  journal
- various i18n improvements
- #478 permissions overview for admin in user edit view
- File view now displays small gravatars off all authors of given file
- Implemented landing revisions. Each repository will get landing_rev attribute
  that defines 'default' revision/branch for generating readme files
- Implemented #509, RhodeCode enforces SSL for push/pulling if requested at 
  earliest possible call.
- Import remote svn repositories to mercurial using hgsubversion.
- Fixed #508 RhodeCode now has a option to explicitly set forking permissions
- RhodeCode can use alternative server for generating avatar icons
- implemented repositories locking. Pull locks, push unlocks. Also can be done
  via API calls
- #538 form for permissions can handle multiple users at once 

fixes
+++++

- improved translations
- fixes issue #455 Creating an archive generates an exception on Windows
- fixes #448 Download ZIP archive keeps file in /tmp open and results 
  in out of disk space
- fixes issue #454 Search results under Windows include proceeding
  backslash
- fixed issue #450. Rhodecode no longer will crash when bad revision is
  present in journal data.
- fix for issue #417, git execution was broken on windows for certain
  commands.
- fixed #413. Don't disable .git directory for bare repos on deleting
- fixed issue #459. Changed the way of obtaining logger in reindex task.
- fixed #453 added ID field in whoosh SCHEMA that solves the issue of
  reindexing modified files
- fixed #481 rhodecode emails are sent without Date header 
- fixed #458 wrong count when no repos are present
- fixed issue #492 missing `\ No newline at end of file` test at the end of 
  new chunk in html diff
- full text search now works also for commit messages

1.3.6 (**2012-05-17**)
----------------------

news
++++

- chinese traditional translation
- changed setup-app into setup-rhodecode and added arguments for auto-setup 
  mode that doesn't need user interaction 

fixes
+++++

- fixed no scm found warning
- fixed __future__ import error on rcextensions
- made simplejson required lib for speedup on JSON encoding
- fixes #449 bad regex could get more than revisions from parsing history
- don't clear DB session when CELERY_EAGER is turned ON

1.3.5 (**2012-05-10**)
----------------------

news
++++

- use ext_json for json module
- unified annotation view with file source view
- notification improvements, better inbox + css
- #419 don't strip passwords for login forms, make rhodecode 
  more compatible with LDAP servers
- Added HTTP_X_FORWARDED_FOR as another method of extracting 
  IP for pull/push logs. - moved all to base controller  
- #415: Adding comment to changeset causes reload. 
  Comments are now added via ajax and doesn't reload the page
- #374 LDAP config is discarded when LDAP can't be activated
- limited push/pull operations are now logged for git in the journal
- bumped mercurial to 2.2.X series
- added support for displaying submodules in file-browser
- #421 added bookmarks in changelog view

fixes
+++++

- fixed dev-version marker for stable when served from source codes
- fixed missing permission checks on show forks page
- #418 cast to unicode fixes in notification objects
- #426 fixed mention extracting regex
- fixed remote-pulling for git remotes remopositories
- fixed #434: Error when accessing files or changesets of a git repository 
  with submodules
- fixed issue with empty APIKEYS for users after registration ref. #438
- fixed issue with getting README files from git repositories

1.3.4 (**2012-03-28**)
----------------------

news
++++

- Whoosh logging is now controlled by the .ini files logging setup
- added clone-url into edit form on /settings page
- added help text into repo add/edit forms
- created rcextensions module with additional mappings (ref #322) and
  post push/pull/create repo hooks callbacks
- implemented #377 Users view for his own permissions on account page
- #399 added inheritance of permissions for users group on repos groups
- #401 repository group is automatically pre-selected when adding repos 
  inside a repository group
- added alternative HTTP 403 response when client failed to authenticate. Helps 
  solving issues with Mercurial and LDAP
- #402 removed group prefix from repository name when listing repositories 
  inside a group
- added gravatars into permission view and permissions autocomplete
- #347 when running multiple RhodeCode instances, properly invalidates cache 
  for all registered servers

fixes
+++++

- fixed #390 cache invalidation problems on repos inside group
- fixed #385 clone by ID url was loosing proxy prefix in URL
- fixed some unicode problems with waitress
- fixed issue with escaping < and > in changeset commits
- fixed error occurring during recursive group creation in API 
  create_repo function
- fixed #393 py2.5 fixes for routes url generator
- fixed #397 Private repository groups shows up before login
- fixed #396 fixed problems with revoking users in nested groups
- fixed mysql unicode issues + specified InnoDB as default engine with 
  utf8 charset
- #406 trim long branch/tag names in changelog to not break UI
  
1.3.3 (**2012-03-02**)
----------------------

news
++++


fixes
+++++

- fixed some python2.5 compatibility issues 
- fixed issues with removed repos was accidentally added as groups, after
  full rescan of paths
- fixes #376 Cannot edit user (using container auth)
- fixes #378 Invalid image urls on changeset screen with proxy-prefix 
  configuration
- fixed initial sorting of repos inside repo group
- fixes issue when user tried to resubmit same permission into user/user_groups
- bumped beaker version that fixes #375 leap error bug
- fixed raw_changeset for git. It was generated with hg patch headers
- fixed vcs issue with last_changeset for filenodes
- fixed missing commit after hook delete
- fixed #372 issues with git operation detection that caused a security issue 
  for git repos

1.3.2 (**2012-02-28**)
----------------------

news
++++


fixes
+++++

- fixed git protocol issues with repos-groups
- fixed git remote repos validator that prevented from cloning remote git repos
- fixes #370 ending slashes fixes for repo and groups
- fixes #368 improved git-protocol detection to handle other clients
- fixes #366 When Setting Repository Group To Blank Repo Group Wont Be 
  Moved To Root
- fixes #371 fixed issues with beaker/sqlalchemy and non-ascii cache keys 
- fixed #373 missing cascade drop on user_group_to_perm table

1.3.1 (**2012-02-27**)
----------------------

news
++++


fixes
+++++

- redirection loop occurs when remember-me wasn't checked during login
- fixes issues with git blob history generation 
- don't fetch branch for git in file history dropdown. Causes unneeded slowness

1.3.0 (**2012-02-26**)
----------------------

news
++++

- code review, inspired by github code-comments 
- #215 rst and markdown README files support
- #252 Container-based and proxy pass-through authentication support
- #44 branch browser. Filtering of changelog by branches
- mercurial bookmarks support
- new hover top menu, optimized to add maximum size for important views
- configurable clone url template with possibility to specify  protocol like 
  ssh:// or http:// and also manually alter other parts of clone_url.
- enabled largefiles extension by default
- optimized summary file pages and saved a lot of unused space in them
- #239 option to manually mark repository as fork
- #320 mapping of commit authors to RhodeCode users
- #304 hashes are displayed using monospace font    
- diff configuration, toggle white lines and context lines
- #307 configurable diffs, whitespace toggle, increasing context lines
- sorting on branches, tags and bookmarks using YUI datatable
- improved file filter on files page
- implements #330 api method for listing nodes ar particular revision
- #73 added linking issues in commit messages to chosen issue tracker url
  based on user defined regular expression
- added linking of changesets in commit messages  
- new compact changelog with expandable commit messages
- firstname and lastname are optional in user creation
- #348 added post-create repository hook
- #212 global encoding settings is now configurable from .ini files 
- #227 added repository groups permissions
- markdown gets codehilite extensions
- new API methods, delete_repositories, grante/revoke permissions for groups 
  and repos
  
    
fixes
+++++

- rewrote dbsession management for atomic operations, and better error handling
- fixed sorting of repo tables
- #326 escape of special html entities in diffs
- normalized user_name => username in api attributes
- fixes #298 ldap created users with mixed case emails created conflicts 
  on saving a form
- fixes issue when owner of a repo couldn't revoke permissions for users 
  and groups
- fixes #271 rare JSON serialization problem with statistics
- fixes #337 missing validation check for conflicting names of a group with a
  repositories group
- #340 fixed session problem for mysql and celery tasks
- fixed #331 RhodeCode mangles repository names if the a repository group 
  contains the "full path" to the repositories
- #355 RhodeCode doesn't store encrypted LDAP passwords

1.2.5 (**2012-01-28**)
----------------------

news
++++

fixes
+++++

- #340 Celery complains about MySQL server gone away, added session cleanup
  for celery tasks
- #341 "scanning for repositories in None" log message during Rescan was missing
  a parameter
- fixed creating archives with subrepos. Some hooks were triggered during that
  operation leading to crash.
- fixed missing email in account page.
- Reverted Mercurial to 2.0.1 for windows due to bug in Mercurial that makes
  forking on windows impossible 

1.2.4 (**2012-01-19**)
----------------------

news
++++

- RhodeCode is bundled with mercurial series 2.0.X by default, with
  full support to largefiles extension. Enabled by default in new installations
- #329 Ability to Add/Remove Groups to/from a Repository via AP
- added requires.txt file with requirements
     
fixes
+++++

- fixes db session issues with celery when emailing admins
- #331 RhodeCode mangles repository names if the a repository group 
  contains the "full path" to the repositories
- #298 Conflicting e-mail addresses for LDAP and RhodeCode users
- DB session cleanup after hg protocol operations, fixes issues with
  `mysql has gone away` errors
- #333 doc fixes for get_repo api function
- #271 rare JSON serialization problem with statistics enabled
- #337 Fixes issues with validation of repository name conflicting with 
  a group name. A proper message is now displayed.
- #292 made ldap_dn in user edit readonly, to get rid of confusion that field
  doesn't work   
- #316 fixes issues with web description in hgrc files 

1.2.3 (**2011-11-02**)
----------------------

news
++++

- added option to manage repos group for non admin users
- added following API methods for get_users, create_user, get_users_groups, 
  get_users_group, create_users_group, add_user_to_users_groups, get_repos, 
  get_repo, create_repo, add_user_to_repo
- implements #237 added password confirmation for my account 
  and admin edit user.
- implements #291 email notification for global events are now sent to all
  administrator users, and global config email.
     
fixes
+++++

- added option for passing auth method for smtp mailer
- #276 issue with adding a single user with id>10 to usergroups
- #277 fixes windows LDAP settings in which missing values breaks the ldap auth 
- #288 fixes managing of repos in a group for non admin user

1.2.2 (**2011-10-17**)
----------------------

news
++++

- #226 repo groups are available by path instead of numerical id
 
fixes
+++++

- #259 Groups with the same name but with different parent group
- #260 Put repo in group, then move group to another group -> repo becomes unavailable
- #258 RhodeCode 1.2 assumes egg folder is writable (lockfiles problems)
- #265 ldap save fails sometimes on converting attributes to booleans, 
  added getter and setter into model that will prevent from this on db model level
- fixed problems with timestamps issues #251 and #213
- fixes #266 RhodeCode allows to create repo with the same name and in 
  the same parent as group
- fixes #245 Rescan of the repositories on Windows
- fixes #248 cannot edit repos inside a group on windows
- fixes #219 forking problems on windows

1.2.1 (**2011-10-08**)
----------------------

news
++++


fixes
+++++

- fixed problems with basic auth and push problems 
- gui fixes
- fixed logger

1.2.0 (**2011-10-07**)
----------------------

news
++++

- implemented #47 repository groups
- implemented #89 Can setup google analytics code from settings menu
- implemented #91 added nicer looking archive urls with more download options
  like tags, branches
- implemented #44 into file browsing, and added follow branch option
- implemented #84 downloads can be enabled/disabled for each repository
- anonymous repository can be cloned without having to pass default:default
  into clone url
- fixed #90 whoosh indexer can index chooses repositories passed in command 
  line
- extended journal with day aggregates and paging
- implemented #107 source code lines highlight ranges
- implemented #93 customizable changelog on combined revision ranges - 
  equivalent of githubs compare view 
- implemented #108 extended and more powerful LDAP configuration
- implemented #56 users groups
- major code rewrites optimized codes for speed and memory usage
- raw and diff downloads are now in git format
- setup command checks for write access to given path
- fixed many issues with international characters and unicode. It uses utf8
  decode with replace to provide less errors even with non utf8 encoded strings
- #125 added API KEY access to feeds
- #109 Repository can be created from external Mercurial link (aka. remote 
  repository, and manually updated (via pull) from admin panel
- beta git support - push/pull server + basic view for git repos
- added followers page and forks page
- server side file creation (with binary file upload interface) 
  and edition with commits powered by codemirror 
- #111 file browser file finder, quick lookup files on whole file tree 
- added quick login sliding menu into main page
- changelog uses lazy loading of affected files details, in some scenarios 
  this can improve speed of changelog page dramatically especially for 
  larger repositories.
- implements #214 added support for downloading subrepos in download menu.
- Added basic API for direct operations on rhodecode via JSON
- Implemented advanced hook management

fixes
+++++

- fixed file browser bug, when switching into given form revision the url was 
  not changing
- fixed propagation to error controller on simplehg and simplegit middlewares
- fixed error when trying to make a download on empty repository
- fixed problem with '[' chars in commit messages in journal
- fixed #99 Unicode errors, on file node paths with non utf-8 characters
- journal fork fixes
- removed issue with space inside renamed repository after deletion
- fixed strange issue on formencode imports
- fixed #126 Deleting repository on Windows, rename used incompatible chars. 
- #150 fixes for errors on repositories mapped in db but corrupted in 
  filesystem
- fixed problem with ascendant characters in realm #181
- fixed problem with sqlite file based database connection pool
- whoosh indexer and code stats share the same dynamic extensions map
- fixes #188 - relationship delete of repo_to_perm entry on user removal
- fixes issue #189 Trending source files shows "show more" when no more exist
- fixes issue #197 Relative paths for pidlocks
- fixes issue #198 password will require only 3 chars now for login form
- fixes issue #199 wrong redirection for non admin users after creating a repository
- fixes issues #202, bad db constraint made impossible to attach same group 
  more than one time. Affects only mysql/postgres
- fixes #218 os.kill patch for windows was missing sig param
- improved rendering of dag (they are not trimmed anymore when number of 
  heads exceeds 5)
    
1.1.8 (**2011-04-12**)
----------------------

news
++++

- improved windows support

fixes
+++++

- fixed #140 freeze of python dateutil library, since new version is python2.x
  incompatible
- setup-app will check for write permission in given path
- cleaned up license info issue #149
- fixes for issues #137,#116 and problems with unicode and accented characters.
- fixes crashes on gravatar, when passed in email as unicode
- fixed tooltip flickering problems
- fixed came_from redirection on windows
- fixed logging modules, and sql formatters
- windows fixes for os.kill issue #133
- fixes path splitting for windows issues #148
- fixed issue #143 wrong import on migration to 1.1.X
- fixed problems with displaying binary files, thanks to Thomas Waldmann
- removed name from archive files since it's breaking ui for long repo names
- fixed issue with archive headers sent to browser, thanks to Thomas Waldmann
- fixed compatibility for 1024px displays, and larger dpi settings, thanks to 
  Thomas Waldmann
- fixed issue #166 summary pager was skipping 10 revisions on second page


1.1.7 (**2011-03-23**)
----------------------

news
++++

fixes
+++++

- fixed (again) #136 installation support for FreeBSD


1.1.6 (**2011-03-21**)
----------------------

news
++++

fixes
+++++

- fixed #136 installation support for FreeBSD
- RhodeCode will check for python version during installation

1.1.5 (**2011-03-17**)
----------------------

news
++++

- basic windows support, by exchanging pybcrypt into sha256 for windows only
  highly inspired by idea of mantis406

fixes
+++++

- fixed sorting by author in main page
- fixed crashes with diffs on binary files
- fixed #131 problem with boolean values for LDAP
- fixed #122 mysql problems thanks to striker69 
- fixed problem with errors on calling raw/raw_files/annotate functions 
  with unknown revisions
- fixed returned rawfiles attachment names with international character
- cleaned out docs, big thanks to Jason Harris

1.1.4 (**2011-02-19**)
----------------------

news
++++

fixes
+++++

- fixed formencode import problem on settings page, that caused server crash
  when that page was accessed as first after server start
- journal fixes
- fixed option to access repository just by entering http://server/<repo_name> 

1.1.3 (**2011-02-16**)
----------------------

news
++++

- implemented #102 allowing the '.' character in username
- added option to access repository just by entering http://server/<repo_name>
- celery task ignores result for better performance

fixes
+++++

- fixed ehlo command and non auth mail servers on smtp_lib. Thanks to 
  apollo13 and Johan Walles
- small fixes in journal
- fixed problems with getting setting for celery from .ini files
- registration, password reset and login boxes share the same title as main 
  application now
- fixed #113: to high permissions to fork repository
- fixed problem with '[' chars in commit messages in journal
- removed issue with space inside renamed repository after deletion
- db transaction fixes when filesystem repository creation failed
- fixed #106 relation issues on databases different than sqlite
- fixed static files paths links to use of url() method

1.1.2 (**2011-01-12**)
----------------------

news
++++


fixes
+++++

- fixes #98 protection against float division of percentage stats
- fixed graph bug
- forced webhelpers version since it was making troubles during installation 

1.1.1 (**2011-01-06**)
----------------------
 
news
++++

- added force https option into ini files for easier https usage (no need to
  set server headers with this options)
- small css updates

fixes
+++++

- fixed #96 redirect loop on files view on repositories without changesets
- fixed #97 unicode string passed into server header in special cases (mod_wsgi)
  and server crashed with errors
- fixed large tooltips problems on main page
- fixed #92 whoosh indexer is more error proof

1.1.0 (**2010-12-18**)
----------------------

news
++++

- rewrite of internals for vcs >=0.1.10
- uses mercurial 1.7 with dotencode disabled for maintaining compatibility 
  with older clients
- anonymous access, authentication via ldap
- performance upgrade for cached repos list - each repository has its own 
  cache that's invalidated when needed.
- performance upgrades on repositories with large amount of commits (20K+)
- main page quick filter for filtering repositories
- user dashboards with ability to follow chosen repositories actions
- sends email to admin on new user registration
- added cache/statistics reset options into repository settings
- more detailed action logger (based on hooks) with pushed changesets lists
  and options to disable those hooks from admin panel
- introduced new enhanced changelog for merges that shows more accurate results
- new improved and faster code stats (based on pygments lexers mapping tables, 
  showing up to 10 trending sources for each repository. Additionally stats
  can be disabled in repository settings.
- gui optimizations, fixed application width to 1024px
- added cut off (for large files/changesets) limit into config files
- whoosh, celeryd, upgrade moved to paster command
- other than sqlite database backends can be used

fixes
+++++

- fixes #61 forked repo was showing only after cache expired
- fixes #76 no confirmation on user deletes
- fixes #66 Name field misspelled
- fixes #72 block user removal when he owns repositories
- fixes #69 added password confirmation fields
- fixes #87 RhodeCode crashes occasionally on updating repository owner
- fixes #82 broken annotations on files with more than 1 blank line at the end
- a lot of fixes and tweaks for file browser
- fixed detached session issues
- fixed when user had no repos he would see all repos listed in my account
- fixed ui() instance bug when global hgrc settings was loaded for server 
  instance and all hgrc options were merged with our db ui() object
- numerous small bugfixes
 
(special thanks for TkSoh for detailed feedback)


1.0.2 (**2010-11-12**)
----------------------

news
++++

- tested under python2.7
- bumped sqlalchemy and celery versions

fixes
+++++

- fixed #59 missing graph.js
- fixed repo_size crash when repository had broken symlinks
- fixed python2.5 crashes.


1.0.1 (**2010-11-10**)
----------------------

news
++++

- small css updated

fixes
+++++

- fixed #53 python2.5 incompatible enumerate calls
- fixed #52 disable mercurial extension for web
- fixed #51 deleting repositories don't delete it's dependent objects


1.0.0 (**2010-11-02**)
----------------------

- security bugfix simplehg wasn't checking for permissions on commands
  other than pull or push.
- fixed doubled messages after push or pull in admin journal
- templating and css corrections, fixed repo switcher on chrome, updated titles
- admin menu accessible from options menu on repository view
- permissions cached queries

1.0.0rc4  (**2010-10-12**)
--------------------------

- fixed python2.5 missing simplejson imports (thanks to Jens Bäckman)
- removed cache_manager settings from sqlalchemy meta
- added sqlalchemy cache settings to ini files
- validated password length and added second try of failure on paster setup-app
- fixed setup database destroy prompt even when there was no db


1.0.0rc3 (**2010-10-11**)
-------------------------

- fixed i18n during installation.

1.0.0rc2 (**2010-10-11**)
-------------------------

- Disabled dirsize in file browser, it's causing nasty bug when dir renames 
  occure. After vcs is fixed it'll be put back again.
- templating/css rewrites, optimized css.