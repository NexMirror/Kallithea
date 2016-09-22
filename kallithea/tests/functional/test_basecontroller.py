from kallithea.tests.base import TestController, url


class TestBaseController(TestController):

    def test_banned_http_methods(self):
        self.app.request(url(controller='login', action='index'), method='PUT', status=405)
        self.app.request(url(controller='login', action='index'), method='DELETE', status=405)

    def test_banned_http_method_override(self):
        self.app.get(url(controller='login', action='index'), {'_method': 'POST'}, status=405)
        self.app.post(url(controller='login', action='index'), {'_method': 'PUT'}, status=405)
