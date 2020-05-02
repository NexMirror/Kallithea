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
from kallithea.tests import base


@pytest.mark.skipif("'TEST_PERFORMANCE' not in os.environ", reason="skipping performance tests, set TEST_PERFORMANCE in environment if desired")
class TestVCSPerformance(base.TestController):

    def graphmod(self, repo):
        """ Simple test for running the graph_data function for profiling/testing performance. """
        from kallithea.lib.graphmod import graph_data
        dbr = Repository.get_by_repo_name(repo)
        scm_inst = dbr.scm_instance
        collection = scm_inst.get_changesets(start=0, end=None, branch_name=None)
        revs = [x.revision for x in collection]
        jsdata = graph_data(scm_inst, revs)

    def test_graphmod_hg(self, benchmark):
        benchmark(self.graphmod, base.HG_REPO)

    def test_graphmod_git(self, benchmark):
        benchmark(self.graphmod, base.GIT_REPO)
