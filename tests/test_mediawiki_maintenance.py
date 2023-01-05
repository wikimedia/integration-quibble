import pytest
import unittest
from unittest import mock

import quibble.mediawiki.maintenance
from quibble.mediawiki.maintenance import getMaintenanceScript


class TestMediawikiMaintenance(unittest.TestCase):
    @mock.patch.dict('os.environ', {'BAR': 'foo'}, clear=True)
    @mock.patch('subprocess.Popen')
    def test_install_php_uses_os_environment(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.install([])

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertIn('BAR', env)
        self.assertEqual('foo', env['BAR'])

    @mock.patch.dict('os.environ', {'LANG': 'C'}, clear=True)
    @mock.patch('subprocess.Popen')
    def test_install_php_enforces_LANG(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.install([])

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertEqual({'LANG': 'C.UTF-8'}, env)

    @mock.patch.dict('os.environ', {'BAR': 'foo'}, clear=True)
    @mock.patch('subprocess.Popen')
    def test_update_php_uses_os_environment(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.update([])

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertEqual({'BAR': 'foo'}, env)

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
        with self.assertRaisesRegex(
            Exception, 'Update failed with exit code: 42'
        ):
            quibble.mediawiki.maintenance.update([], mwdir='test/sources')

    @mock.patch('subprocess.Popen')
    def test_rebuildlocalisationcache_default_lang_parameter(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.rebuildLocalisationCache()

        (args, kwargs) = mock_popen.call_args
        params = args[0][2:]

        self.assertEqual(['--lang', 'en'], params)

    @mock.patch('subprocess.Popen')
    def test_rebuildlocalisationcache_lang_parameter(self, mock_popen):
        mock_popen.return_value.returncode = 0
        quibble.mediawiki.maintenance.rebuildLocalisationCache(
            lang=['fr', 'zh']
        )

        (args, kwargs) = mock_popen.call_args
        params = args[0][2:]

        self.assertEqual(['--lang', 'fr,zh'], params)

    @mock.patch('subprocess.Popen')
    def test_rebuildlocalisationcache_raises_exception_on_bad_exit_code(
        self, mock_popen
    ):
        mock_popen.return_value.returncode = 43
        with self.assertRaisesRegex(
            Exception, 'rebuildLocalisationCache failed with exit code: 43'
        ):
            quibble.mediawiki.maintenance.rebuildLocalisationCache()


getMaintenanceScriptTestCases = (
    'script,args,withRunPhp,expected',
    [
        pytest.param(
            'update',
            None,
            True,
            ['php', 'maintenance/run.php', 'update'],
            id='short script',
        ),
        pytest.param(
            'update',
            None,
            False,
            ['php', 'maintenance/update.php'],
            id='short script (legacy)',
        ),
        pytest.param(
            'update.php',
            None,
            True,
            ['php', 'maintenance/run.php', 'update'],
            id='php script',
        ),
        pytest.param(
            'update.php',
            None,
            False,
            ['php', 'maintenance/update.php'],
            id='php script (legacy)',
        ),
        pytest.param(
            'foo',
            '--lang=en',
            True,
            ['php', 'maintenance/run.php', 'foo', '--lang=en'],
            id='with a single argument as string',
        ),
        pytest.param(
            'foo',
            ['--lang=fr,de'],
            True,
            ['php', 'maintenance/run.php', 'foo', '--lang=fr,de'],
            id='with argument list',
        ),
        pytest.param(
            'foo',
            ['--verbose', '--lang=fr,de'],
            True,
            ['php', 'maintenance/run.php', 'foo', '--verbose', '--lang=fr,de'],
            id='with list of multiple arguments',
        ),
    ],
)


@pytest.mark.parametrize(*getMaintenanceScriptTestCases)
def test_getMaintenanceScript(script, args, withRunPhp, expected):
    with mock.patch('os.path.exists', return_value=withRunPhp):
        if args is None:
            assert getMaintenanceScript(script) == expected
        else:
            assert getMaintenanceScript(script, args) == expected
