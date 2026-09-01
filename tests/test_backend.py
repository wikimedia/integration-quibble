import json
import os
import shutil
import socket
from unittest import mock
from unittest.mock import ANY
import urllib.request

from pytest import mark
import pytest
from quibble.backend import getDatabase, get_backend, _tcp_wait
from quibble.backend import DatabaseServer
from quibble.backend import ChromeWebDriver
from quibble.backend import PhpWebserver
from quibble.backend import ExternalWebserver
from quibble.backend import MySQL
from quibble.backend import Postgres
from quibble.backend import Memcached

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
PHPDOCROOT = os.path.join(FIXTURES_DIR, 'phpdocroot')


class TestBackendRegistry:
    def test_recognizes_mysql(self):
        get_backend(DatabaseServer, 'mysql')
        get_backend(DatabaseServer, 'MySQL')

    def test_recognizes_sqlite(self):
        get_backend(DatabaseServer, 'sqlite')

    def test_raises_an_exception_on_unknown_db(self):
        with pytest.raises(
            match="^Backend .*DatabaseServer.*" + "not supported: fakedbengine"
        ):
            get_backend(DatabaseServer, 'fakeDBengine')

    def test_getDatabase(self):
        getDatabase('mysql', '/tmp/db', '/tmp/dump', '/tmp/log')


class TestDatabaseServer:
    @mock.patch('quibble.backend.os.makedirs')
    @mock.patch('quibble.backend.tempfile.TemporaryDirectory')
    def test_creates_basedir(self, mock_makedirs, _):
        DatabaseServer(base_dir='/tmp/booo').start()
        assert (
            mock_makedirs.called is True
        ), 'Must try to create the database base directory'

    @mock.patch('quibble.backend.os.makedirs')
    @mock.patch('quibble.backend.tempfile.TemporaryDirectory')
    def test_honor_basedir_and_prefix(self, mock_makedirs, _):
        DatabaseServer(base_dir='/tmp/booo').start()
        (args, kwargs) = mock_makedirs.call_args
        assert kwargs == {
            'dir': '/tmp/booo',
            'prefix': 'quibble-databaseserver-',
        }

    @mock.patch('quibble.backend.os.makedirs')
    @mock.patch('quibble.backend.tempfile.TemporaryDirectory')
    def test_basedir_is_made_absolute(self, mock_makedirs, _):
        DatabaseServer(base_dir='data').start()
        (args, kwargs) = mock_makedirs.call_args
        assert kwargs.get('dir') == os.path.join(os.getcwd(), 'data')


class TestChromeWebDriver:
    @mock.patch('quibble.backend._stream_relay', return_value=True)
    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_on_docker_pass_no_sandbox(self, mock_popen, *mocks):
        ChromeWebDriver().start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        assert 'CHROMIUM_FLAGS' in env

        assert '--no-sandbox' in env.get(
            'CHROMIUM_FLAGS', ''
        ), 'In a Docker container we must pass --no-sandbox'

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('quibble.backend._stream_relay', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_without_display_env_pass_headless(self, mock_popen, *mocks):
        ChromeWebDriver().start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        assert 'CHROMIUM_FLAGS' in env

        assert '--headless' in env.get(
            'CHROMIUM_FLAGS', ''
        ), 'Without DISPLAY, we must run headlessly with --headless'

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('quibble.backend._stream_relay', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_explicit_display(self, mock_popen, *mocks):
        ChromeWebDriver(display=':42').start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        assert 'DISPLAY' in env
        assert env.get('DISPLAY') == ':42'
        assert 'CHROMIUM_FLAGS' in env
        assert '--headless' not in env.get('CHROMIUM_FLAGS', '')

        assert (
            'DISPLAY' not in os.environ
        ), 'Must not have set DISPLAY when previously not set'

    @mock.patch.dict(os.environ, {'DISPLAY': ':30'})
    @mock.patch('quibble.backend._stream_relay', return_value=True)
    @mock.patch('subprocess.Popen')
    def test_restore_display(self, mock_popen, *mocks):
        ChromeWebDriver(display=':42').start()
        assert os.environ['DISPLAY'] == ':30'


class TestExternalWebserverEngine:
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_start_does_not_invoke_any_command(self, mock_popen):
        ExternalWebserver().start()
        mock_popen.assert_not_called()

    @mock.patch('quibble.backend._tcp_wait')
    def test_start_does_not_uses_tcp_wait(self, _tcp_wait):
        ExternalWebserver().start()
        _tcp_wait.assert_not_called()


class TestPhpWebserver:
    def assertServerRespond(self, flavor, url):
        with urllib.request.urlopen(url) as resp:
            assert (
                resp.read().decode()
                == "Built-in %s server reached.\n" % flavor
            )

    @mark.integration
    def test_PhpWebserver_listens_on_specific_ip(self):
        # Loopback interface has 127.0.0.1/8, so we can pick any IP address in
        # that range.
        url = 'http://127.0.0.2:4880'
        with PhpWebserver(mwdir=PHPDOCROOT, url=url):
            self.assertServerRespond('zend', url)

    @mark.integration
    def test_server_respond(self):
        url = 'http://127.0.0.1:4881'
        with PhpWebserver(mwdir=PHPDOCROOT, url=url):
            self.assertServerRespond('zend', url)

    @mark.integration
    def test_has_os_environment_variables(self):
        with mock.patch.dict(
            'quibble.backend.os.environ',
            {
                'MW_INSTALL_PATH': '/tmp/mw',
                'MW_LOG_DIR': '/tmp/log',
                'LOG_DIR': '/tmp/log',
            },
            clear=True,
        ):
            url = 'http://127.0.0.1:4885'
            with PhpWebserver(mwdir=PHPDOCROOT, url=url):
                env_url = url + '/env.php'
                with urllib.request.urlopen(env_url) as resp:
                    env_resp = resp.read().decode()
                    server_env = json.loads(env_resp)

        assert 'MW_INSTALL_PATH' in server_env
        assert 'MW_LOG_DIR' in server_env
        assert 'LOG_DIR' in server_env

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_php_workers_default(self, mock_popen):
        with mock.patch('quibble.backend._stream_relay'):
            PhpWebserver(mwdir=PHPDOCROOT, url='http://example.org').start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        assert 'PHP_CLI_SERVER_WORKERS' not in env

    @mock.patch.dict(os.environ, clear=True)
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_php_with_four_workers(self, mock_popen):
        with mock.patch('quibble.backend._stream_relay'):
            PhpWebserver(
                mwdir=PHPDOCROOT, url='http://example.org', workers=4
            ).start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})
        assert 'PHP_CLI_SERVER_WORKERS' in env
        assert env['PHP_CLI_SERVER_WORKERS'] == '4'

    @mock.patch('quibble.backend.subprocess.Popen')
    def test_php_workers_from_env(self, mock_popen):
        with mock.patch.dict(
            'quibble.backend.os.environ',
            {
                'PHP_CLI_SERVER_WORKERS': '42',
            },
            clear=True,
        ):
            with mock.patch('quibble.backend._stream_relay'):
                PhpWebserver(
                    mwdir=PHPDOCROOT, url='http://example.org'
                ).start()

        (args, kwargs) = mock_popen.call_args
        env = kwargs.get('env', {})

        assert 'PHP_CLI_SERVER_WORKERS' in env
        assert env['PHP_CLI_SERVER_WORKERS'] == '42'


class TestMySQL:
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_install_db_exception(self, mock_popen):
        mock_popen.return_value.communicate.return_value = ('some output', '')
        mock_popen.return_value.returncode = 42
        mysql = MySQL()
        # The root dir is normalized initialized by start() which we do not
        # need to invoke for the purpose of this test.
        with mock.patch('tempfile.TemporaryDirectory'):
            mysql._init_rootdir('/tmp/base_dir')

        with pytest.raises(match='FAILED \\(42\\): some output'):
            mysql._install_db()

    @mock.patch('quibble.backend.MySQL._install_db')
    @mock.patch('quibble.backend.subprocess.Popen')
    def test_createwikidb_exception(self, mock_popen, _):
        mock_popen.return_value.communicate.return_value = (
            'some output',
            None,
        )
        mock_popen.return_value.returncode = 42
        with pytest.raises(match='FAILED \\(42\\): some output'):
            MySQL()._createwikidb()


@mark.skipif(
    not shutil.which('pg_virtualenv'),
    reason='Requires pg_virtualenv PostgreSQL command',
)
class TestPostgres:
    @mark.integration
    def test_it_starts(self):
        pg = Postgres()
        with pg:
            assert (
                os.path.exists(pg.socket) is True
            ), 'PostgreSQL socket has been created'


@mark.skipif(
    not shutil.which('memcached'),
    reason='Requires memcached command',
)
class TestMemcached:
    @mark.integration
    def test_it_starts(self):
        # Get a free port to listen on
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            (addr, free_port) = s.getsockname()
        mc = Memcached(port=free_port)

        with mock.patch(
            'quibble.backend._tcp_wait', side_effect=_tcp_wait
        ) as tcp_wait:
            with mc:
                tcp_wait.assert_called_once_with(
                    host=ANY, port=free_port, timeout=ANY
                )
