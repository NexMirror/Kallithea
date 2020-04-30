from kallithea.lib.auth import AuthUser
from kallithea.model import db
from kallithea.model.db import Permission, User, UserGroupRepoGroupToPerm, UserToPerm
from kallithea.model.meta import Session
from kallithea.model.permission import PermissionModel
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.user import UserModel
from kallithea.model.user_group import UserGroupModel
from kallithea.tests import base
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class TestPermissions(base.TestController):

    @classmethod
    def setup_class(cls):
        # recreate default user to get a clean start
        PermissionModel().create_default_permissions(user=User.DEFAULT_USER_NAME,
                                                     force=True)
        Session().commit()

    def setup_method(self, method):
        self.u1 = UserModel().create_or_update(
            username='u1', password='qweqwe',
            email='u1@example.com', firstname='u1', lastname='u1'
        )
        self.u2 = UserModel().create_or_update(
            username='u2', password='qweqwe',
            email='u2@example.com', firstname='u2', lastname='u2'
        )
        self.u3 = UserModel().create_or_update(
            username='u3', password='qweqwe',
            email='u3@example.com', firstname='u3', lastname='u3'
        )
        self.anon = User.get_default_user()
        self.a1 = UserModel().create_or_update(
            username='a1', password='qweqwe',
            email='a1@example.com', firstname='a1', lastname='a1', admin=True
        )
        Session().commit()

    def teardown_method(self, method):
        if hasattr(self, 'test_repo'):
            RepoModel().delete(repo=self.test_repo)

        UserModel().delete(self.u1)
        UserModel().delete(self.u2)
        UserModel().delete(self.u3)
        UserModel().delete(self.a1)

        Session().commit() # commit early to avoid SQLAlchemy warning from double cascade delete to users_groups_members

        if hasattr(self, 'g1'):
            RepoGroupModel().delete(self.g1.group_id)
        if hasattr(self, 'g2'):
            RepoGroupModel().delete(self.g2.group_id)

        if hasattr(self, 'ug2'):
            UserGroupModel().delete(self.ug2, force=True)
        if hasattr(self, 'ug1'):
            UserGroupModel().delete(self.ug1, force=True)

        Session().commit()

    def test_default_perms_set(self):
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == 'repository.read'
        new_perm = 'repository.write'
        RepoModel().grant_user_permission(repo=base.HG_REPO, user=self.u1,
                                          perm=new_perm)
        Session().commit()

        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == new_perm

    def test_default_admin_perms_set(self):
        a1_auth = AuthUser(user_id=self.a1.user_id)
        assert a1_auth.permissions['repositories'][base.HG_REPO] == 'repository.admin'
        new_perm = 'repository.write'
        RepoModel().grant_user_permission(repo=base.HG_REPO, user=self.a1,
                                          perm=new_perm)
        Session().commit()
        # cannot really downgrade admins permissions !? they still gets set as
        # admin !
        u1_auth = AuthUser(user_id=self.a1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == 'repository.admin'

    def test_default_group_perms(self):
        self.g1 = fixture.create_repo_group('test1', skip_if_exists=True)
        self.g2 = fixture.create_repo_group('test2', skip_if_exists=True)
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == 'repository.read'
        assert u1_auth.permissions['repositories_groups'].get('test1') == 'group.read'
        assert u1_auth.permissions['repositories_groups'].get('test2') == 'group.read'
        assert u1_auth.permissions['global'] == set(Permission.DEFAULT_USER_PERMISSIONS)

    def test_default_admin_group_perms(self):
        self.g1 = fixture.create_repo_group('test1', skip_if_exists=True)
        self.g2 = fixture.create_repo_group('test2', skip_if_exists=True)
        a1_auth = AuthUser(user_id=self.a1.user_id)
        assert a1_auth.permissions['repositories'][base.HG_REPO] == 'repository.admin'
        assert a1_auth.permissions['repositories_groups'].get('test1') == 'group.admin'
        assert a1_auth.permissions['repositories_groups'].get('test2') == 'group.admin'

    def test_propagated_permission_from_users_group_by_explicit_perms_exist(self):
        # make group
        self.ug1 = fixture.create_user_group('G1')
        UserGroupModel().add_user_to_group(self.ug1, self.u1)

        # set user permission none
        RepoModel().grant_user_permission(repo=base.HG_REPO, user=self.u1, perm='repository.none')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == 'repository.read' # inherit from default user

        # grant perm for group this should override permission from user
        RepoModel().grant_user_group_permission(repo=base.HG_REPO,
                                                 group_name=self.ug1,
                                                 perm='repository.write')

        # verify that user group permissions win
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == 'repository.write'

    def test_propagated_permission_from_users_group(self):
        # make group
        self.ug1 = fixture.create_user_group('G1')
        UserGroupModel().add_user_to_group(self.ug1, self.u3)

        # grant perm for group this should override default permission from user
        new_perm_gr = 'repository.write'
        RepoModel().grant_user_group_permission(repo=base.HG_REPO,
                                                 group_name=self.ug1,
                                                 perm=new_perm_gr)
        # check perms
        u3_auth = AuthUser(user_id=self.u3.user_id)
        assert u3_auth.permissions['repositories'][base.HG_REPO] == new_perm_gr

    def test_propagated_permission_from_users_group_lower_weight(self):
        # make group
        self.ug1 = fixture.create_user_group('G1')
        # add user to group
        UserGroupModel().add_user_to_group(self.ug1, self.u1)

        # set permission to lower
        new_perm_h = 'repository.write'
        RepoModel().grant_user_permission(repo=base.HG_REPO, user=self.u1,
                                          perm=new_perm_h)
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == new_perm_h

        # grant perm for group this should NOT override permission from user
        # since it's lower than granted
        new_perm_l = 'repository.read'
        RepoModel().grant_user_group_permission(repo=base.HG_REPO,
                                                 group_name=self.ug1,
                                                 perm=new_perm_l)
        # check perms
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories'][base.HG_REPO] == new_perm_h

    def test_repo_in_group_permissions(self):
        self.g1 = fixture.create_repo_group('group1', skip_if_exists=True)
        self.g2 = fixture.create_repo_group('group2', skip_if_exists=True)
        # both perms should be read !
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.read'
        assert u1_auth.permissions['repositories_groups'].get('group2') == 'group.read'

        a1_auth = AuthUser(user_id=self.anon.user_id)
        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.read'
        assert a1_auth.permissions['repositories_groups'].get('group2') == 'group.read'

        # Change perms to none for both groups
        RepoGroupModel().grant_user_permission(repo_group=self.g1,
                                               user=self.anon,
                                               perm='group.none')
        RepoGroupModel().grant_user_permission(repo_group=self.g2,
                                               user=self.anon,
                                               perm='group.none')

        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert u1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

        a1_auth = AuthUser(user_id=self.anon.user_id)
        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert a1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

        # add repo to group
        name = db.URL_SEP.join([self.g1.group_name, 'test_perm'])
        self.test_repo = fixture.create_repo(name=name,
                                             repo_type='hg',
                                             repo_group=self.g1,
                                             cur_user=self.u1,)

        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert u1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

        a1_auth = AuthUser(user_id=self.anon.user_id)
        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert a1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

        # grant permission for u2 !
        RepoGroupModel().grant_user_permission(repo_group=self.g1, user=self.u2,
                                               perm='group.read')
        RepoGroupModel().grant_user_permission(repo_group=self.g2, user=self.u2,
                                               perm='group.read')
        Session().commit()
        assert self.u1 != self.u2
        # u1 and anon should have not change perms while u2 should !
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert u1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

        u2_auth = AuthUser(user_id=self.u2.user_id)
        assert u2_auth.permissions['repositories_groups'].get('group1') == 'group.read'
        assert u2_auth.permissions['repositories_groups'].get('group2') == 'group.read'

        a1_auth = AuthUser(user_id=self.anon.user_id)
        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.none'
        assert a1_auth.permissions['repositories_groups'].get('group2') == 'group.none'

    def test_repo_group_user_as_user_group_member(self):
        # create Group1
        self.g1 = fixture.create_repo_group('group1', skip_if_exists=True)
        a1_auth = AuthUser(user_id=self.anon.user_id)

        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.read'

        # set default permission to none
        RepoGroupModel().grant_user_permission(repo_group=self.g1,
                                               user=self.anon,
                                               perm='group.none')
        # make group
        self.ug1 = fixture.create_user_group('G1')
        # add user to group
        UserGroupModel().add_user_to_group(self.ug1, self.u1)
        Session().commit()

        # check if user is in the group
        members = [x.user_id for x in UserGroupModel().get(self.ug1.users_group_id).members]
        assert members == [self.u1.user_id]
        # add some user to that group

        # check his permissions
        a1_auth = AuthUser(user_id=self.anon.user_id)
        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.none'

        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.none'

        # grant ug1 read permissions for
        RepoGroupModel().grant_user_group_permission(repo_group=self.g1,
                                                      group_name=self.ug1,
                                                      perm='group.read')
        Session().commit()
        # check if the
        obj = Session().query(UserGroupRepoGroupToPerm) \
            .filter(UserGroupRepoGroupToPerm.group == self.g1) \
            .filter(UserGroupRepoGroupToPerm.users_group == self.ug1) \
            .scalar()
        assert obj.permission.permission_name == 'group.read'

        a1_auth = AuthUser(user_id=self.anon.user_id)

        assert a1_auth.permissions['repositories_groups'].get('group1') == 'group.none'

        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.read'

    def test_inherit_nice_permissions_from_default_user(self):
        user_model = UserModel()
        # enable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.none')
        user_model.grant_perm(usr, 'hg.create.repository')
        user_model.revoke_perm(usr, 'hg.fork.none')
        user_model.grant_perm(usr, 'hg.fork.repository')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        # this user will have inherited permissions from default user
        assert u1_auth.permissions['global'] == set(['hg.create.repository', 'hg.fork.repository',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read', 'hg.create.write_on_repogroup.true'])

    def test_inherit_sad_permissions_from_default_user(self):
        user_model = UserModel()
        # disable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.repository')
        user_model.grant_perm(usr, 'hg.create.none')
        user_model.revoke_perm(usr, 'hg.fork.repository')
        user_model.grant_perm(usr, 'hg.fork.none')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        # this user will have inherited permissions from default user
        assert u1_auth.permissions['global'] == set(['hg.create.none', 'hg.fork.none',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read', 'hg.create.write_on_repogroup.true'])

    def test_inherit_more_permissions_from_default_user(self):
        user_model = UserModel()
        # enable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.none')
        user_model.grant_perm(usr, 'hg.create.repository')
        user_model.revoke_perm(usr, 'hg.fork.none')
        user_model.grant_perm(usr, 'hg.fork.repository')

        # disable global perms on specific user
        user_model.revoke_perm(self.u1, 'hg.create.repository')
        user_model.grant_perm(self.u1, 'hg.create.none')
        user_model.revoke_perm(self.u1, 'hg.fork.repository')
        user_model.grant_perm(self.u1, 'hg.fork.none')

        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        # this user will have inherited more permissions from default user
        assert u1_auth.permissions['global'] == set([
                              'hg.create.repository',
                              'hg.fork.repository',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read', 'hg.create.write_on_repogroup.true'])

    def test_inherit_less_permissions_from_default_user(self):
        user_model = UserModel()
        # disable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.repository')
        user_model.grant_perm(usr, 'hg.create.none')
        user_model.revoke_perm(usr, 'hg.fork.repository')
        user_model.grant_perm(usr, 'hg.fork.none')

        # enable global perms on specific user
        user_model.revoke_perm(self.u1, 'hg.create.none')
        user_model.grant_perm(self.u1, 'hg.create.repository')
        user_model.revoke_perm(self.u1, 'hg.fork.none')
        user_model.grant_perm(self.u1, 'hg.fork.repository')

        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        # this user will have inherited less permissions from default user
        assert u1_auth.permissions['global'] == set([
                              'hg.create.repository',
                              'hg.fork.repository',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read', 'hg.create.write_on_repogroup.true'])

    def test_inactive_user_group_does_not_affect_global_permissions(self):
        # Add user to inactive user group, set specific permissions on user
        # group and and verify it really is inactive.
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        # enable fork and create on user group
        user_group_model.revoke_perm(self.ug1, perm='hg.create.none')
        user_group_model.grant_perm(self.ug1, perm='hg.create.repository')
        user_group_model.revoke_perm(self.ug1, perm='hg.fork.none')
        user_group_model.grant_perm(self.ug1, perm='hg.fork.repository')

        user_model = UserModel()
        # disable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.repository')
        user_model.grant_perm(usr, 'hg.create.none')
        user_model.revoke_perm(usr, 'hg.fork.repository')
        user_model.grant_perm(usr, 'hg.fork.none')

        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)

        assert u1_auth.permissions['global'] == set(['hg.create.none', 'hg.fork.none',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read',
                              'hg.create.write_on_repogroup.true'])

    def test_inactive_user_group_does_not_affect_global_permissions_inverse(self):
        # Add user to inactive user group, set specific permissions on user
        # group and and verify it really is inactive.
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        # disable fork and create on user group
        user_group_model.revoke_perm(self.ug1, perm='hg.create.repository')
        user_group_model.grant_perm(self.ug1, perm='hg.create.none')
        user_group_model.revoke_perm(self.ug1, perm='hg.fork.repository')
        user_group_model.grant_perm(self.ug1, perm='hg.fork.none')

        user_model = UserModel()
        # enable fork and create on default user
        usr = 'default'
        user_model.revoke_perm(usr, 'hg.create.none')
        user_model.grant_perm(usr, 'hg.create.repository')
        user_model.revoke_perm(usr, 'hg.fork.none')
        user_model.grant_perm(usr, 'hg.fork.repository')

        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)

        assert u1_auth.permissions['global'] == set(['hg.create.repository', 'hg.fork.repository',
                              'hg.register.manual_activate',
                              'hg.extern_activate.auto',
                              'repository.read', 'group.read',
                              'usergroup.read',
                              'hg.create.write_on_repogroup.true'])

    def test_inactive_user_group_does_not_affect_repo_permissions(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        # note: make u2 repo owner rather than u1, because the owner always has
        # admin permissions
        self.test_repo = fixture.create_repo(name='myownrepo',
                                             repo_type='hg',
                                             cur_user=self.u2)

        # enable admin access for user group on repo
        RepoModel().grant_user_group_permission(self.test_repo,
                                                group_name=self.ug1,
                                                perm='repository.admin')
        # enable only write access for default user on repo
        RepoModel().grant_user_permission(self.test_repo,
                                          user='default',
                                          perm='repository.write')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.write'

    def test_inactive_user_group_does_not_affect_repo_permissions_inverse(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        # note: make u2 repo owner rather than u1, because the owner always has
        # admin permissions
        self.test_repo = fixture.create_repo(name='myownrepo',
                                             repo_type='hg',
                                             cur_user=self.u2)

        # enable only write access for user group on repo
        RepoModel().grant_user_group_permission(self.test_repo,
                                                group_name=self.ug1,
                                                perm='repository.write')
        # enable admin access for default user on repo
        RepoModel().grant_user_permission(self.test_repo,
                                          user='default',
                                          perm='repository.admin')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.admin'

    def test_inactive_user_group_does_not_affect_repo_group_permissions(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        self.g1 = fixture.create_repo_group('group1', skip_if_exists=True)

        # enable admin access for user group on repo group
        RepoGroupModel().grant_user_group_permission(self.g1,
                                                     group_name=self.ug1,
                                                     perm='group.admin')
        # enable only write access for default user on repo group
        RepoGroupModel().grant_user_permission(self.g1,
                                               user='default',
                                               perm='group.write')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.write'

    def test_inactive_user_group_does_not_affect_repo_group_permissions_inverse(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        self.g1 = fixture.create_repo_group('group1', skip_if_exists=True)

        # enable only write access for user group on repo group
        RepoGroupModel().grant_user_group_permission(self.g1,
                                                     group_name=self.ug1,
                                                     perm='group.write')
        # enable admin access for default user on repo group
        RepoGroupModel().grant_user_permission(self.g1,
                                               user='default',
                                               perm='group.admin')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories_groups'].get('group1') == 'group.admin'

    def test_inactive_user_group_does_not_affect_user_group_permissions(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        self.ug2 = fixture.create_user_group('G2')

        # enable admin access for user group on user group
        UserGroupModel().grant_user_group_permission(self.ug2,
                                                     user_group=self.ug1,
                                                     perm='usergroup.admin')
        # enable only write access for default user on user group
        UserGroupModel().grant_user_permission(self.ug2,
                                               user='default',
                                               perm='usergroup.write')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['user_groups']['G1'] == 'usergroup.read'
        assert u1_auth.permissions['user_groups']['G2'] == 'usergroup.write'

    def test_inactive_user_group_does_not_affect_user_group_permissions_inverse(self):
        self.ug1 = fixture.create_user_group('G1')
        user_group_model = UserGroupModel()
        user_group_model.add_user_to_group(self.ug1, self.u1)
        user_group_model.update(self.ug1, {'users_group_active': False})

        self.ug2 = fixture.create_user_group('G2')

        # enable only write access for user group on user group
        UserGroupModel().grant_user_group_permission(self.ug2,
                                                     user_group=self.ug1,
                                                     perm='usergroup.write')
        # enable admin access for default user on user group
        UserGroupModel().grant_user_permission(self.ug2,
                                               user='default',
                                               perm='usergroup.admin')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['user_groups']['G1'] == 'usergroup.read'
        assert u1_auth.permissions['user_groups']['G2'] == 'usergroup.admin'

    def test_owner_permissions_doesnot_get_overwritten_by_group(self):
        # create repo as USER,
        self.test_repo = fixture.create_repo(name='myownrepo',
                                             repo_type='hg',
                                             cur_user=self.u1)

        # he has permissions of admin as owner
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.admin'
        # set his permission as user group, he should still be admin
        self.ug1 = fixture.create_user_group('G1')
        UserGroupModel().add_user_to_group(self.ug1, self.u1)
        RepoModel().grant_user_group_permission(self.test_repo,
                                                 group_name=self.ug1,
                                                 perm='repository.none')

        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.admin'

    def test_owner_permissions_doesnot_get_overwritten_by_others(self):
        # create repo as USER,
        self.test_repo = fixture.create_repo(name='myownrepo',
                                             repo_type='hg',
                                             cur_user=self.u1)

        # he has permissions of admin as owner
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.admin'
        # set his permission as user, he should still be admin
        RepoModel().grant_user_permission(self.test_repo, user=self.u1,
                                          perm='repository.none')
        Session().commit()
        u1_auth = AuthUser(user_id=self.u1.user_id)
        assert u1_auth.permissions['repositories']['myownrepo'] == 'repository.admin'

    def _test_def_perm_equal(self, user, change_factor=0):
        perms = UserToPerm.query() \
                .filter(UserToPerm.user == user) \
                .all()
        assert len(perms) == len(Permission.DEFAULT_USER_PERMISSIONS,)+change_factor, perms

    def test_set_default_permissions(self):
        PermissionModel().create_default_permissions(user=self.u1)
        self._test_def_perm_equal(user=self.u1)

    def test_set_default_permissions_after_one_is_missing(self):
        PermissionModel().create_default_permissions(user=self.u1)
        self._test_def_perm_equal(user=self.u1)
        # now we delete one, it should be re-created after another call
        perms = UserToPerm.query() \
                .filter(UserToPerm.user == self.u1) \
                .all()
        Session().delete(perms[0])
        Session().commit()

        self._test_def_perm_equal(user=self.u1, change_factor=-1)

        # create missing one !
        PermissionModel().create_default_permissions(user=self.u1)
        self._test_def_perm_equal(user=self.u1)

    @base.parametrize('perm,modify_to', [
        ('repository.read', 'repository.none'),
        ('group.read', 'group.none'),
        ('usergroup.read', 'usergroup.none'),
        ('hg.create.repository', 'hg.create.none'),
        ('hg.fork.repository', 'hg.fork.none'),
        ('hg.register.manual_activate', 'hg.register.auto_activate',)
    ])
    def test_set_default_permissions_after_modification(self, perm, modify_to):
        PermissionModel().create_default_permissions(user=self.u1)
        self._test_def_perm_equal(user=self.u1)

        old = Permission.get_by_key(perm)
        new = Permission.get_by_key(modify_to)
        assert old is not None
        assert new is not None

        # now modify permissions
        p = UserToPerm.query() \
                .filter(UserToPerm.user == self.u1) \
                .filter(UserToPerm.permission == old) \
                .one()
        p.permission = new
        Session().commit()

        PermissionModel().create_default_permissions(user=self.u1)
        self._test_def_perm_equal(user=self.u1)
