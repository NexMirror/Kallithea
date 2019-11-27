# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest

from kallithea.model.db import Repository
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.scm import ScmModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture


fixture = Fixture()

@pytest.fixture
def custom_settings(set_test_settings):
    # overwrite DEFAULT_CLONE_SSH = 'ssh://{system_user}@{hostname}/{repo}'
    set_test_settings(
        ('clone_ssh_tmpl', 'ssh://ssh_user@ssh_hostname/{repo}', 'unicode'),
        )


class TestSummaryController(TestController):

    def test_index_hg(self, custom_settings):
        self.log_user()
        ID = Repository.get_by_repo_name(HG_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name=HG_REPO))

        # repo type
        response.mustcontain(
            """<span class="label label-repo" title="Mercurial repository">hg"""
        )
        # public/private
        response.mustcontain(
            """<i class="icon-globe">"""
        )
        # clone URLs
        response.mustcontain(
            '''<input class="form-control" size="80" readonly="readonly" value="http://%s@localhost:80/%s"/>''' %
            (TEST_USER_ADMIN_LOGIN, HG_REPO)
        )
        response.mustcontain(
            '''<input class="form-control" size="80" readonly="readonly" value="http://%s@localhost:80/_%s"/>''' %
            (TEST_USER_ADMIN_LOGIN, ID)
        )
        response.mustcontain(
            '''<input id="ssh_url" class="form-control" size="80" readonly="readonly" value="ssh://ssh_user@ssh_hostname/%s"/>''' %
            (HG_REPO)
        )


    def test_index_git(self, custom_settings):
        self.log_user()
        ID = Repository.get_by_repo_name(GIT_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name=GIT_REPO))

        # repo type
        response.mustcontain(
            """<span class="label label-repo" title="Git repository">git"""
        )
        # public/private
        response.mustcontain(
            """<i class="icon-globe">"""
        )
        # clone URLs
        response.mustcontain(
            '''<input class="form-control" size="80" readonly="readonly" value="http://%s@localhost:80/%s"/>''' %
            (TEST_USER_ADMIN_LOGIN, GIT_REPO)
        )
        response.mustcontain(
            '''<input class="form-control" size="80" readonly="readonly" value="http://%s@localhost:80/_%s"/>''' %
            (TEST_USER_ADMIN_LOGIN, ID)
        )
        response.mustcontain(
            '''<input id="ssh_url" class="form-control" size="80" readonly="readonly" value="ssh://ssh_user@ssh_hostname/%s"/>''' %
            (GIT_REPO)
        )

    def test_index_by_id_hg(self):
        self.log_user()
        ID = Repository.get_by_repo_name(HG_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='_%s' % ID))

        # repo type
        response.mustcontain(
            """<span class="label label-repo" title="Mercurial repository">hg"""
        )
        # public/private
        response.mustcontain(
            """<i class="icon-globe">"""
        )

    def test_index_by_repo_having_id_path_in_name_hg(self):
        self.log_user()
        fixture.create_repo(name=u'repo_1')
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='repo_1'))

        try:
            response.mustcontain("repo_1")
        finally:
            RepoModel().delete(Repository.get_by_repo_name(u'repo_1'))
            Session().commit()

    def test_index_by_id_git(self):
        self.log_user()
        ID = Repository.get_by_repo_name(GIT_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='_%s' % ID))

        # repo type
        response.mustcontain(
            """<span class="label label-repo" title="Git repository">git"""
        )
        # public/private
        response.mustcontain(
            """<i class="icon-globe">"""
        )

    def _enable_stats(self, repo):
        r = Repository.get_by_repo_name(repo)
        r.enable_statistics = True
        Session().commit()

    def test_index_trending(self):
        self.log_user()
        # codes stats
        self._enable_stats(HG_REPO)

        ScmModel().mark_for_invalidation(HG_REPO)
        # generate statistics first
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=HG_REPO))
        response = self.app.get(url(controller='summary', action='index',
                                    repo_name=HG_REPO))
        response.mustcontain(
            '[["py", {"count": 68, "desc": ["Python"]}], '
            '["rst", {"count": 16, "desc": ["Rst"]}], '
            '["css", {"count": 2, "desc": ["Css"]}], '
            '["sh", {"count": 2, "desc": ["Bash"]}], '
            '["bat", {"count": 1, "desc": ["Batch"]}], '
            '["cfg", {"count": 1, "desc": ["Ini"]}], '
            '["html", {"count": 1, "desc": ["EvoqueHtml", "Html"]}], '
            '["ini", {"count": 1, "desc": ["Ini"]}], '
            '["js", {"count": 1, "desc": ["Javascript"]}], '
            '["makefile", {"count": 1, "desc": ["Makefile", "Makefile"]}]]',
        )

    def test_index_statistics(self):
        self.log_user()
        # codes stats
        self._enable_stats(HG_REPO)

        ScmModel().mark_for_invalidation(HG_REPO)
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=HG_REPO))

    def test_index_trending_git(self):
        self.log_user()
        # codes stats
        self._enable_stats(GIT_REPO)

        ScmModel().mark_for_invalidation(GIT_REPO)
        # generate statistics first
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=GIT_REPO))
        response = self.app.get(url(controller='summary', action='index',
                                    repo_name=GIT_REPO))
        response.mustcontain(
            '[["py", {"count": 68, "desc": ["Python"]}], '
            '["rst", {"count": 16, "desc": ["Rst"]}], '
            '["css", {"count": 2, "desc": ["Css"]}], '
            '["sh", {"count": 2, "desc": ["Bash"]}], '
            '["bat", {"count": 1, "desc": ["Batch"]}], '
            '["cfg", {"count": 1, "desc": ["Ini"]}], '
            '["html", {"count": 1, "desc": ["EvoqueHtml", "Html"]}], '
            '["ini", {"count": 1, "desc": ["Ini"]}], '
            '["js", {"count": 1, "desc": ["Javascript"]}], '
            '["makefile", {"count": 1, "desc": ["Makefile", "Makefile"]}]]',
        )

    def test_index_statistics_git(self):
        self.log_user()
        # codes stats
        self._enable_stats(GIT_REPO)

        ScmModel().mark_for_invalidation(GIT_REPO)
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=GIT_REPO))
