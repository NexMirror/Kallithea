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
from kallithea.tests.base import HG_REPO, HG_TEST_REVISION, TestController


class TestHgApi(_BaseTestApi, TestController):
    REPO = HG_REPO
    REPO_TYPE = 'hg'
    TEST_REVISION = HG_TEST_REVISION
    TEST_PR_SRC = u'4f7e2131323e0749a740c0a56ab68ae9269c562a'
    TEST_PR_DST = u'92831aebf2f8dd4879e897024b89d09af214df1c'
    TEST_PR_REVISIONS = [u'720bbdb27665d6262b313e8a541b654d0cbd5b27',
                         u'f41649565a9e89919a588a163e717b4084f8a3b1',
                         u'94f45ed825a113e61af7e141f44ca578374abef0',
                         u'fef5bfe1dc17611d5fb59a7f6f95c55c3606f933',
                         u'4f7e2131323e0749a740c0a56ab68ae9269c562a']
