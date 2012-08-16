import os
from rhodecode.tests import *
from nose.plugins.skip import SkipTest


class TestSearchController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'))

        self.assertTrue('class="small" id="q" name="q" type="text"' in
                        response.body)
        # Test response...

    def test_empty_search(self):
        if os.path.isdir(self.index_location):
            raise SkipTest('skipped due to existing index')
        else:
            self.log_user()
            response = self.app.get(url(controller='search', action='index'),
                                    {'q': HG_REPO})
            self.assertTrue('There is no index to search in. '
                            'Please run whoosh indexer' in response.body)

    def test_normal_search(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                                {'q': 'def repo'})
        response.mustcontain('39 results')

    def test_repo_search(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                                {'q': 'repository:%s def test' % HG_REPO})

        response.mustcontain('4 results')

    def test_search_last(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                                {'q': 'last:t', 'type': 'commit'})

        response.mustcontain('2 results')

    def test_search_commit_message(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                    {'q': 'bother to ask where to fetch repo during tests',
                     'type': 'commit'})

        response.mustcontain('2 results')
        response.mustcontain('a00c1b6f5d7a6ae678fd553a8b81d92367f7ecf1')
        response.mustcontain('c6eb379775c578a95dad8ddab53f963b80894850')

    def test_search_commit_message_hg_repo(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index',
                                    search_repo=HG_REPO),
                    {'q': 'bother to ask where to fetch repo during tests',
                     'type': 'commit'})

        response.mustcontain('1 results')
        response.mustcontain('a00c1b6f5d7a6ae678fd553a8b81d92367f7ecf1')

    def test_search_commit_changed_file(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                                {'q': 'changed:tests/utils.py',
                                 'type': 'commit'})

        response.mustcontain('a00c1b6f5d7a6ae678fd553a8b81d92367f7ecf1')

    def test_search_commit_added_file(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                                {'q': 'added:README.rst',
                                 'type': 'commit'})

        response.mustcontain('2 results')
        #HG
        response.mustcontain('3803844fdbd3b711175fc3da9bdacfcd6d29a6fb')
        #GIT
        response.mustcontain('ff7ca51e58c505fec0dd2491de52c622bb7a806b')

    def test_search_author(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                    {'q': 'author:marcin@python-blog.com raw_id:b986218ba1c9b0d6a259fac9b050b1724ed8e545',
                     'type': 'commit'})

        response.mustcontain('1 results')

    def test_search_file_name(self):
        self.log_user()
        response = self.app.get(url(controller='search', action='index'),
                    {'q': 'README.rst', 'type': 'path'})

        response.mustcontain('2 results')