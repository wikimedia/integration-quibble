import unittest
from unittest import mock

import quibble.mediawiki.maintenance


class TestMediawikiMaintenance(unittest.TestCase):

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('subprocess.Popen')
    def test_update_php_default_to_no_mw_install_path(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.update([])

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertNotIn('MW_INSTALL_PATH', env)

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('subprocess.Popen')
    def test_update_php_sets_mw_install_path(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.update([], mwdir='test/sources')

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertIn('MW_INSTALL_PATH', env)
        self.assertEqual(env['MW_INSTALL_PATH'], 'test/sources')

    @mock.patch('subprocess.Popen')
    def test_update_php_raises_exception_on_bad_exit_code(self, mock_popen):
        mock_popen.return_value.returncode = 42
        with self.assertRaisesRegexp(Exception,
                                     'Update failed with exit code: 42'):
            quibble.mediawiki.maintenance.update([], mwdir='test/sources')
