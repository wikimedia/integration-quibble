import os
import unittest
from unittest import mock

from quibble.backend import getDBClass
from quibble.backend import ChromeWebDriver


class TestGetDBClass(unittest.TestCase):

    def test_recognizes_mysql(self):
        getDBClass('mysql')
        getDBClass('MySQL')

    def test_recongizes_sqlite(self):
        getDBClass('sqlite')

    def test_raises_an_exception_on_unknown_db(self):
        with self.assertRaisesRegex(Exception,
                                    '^Backend database engine not supported'):
            getDBClass('fakeDBengine')


class TestChromeWebDriver(unittest.TestCase):

    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_on_docker_pass_no_sandbox(self, mock_popen, _):
        mock_popen.return_value.communicate.return_value = True
        ChromeWebDriver().start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        self.assertIn('CHROMIUM_FLAGS', env)

        self.assertIn(
            '--no-sandbox', env.get('CHROMIUM_FLAGS', ''),
            'In a Docker container we must pass --no-sandbox')

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('subprocess.Popen')
    def test_without_display_env_pass_headless(self, mock_popen):
        mock_popen.return_value.communicate.return_value = True
        ChromeWebDriver().start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        self.assertIn('CHROMIUM_FLAGS', env)

        self.assertIn(
            '--headless', env.get('CHROMIUM_FLAGS', ''),
            'Without DISPLAY, we must run headlessly with --headless')

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('subprocess.Popen')
    def test_explicit_display(self, mock_popen):
        mock_popen.return_value.communicate.return_value = True
        ChromeWebDriver(display=':42').start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        self.assertIn('DISPLAY', env)
        self.assertEqual(':42', env.get('DISPLAY'))
        self.assertIn('CHROMIUM_FLAGS', env)
        self.assertNotIn('--headless', env.get('CHROMIUM_FLAGS', ''))

        self.assertNotIn(
            'DISPLAY', os.environ,
            'Must not have set DISPLAY when previously not set')

    @mock.patch.dict(os.environ, {'DISPLAY': ':30'})
    @mock.patch('subprocess.Popen')
    def test_restore_display(self, mock_popen):
        mock_popen.return_value.communicate.return_value = True
        ChromeWebDriver(display=':42').start()
        self.assertEqual(os.environ['DISPLAY'], ':30')


class TestBackend2(unittest.TestCase):

    def test_foo(self):
        self.assertTrue(True)
