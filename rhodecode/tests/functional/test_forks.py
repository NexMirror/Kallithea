from rhodecode.tests import *

from rhodecode.model.db import Repository
from rhodecode.model.repo import RepoModel
from rhodecode.model.user import UserModel
from rhodecode.model.meta import Session


class TestForksController(TestController):

    def setUp(self):
        self.username = u'forkuser'
        self.password = u'qweqwe'
        self.u1 = UserModel().create_or_update(
            username=self.username, password=self.password,
            email=u'fork_king@rhodecode.org', firstname=u'u1', lastname=u'u1'
        )
        Session().commit()

    def tearDown(self):
        Session().delete(self.u1)
        Session().commit()

    def test_index(self):
        self.log_user()
        repo_name = HG_REPO
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain("""There are no forks yet""")

    def test_no_permissions_to_fork(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN,
                            TEST_USER_REGULAR_PASS)['user_id']
        user_model = UserModel()
        user_model.revoke_perm(usr, 'hg.fork.repository')
        user_model.grant_perm(usr, 'hg.fork.none')
        u = UserModel().get(usr)
        u.inherit_default_permissions = False
        Session().commit()
        # try create a fork
        repo_name = HG_REPO
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), {}, status=403)

    def test_index_with_fork_hg(self):
        self.log_user()

        # create a fork
        fork_name = HG_FORK
        description = 'fork of vcs test'
        repo_name = HG_REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        response = self.app.post(url(controller='forks',
                                     action='fork_create',
                                    repo_name=repo_name),
                                    {'repo_name': fork_name,
                                     'repo_group': '',
                                     'fork_parent_id': org_repo.repo_id,
                                     'repo_type': 'hg',
                                     'description': description,
                                     'private': 'False',
                                     'landing_rev': 'tip'})

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain(
            """<a href="/%s">%s</a>""" % (fork_name, fork_name)
        )

        #remove this fork
        response = self.app.delete(url('repo', repo_name=fork_name))

    def test_index_with_fork_git(self):
        self.log_user()

        # create a fork
        fork_name = GIT_FORK
        description = 'fork of vcs test'
        repo_name = GIT_REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        response = self.app.post(url(controller='forks',
                                     action='fork_create',
                                    repo_name=repo_name),
                                    {'repo_name': fork_name,
                                     'repo_group': '',
                                     'fork_parent_id': org_repo.repo_id,
                                     'repo_type': 'git',
                                     'description': description,
                                     'private': 'False',
                                     'landing_rev': 'tip'})

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain(
            """<a href="/%s">%s</a>""" % (fork_name, fork_name)
        )

        #remove this fork
        response = self.app.delete(url('repo', repo_name=fork_name))

    def test_z_fork_create(self):
        self.log_user()
        fork_name = HG_FORK
        description = 'fork of vcs test'
        repo_name = HG_REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        response = self.app.post(url(controller='forks', action='fork_create',
                                    repo_name=repo_name),
                                    {'repo_name': fork_name,
                                     'repo_group':'',
                                     'fork_parent_id':org_repo.repo_id,
                                     'repo_type':'hg',
                                     'description':description,
                                     'private':'False',
                                     'landing_rev': 'tip'})

        #test if we have a message that fork is ok
        self.checkSessionFlash(response,
                'Forked repository %s as <a href="/%s">%s</a>'
                % (repo_name, fork_name, fork_name))

        #test if the fork was created in the database
        fork_repo = Session().query(Repository)\
            .filter(Repository.repo_name == fork_name).one()

        self.assertEqual(fork_repo.repo_name, fork_name)
        self.assertEqual(fork_repo.fork.repo_name, repo_name)

        #test if fork is visible in the list ?
        response = response.follow()

        response = self.app.get(url(controller='summary', action='index',
                                    repo_name=fork_name))

        response.mustcontain('Fork of %s' % repo_name)

    def test_zz_fork_permission_page(self):
        usr = self.log_user(self.username, self.password)['user_id']
        repo_name = HG_REPO

        forks = Session().query(Repository)\
            .filter(Repository.fork_id != None)\
            .all()
        self.assertEqual(1, len(forks))

        # set read permissions for this
        RepoModel().grant_user_permission(repo=forks[0],
                                          user=usr,
                                          perm='repository.read')
        Session().commit()

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain('<div style="padding:5px 3px 3px 42px;">fork of vcs test</div>')

    def test_zzz_fork_permission_page(self):
        usr = self.log_user(self.username, self.password)['user_id']
        repo_name = HG_REPO

        forks = Session().query(Repository)\
            .filter(Repository.fork_id != None)\
            .all()
        self.assertEqual(1, len(forks))

        # set none
        RepoModel().grant_user_permission(repo=forks[0],
                                          user=usr, perm='repository.none')
        Session().commit()
        # fork shouldn't be there
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))
        response.mustcontain('There are no forks yet')
