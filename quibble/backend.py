# Copyright 2018 Antoine "hashar" Musso
# Copyright 2018 Wikimedia Foundation Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import json
import logging
import os
import pwd
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib

import quibble

backend_registry = {}


def _tcp_wait(host, port, timeout=3):
    step = 0
    delay = 0.1  # seconds
    socket_timeout = 1  # seconds
    connected = False
    while step < timeout:
        try:
            s = socket.socket()
            s.settimeout(socket_timeout)
            s.connect((host, int(port)))
            connected = True
            break
        except (ConnectionAbortedError, ConnectionRefusedError):
            step = step + delay
            time.sleep(delay)
        finally:
            s.close()

    if not connected:
        raise TimeoutError(
            'Could not connect to port %s after %s seconds' % (port, timeout)
        )


def backend(interface, key):
    """Register a backend class by name, for a given interface class."""

    def _register_backend(backend_class):
        if not issubclass(backend_class, interface):
            raise Exception(
                'Registered backend "%s" does not extend %s'
                % (backend_class, interface)
            )

        interface_name = str(interface)
        if interface_name not in backend_registry:
            backend_registry[interface_name] = {}
        backend_registry[interface_name][key] = backend_class

        return backend_class

    return _register_backend


def get_backend(interface, key):
    key = key.lower()
    interface = str(interface)
    if key in backend_registry[interface]:
        return backend_registry[interface][key]

    raise Exception('Backend %s not supported: %s' % (interface, key))


def web_backend(key):
    return backend(WebserverEngine, key)


def db_backend(key):
    return backend(DatabaseServer, key)


def getDatabase(engine, db_dir, dump_dir):
    '''Set up a database backend, without starting it.'''
    dbclass = get_backend(DatabaseServer, engine)
    db = dbclass(base_dir=db_dir, dump_dir=dump_dir)
    db.type = engine
    return db


def getWebserver(engine, mw_install_path, web_url, kwargs={}):
    webclass = get_backend(WebserverEngine, engine)
    backend = webclass(mwdir=mw_install_path, url=web_url, **kwargs)
    return backend


def _stream_relay(process, stream, log_function):
    thread = threading.Thread(
        target=_stream_to_log, args=(process, stream, log_function)
    )
    thread.start()
    return thread


def _stream_to_log(process, stream, log_function):
    while True:
        line = stream.readline()
        if not line:
            break
        log_function(line.rstrip())


class BackendServer:

    server = None

    def __init__(self):
        self.log = logging.getLogger('backend.%s' % self.__class__.__name__)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        pass

    def stop(self):
        if self.server is not None:
            self.log.info('Terminating %s', self.__class__.__name__)
            self.server.terminate()
            try:
                self.server.wait(2)
            except subprocess.TimeoutExpired:
                self.server.kill()  # SIGKILL
            finally:
                self.server = None


class DatabaseServer(BackendServer):

    dump_dir = None

    def __init__(self, base_dir=None, dump_dir=None):
        super(DatabaseServer, self).__init__()
        self.base_dir = base_dir
        self.dump_dir = dump_dir

    def _init_rootdir(self, base_dir):
        # Create a temporary data directory
        prefix = 'quibble-%s-' % self.__class__.__name__.lower()

        if base_dir is not None:
            base_dir = os.path.abspath(base_dir)
            os.makedirs(base_dir, exist_ok=True)

        # Create and hold a reference
        self._tmpdir = tempfile.TemporaryDirectory(dir=base_dir, prefix=prefix)
        self.rootdir = self._tmpdir.name
        self.log.debug('Root dir: %s', self.rootdir)

    def start(self):
        self._init_rootdir(self.base_dir)

    def stop(self):
        if self.dump_dir:
            self.dump()
        super(DatabaseServer, self).stop()

    def dump(self):
        self.log.warning(
            '%s does not support dumping database', self.__class__.__name__
        )


@db_backend('postgres')
class Postgres(DatabaseServer):
    def __init__(self, base_dir=None, dump_dir=None):
        super(Postgres, self).__init__(base_dir, dump_dir)

    def start(self):
        super(Postgres, self).start()

        self.conffile = os.path.join(self.rootdir, 'conf')
        self.socket = os.path.join(self.rootdir, 'socket')

        # Start pg_virtualenv and save configuration settings
        self.server = subprocess.Popen(
            [
                # fmt: off
                'pg_virtualenv',
                # Option for pg_createcluster
                '-c',
                '--socketdir=%s' % self.socket,
                'python3',
                '-m', 'quibble.pg_virtualenv_hook'
                # fmt: on
            ],
            env={'QUIBBLE_TMPFILE': self.conffile},
        )

        while not os.path.exists(self.conffile):
            if self.server.poll() is not None:
                raise Exception(
                    'Postgres failed during startup (%s)'
                    % self.server.returncode
                )
            time.sleep(1)

        with open(self.conffile) as f:
            conf = json.load(f)

        self.user = conf['PGUSER']
        self.password = conf['PGPASSWORD']
        self.dbname = conf['PGDATABASE']
        self.dbserver = self.socket
        self.hook_pid = conf['PID']
        self.log.info('Postgres is ready')

    def stop(self):
        # Send a signal to the hook since it's waiting on one
        os.kill(self.hook_pid, signal.SIGUSR1)
        super(Postgres, self).stop()


@db_backend('mysql')
class MySQL(DatabaseServer):
    def __init__(
        self,
        base_dir=None,
        dump_dir=None,
        user='wikiuser',
        password='secret',
        dbname='wikidb',
        dbserver='localhost',
    ):
        super(MySQL, self).__init__(base_dir, dump_dir)

        self.user = user
        self.password = password
        self.dbname = dbname
        self.socket = None
        self.dbserver = dbserver

    def _install_db(self):
        self.log.info('Initializing MySQL data directory')
        p = subprocess.Popen(
            [
                'mysql_install_db',
                '--datadir=%s' % self.rootdir,
                '--user=%s' % pwd.getpwuid(os.getuid())[0],
            ],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        outs, errs = p.communicate()
        if p.returncode != 0:
            raise Exception("FAILED (%s): %s" % (p.returncode, outs))

    def _createwikidb(self):
        """Create a database and necessary grants.
        Will drop existing database if it already exists."""
        self.log.info('Creating the wiki database and grant')
        mysql_cmd = ['mysql', '--user=root']
        if self.socket:
            mysql_cmd.append('--socket=%s' % self.socket)
        p = subprocess.Popen(
            mysql_cmd,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        grant = (
            "DROP DATABASE IF EXISTS %s;"
            "CREATE DATABASE %s;"
            "GRANT ALL ON %s.* TO '%s'@'localhost'"
            "IDENTIFIED BY '%s';\n"
            % (self.dbname, self.dbname, self.dbname, self.user, self.password)
        )
        outs, errs = p.communicate(input=grant)
        if p.returncode != 0:
            raise Exception("FAILED (%s): %s" % (p.returncode, outs))

    def start(self):
        self.log.info('Starting MySQL')
        super(MySQL, self).start()

        self.errorlog = os.path.join(self.rootdir, 'error.log')
        self.pidfile = os.path.join(self.rootdir, 'mysqld.pid')
        self.socket = os.path.join(self.rootdir, 'socket')
        self.dbserver = 'localhost:' + self.socket

        self._install_db()

        self.server = subprocess.Popen(
            [
                '/usr/sbin/mysqld',  # fixme drop path
                '--skip-networking',
                '--datadir=%s' % self.rootdir,
                '--log-error=%s' % self.errorlog,
                '--pid-file=%s' % self.pidfile,
                '--socket=%s' % self.socket,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        while not os.path.exists(self.socket):
            if self.server.poll() is not None:
                with open(self.errorlog) as errlog:
                    print(errlog.read())
                raise Exception(
                    "MySQL died during startup (%s)" % self.server.returncode
                )
            self.log.info("Waiting for MySQL socket")
            time.sleep(1)

        self._createwikidb()
        self.log.info('MySQL is ready')

    def dump(self):
        dumpfile = os.path.join(self.dump_dir, 'mysqldump.sql')
        self.log.info('Dumping database to %s', dumpfile)

        mysqldump = open(dumpfile, 'wb')
        subprocess.Popen(
            [
                'mysqldump',
                '--socket=%s' % self.socket,
                '--user=root',
                '--all-databases',
            ],
            stdin=subprocess.PIPE,
            stdout=mysqldump,
            stderr=subprocess.STDOUT,
        ).wait()

    def __str__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            self.socket if self.socket else "(no socket)",
        )


@db_backend('sqlite')
class SQLite(DatabaseServer):
    def __init__(self, base_dir=None, dump_dir=None, dbname='wikidb'):
        super(SQLite, self).__init__(base_dir, dump_dir)

        self.dbname = dbname


class ChromeWebDriver(BackendServer):
    def __init__(self, display=None, port=4444, url_base='/wd/hub'):
        super(ChromeWebDriver, self).__init__()

        self.display = display
        self.port = port
        self.url_base = url_base

    def start(self):
        self.log.info('Starting Chromedriver')
        try:
            prev_display = os.environ.get('DISPLAY', None)
            if self.display:
                # We need DISPLAY in the env for chromium_flags()
                os.environ.update({'DISPLAY': self.display})
            env = {
                'CHROMIUM_FLAGS': quibble.chromium_flags(),
                'PATH': os.environ.get('PATH'),
            }

            if self.display is not None:
                # Pass it to chromedriver
                env.update({'DISPLAY': self.display})

            self.server = subprocess.Popen(
                [
                    'chromedriver',
                    '--port=%s' % self.port,
                    '--url-base=%s' % self.url_base,
                ],
                env=env,
                universal_newlines=True,
                bufsize=1,  # line buffered
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _stream_relay(self.server, self.server.stderr, self.log.warning)

        finally:
            if prev_display:
                os.environ.update({'DISPLAY': prev_display})
            elif prev_display is None and self.display:
                del os.environ['DISPLAY']

    def __str__(self):
        return "<ChromeWebDriver {}>".format(self.display)


class WebserverEngine(BackendServer):
    default_url = None

    def __init__(self, url=None, mwdir=None):
        super(WebserverEngine, self).__init__()

        self.url = url or self.default_url
        self.mwdir = mwdir

        parsed_url = urllib.parse.urlparse(self.url)
        self.host = parsed_url.hostname
        self.port = parsed_url.port

    def start(self):
        if self.server:
            _stream_relay(self.server, self.server.stderr, self.log.info)

        if self.host and self.port:
            _tcp_wait(host=self.host, port=self.port, timeout=5)


@web_backend('external')
class ExternalWebserver(WebserverEngine):
    def start(self):
        self.log.info('Not starting a webserver.')

    def __str__(self):
        return '<ExternalWebserver %s %s>' % (self.url, self.mwdir)


@web_backend('php')
class PhpWebserver(WebserverEngine):
    default_url = 'http://127.0.0.1:9412'
    default_router = 'maintenance/dev/includes/router.php'

    def __init__(self, router=default_router, workers=False, **kwargs):
        self.router = router
        self.workers = workers

        super(PhpWebserver, self).__init__(**kwargs)

    def start(self):
        server_cmd = [
            # fmt: off
            'php',
            '-d', 'output_buffering=Off',
            '-S', '%s:%s' % (self.host, self.port),
            # fmt: on
        ]
        if self.router:
            server_cmd.append(os.path.join(self.mwdir, self.router))

        server_env = {}
        if self.workers:
            server_env = {
                'PHP_CLI_SERVER_WORKERS': str(self.workers),
            }
        server_env.update(os.environ)

        self.server = subprocess.Popen(
            server_cmd,
            cwd=self.mwdir,
            universal_newlines=True,
            bufsize=1,  # line buffered
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=server_env,
        )
        super(PhpWebserver, self).start()

    def __str__(self):
        if not self.workers:
            return '<PhpWebserver %s %s>' % (self.url, self.mwdir)
        else:
            return '<PhpWebserver %s %s with %s workers>' % (
                self.url,
                self.mwdir,
                self.workers,
            )


class Xvfb(BackendServer):
    def __init__(self, display=':94'):
        super(Xvfb, self).__init__()
        self.display = display

    def start(self):
        self.log.info('Starting Xvfb on display %s', self.display)
        self.server = subprocess.Popen(
            [
                # fmt: off
                'Xvfb', self.display,
                '-screen', '0', '1280x1024x24',
                '-nolisten', 'tcp',
                '-nolisten', 'unix',
                # fmt: on
            ]
        )

    def __str__(self):
        return "<Xvfb {}>".format(self.display)
