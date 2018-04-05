import unittest
from unittest import mock

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
