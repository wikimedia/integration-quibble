import unittest
from unittest import mock

import quibble.test


class TestTestCommand(unittest.TestCase):

    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_on_docker_run_qunit_pass_no_sandbox(self, mock_popen, _):
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.communicate.return_value = True

        quibble.test.run_qunit(mwdir='')

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        self.assertIn('CHROMIUM_FLAGS', env)

        self.assertIn(
            '--no-sandbox', env.get('CHROMIUM_FLAGS', ''),
            'In a Docker container we must pass --no-sandbox')
