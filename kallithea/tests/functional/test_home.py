# -*- coding: utf-8 -*-
import json

from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()


class TestHomeController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='home', action='index'))
        # if global permission is set
        response.mustcontain('Add Repository')

        response.mustcontain(
            """<span class="label label-repo" title="Git repository">git"""
        )

        response.mustcontain(
            """<span class="label label-repo" title="Mercurial repository">hg"""
        )

        # html in javascript variable:
        response.mustcontain(r'href=\"/%s\"' % HG_REPO)

        response.mustcontain(r'\x3ci class=\"icon-globe\"')

        response.mustcontain(r'\"fixes issue with having custom format for git-log\n\"')
        response.mustcontain(r'\"/%s/changeset/5f2c6ee195929b0be80749243c18121c9864a3b3\"' % GIT_REPO)

        response.mustcontain(r'\"disable security checks on hg clone for travis\"')
        response.mustcontain(r'\"/%s/changeset/96507bd11ecc815ebc6270fdf6db110928c09c1e\"' % HG_REPO)

    def test_repo_summary_with_anonymous_access_disabled(self):
        with fixture.anon_access(False):
            response = self.app.get(url(controller='summary',
                                        action='index', repo_name=HG_REPO),
                                        status=302)
            assert 'login' in response.location

    def test_index_with_anonymous_access_disabled(self):
        with fixture.anon_access(False):
            response = self.app.get(url(controller='home', action='index'),
                                    status=302)
            assert 'login' in response.location

    def test_index_page_on_groups(self):
        self.log_user()
        gr = fixture.create_repo_group(u'gr1')
        fixture.create_repo(name=u'gr1/repo_in_group', repo_group=gr)
        response = self.app.get(url('repos_group_home', group_name=u'gr1'))

        try:
            response.mustcontain(u"gr1/repo_in_group")
        finally:
            RepoModel().delete(u'gr1/repo_in_group')
            RepoGroupModel().delete(repo_group=u'gr1', force_delete=True)
            Session().commit()

    def test_users_and_groups_data(self):
        fixture.create_user('evil', firstname=u'D\'o\'ct"o"r', lastname=u'Évíl')
        fixture.create_user_group(u'grrrr', user_group_description=u"Groüp")
        response = self.app.get(url('users_and_groups_data', query=u'evi'))
        assert response.status_code == 302
        assert url('login_home') in response.location
        self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        response = self.app.get(url('users_and_groups_data', query=u'evi'))
        result = json.loads(response.body)['results']
        assert result[0].get('fname') == u'D\'o\'ct"o"r'
        assert result[0].get('lname') == u'Évíl'
        response = self.app.get(url('users_and_groups_data', key=u'evil'))
        result = json.loads(response.body)['results']
        assert result[0].get('fname') == u'D\'o\'ct"o"r'
        assert result[0].get('lname') == u'Évíl'
        response = self.app.get(url('users_and_groups_data', query=u'rrrr'))
        result = json.loads(response.body)['results']
        assert not result
        response = self.app.get(url('users_and_groups_data', types='users,groups', query=u'rrrr'))
        result = json.loads(response.body)['results']
        assert result[0].get('grname') == u'grrrr'
