from rhodecode.tests import *

class TestFilesController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='tip',
                                    f_path='/'))
        # Test response...
        assert '<a class="browser-dir" href="/vcs_test_hg/files/27cd5cce30c96924232dffcd24178a07ffeb5dfc/docs">docs</a>' in response.body, 'missing dir'
        assert '<a class="browser-dir" href="/vcs_test_hg/files/27cd5cce30c96924232dffcd24178a07ffeb5dfc/tests">tests</a>' in response.body, 'missing dir'
        assert '<a class="browser-dir" href="/vcs_test_hg/files/27cd5cce30c96924232dffcd24178a07ffeb5dfc/vcs">vcs</a>' in response.body, 'missing dir'
        assert '<a class="browser-file" href="/vcs_test_hg/files/27cd5cce30c96924232dffcd24178a07ffeb5dfc/.hgignore">.hgignore</a>' in response.body, 'missing file'
        assert '<a class="browser-file" href="/vcs_test_hg/files/27cd5cce30c96924232dffcd24178a07ffeb5dfc/MANIFEST.in">MANIFEST.in</a>' in response.body, 'missing file'


    def test_index_revision(self):
        self.log_user()

        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='7ba66bec8d6dbba14a2155be32408c435c5f4492',
                                    f_path='/'))



        #Test response...

        assert '<a class="browser-dir" href="/vcs_test_hg/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/docs">docs</a>' in response.body, 'missing dir'
        assert '<a class="browser-dir" href="/vcs_test_hg/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/tests">tests</a>' in response.body, 'missing dir'
        assert '<a class="browser-file" href="/vcs_test_hg/files/7ba66bec8d6dbba14a2155be32408c435c5f4492/README.rst">README.rst</a>' in response.body, 'missing file'
        assert '1.1 KiB' in response.body, 'missing size of setup.py'
        assert 'text/x-python' in response.body, 'missing mimetype of setup.py'



    def test_index_different_branch(self):
        self.log_user()

        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='97e8b885c04894463c51898e14387d80c30ed1ee',
                                    f_path='/'))



        assert """<span style="text-transform: uppercase;"><a href="#">branch: git</a></span>""" in response.body, 'missing or wrong branch info'



    def test_index_paging(self):
        self.log_user()

        for r in [(73, 'a066b25d5df7016b45a41b7e2a78c33b57adc235'),
                  (92, 'cc66b61b8455b264a7a8a2d8ddc80fcfc58c221e'),
                  (109, '75feb4c33e81186c87eac740cee2447330288412'),
                  (1, '3d8f361e72ab303da48d799ff1ac40d5ac37c67e'),
                  (0, 'b986218ba1c9b0d6a259fac9b050b1724ed8e545')]:

            response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision=r[1],
                                    f_path='/'))

            assert """@ r%s:%s""" % (r[0], r[1][:12]) in response.body, 'missing info about current revision'

    def test_file_source(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='index',
                                    repo_name=HG_REPO,
                                    revision='27cd5cce30c96924232dffcd24178a07ffeb5dfc',
                                    f_path='vcs/nodes.py'))

        #test or history
        assert """<optgroup label="Changesets">
<option selected="selected" value="8911406ad776fdd3d0b9932a2e89677e57405a48">r167:8911406ad776</option>
<option value="aa957ed78c35a1541f508d2ec90e501b0a9e3167">r165:aa957ed78c35</option>
<option value="48e11b73e94c0db33e736eaeea692f990cb0b5f1">r140:48e11b73e94c</option>
<option value="adf3cbf483298563b968a6c673cd5bde5f7d5eea">r126:adf3cbf48329</option>
<option value="6249fd0fb2cfb1411e764129f598e2cf0de79a6f">r113:6249fd0fb2cf</option>
<option value="75feb4c33e81186c87eac740cee2447330288412">r109:75feb4c33e81</option>
<option value="9a4dc232ecdc763ef2e98ae2238cfcbba4f6ad8d">r108:9a4dc232ecdc</option>
<option value="595cce4efa21fda2f2e4eeb4fe5f2a6befe6fa2d">r107:595cce4efa21</option>
<option value="4a8bd421fbc2dfbfb70d85a3fe064075ab2c49da">r104:4a8bd421fbc2</option>
<option value="57be63fc8f85e65a0106a53187f7316f8c487ffa">r102:57be63fc8f85</option>
<option value="5530bd87f7e2e124a64d07cb2654c997682128be">r101:5530bd87f7e2</option>
<option value="e516008b1c93f142263dc4b7961787cbad654ce1">r99:e516008b1c93</option>
<option value="41f43fc74b8b285984554532eb105ac3be5c434f">r93:41f43fc74b8b</option>
<option value="cc66b61b8455b264a7a8a2d8ddc80fcfc58c221e">r92:cc66b61b8455</option>
<option value="73ab5b616b3271b0518682fb4988ce421de8099f">r91:73ab5b616b32</option>
<option value="e0da75f308c0f18f98e9ce6257626009fdda2b39">r82:e0da75f308c0</option>
<option value="fb2e41e0f0810be4d7103bc2a4c7be16ee3ec611">r81:fb2e41e0f081</option>
<option value="602ae2f5e7ade70b3b66a58cdd9e3e613dc8a028">r76:602ae2f5e7ad</option>
<option value="a066b25d5df7016b45a41b7e2a78c33b57adc235">r73:a066b25d5df7</option>
<option value="637a933c905958ce5151f154147c25c1c7b68832">r61:637a933c9059</option>
<option value="0c21004effeb8ce2d2d5b4a8baf6afa8394b6fbc">r60:0c21004effeb</option>
<option value="a1f39c56d3f1d52d5fb5920370a2a2716cd9a444">r59:a1f39c56d3f1</option>
<option value="97d32df05c715a3bbf936bf3cc4e32fb77fe1a7f">r58:97d32df05c71</option>
<option value="08eaf14517718dccea4b67755a93368341aca919">r57:08eaf1451771</option>
<option value="22f71ad265265a53238359c883aa976e725aa07d">r56:22f71ad26526</option>
<option value="97501f02b7b4330924b647755663a2d90a5e638d">r49:97501f02b7b4</option>
<option value="86ede6754f2b27309452bb11f997386ae01d0e5a">r47:86ede6754f2b</option>
<option value="014c40c0203c423dc19ecf94644f7cac9d4cdce0">r45:014c40c0203c</option>
<option value="ee87846a61c12153b51543bf860e1026c6d3dcba">r30:ee87846a61c1</option>
<option value="9bb326a04ae5d98d437dece54be04f830cf1edd9">r26:9bb326a04ae5</option>
<option value="536c1a19428381cfea92ac44985304f6a8049569">r24:536c1a194283</option>
<option value="dc5d2c0661b61928834a785d3e64a3f80d3aad9c">r8:dc5d2c0661b6</option>
<option value="3803844fdbd3b711175fc3da9bdacfcd6d29a6fb">r7:3803844fdbd3</option>
</optgroup>
<optgroup label="Branches">
<option value="27cd5cce30c96924232dffcd24178a07ffeb5dfc">default</option>
<option value="97e8b885c04894463c51898e14387d80c30ed1ee">git</option>
<option value="2e6a2bf9356ca56df08807f4ad86d480da72a8f4">web</option>
</optgroup>
<optgroup label="Tags">
<option value="27cd5cce30c96924232dffcd24178a07ffeb5dfc">tip</option>
<option value="fd4bdb5e9b2a29b4393a4ac6caef48c17ee1a200">0.1.4</option>
<option value="17544fbfcd33ffb439e2b728b5d526b1ef30bfcf">0.1.3</option>
<option value="a7e60bff65d57ac3a1a1ce3b12a70f8a9e8a7720">0.1.2</option>
<option value="eb3a60fc964309c1a318b8dfe26aa2d1586c85ae">0.1.1</option>
</optgroup>""" in response.body


        assert """<div class="commit">"Partially implemented #16. filecontent/commit message/author/node name are safe_unicode now.
In addition some other __str__ are unicode as well
Added test for unicode
Improved test to clone into uniq repository.
removed extra unicode conversion in diff."</div>""" in response.body

        assert """<span style="text-transform: uppercase;"><a href="#">branch: default</a></span>""" in response.body, 'missing or wrong branch info'

    def test_file_annotation(self):
        self.log_user()
        response = self.app.get(url(controller='files', action='annotate',
                                    repo_name=HG_REPO,
                                    revision='27cd5cce30c96924232dffcd24178a07ffeb5dfc',
                                    f_path='vcs/nodes.py'))

        print response.body
        assert """<optgroup label="Changesets">
<option selected="selected" value="8911406ad776fdd3d0b9932a2e89677e57405a48">r167:8911406ad776</option>
<option value="aa957ed78c35a1541f508d2ec90e501b0a9e3167">r165:aa957ed78c35</option>
<option value="48e11b73e94c0db33e736eaeea692f990cb0b5f1">r140:48e11b73e94c</option>
<option value="adf3cbf483298563b968a6c673cd5bde5f7d5eea">r126:adf3cbf48329</option>
<option value="6249fd0fb2cfb1411e764129f598e2cf0de79a6f">r113:6249fd0fb2cf</option>
<option value="75feb4c33e81186c87eac740cee2447330288412">r109:75feb4c33e81</option>
<option value="9a4dc232ecdc763ef2e98ae2238cfcbba4f6ad8d">r108:9a4dc232ecdc</option>
<option value="595cce4efa21fda2f2e4eeb4fe5f2a6befe6fa2d">r107:595cce4efa21</option>
<option value="4a8bd421fbc2dfbfb70d85a3fe064075ab2c49da">r104:4a8bd421fbc2</option>
<option value="57be63fc8f85e65a0106a53187f7316f8c487ffa">r102:57be63fc8f85</option>
<option value="5530bd87f7e2e124a64d07cb2654c997682128be">r101:5530bd87f7e2</option>
<option value="e516008b1c93f142263dc4b7961787cbad654ce1">r99:e516008b1c93</option>
<option value="41f43fc74b8b285984554532eb105ac3be5c434f">r93:41f43fc74b8b</option>
<option value="cc66b61b8455b264a7a8a2d8ddc80fcfc58c221e">r92:cc66b61b8455</option>
<option value="73ab5b616b3271b0518682fb4988ce421de8099f">r91:73ab5b616b32</option>
<option value="e0da75f308c0f18f98e9ce6257626009fdda2b39">r82:e0da75f308c0</option>
<option value="fb2e41e0f0810be4d7103bc2a4c7be16ee3ec611">r81:fb2e41e0f081</option>
<option value="602ae2f5e7ade70b3b66a58cdd9e3e613dc8a028">r76:602ae2f5e7ad</option>
<option value="a066b25d5df7016b45a41b7e2a78c33b57adc235">r73:a066b25d5df7</option>
<option value="637a933c905958ce5151f154147c25c1c7b68832">r61:637a933c9059</option>
<option value="0c21004effeb8ce2d2d5b4a8baf6afa8394b6fbc">r60:0c21004effeb</option>
<option value="a1f39c56d3f1d52d5fb5920370a2a2716cd9a444">r59:a1f39c56d3f1</option>
<option value="97d32df05c715a3bbf936bf3cc4e32fb77fe1a7f">r58:97d32df05c71</option>
<option value="08eaf14517718dccea4b67755a93368341aca919">r57:08eaf1451771</option>
<option value="22f71ad265265a53238359c883aa976e725aa07d">r56:22f71ad26526</option>
<option value="97501f02b7b4330924b647755663a2d90a5e638d">r49:97501f02b7b4</option>
<option value="86ede6754f2b27309452bb11f997386ae01d0e5a">r47:86ede6754f2b</option>
<option value="014c40c0203c423dc19ecf94644f7cac9d4cdce0">r45:014c40c0203c</option>
<option value="ee87846a61c12153b51543bf860e1026c6d3dcba">r30:ee87846a61c1</option>
<option value="9bb326a04ae5d98d437dece54be04f830cf1edd9">r26:9bb326a04ae5</option>
<option value="536c1a19428381cfea92ac44985304f6a8049569">r24:536c1a194283</option>
<option value="dc5d2c0661b61928834a785d3e64a3f80d3aad9c">r8:dc5d2c0661b6</option>
<option value="3803844fdbd3b711175fc3da9bdacfcd6d29a6fb">r7:3803844fdbd3</option>
</optgroup>
<optgroup label="Branches">
<option value="27cd5cce30c96924232dffcd24178a07ffeb5dfc">default</option>
<option value="97e8b885c04894463c51898e14387d80c30ed1ee">git</option>
<option value="2e6a2bf9356ca56df08807f4ad86d480da72a8f4">web</option>
</optgroup>
<optgroup label="Tags">
<option value="27cd5cce30c96924232dffcd24178a07ffeb5dfc">tip</option>
<option value="fd4bdb5e9b2a29b4393a4ac6caef48c17ee1a200">0.1.4</option>
<option value="17544fbfcd33ffb439e2b728b5d526b1ef30bfcf">0.1.3</option>
<option value="a7e60bff65d57ac3a1a1ce3b12a70f8a9e8a7720">0.1.2</option>
<option value="eb3a60fc964309c1a318b8dfe26aa2d1586c85ae">0.1.1</option>
</optgroup>""" in response.body, 'missing or wrong history in annotation'

        assert """<span style="text-transform: uppercase;"><a href="#">branch: default</a></span>""" in response.body, 'missing or wrong branch info'
