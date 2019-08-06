from kallithea.model.db import UserSshKeys
from kallithea.tests.base import TestController
from kallithea.tests.fixture import Fixture


fixture = Fixture()

public_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQC6Ycnc2oUZHQnQwuqgZqTTdMDZD7ataf3JM7oG2Fw8JR6cdmz4QZLe5mfDwaFwG2pWHLRpVqzfrD/Pn3rIO++bgCJH5ydczrl1WScfryV1hYMJ/4EzLGM657J1/q5EI+b9SntKjf4ax+KP322L0TNQGbZUHLbfG2MwHMrYBQpHUQ== kallithea@localhost'


class TestUserSshKeys(TestController):

    def test_fingerprint_generation(self):
        key_model = UserSshKeys()
        key_model.public_key = public_key
        expected = 'Ke3oUCNJM87P0jJTb3D+e3shjceP2CqMpQKVd75E9I8'
        assert expected == key_model.fingerprint
