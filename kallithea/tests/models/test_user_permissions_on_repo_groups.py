import functools
from kallithea.tests import *

from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.db import RepoGroup, User

from kallithea.model.meta import Session
from nose.tools import with_setup
from kallithea.tests.models.common import _create_project_tree, check_tree_perms, \
    _get_perms, _check_expected_count, expected_count, _destroy_project_tree


test_u1_id = None
_get_repo_perms = None
_get_group_perms = None


def permissions_setup_func(group_name='g0', perm='group.read', recursive='all',
                           user_id=None):
    """
    Resets all permissions to perm attribute
    """
    if not user_id:
        user_id = test_u1_id
        # called by the @with_setup decorator also reset the default user stuff
        permissions_setup_func(group_name, perm, recursive,
                               user_id=User.get_default_user().user_id)

    repo_group = RepoGroup.get_by_group_name(group_name=group_name)
    if not repo_group:
        raise Exception('Cannot get group %s' % group_name)

    perms_updates = [[user_id, perm, 'user']]
    RepoGroupModel()._update_permissions(repo_group,
                                         perms_updates=perms_updates,
                                         recursive=recursive, check_perms=False)
    Session().commit()

def setup_module():
    global test_u1_id, _get_repo_perms, _get_group_perms
    test_u1 = _create_project_tree()
    Session().commit()
    test_u1_id = test_u1.user_id
    _get_repo_perms = functools.partial(_get_perms, key='repositories',
                                        test_u1_id=test_u1_id)
    _get_group_perms = functools.partial(_get_perms, key='repositories_groups',
                                         test_u1_id=test_u1_id)


def teardown_module():
    _destroy_project_tree(test_u1_id)


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_without_recursive_mode():
    # set permission to g0 non-recursive mode
    recursive = 'none'
    group = 'g0'
    permissions_setup_func(group, 'group.write', recursive=recursive)

    items = [x for x in _get_repo_perms(group, recursive)]
    expected = 0
    assert len(items) == expected, ' %s != %s' % (len(items), expected)
    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'repository.read'

    items = [x for x in _get_group_perms(group, recursive)]
    expected = 1
    assert len(items) == expected, ' %s != %s' % (len(items), expected)
    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_without_recursive_mode_subgroup():
    # set permission to g0 non-recursive mode
    recursive = 'none'
    group = 'g0/g0_1'
    permissions_setup_func(group, 'group.write', recursive=recursive)

    items = [x for x in _get_repo_perms(group, recursive)]
    expected = 0
    assert len(items) == expected, ' %s != %s' % (len(items), expected)
    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'repository.read'

    items = [x for x in _get_group_perms(group, recursive)]
    expected = 1
    assert len(items) == expected, ' %s != %s' % (len(items), expected)
    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_mode():

    # set permission to g0 recursive mode, all children including
    # other repos and groups should have this permission now set !
    recursive = 'all'
    group = 'g0'
    permissions_setup_func(group, 'group.write', recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.write'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_mode_for_default_user():

    # set permission to g0 recursive mode, all children including
    # other repos and groups should have this permission now set !
    recursive = 'all'
    group = 'g0'
    default_user_id = User.get_default_user().user_id
    permissions_setup_func(group, 'group.write', recursive=recursive,
                           user_id=default_user_id)

    # change default to get perms for default user
    _get_repo_perms = functools.partial(_get_perms, key='repositories',
                                        test_u1_id=default_user_id)
    _get_group_perms = functools.partial(_get_perms, key='repositories_groups',
                                         test_u1_id=default_user_id)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.write'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_mode_inner_group():
    ## set permission to g0_3 group to none
    recursive = 'all'
    group = 'g0/g0_3'
    permissions_setup_func(group, 'group.none', recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.none'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.none'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_mode_deepest():
    ## set permission to g0_3 group to none
    recursive = 'all'
    group = 'g0/g0_1/g0_1_1'
    permissions_setup_func(group, 'group.write', recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.write'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_mode_only_with_repos():
    ## set permission to g0_3 group to none
    recursive = 'all'
    group = 'g0/g0_2'
    permissions_setup_func(group, 'group.admin', recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.admin'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.admin'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_repo_mode_for_default_user():
    # set permission to g0/g0_1 recursive repos only mode, all children including
    # other repos should have this permission now set, inner groups are excluded!
    recursive = 'repos'
    group = 'g0/g0_1'
    perm = 'group.none'
    default_user_id = User.get_default_user().user_id

    permissions_setup_func(group, perm, recursive=recursive,
                           user_id=default_user_id)

    # change default to get perms for default user
    _get_repo_perms = functools.partial(_get_perms, key='repositories',
                                        test_u1_id=default_user_id)
    _get_group_perms = functools.partial(_get_perms, key='repositories_groups',
                                         test_u1_id=default_user_id)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.none'

    for name, perm in items:
        # permission is set with repos only mode, but we also change the permission
        # on the group we trigger the apply to children from, thus we need
        # to change its permission check
        old_perm = 'group.read'
        if name == group:
            old_perm = perm
        yield check_tree_perms, name, perm, group, old_perm


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_repo_mode_inner_group():
    ## set permission to g0_3 group to none, with recursive repos only
    recursive = 'repos'
    group = 'g0/g0_3'
    perm = 'group.none'
    permissions_setup_func(group, perm, recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.none'

    for name, perm in items:
        # permission is set with repos only mode, but we also change the permission
        # on the group we trigger the apply to children from, thus we need
        # to change its permission check
        old_perm = 'group.read'
        if name == group:
            old_perm = perm
        yield check_tree_perms, name, perm, group, old_perm


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_group_mode_for_default_user():
    # set permission to g0/g0_1 with recursive groups only mode, all children including
    # other groups should have this permission now set. repositories should
    # remain intact as we use groups only mode !
    recursive = 'groups'
    group = 'g0/g0_1'
    default_user_id = User.get_default_user().user_id
    permissions_setup_func(group, 'group.write', recursive=recursive,
                           user_id=default_user_id)

    # change default to get perms for default user
    _get_repo_perms = functools.partial(_get_perms, key='repositories',
                                        test_u1_id=default_user_id)
    _get_group_perms = functools.partial(_get_perms, key='repositories_groups',
                                         test_u1_id=default_user_id)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.read'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.write'


@with_setup(permissions_setup_func)
def test_user_permissions_on_group_with_recursive_group_mode_inner_group():
    ## set permission to g0_3 group to none, with recursive mode for groups only
    recursive = 'groups'
    group = 'g0/g0_3'
    permissions_setup_func(group, 'group.none', recursive=recursive)

    repo_items = [x for x in _get_repo_perms(group, recursive)]
    items = [x for x in _get_group_perms(group, recursive)]
    _check_expected_count(items, repo_items, expected_count(group, True))

    for name, perm in repo_items:
        yield check_tree_perms, name, perm, group, 'repository.read'

    for name, perm in items:
        yield check_tree_perms, name, perm, group, 'group.none'
