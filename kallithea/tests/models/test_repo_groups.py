import os

import pytest
from sqlalchemy.exc import IntegrityError

from kallithea.model import db
from kallithea.model.db import RepoGroup
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.tests import base
from kallithea.tests.fixture import Fixture


fixture = Fixture()


def _update_repo_group(id_, group_name, desc='desc', parent_id=None):
    form_data = dict(
        group_name=group_name,
        group_description=desc,
        parent_group_id=parent_id,
        )
    return RepoGroupModel().update(id_, form_data)


def _update_repo(name, **kwargs):
    if 'repo_name' not in kwargs:
        kwargs['repo_name'] = name
    if 'perms_new' not in kwargs:
        kwargs['perms_new'] = []
    if 'perms_updates' not in kwargs:
        kwargs['perms_updates'] = []
    r = RepoModel().update(name, **kwargs)
    return r


class TestRepoGroups(base.TestController):

    def setup_method(self, method):
        self.g1 = fixture.create_repo_group('test1', skip_if_exists=True)
        self.g2 = fixture.create_repo_group('test2', skip_if_exists=True)
        self.g3 = fixture.create_repo_group('test3', skip_if_exists=True)

    def teardown_method(self, method):
        Session.remove()

    def __check_path(self, *path):
        """
        Checks the path for existence !
        """
        path = [base.TESTS_TMP_PATH] + list(path)
        path = os.path.join(*path)
        return os.path.isdir(path)

    def __delete_group(self, id_):
        RepoGroupModel().delete(id_)

    def test_create_group(self):
        g = fixture.create_repo_group('newGroup')
        Session().commit()
        assert g.full_path == 'newGroup'

        assert self.__check_path('newGroup')

        # test_create_same_name_group
        with pytest.raises(IntegrityError):
            fixture.create_repo_group('newGroup')
        Session().rollback()

    def test_same_subgroup(self):
        sg1 = fixture.create_repo_group('sub1', parent_group_id=self.g1.group_id)
        assert sg1.parent_group == self.g1
        assert sg1.full_path == 'test1/sub1'
        assert self.__check_path('test1', 'sub1')

        ssg1 = fixture.create_repo_group('subsub1', parent_group_id=sg1.group_id)
        assert ssg1.parent_group == sg1
        assert ssg1.full_path == 'test1/sub1/subsub1'
        assert self.__check_path('test1', 'sub1', 'subsub1')

    def test_remove_group(self):
        sg1 = fixture.create_repo_group('deleteme')
        self.__delete_group(sg1.group_id)

        assert RepoGroup.get(sg1.group_id) is None
        assert not self.__check_path('deteteme')

        sg1 = fixture.create_repo_group('deleteme', parent_group_id=self.g1.group_id)
        self.__delete_group(sg1.group_id)

        assert RepoGroup.get(sg1.group_id) is None
        assert not self.__check_path('test1', 'deteteme')

    def test_rename_single_group(self):
        sg1 = fixture.create_repo_group('initial')

        new_sg1 = _update_repo_group(sg1.group_id, 'after')
        assert self.__check_path('after')
        assert RepoGroup.get_by_group_name('initial') is None

    def test_update_group_parent(self):

        sg1 = fixture.create_repo_group('initial', parent_group_id=self.g1.group_id)

        new_sg1 = _update_repo_group(sg1.group_id, 'after', parent_id=self.g1.group_id)
        assert self.__check_path('test1', 'after')
        assert RepoGroup.get_by_group_name('test1/initial') is None

        new_sg1 = _update_repo_group(sg1.group_id, 'after', parent_id=self.g3.group_id)
        assert self.__check_path('test3', 'after')
        assert RepoGroup.get_by_group_name('test3/initial') == None

        new_sg1 = _update_repo_group(sg1.group_id, 'hello')
        assert self.__check_path('hello')

        assert RepoGroup.get_by_group_name('hello') == new_sg1

    def test_subgrouping_with_repo(self):

        g1 = fixture.create_repo_group('g1')
        g2 = fixture.create_repo_group('g2')
        # create new repo
        r = fixture.create_repo('john')

        assert r.repo_name == 'john'
        # put repo into group
        r = _update_repo('john', repo_group=g1.group_id)
        Session().commit()
        assert r.repo_name == 'g1/john'

        _update_repo_group(g1.group_id, 'g1', parent_id=g2.group_id)
        assert self.__check_path('g2', 'g1')

        # test repo
        assert r.repo_name == db.URL_SEP.join(['g2', 'g1', r.just_name])

    def test_move_to_root(self):
        g1 = fixture.create_repo_group('t11')
        g2 = fixture.create_repo_group('t22', parent_group_id=g1.group_id)

        assert g2.full_path == 't11/t22'
        assert self.__check_path('t11', 't22')

        g2 = _update_repo_group(g2.group_id, 'g22', parent_id=None)
        Session().commit()

        assert g2.group_name == 'g22'
        # we moved out group from t1 to '' so it's full path should be 'g2'
        assert g2.full_path == 'g22'
        assert not self.__check_path('t11', 't22')
        assert self.__check_path('g22')

    def test_rename_top_level_group_in_nested_setup(self):
        g1 = fixture.create_repo_group('L1')
        g2 = fixture.create_repo_group('L2', parent_group_id=g1.group_id)
        g3 = fixture.create_repo_group('L3', parent_group_id=g2.group_id)

        r = fixture.create_repo('L1/L2/L3/L3_REPO', repo_group=g3.group_id)

        ## rename L1 all groups should be now changed
        _update_repo_group(g1.group_id, 'L1_NEW')
        Session().commit()
        assert g1.full_path == 'L1_NEW'
        assert g2.full_path == 'L1_NEW/L2'
        assert g3.full_path == 'L1_NEW/L2/L3'
        assert r.repo_name == 'L1_NEW/L2/L3/L3_REPO'

    def test_change_parent_of_top_level_group_in_nested_setup(self):
        g1 = fixture.create_repo_group('R1')
        g2 = fixture.create_repo_group('R2', parent_group_id=g1.group_id)
        g3 = fixture.create_repo_group('R3', parent_group_id=g2.group_id)
        g4 = fixture.create_repo_group('R1_NEW')

        r = fixture.create_repo('R1/R2/R3/R3_REPO', repo_group=g3.group_id)
        ## rename L1 all groups should be now changed
        _update_repo_group(g1.group_id, 'R1', parent_id=g4.group_id)
        Session().commit()
        assert g1.full_path == 'R1_NEW/R1'
        assert g2.full_path == 'R1_NEW/R1/R2'
        assert g3.full_path == 'R1_NEW/R1/R2/R3'
        assert r.repo_name == 'R1_NEW/R1/R2/R3/R3_REPO'

    def test_change_parent_of_top_level_group_in_nested_setup_with_rename(self):
        g1 = fixture.create_repo_group('X1')
        g2 = fixture.create_repo_group('X2', parent_group_id=g1.group_id)
        g3 = fixture.create_repo_group('X3', parent_group_id=g2.group_id)
        g4 = fixture.create_repo_group('X1_NEW')

        r = fixture.create_repo('X1/X2/X3/X3_REPO', repo_group=g3.group_id)

        ## rename L1 all groups should be now changed
        _update_repo_group(g1.group_id, 'X1_PRIM', parent_id=g4.group_id)
        Session().commit()
        assert g1.full_path == 'X1_NEW/X1_PRIM'
        assert g2.full_path == 'X1_NEW/X1_PRIM/X2'
        assert g3.full_path == 'X1_NEW/X1_PRIM/X2/X3'
        assert r.repo_name == 'X1_NEW/X1_PRIM/X2/X3/X3_REPO'
