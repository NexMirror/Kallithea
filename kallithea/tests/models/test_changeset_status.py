from kallithea.tests import *
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.db import ChangesetStatus as CS

class CSM(object): # ChangesetStatusMock

    def __init__(self, status):
        self.status = status

class TestChangesetStatusCalculation(BaseTestCase):

    def setUp(self):
        self.m = ChangesetStatusModel()

    @parameterized.expand([
        ('empty list', CS.STATUS_UNDER_REVIEW, []),
        ('approve', CS.STATUS_APPROVED, [CSM(CS.STATUS_APPROVED)]),
        ('approve2', CS.STATUS_APPROVED, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_APPROVED)]),
        ('approve_reject', CS.STATUS_REJECTED, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_REJECTED)]),
        ('approve_underreview', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_UNDER_REVIEW)]),
        ('approve_notreviewed', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_NOT_REVIEWED)]),
        ('underreview', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_UNDER_REVIEW), CSM(CS.STATUS_UNDER_REVIEW)]),
        ('reject', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED)]),
        ('reject_underreview', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED), CSM(CS.STATUS_UNDER_REVIEW)]),
        ('reject_notreviewed', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED), CSM(CS.STATUS_NOT_REVIEWED)]),
        ('notreviewed', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_NOT_REVIEWED)]),
        ('approve_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), None]),
        ('approve2_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_APPROVED), None]),
        ('approve_reject_none', CS.STATUS_REJECTED, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_REJECTED), None]),
        ('approve_underreview_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_UNDER_REVIEW), None]),
        ('approve_notreviewed_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_APPROVED), CSM(CS.STATUS_NOT_REVIEWED), None]),
        ('underreview_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_UNDER_REVIEW), CSM(CS.STATUS_UNDER_REVIEW), None]),
        ('reject_none', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED), None]),
        ('reject_underreview_none', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED), CSM(CS.STATUS_UNDER_REVIEW), None]),
        ('reject_notreviewed_none', CS.STATUS_REJECTED, [CSM(CS.STATUS_REJECTED), CSM(CS.STATUS_NOT_REVIEWED), None]),
        ('notreviewed_none', CS.STATUS_UNDER_REVIEW, [CSM(CS.STATUS_NOT_REVIEWED), None]),
    ])
    def test_result(self, name, expected_result, statuses):
        result = self.m._calculate_status(statuses)
        self.assertEqual(result, expected_result)
