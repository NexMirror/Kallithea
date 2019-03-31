from kallithea.lib.vcs.utils.filesize import filesizeformat


class TestFilesizeformat(object):

    def test_bytes(self):
        assert filesizeformat(10) == '10 B'

    def test_kilobytes(self):
        assert filesizeformat(1024 * 2) == '2 KB'

    def test_megabytes(self):
        assert filesizeformat(1024 * 1024 * 2.3) == '2.3 MB'

    def test_gigabytes(self):
        assert filesizeformat(1024 * 1024 * 1024 * 12.92) == '12.92 GB'

    def test_that_function_respects_sep_parameter(self):
        assert filesizeformat(1, '') == '1B'
