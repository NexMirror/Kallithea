from kallithea.tests import *
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.db import ChangesetStatus

# shorthands
STATUS_APPROVED = ChangesetStatus.STATUS_APPROVED
STATUS_REJECTED = ChangesetStatus.STATUS_REJECTED
STATUS_NOT_REVIEWED = ChangesetStatus.STATUS_NOT_REVIEWED
STATUS_UNDER_REVIEW = ChangesetStatus.STATUS_UNDER_REVIEW

class ChangesetStatusMock(object):

    def __init__(self, status):
        self.status = status

S = ChangesetStatusMock

class TestChangesetStatusCalculation(BaseTestCase):

    def setUp(self):
        self.m = ChangesetStatusModel()

    @parameterized.expand([
        ('empty list', STATUS_UNDER_REVIEW, []),
        ('approve', STATUS_APPROVED, [S(STATUS_APPROVED)]),
        ('approve2', STATUS_APPROVED, [S(STATUS_APPROVED), S(STATUS_APPROVED)]),
        ('approve_reject', STATUS_REJECTED, [S(STATUS_APPROVED), S(STATUS_REJECTED)]),
        ('approve_underreview', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), S(STATUS_UNDER_REVIEW)]),
        ('approve_notreviewed', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), S(STATUS_NOT_REVIEWED)]),
        ('underreview', STATUS_UNDER_REVIEW, [S(STATUS_UNDER_REVIEW), S(STATUS_UNDER_REVIEW)]),
        ('reject', STATUS_REJECTED, [S(STATUS_REJECTED)]),
        ('reject_underreview', STATUS_REJECTED, [S(STATUS_REJECTED), S(STATUS_UNDER_REVIEW)]),
        ('reject_notreviewed', STATUS_REJECTED, [S(STATUS_REJECTED), S(STATUS_NOT_REVIEWED)]),
        ('notreviewed', STATUS_UNDER_REVIEW, [S(STATUS_NOT_REVIEWED)]),
        ('approve_none', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), None]),
        ('approve2_none', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), S(STATUS_APPROVED), None]),
        ('approve_reject_none', STATUS_REJECTED, [S(STATUS_APPROVED), S(STATUS_REJECTED), None]),
        ('approve_underreview_none', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), S(STATUS_UNDER_REVIEW), None]),
        ('approve_notreviewed_none', STATUS_UNDER_REVIEW, [S(STATUS_APPROVED), S(STATUS_NOT_REVIEWED), None]),
        ('underreview_none', STATUS_UNDER_REVIEW, [S(STATUS_UNDER_REVIEW), S(STATUS_UNDER_REVIEW), None]),
        ('reject_none', STATUS_REJECTED, [S(STATUS_REJECTED), None]),
        ('reject_underreview_none', STATUS_REJECTED, [S(STATUS_REJECTED), S(STATUS_UNDER_REVIEW), None]),
        ('reject_notreviewed_none', STATUS_REJECTED, [S(STATUS_REJECTED), S(STATUS_NOT_REVIEWED), None]),
        ('notreviewed_none', STATUS_UNDER_REVIEW, [S(STATUS_NOT_REVIEWED), None]),
    ])
    def test_result(self, name, expected_result, statuses):
        result = self.m._calculate_status(statuses)
        self.assertEqual(result, expected_result)
