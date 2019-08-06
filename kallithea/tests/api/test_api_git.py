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

from kallithea.tests.api.api_base import _BaseTestApi
from kallithea.tests.base import GIT_REPO, GIT_TEST_REVISION, TestController


class TestGitApi(_BaseTestApi, TestController):
    REPO = GIT_REPO
    REPO_TYPE = 'git'
    TEST_REVISION = GIT_TEST_REVISION
    TEST_PR_SRC = u'c60f01b77c42dce653d6b1d3b04689862c261929'
    TEST_PR_DST = u'10cddef6b794696066fb346434014f0a56810218'
    TEST_PR_REVISIONS = [u'1bead5880d2dbe831762bf7fb439ba2919b75fdd',
                         u'9bcd3ecfc8832a8cd881c1c1bbe2d13ffa9d94c7',
                         u'283de4dfca8479875a1befb8d4059f3bbb725145',
                         u'c60f01b77c42dce653d6b1d3b04689862c261929']
