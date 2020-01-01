from kallithea.tests import base


class TestFeedController(base.TestController):

    def test_rss(self):
        self.log_user()
        response = self.app.get(base.url(controller='feed', action='rss',
                                    repo_name=base.HG_REPO))

        assert response.content_type == "application/rss+xml"
        assert """<rss version="2.0">""" in response

    def test_atom(self):
        self.log_user()
        response = self.app.get(base.url(controller='feed', action='atom',
                                    repo_name=base.HG_REPO))

        assert response.content_type == """application/atom+xml"""
        assert """<?xml version="1.0" encoding="utf-8"?>""" in response
        assert """<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-us">""" in response
