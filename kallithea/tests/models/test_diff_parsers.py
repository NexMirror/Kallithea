from kallithea.tests import *
from kallithea.lib.diffs import DiffProcessor, NEW_FILENODE, DEL_FILENODE, \
    MOD_FILENODE, RENAMED_FILENODE, CHMOD_FILENODE, BIN_FILENODE, COPIED_FILENODE
from kallithea.tests.fixture import Fixture

fixture = Fixture()


DIFF_FIXTURES = {
    'hg_diff_add_single_binary_file.diff': [
        ('US Warszawa.jpg', 'A',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {NEW_FILENODE: 'new file 100755',
                  BIN_FILENODE: 'binary diff not shown'}}),
    ],
    'hg_diff_mod_single_binary_file.diff': [
        ('US Warszawa.jpg', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {MOD_FILENODE: 'modified file',
                  BIN_FILENODE: 'binary diff not shown'}}),
    ],

    'hg_diff_mod_single_file_and_rename_and_chmod.diff': [
        ('README', 'R',
         {'added': 3,
          'deleted': 0,
          'binary': False,
          'ops': {RENAMED_FILENODE: 'file renamed from README.rst to README',
                  CHMOD_FILENODE: 'modified file chmod 100755 => 100644'}}),
    ],
    'hg_diff_mod_file_and_rename.diff': [
        ('README.rst', 'R',
         {'added': 3,
          'deleted': 0,
          'binary': False,
          'ops': {RENAMED_FILENODE: 'file renamed from README to README.rst'}}),
    ],
    'hg_diff_del_single_binary_file.diff': [
        ('US Warszawa.jpg', 'D',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {DEL_FILENODE: 'deleted file',
                  BIN_FILENODE: 'binary diff not shown'}}),
    ],
    'hg_diff_chmod_and_mod_single_binary_file.diff': [
        ('gravatar.png', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {CHMOD_FILENODE: 'modified file chmod 100644 => 100755',
                  BIN_FILENODE: 'binary diff not shown'}}),
    ],
    'hg_diff_chmod.diff': [
        ('file', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {CHMOD_FILENODE: 'modified file chmod 100755 => 100644'}}),
    ],
    'hg_diff_rename_file.diff': [
        ('file_renamed', 'R',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {RENAMED_FILENODE: 'file renamed from file to file_renamed'}}),
    ],
    'hg_diff_rename_and_chmod_file.diff': [
        ('README', 'R',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {CHMOD_FILENODE: 'modified file chmod 100644 => 100755',
                  RENAMED_FILENODE: 'file renamed from README.rst to README'}}),
    ],
    'hg_diff_binary_and_normal.diff': [
        ('img/baseline-10px.png', 'A',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {NEW_FILENODE: 'new file 100644',
                  BIN_FILENODE: 'binary diff not shown'}}),
        ('img/baseline-20px.png', 'D',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {DEL_FILENODE: 'deleted file',
                  BIN_FILENODE: 'binary diff not shown'}}),
        ('index.html', 'M',
         {'added': 3,
          'deleted': 2,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('js/global.js', 'D',
         {'added': 0,
          'deleted': 75,
          'binary': False,
          'ops': {DEL_FILENODE: 'deleted file'}}),
        ('js/jquery/hashgrid.js', 'A',
         {'added': 340,
          'deleted': 0,
          'binary': False,
          'ops': {NEW_FILENODE: 'new file 100755'}}),
        ('less/docs.less', 'M',
         {'added': 34,
          'deleted': 0,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('less/scaffolding.less', 'M',
         {'added': 1,
          'deleted': 3,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('readme.markdown', 'M',
         {'added': 1,
          'deleted': 10,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
    ],
    'git_diff_chmod.diff': [
        ('work-horus.xls', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {CHMOD_FILENODE: 'modified file chmod 100644 => 100755'}})
    ],
    'git_diff_rename_file.diff': [
        ('file.xls', 'R',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {RENAMED_FILENODE: 'file renamed from work-horus.xls to file.xls'}}),
        ('files/var/www/favicon.ico/DEFAULT',
         'R',
         {'added': 0,
          'binary': True,
          'deleted': 0,
          'ops': {4: 'file renamed from files/var/www/favicon.ico to files/var/www/favicon.ico/DEFAULT',
                  6: 'modified file chmod 100644 => 100755'}})
    ],
    'git_diff_mod_single_binary_file.diff': [
        ('US Warszawa.jpg', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {MOD_FILENODE: 'modified file',
                  BIN_FILENODE: 'binary diff not shown'}})
    ],
    'git_diff_binary_and_normal.diff': [
        ('img/baseline-10px.png', 'A',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {NEW_FILENODE: 'new file 100644',
                  BIN_FILENODE: 'binary diff not shown'}}),
        ('img/baseline-20px.png', 'D',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {DEL_FILENODE: 'deleted file',
                  BIN_FILENODE: 'binary diff not shown'}}),
        ('index.html', 'M',
         {'added': 3,
          'deleted': 2,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('js/global.js', 'D',
         {'added': 0,
          'deleted': 75,
          'binary': False,
          'ops': {DEL_FILENODE: 'deleted file'}}),
        ('js/jquery/hashgrid.js', 'A',
         {'added': 340,
          'deleted': 0,
          'binary': False,
          'ops': {NEW_FILENODE: 'new file 100755'}}),
        ('less/docs.less', 'M',
         {'added': 34,
          'deleted': 0,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('less/scaffolding.less', 'M',
         {'added': 1,
          'deleted': 3,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('readme.markdown', 'M',
         {'added': 1,
          'deleted': 10,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
    ],
    'diff_with_diff_data.diff': [
        ('vcs/backends/base.py', 'M',
         {'added': 18,
          'deleted': 2,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('vcs/backends/git/repository.py', 'M',
         {'added': 46,
          'deleted': 15,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('vcs/backends/hg.py', 'M',
         {'added': 22,
          'deleted': 3,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('vcs/tests/test_git.py', 'M',
         {'added': 5,
          'deleted': 5,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
        ('vcs/tests/test_repository.py', 'M',
         {'added': 174,
          'deleted': 2,
          'binary': False,
          'ops': {MOD_FILENODE: 'modified file'}}),
    ],
    'git_diff_modify_binary_file.diff': [
        ('file.name', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {MOD_FILENODE: 'modified file',
                  BIN_FILENODE: 'binary diff not shown'}})
    ],
    'hg_diff_copy_file.diff': [
        ('file2', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {COPIED_FILENODE: 'file copied from file1 to file2'}}),
    ],
    'hg_diff_copy_and_modify_file.diff': [
        ('file3', 'M',
         {'added': 1,
          'deleted': 0,
          'binary': False,
          'ops': {COPIED_FILENODE: 'file copied from file2 to file3',
                  MOD_FILENODE: 'modified file'}}),
    ],
    'hg_diff_copy_and_chmod_file.diff': [
        ('file4', 'M',
         {'added': 0,
          'deleted': 0,
          'binary': True,
          'ops': {COPIED_FILENODE: 'file copied from file3 to file4',
                  CHMOD_FILENODE: 'modified file chmod 100644 => 100755'}}),
    ],
    'hg_diff_copy_chmod_and_edit_file.diff': [
        ('file5', 'M',
         {'added': 2,
          'deleted': 1,
          'binary': False,
          'ops': {COPIED_FILENODE: 'file copied from file4 to file5',
                  CHMOD_FILENODE: 'modified file chmod 100755 => 100644',
                  MOD_FILENODE: 'modified file'}}),
    ],
    'hg_diff_rename_space_cr.diff': [
        ('oh yes', 'R',
         {'added': 3,
          'deleted': 2,
          'binary': False,
          'ops': {RENAMED_FILENODE: 'file renamed from oh no to oh yes'}}),
    ],
}


class DiffLibTest(BaseTestCase):

    @parameterized.expand([(x,) for x in DIFF_FIXTURES])
    def test_diff(self, diff_fixture):
        diff = fixture.load_resource(diff_fixture, strip=False)
        diff_proc = DiffProcessor(diff)
        diff_proc_d = diff_proc.prepare()
        data = [(x['filename'], x['operation'], x['stats']) for x in diff_proc_d]
        expected_data = DIFF_FIXTURES[diff_fixture]
        self.assertListEqual(expected_data, data)

    def test_diff_markup(self):
        diff = fixture.load_resource('markuptest.diff', strip=False)
        diff_proc = DiffProcessor(diff)
        diff_proc_d = diff_proc.prepare()
        chunks = diff_proc_d[0]['chunks']
        self.assertFalse(chunks[0])
        #from pprint import pprint; pprint(chunks[1])
        l = ['\n']
        for d in chunks[1]:
            l.append('%(action)-7s %(new_lineno)3s %(old_lineno)3s %(line)r\n' % d)
        s = ''.join(l)
        print s
        self.assertEqual(s, r'''
context ... ... u'@@ -51,5 +51,12 @@\n'
unmod    51  51 u'<u>\t</u>begin();\n'
unmod    52  52 u'<u>\t</u>\n'
add      53     u'<u>\t</u>int foo;<u class="cr"></u>\n'
add      54     u'<u>\t</u>int bar; <u class="cr"></u>\n'
add      55     u'<u>\t</u>int baz;<u>\t</u><u class="cr"></u>\n'
add      56     u'<u>\t</u>int space; <i></i>'
add      57     u'<u>\t</u>int tab;<u>\t</u>\n'
add      58     u'<u>\t</u>\n'
unmod    59  53 u' <i></i>'
del          54 u'<u>\t</u><del>#define MAX_STEPS (48)</del>\n'
add      60     u'<u>\t</u><ins><u class="cr"></u></ins>\n'
add      61     u'<u>\t</u>#define MAX_STEPS (64)<u class="cr"></u>\n'
unmod    62  55 u'\n'
''')
