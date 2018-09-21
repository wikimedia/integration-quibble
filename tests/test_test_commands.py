import unittest
from unittest import mock
from subprocess import CalledProcessError

import quibble.test


class TestTestCommand(unittest.TestCase):

    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_on_docker_run_qunit_pass_no_sandbox(self, mock_check_call, _):
        quibble.test.run_qunit(mwdir='')

        (args, kwargs) = mock_check_call.call_args
        env = kwargs.get('env', {})
        self.assertIn('CHROMIUM_FLAGS', env)

        self.assertIn(
            '--no-sandbox', env.get('CHROMIUM_FLAGS', ''),
            'In a Docker container we must pass --no-sandbox')

    @mock.patch('quibble.test.GitChangedInHead')
    @mock.patch('subprocess.check_call')
    def test_all_run_commands_pass_os_environment(
            self, mock_check_call, mock_git_changed):

        ignored_check_call = ['git']
        required_args = {
            'run_composer_test': {'mwdir': '/tmp'},
            'run_extskin': {'directory': '/tmp'},
            'run_extskin_composer': {'directory': '/tmp'},
            'run_extskin_npm': {'directory': '/tmp'},
            'run_npm_test': {'mwdir': '/tmp'},
            'run_phpunit': {'mwdir': '/tmp'},
            'run_phpunit_database': {'mwdir': '/tmp'},
            'run_phpunit_databaseless': {'mwdir': '/tmp'},
            'run_qunit': {'mwdir': '/tmp'},
            'run_webdriver': {'mwdir': '/tmp', 'display': ':0'},
        }
        run_cmds = [
            func for name, func in sorted(quibble.test.__dict__.items())
            if name.startswith('run_') and callable(func)]

        for func in run_cmds:
            with mock.patch.dict('os.environ', {'somevar': '42'}, clear=True):
                func(**required_args.get(func.__name__, []))
                (args, kwargs) = mock_check_call.call_args

                if args[0][0] in ignored_check_call:
                    continue

                env = kwargs.get('env', {})
                self.assertIn(
                    'somevar', env,
                    '%s must pass os.environ' % func.__name__)

    def test_commands(self):
        self.assertTrue(quibble.test.commands(['true'], cwd='/tmp'))
        self.assertTrue(quibble.test.commands(['true', 'true'], cwd='/tmp'))

    def test_commands_raises_exception_on_error(self):
        with self.assertRaises(CalledProcessError, msg=''):
            quibble.test.commands(['false'], cwd='/tmp')

        with self.assertRaises(CalledProcessError, msg=''):
            quibble.test.commands(['true', 'false'], cwd='/tmp')
