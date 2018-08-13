import json
import os
import shutil
import unittest
from unittest import mock
import urllib.request

from nose.plugins.attrib import attr
from quibble.backend import getDBClass
from quibble.backend import ChromeWebDriver
from quibble.backend import DevWebServer
from quibble.backend import MySQL
from quibble import php_is_hhvm

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
PHPDOCROOT = os.path.join(FIXTURES_DIR, 'phpdocroot')


class TestGetDBClass(unittest.TestCase):

    def test_recognizes_mysql(self):
        getDBClass('mysql')
        getDBClass('MySQL')

    def test_recognizes_sqlite(self):
        getDBClass('sqlite')

    def test_raises_an_exception_on_non_db_backendb(self):
        with self.assertRaisesRegex(
            Exception, '^Requested database engine "BackendServer" '
            'is not a database server'
        ):
            getDBClass('BackendServer')

    def test_raises_an_exception_on_unknown_db(self):
        with self.assertRaisesRegex(Exception,
                                    '^Backend database engine not supported'):
            getDBClass('fakeDBengine')


class TestChromeWebDriver(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch('quibble.backend.stream_relay', return_value=True)
        self.addCleanup(patcher.stop)
        patcher.start()

    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_on_docker_pass_no_sandbox(self, mock_popen, _):
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
        ChromeWebDriver(display=':42').start()
        self.assertEqual(os.environ['DISPLAY'], ':30')


class TestDevWebServer(unittest.TestCase):

    def assertServerRespond(self, flavor, url):
        with urllib.request.urlopen(url) as resp:
            self.assertEqual("Built-in %s server reached.\n" % flavor,
                             resp.read().decode())

    @attr('integration')
    # assumes "php" is Zend. Would fail if it happens to be HHVM
    @mock.patch('quibble.backend.subprocess.check_output',
                return_value=b'')
    def test_using_php(self, _):
        http_port = '4881'
        php_is_hhvm.cache_clear()
        with DevWebServer(mwdir=PHPDOCROOT, port=http_port, router=None):
            self.assertServerRespond('zend', 'http://127.0.0.1:%s' % http_port)

    @attr('integration')
    @mock.patch('quibble.backend.subprocess.check_output',
                return_value=b'HipHop')
    @unittest.skipUnless(shutil.which('hhvm'), 'requires HHVM')
    def test_using_hhvm(self, _):
        http_port = '4882'
        php_is_hhvm.cache_clear()
        with DevWebServer(mwdir=PHPDOCROOT, port=http_port, router=None):
            self.assertServerRespond('hhvm', 'http://127.0.0.1:%s' % http_port)

    @attr('integration')
    # assumes "php" is Zend. Would fail if it happens to be HHVM
    @mock.patch('quibble.backend.subprocess.check_output',
                return_value=b'')
    def test_php_sets_svg_content_type(self, _):
        http_port = '4883'
        php_is_hhvm.cache_clear()
        with DevWebServer(mwdir=PHPDOCROOT, port=http_port, router=None):
            svg_url = 'http://127.0.0.1:%s/image.svg' % http_port
            with urllib.request.urlopen(svg_url) as resp:
                headers = resp.info()
                self.assertIn('Content-Type', headers)
                self.assertEquals(headers['Content-Type'], 'image/svg+xml')

    @attr('integration')
    @mock.patch('quibble.backend.subprocess.check_output',
                return_value=b'HipHop')
    @unittest.skipUnless(shutil.which('hhvm'), 'requires HHVM')
    def test_hhvm_sets_svg_content_type(self, _):
        http_port = '4884'
        php_is_hhvm.cache_clear()
        with DevWebServer(mwdir=PHPDOCROOT, port=http_port, router=None):
            svg_url = 'http://127.0.0.1:%s/image.svg' % http_port
            with urllib.request.urlopen(svg_url) as resp:
                headers = resp.info()
                self.assertIn('Content-Type', headers)
                self.assertEquals(headers['Content-Type'], 'image/svg+xml')

    @attr('integration')
    def test_has_os_environment_variables(self):
        http_port = '4885'
        php_is_hhvm.cache_clear()

        with mock.patch.dict('quibble.backend.os.environ',
                             {
                                 'MW_INSTALL_PATH': '/tmp/mw',
                                 'MW_LOG_DIR': '/tmp/log',
                                 'LOG_DIR': '/tmp/log',
                             },
                             clear=True):
            with DevWebServer(mwdir=PHPDOCROOT, port=http_port, router=None):
                env_url = 'http://127.0.0.1:%s/env.php' % http_port
                with urllib.request.urlopen(env_url) as resp:
                    env_resp = resp.read().decode()
                    server_env = json.loads(env_resp)

        self.assertIn('MW_INSTALL_PATH', server_env)
        self.assertIn('MW_LOG_DIR', server_env)
        self.assertIn('LOG_DIR', server_env)


class TestMySQL(unittest.TestCase):

    @mock.patch('quibble.backend.subprocess.Popen')
    def test_install_db_exception(self, mock_popen):
        mock_popen.return_value.communicate.return_value = (
            'some output')
        mock_popen.return_value.returncode = 42
        with self.assertRaises(Exception, msg='FAILED (42): some output'):
            MySQL()._install_db()

    @mock.patch('quibble.backend.MySQL._install_db')
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_createwikidb_exception(self, mock_popen, _):
        mock_popen.return_value.communicate.return_value = (
            'some output', None)
        mock_popen.return_value.returncode = 42
        with self.assertRaises(Exception, msg='FAILED (42): some output'):
            MySQL()._createwikidb()
