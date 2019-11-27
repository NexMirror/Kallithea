.. _api:

===
API
===

Kallithea has a simple JSON RPC API with a single schema for calling all API
methods. Everything is available by sending JSON encoded http(s) requests to
``<your_server>/_admin/api``.


API keys
--------

Every Kallithea user automatically receives an API key, which they can
view under "My Account". On this page, API keys can also be revoked, and
additional API keys can be generated.


API access
----------

Clients must send JSON encoded JSON-RPC requests::

    {
        "id: "<id>",
        "api_key": "<api_key>",
        "method": "<method_name>",
        "args": {"<arg_key>": "<arg_val>"}
    }

For example, to pull to a local "CPython" mirror using curl::

    curl https://kallithea.example.com/_admin/api -X POST -H 'content-type:text/plain' \
        --data-binary '{"id":1,"api_key":"xe7cdb2v278e4evbdf5vs04v832v0efvcbcve4a3","method":"pull","args":{"repoid":"CPython"}}'

In general, provide
 - *id*, a value of any type, can be used to match the response with the request that it is replying to.
 - *api_key*, for authentication and permission validation.
 - *method*, the name of the method to call -- a list of available methods can be found below.
 - *args*, the arguments to pass to the method.

.. note::

    api_key can be found or set on the user account page.

The response to the JSON-RPC API call will always be a JSON structure::

    {
        "id": <id>,  # the id that was used in the request
        "result": <result>|null,  # JSON formatted result (null on error)
        "error": null|<error_message>  # JSON formatted error (null on success)
    }

All responses from the API will be ``HTTP/1.0 200 OK``. If an error occurs,
the reponse will have a failure description in *error* and
*result* will be null.


API client
----------

Kallithea comes with a ``kallithea-api`` command line tool, providing a convenient
way to call the JSON-RPC API.

For example, to call ``get_repo``::

    kallithea-api --apihost=<Kallithea URL> --apikey=<API key> get_repo

    Calling method get_repo => <Kallithea URL>
    Server response
    ERROR:"Missing non optional `repoid` arg in JSON DATA"

Oops, looks like we forgot to add an argument. Let's try again, now
providing the ``repoid`` as a parameter::

    kallithea-api --apihost=<Kallithea URL> --apikey=<API key> get_repo repoid:myrepo

    Calling method get_repo => <Kallithea URL>
    Server response
    {
        "clone_uri": null,
        "created_on": "2015-08-31T14:55:19.042",
    ...

To avoid specifying ``apihost`` and ``apikey`` every time, run::

    kallithea-api --save-config --apihost=<Kallithea URL> --apikey=<API key>

This will create a ``~/.config/kallithea`` with the specified URL and API key
so you don't have to specify them every time.


API methods
-----------


pull
^^^^

Pull the given repo from remote location. Can be used to automatically keep
remote repos up to date.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "pull"
    args :    {
                "repoid" : "<reponame or repo_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "Pulled from `<reponame>`"
    error :  null

rescan_repos
^^^^^^^^^^^^

Rescan repositories. If ``remove_obsolete`` is set,
Kallithea will delete repos that are in the database but not in the filesystem.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "rescan_repos"
    args :    {
                "remove_obsolete" : "<boolean = Optional(False)>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "{'added': [<list of names of added repos>],
               'removed': [<list of names of removed repos>]}"
    error :  null

invalidate_cache
^^^^^^^^^^^^^^^^

Invalidate the cache for a repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with admin or write access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "invalidate_cache"
    args :    {
                "repoid" : "<reponame or repo_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "Caches of repository `<reponame>`"
    error :  null

get_ip
^^^^^^

Return IP address as seen from Kallithea server, together with all
defined IP addresses for given user.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_ip"
    args :    {
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result : {
                 "ip_addr_server": <ip_from_clien>",
                 "user_ips": [
                                {
                                   "ip_addr": "<ip_with_mask>",
                                   "ip_range": ["<start_ip>", "<end_ip>"],
                                },
                                ...
                             ]
             }

    error :  null

get_user
^^^^^^^^

Get a user by username or userid. The result is empty if user can't be found.
If userid param is skipped, it is set to id of user who is calling this method.
Any userid can be specified when the command is executed using the api_key of a user with admin rights.
Regular users can only specify their own userid.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user"
    args :    {
                "userid" : "<username or user_id Optional(=apiuser)>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: None if user does not exist or
            {
                "user_id" :     "<user_id>",
                "api_key" :     "<api_key>",
                "username" :    "<username>",
                "firstname":    "<firstname>",
                "lastname" :    "<lastname>",
                "email" :       "<email>",
                "emails":       "<list_of_all_additional_emails>",
                "ip_addresses": "<list_of_ip_addresses_for_user>",
                "active" :      "<bool>",
                "admin" :       "<bool>",
                "ldap_dn" :     "<ldap_dn>",
                "last_login":   "<last_login>",
                "permissions": {
                    "global": ["hg.create.repository",
                               "repository.read",
                               "hg.register.manual_activate"],
                    "repositories": {"repo1": "repository.none"},
                    "repositories_groups": {"Group1": "group.read"}
                 },
            }
    error:  null

get_users
^^^^^^^^^

List all existing users.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_users"
    args :    { }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "user_id" :     "<user_id>",
                "api_key" :     "<api_key>",
                "username" :    "<username>",
                "firstname":    "<firstname>",
                "lastname" :    "<lastname>",
                "email" :       "<email>",
                "emails":       "<list_of_all_additional_emails>",
                "ip_addresses": "<list_of_ip_addresses_for_user>",
                "active" :      "<bool>",
                "admin" :       "<bool>",
                "ldap_dn" :     "<ldap_dn>",
                "last_login":   "<last_login>",
              },
              …
            ]
    error:  null

.. _create-user:

create_user
^^^^^^^^^^^

Create new user.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_user"
    args :    {
                "username" :  "<username>",
                "email" :     "<useremail>",
                "password" :  "<password = Optional(None)>",
                "firstname" : "<firstname> = Optional(None)",
                "lastname" :  "<lastname> = Optional(None)",
                "active" :    "<bool> = Optional(True)",
                "admin" :     "<bool> = Optional(False)",
                "ldap_dn" :   "<ldap_dn> = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "created new user `<username>`",
              "user": {
                "user_id" :  "<user_id>",
                "username" : "<username>",
                "firstname": "<firstname>",
                "lastname" : "<lastname>",
                "email" :    "<email>",
                "emails":    "<list_of_all_additional_emails>",
                "active" :   "<bool>",
                "admin" :    "<bool>",
                "ldap_dn" :  "<ldap_dn>",
                "last_login": "<last_login>",
              },
            }
    error:  null

Example::

    kallithea-api create_user username:bent email:bent@example.com firstname:Bent lastname:Bentsen extern_type:ldap extern_name:uid=bent,dc=example,dc=com

update_user
^^^^^^^^^^^

Update the given user if such user exists.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "update_user"
    args :    {
                "userid" : "<user_id or username>",
                "username" :  "<username> = Optional(None)",
                "email" :     "<useremail> = Optional(None)",
                "password" :  "<password> = Optional(None)",
                "firstname" : "<firstname> = Optional(None)",
                "lastname" :  "<lastname> = Optional(None)",
                "active" :    "<bool> = Optional(None)",
                "admin" :     "<bool> = Optional(None)",
                "ldap_dn" :   "<ldap_dn> = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "updated user ID:<userid> <username>",
              "user": {
                "user_id" :  "<user_id>",
                "api_key" :  "<api_key>",
                "username" : "<username>",
                "firstname": "<firstname>",
                "lastname" : "<lastname>",
                "email" :    "<email>",
                "emails":    "<list_of_all_additional_emails>",
                "active" :   "<bool>",
                "admin" :    "<bool>",
                "ldap_dn" :  "<ldap_dn>",
                "last_login": "<last_login>",
              },
            }
    error:  null

delete_user
^^^^^^^^^^^

Delete the given user if such a user exists.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "delete_user"
    args :    {
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "deleted user ID:<userid> <username>",
              "user": null
            }
    error:  null

get_user_group
^^^^^^^^^^^^^^

Get an existing user group.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user_group"
    args :    {
                "usergroupid" : "<user group id or name>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : None if group not exist
             {
               "users_group_id" : "<id>",
               "group_name" :     "<groupname>",
               "active":          "<bool>",
               "members" :  [
                              {
                                "user_id" :  "<user_id>",
                                "api_key" :  "<api_key>",
                                "username" : "<username>",
                                "firstname": "<firstname>",
                                "lastname" : "<lastname>",
                                "email" :    "<email>",
                                "emails":    "<list_of_all_additional_emails>",
                                "active" :   "<bool>",
                                "admin" :    "<bool>",
                                "ldap_dn" :  "<ldap_dn>",
                                "last_login": "<last_login>",
                              },
                              …
                            ]
             }
    error : null

get_user_groups
^^^^^^^^^^^^^^^

List all existing user groups.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user_groups"
    args :    { }

OUTPUT::

    id : <id_given_in_input>
    result : [
               {
               "users_group_id" : "<id>",
               "group_name" :     "<groupname>",
               "active":          "<bool>",
               },
               …
              ]
    error : null

create_user_group
^^^^^^^^^^^^^^^^^

Create a new user group.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_user_group"
    args:     {
                "group_name": "<groupname>",
                "owner" :     "<owner_name_or_id = Optional(=apiuser)>",
                "active":     "<bool> = Optional(True)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "created new user group `<groupname>`",
              "users_group": {
                     "users_group_id" : "<id>",
                     "group_name" :     "<groupname>",
                     "active":          "<bool>",
               },
            }
    error:  null

add_user_to_user_group
^^^^^^^^^^^^^^^^^^^^^^

Adds a user to a user group. If the user already is in that group, success will be
``false``.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "add_user_user_group"
    args:     {
                "usersgroupid" : "<user group id or name>",
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "success": True|False # depends on if member is in group
              "msg": "added member `<username>` to a user group `<groupname>` |
                      User is already in that group"
            }
    error:  null

remove_user_from_user_group
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remove a user from a user group. If the user isn't in the given group, success will
be ``false``.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "remove_user_from_user_group"
    args:     {
                "usersgroupid" : "<user group id or name>",
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "success":  True|False,  # depends on if member is in group
              "msg": "removed member <username> from user group <groupname> |
                      User wasn't in group"
            }
    error:  null

get_repo
^^^^^^^^

Get an existing repository by its name or repository_id. Members will contain
either users_group or users associated to that repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with at least read access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repo"
    args:     {
                "repoid" : "<reponame or repo_id>",
                "with_revision_names": "<bool> = Optional(False)",
                "with_pullrequests": "<bool> = Optional(False)",
              }

OUTPUT::

    id : <id_given_in_input>
    result: None if repository does not exist or
            {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "enable_downloads":  "<bool>",
                "enable_statistics": "<bool>",
                "private":           "<bool>",
                "created_on" :       "<date_time_created>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "last_changeset":    {
                                       "author":   "<full_author>",
                                       "date":     "<date_time_of_commit>",
                                       "message":  "<commit_message>",
                                       "raw_id":   "<raw_id>",
                                       "revision": "<numeric_revision>",
                                       "short_id": "<short_id>"
                                     },
                "owner":             "<repo_owner>",
                "fork_of":           "<name_of_fork_parent>",
                "members" :     [
                                  {
                                    "type":        "user",
                                    "user_id" :    "<user_id>",
                                    "api_key" :    "<api_key>",
                                    "username" :   "<username>",
                                    "firstname":   "<firstname>",
                                    "lastname" :   "<lastname>",
                                    "email" :      "<email>",
                                    "emails":      "<list_of_all_additional_emails>",
                                    "active" :     "<bool>",
                                    "admin" :      "<bool>",
                                    "ldap_dn" :    "<ldap_dn>",
                                    "last_login":  "<last_login>",
                                    "permission" : "repository.(read|write|admin)"
                                  },
                                  …
                                  {
                                    "type":      "users_group",
                                    "id" :       "<usersgroupid>",
                                    "name" :     "<usersgroupname>",
                                    "active":    "<bool>",
                                    "permission" : "repository.(read|write|admin)"
                                  },
                                  …
                                ],
                 "followers":   [
                                  {
                                    "user_id" :     "<user_id>",
                                    "username" :    "<username>",
                                    "api_key" :     "<api_key>",
                                    "firstname":    "<firstname>",
                                    "lastname" :    "<lastname>",
                                    "email" :       "<email>",
                                    "emails":       "<list_of_all_additional_emails>",
                                    "ip_addresses": "<list_of_ip_addresses_for_user>",
                                    "active" :      "<bool>",
                                    "admin" :       "<bool>",
                                    "ldap_dn" :     "<ldap_dn>",
                                    "last_login":   "<last_login>",
                                  },
                                  …
                                ],
                 <if with_revision_names == True>
                 "tags": {
                            "<tagname>": "<raw_id>",
                            ...
                         },
                 "branches": {
                            "<branchname>": "<raw_id>",
                            ...
                         },
                 "bookmarks": {
                            "<bookmarkname>": "<raw_id>",
                            ...
                         },
                <if with_pullrequests == True>
                "pull_requests": [
                  {
                    "status": "<pull_request_status>",
                    "pull_request_id": <pull_request_id>,
                    "description": "<pull_request_description>",
                    "title": "<pull_request_title>",
                    "url": "<pull_request_url>",
                    "reviewers": [
                      {
                        "username": "<user_id>",
                      },
                      ...
                    ],
                    "org_repo_url": "<repo_url>",
                    "org_ref_parts": [
                      "<ref_type>",
                      "<ref_name>",
                      "<raw_id>"
                    ],
                    "other_ref_parts": [
                      "<ref_type>",
                      "<ref_name>",
                      "<raw_id>"
                    ],
                    "comments": [
                      {
                        "username": "<user_id>",
                        "text": "<comment text>",
                        "comment_id": "<comment_id>",
                      },
                      ...
                    ],
                    "owner": "<username>",
                    "statuses": [
                      {
                        "status": "<status_of_review>",        # "under_review", "approved" or "rejected"
                        "reviewer": "<user_id>",
                        "modified_at": "<date_time_of_review>" # iso 8601 date, server's timezone
                      },
                      ...
                    ],
                    "revisions": [
                      "<raw_id>",
                      ...
                    ]
                  },
                  ...
                ]
            }
    error:  null

get_repos
^^^^^^^^^

List all existing repositories.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with at least read access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repos"
    args:     { }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "private" :          "<bool>",
                "created_on" :       "<datetimecreated>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "owner":             "<repo_owner>",
                "fork_of":           "<name_of_fork_parent>",
                "enable_downloads":  "<bool>",
                "enable_statistics": "<bool>",
              },
              …
            ]
    error:  null

get_repo_nodes
^^^^^^^^^^^^^^

Return a list of files and directories for a given path at the given revision.
It is possible to specify ret_type to show only ``files`` or ``dirs``.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repo_nodes"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "revision"  : "<revision>",
                "root_path" : "<root_path>",
                "ret_type"  : "<ret_type> = Optional('all')"
              }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "name" :        "<name>"
                "type" :        "<type>",
              },
              …
            ]
    error:  null

create_repo
^^^^^^^^^^^

Create a repository. If the repository name contains "/", the repository will be
created in the repository group indicated by that path. Any such repository
groups need to exist before calling this method, or the call will fail.
For example "foo/bar/baz" will create a repository "baz" inside the repository
group "bar" which itself is in a repository group "foo", but both "foo" and
"bar" already need to exist before calling this method.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with create repository permission.
Regular users cannot specify owner parameter.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_repo"
    args:     {
                "repo_name" :        "<reponame>",
                "owner" :            "<owner_name_or_id = Optional(=apiuser)>",
                "repo_type" :        "<repo_type> = Optional('hg')",
                "description" :      "<description> = Optional('')",
                "private" :          "<bool> = Optional(False)",
                "clone_uri" :        "<clone_uri> = Optional(None)",
                "landing_rev" :      "<landing_rev> = Optional('tip')",
                "enable_downloads":  "<bool> = Optional(False)",
                "enable_statistics": "<bool> = Optional(False)",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Created new repository `<reponame>`",
              "repo": {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "private" :          "<bool>",
                "created_on" :       "<datetimecreated>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "owner":             "<username or user_id>",
                "fork_of":           "<name_of_fork_parent>",
                "enable_downloads":  "<bool>",
                "enable_statistics": "<bool>",
              },
            }
    error:  null

update_repo
^^^^^^^^^^^

Update a repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with create repository permission.
Regular users cannot specify owner parameter.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "update_repo"
    args:     {
                "repoid" :           "<reponame or repo_id>"
                "name" :             "<reponame> = Optional('')",
                "group" :            "<group_id> = Optional(None)",
                "owner" :            "<owner_name_or_id = Optional(=apiuser)>",
                "description" :      "<description> = Optional('')",
                "private" :          "<bool> = Optional(False)",
                "clone_uri" :        "<clone_uri> = Optional(None)",
                "landing_rev" :      "<landing_rev> = Optional('tip')",
                "enable_downloads":  "<bool> = Optional(False)",
                "enable_statistics": "<bool> = Optional(False)",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "updated repo ID:repo_id `<reponame>`",
              "repository": {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "private":           "<bool>",
                "created_on" :       "<datetimecreated>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "owner":             "<username or user_id>",
                "fork_of":           "<name_of_fork_parent>",
                "enable_downloads":  "<bool>",
                "enable_statistics": "<bool>",
                "last_changeset":    {
                                       "author":   "<full_author>",
                                       "date":     "<date_time_of_commit>",
                                       "message":  "<commit_message>",
                                       "raw_id":   "<raw_id>",
                                       "revision": "<numeric_revision>",
                                       "short_id": "<short_id>"
                                     }
              },
            }
    error:  null

fork_repo
^^^^^^^^^

Create a fork of the given repo. If using Celery, this will
return success message immediately and a fork will be created
asynchronously.
This command can only be executed using the api_key of a user with admin
rights, or with the global fork permission, by a regular user with create
repository permission and at least read access to the repository.
Regular users cannot specify owner parameter.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "fork_repo"
    args:     {
                "repoid" :          "<reponame or repo_id>",
                "fork_name":        "<forkname>",
                "owner":            "<username or user_id = Optional(=apiuser)>",
                "description":      "<description>",
                "copy_permissions": "<bool>",
                "private":          "<bool>",
                "landing_rev":      "<landing_rev>"

              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Created fork of `<reponame>` as `<forkname>`",
              "success": true
            }
    error:  null

delete_repo
^^^^^^^^^^^

Delete a repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with admin access to the repository.
When ``forks`` param is set it is possible to detach or delete forks of the deleted repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "delete_repo"
    args:     {
                "repoid" : "<reponame or repo_id>",
                "forks"  : "`delete` or `detach` = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Deleted repository `<reponame>`",
              "success": true
            }
    error:  null

grant_user_permission
^^^^^^^^^^^^^^^^^^^^^

Grant permission for a user on the given repository, or update the existing one if found.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "grant_user_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "userid" : "<username or user_id>"
                "perm" :       "(repository.(none|read|write|admin))",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Granted perm: `<perm>` for user: `<username>` in repo: `<reponame>`",
              "success": true
            }
    error:  null

revoke_user_permission
^^^^^^^^^^^^^^^^^^^^^^

Revoke permission for a user on the given repository.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "revoke_user_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "userid" : "<username or user_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Revoked perm for user: `<username>` in repo: `<reponame>`",
              "success": true
            }
    error:  null

grant_user_group_permission
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Grant permission for a user group on the given repository, or update the
existing one if found.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "grant_user_group_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "usersgroupid" : "<user group id or name>"
                "perm" : "(repository.(none|read|write|admin))",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Granted perm: `<perm>` for group: `<usersgroupname>` in repo: `<reponame>`",
              "success": true
            }
    error:  null

revoke_user_group_permission
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Revoke permission for a user group on the given repository.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "revoke_user_group_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "usersgroupid" : "<user group id or name>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Revoked perm for group: `<usersgroupname>` in repo: `<reponame>`",
              "success": true
            }
    error:  null

get_changesets
^^^^^^^^^^^^^^

Get changesets of a given repository. This command can only be executed using the api_key
of a user with read permissions to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "get_changesets"
    args:     {
                "repoid" : "<reponame or repo_id>",
                "start": "<revision number> = Optional(None)",
                "end": "<revision number> = Optional(None)",
                "start_date": "<date> = Optional(None)",    # in "%Y-%m-%dT%H:%M:%S" format
                "end_date": "<date> = Optional(None)",      # in "%Y-%m-%dT%H:%M:%S" format
                "branch_name": "<branch name filter> = Optional(None)",
                "reverse": "<bool> = Optional(False)",
                "with_file_list": "<bool> = Optional(False)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: [
    {
      "raw_id": "<raw_id>",
      "short_id": "short_id": "<short_id>",
      "author": "<full_author>",
      "date": "<date_time_of_commit>",
      "message": "<commit_message>",
      "revision": "<numeric_revision>",
      <if with_file_list == True>
      "added": [<list of added files>],
      "changed": [<list of changed files>],
      "removed": [<list of removed files>]
    },
    ...
    ]
    error:  null

get_changeset
^^^^^^^^^^^^^

Get information and review status for a given changeset. This command can only
be executed using the api_key of a user with read permissions to the
repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "get_changeset"
    args:     {
                "repoid" : "<reponame or repo_id>",
                "raw_id" : "<raw_id>",
                "with_reviews": "<bool> = Optional(False)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "author":   "<full_author>",
              "date":     "<date_time_of_commit>",
              "message":  "<commit_message>",
              "raw_id":   "<raw_id>",
              "revision": "<numeric_revision>",
              "short_id": "<short_id>",
              "reviews": [{
                    "reviewer":   "<username>",
                    "modified_at": "<date_time_of_review>",  # iso 8601 date, server's timezone
                    "status":   "<status_of_review>",        # "under_review", "approved" or "rejected"
                 },
                 ...
              ]
            }
    error:  null

Example output::

    {
      "id" : 1,
      "error" : null,
      "result" : {
        "author" : {
          "email" : "user@example.com",
          "name" : "Kallithea Admin"
        },
        "changed" : [],
        "short_id" : "e1022d3d28df",
        "date" : "2017-03-28T09:09:03",
        "added" : [
          "README.rst"
        ],
        "removed" : [],
        "revision" : 0,
        "raw_id" : "e1022d3d28dfba02f626cde65dbe08f4ceb0e4e7",
        "message" : "Added file via Kallithea",
        "id" : "e1022d3d28dfba02f626cde65dbe08f4ceb0e4e7",
        "reviews" : [
          {
            "status" : "under_review",
            "modified_at" : "2017-03-28T09:17:08.618",
            "reviewer" : "user"
          }
        ]
      }
    }

get_pullrequest
^^^^^^^^^^^^^^^

Get information and review status for a given pull request. This command can only be executed
using the api_key of a user with read permissions to the original repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "get_pullrequest"
    args:     {
                "pullrequest_id" : "<pullrequest_id>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
        "status": "<pull_request_status>",
        "pull_request_id": <pull_request_id>,
        "description": "<pull_request_description>",
        "title": "<pull_request_title>",
        "url": "<pull_request_url>",
        "reviewers": [
          {
            "username": "<user_name>",
          },
          ...
        ],
        "org_repo_url": "<repo_url>",
        "org_ref_parts": [
          "<ref_type>",
          "<ref_name>",
          "<raw_id>"
        ],
        "other_ref_parts": [
          "<ref_type>",
          "<ref_name>",
          "<raw_id>"
        ],
        "comments": [
          {
            "username": "<user_name>",
            "text": "<comment text>",
            "comment_id": "<comment_id>",
          },
          ...
        ],
        "owner": "<username>",
        "statuses": [
          {
            "status": "<status_of_review>",        # "under_review", "approved" or "rejected"
            "reviewer": "<user_name>",
            "modified_at": "<date_time_of_review>" # iso 8601 date, server's timezone
          },
          ...
        ],
        "revisions": [
          "<raw_id>",
          ...
        ]
    },
    error:  null

comment_pullrequest
^^^^^^^^^^^^^^^^^^^

Add comment, change status or close a given pull request. This command can only be executed
using the api_key of a user with read permissions to the original repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "comment_pullrequest"
    args:     {
                "pull_request_id":  "<pull_request_id>",
                "comment_msg":      Optional(''),
                "status":           Optional(None),     # "under_review", "approved" or "rejected"
                "close_pr":         Optional(False)",
              }

OUTPUT::

    id : <id_given_in_input>
    result: True
    error:  null


API access for web views
------------------------

Kallithea HTTP entry points can also be accessed without login using bearer
authentication by including this header with the request::

    Authentication: Bearer <api_key>

Alternatively, the API key can be passed in the URL query string using
``?api_key=<api_key>``, though this is not recommended due to the increased
risk of API key leaks, and support will likely be removed in the future.

Exposing raw diffs is a good way to integrate with
third-party services like code review, or build farms that can download archives.
