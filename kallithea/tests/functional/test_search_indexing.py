import mock

from kallithea import CONFIG
from kallithea.config.conf import INDEX_FILENAMES
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.tests.base import *
from kallithea.tests.fixture import Fixture, create_test_index


fixture = Fixture()


def init_indexing_test(repo):
    prev = fixture.commit_change(repo.repo_name,
                                 filename='this_should_be_unique_filename.txt',
                                 content='this_should_be_unique_content\n',
                                 message='this_should_be_unique_commit_log',
                                 vcs_type='hg',
                                 newfile=True)

def init_stopword_test(repo):
    prev = fixture.commit_change(repo.repo_name,
                                 filename='this/is/it',
                                 content='def test\n',
                                 message='bother to ask where - in folder',
                                 vcs_type='hg',
                                 newfile=True)
    prev = fixture.commit_change(repo.repo_name,
                                 filename='join.us',
                                 content='def test\n',
                                 message='bother to ask where - top level',
                                 author='this is it <this-is-it@foo.bar.com>',
                                 vcs_type='hg',
                                 parent=prev,
                                 newfile=True)


repos = [
    # reponame,              init func or fork base, groupname
    (u'indexing_test',       init_indexing_test,     None),
    (u'indexing_test-fork',  u'indexing_test',       None),
    (u'group/indexing_test', u'indexing_test',       u'group'),
    (u'this-is-it',          u'indexing_test',       None),
    (u'indexing_test-foo',   u'indexing_test',       None),
    (u'stopword_test',       init_stopword_test,     None),
]


# map: name => id
repoids = {}
groupids = {}


def rebuild_index(full_index):
    with mock.patch('kallithea.lib.indexers.daemon.log.debug',
                    lambda *args, **kwargs: None):
        # The more revisions managed repositories have, the more
        # memory capturing "log.debug()" output in "indexers.daemon"
        # requires. This may cause unintentional failure of subsequent
        # tests, if ENOMEM at forking "git" prevents from rebuilding
        # index for search.
        # Therefore, "log.debug()" is disabled regardless of logging
        # level while rebuilding index.
        # (FYI, ENOMEM occurs at forking "git" with python 2.7.3,
        # Linux 3.2.78-1 x86_64, 3GB memory, and no ulimit
        # configuration for memory)
        create_test_index(TESTS_TMP_PATH, CONFIG, full_index=full_index)


class TestSearchControllerIndexing(TestController):
    @classmethod
    def setup_class(cls):
        for reponame, init_or_fork, groupname in repos:
            if groupname and groupname not in groupids:
                group = fixture.create_repo_group(groupname)
                groupids[groupname] = group.group_id
            if callable(init_or_fork):
                repo = fixture.create_repo(reponame,
                                           repo_group=groupname)
                init_or_fork(repo)
            else:
                repo = fixture.create_fork(init_or_fork, reponame,
                                           repo_group=groupname)
            repoids[reponame] = repo.repo_id

        # treat "it" as indexable filename
        filenames_mock = list(INDEX_FILENAMES)
        filenames_mock.append('it')
        with mock.patch('kallithea.lib.indexers.daemon.INDEX_FILENAMES',
                        filenames_mock):
            rebuild_index(full_index=False) # only for newly added repos

    @classmethod
    def teardown_class(cls):
        # delete in reversed order, to delete fork destination at first
        for reponame, init_or_fork, groupname in reversed(repos):
            RepoModel().delete(repoids[reponame])

        for reponame, init_or_fork, groupname in reversed(repos):
            if groupname in groupids:
                RepoGroupModel().delete(groupids.pop(groupname),
                                        force_delete=True)

        Session().commit()
        Session.remove()

        rebuild_index(full_index=True) # rebuild fully for subsequent tests

    @parametrize('reponame', [
        (u'indexing_test'),
        (u'indexing_test-fork'),
        (u'group/indexing_test'),
        (u'this-is-it'),
        (u'*-fork'),
        (u'group/*'),
    ])
    @parametrize('searchtype,query,hit', [
        ('content', 'this_should_be_unique_content', 1),
        ('commit', 'this_should_be_unique_commit_log', 1),
        ('path', 'this_should_be_unique_filename.txt', 1),
    ])
    def test_repository_tokenization(self, reponame, searchtype, query, hit):
        self.log_user()

        q = 'repository:%s %s' % (reponame, query)
        response = self.app.get(url(controller='search', action='index'),
                                {'q': q, 'type': searchtype})
        response.mustcontain('>%d results' % hit)

    @parametrize('reponame', [
        (u'indexing_test'),
        (u'indexing_test-fork'),
        (u'group/indexing_test'),
        (u'this-is-it'),
    ])
    @parametrize('searchtype,query,hit', [
        ('content', 'this_should_be_unique_content', 1),
        ('commit', 'this_should_be_unique_commit_log', 1),
        ('path', 'this_should_be_unique_filename.txt', 1),
    ])
    def test_searching_under_repository(self, reponame, searchtype, query, hit):
        self.log_user()

        response = self.app.get(url(controller='search', action='index',
                                    repo_name=reponame),
                                {'q': query, 'type': searchtype})
        response.mustcontain('>%d results' % hit)

    @parametrize('searchtype,query,hit', [
        ('content', 'path:this/is/it def test', 1),
        ('commit', 'added:this/is/it bother to ask where', 1),
        # this condition matches against files below, because
        # "path:" condition is also applied on "repository path".
        # - "this/is/it" in "stopword_test" repo
        # - "this_should_be_unique_filename.txt" in "this-is-it" repo
        ('path', 'this/is/it', 2),

        ('content', 'extension:us', 1),
        ('path', 'extension:us', 1),
    ])
    def test_filename_stopword(self, searchtype, query, hit):
        response = self.app.get(url(controller='search', action='index'),
                                {'q': query, 'type': searchtype})

        response.mustcontain('>%d results' % hit)

    @parametrize('searchtype,query,hit', [
        # matching against both 2 files
        ('content', 'owner:"this is it"', 0),
        ('content', 'owner:this-is-it', 0),
        ('path', 'owner:"this is it"', 0),
        ('path', 'owner:this-is-it', 0),

        # matching against both 2 revisions
        ('commit', 'owner:"this is it"', 0),
        ('commit', 'owner:"this-is-it"', 0),

        # matching against only 1 revision
        ('commit', 'author:"this is it"', 1),
        ('commit', 'author:"this-is-it"', 1),
    ])
    def test_mailaddr_stopword(self, searchtype, query, hit):
        response = self.app.get(url(controller='search', action='index'),
                                {'q': query, 'type': searchtype})

        response.mustcontain('>%d results' % hit)
