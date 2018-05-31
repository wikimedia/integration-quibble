import json
import logging
import os
import pwd
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

import quibble
from quibble import php_is_hhvm


def tcp_wait(port, timeout=3):
    step = 0
    delay = 0.1  # seconds
    socket_timeout = 1  # seconds
    connected = False
    while step < timeout:
        try:
            s = socket.socket()
            s.settimeout(socket_timeout)
            s.connect(('127.0.0.1', int(port)))
            connected = True
            break
        except (ConnectionAbortedError, ConnectionRefusedError):
            step = step + delay
            time.sleep(delay)
        finally:
            s.close()

    if not connected:
        raise TimeoutError(
            'Could not connect to port %s after %s seconds' % (port, timeout))


def getDBClass(engine):
    this_module = sys.modules[__name__]
    for attr in dir(this_module):
        if engine.lower() == attr.lower():
            return getattr(this_module, attr)
    raise Exception('Backend database engine not supported: %s' % engine)


def stream_relay(process, stream, log_function):
    thread = threading.Thread(
        target=stream_to_log,
        args=(process, stream, log_function))
    thread.start()
    return thread


def stream_to_log(process, stream, log_function):
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
            self.log.info('Terminating %s' % self.__class__.__name__)
            self.server.terminate()
            try:
                self.server.wait(2)
            except subprocess.TimeoutExpired:
                self.server.kill()  # SIGKILL
            finally:
                self.server = None


class Postgres(BackendServer):

    def __init__(self):
        super(Postgres, self).__init__()
        self.tmpdir = tempfile.TemporaryDirectory(prefix='quibble-postgres-')
        self.rootdir = self.tmpdir.name
        self.log.debug('Root dir: %s' % self.rootdir)

        self.conffile = os.path.join(self.rootdir, 'conf')
        self.socket = os.path.join(self.rootdir, 'socket')

    def start(self):
        # Start pg_virtualenv and save configuration settings
        self.server = subprocess.Popen([
            'pg_virtualenv',
            '-c -s %s' % self.socket,
            'python3', '-m', 'quibble.pg_virtualenv_hook'
        ], env={'QUIBBLE_TMPFILE': self.conffile})

        while not os.path.exists(self.conffile):
            if self.server.poll() is not None:
                raise Exception(
                    'Postgres failed during startup (%s)'
                    % self.server.returncode)
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

    def __del__(self):
        self.stop()
        self.tmpdir.cleanup()


class MySQL(BackendServer):

    def __init__(self, user='wikiuser', password='secret', dbname='wikidb'):
        super(MySQL, self).__init__()

        self.user = user
        self.password = password
        self.dbname = dbname

        self.tmpdir = tempfile.TemporaryDirectory(prefix='quibble-mysql-')
        self.rootdir = self.tmpdir.name
        self.log.debug('Root dir: %s' % self.rootdir)

        self.errorlog = os.path.join(self.rootdir, 'error.log')
        self.pidfile = os.path.join(self.rootdir, 'mysqld.pid')
        self.socket = os.path.join(self.rootdir, 'socket')

        if php_is_hhvm():
            self.dbserver = self.socket
        else:
            self.dbserver = 'localhost:' + self.socket

        self._install_db()

    def _install_db(self):
        self.log.info('Initializing MySQL data directory')
        p = subprocess.Popen([
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
        self.log.info('Creating the wiki database and grant')
        p = subprocess.Popen([
            'mysql',
            '--user=root',
            '--socket=%s' % self.socket,
            ],
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            )
        grant = ("CREATE DATABASE IF NOT EXISTS %s;"
                 "GRANT ALL ON %s.* TO '%s'@'localhost'"
                 "IDENTIFIED BY '%s';\n" % (
                     self.dbname, self.dbname, self.user, self.password))
        outs, errs = p.communicate(input=grant)
        if p.returncode != 0:
            raise Exception("FAILED (%s): %s" % (p.returncode, outs))

    def start(self):
        self.log.info('Starting MySQL')
        self.server = subprocess.Popen([
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
                    "MySQL died during startup (%s)" % self.server.returncode)
            self.log.info("Waiting for MySQL socket")
            time.sleep(1)
        self._createwikidb()
        self.log.info('MySQL is ready')

    def __str__(self):
        return self.socket

    def __del__(self):
        self.stop()


class SQLite(object):

    def __init__(self, dbname='wikidb'):
        self.log = logging.getLogger('backend.SQLite')

        self.dbname = dbname

        self.tmpdir = tempfile.TemporaryDirectory(prefix='quibble-sqlite-')
        self.datadir = self.tmpdir.name
        self.log.debug('Data dir: %s' % self.datadir)

    def start(self):
        # Created by MediaWiki
        pass


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

            self.server = subprocess.Popen([
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
            stream_relay(self.server, self.server.stderr, self.log.warning)

        finally:
            if prev_display:
                os.environ.update({'DISPLAY': prev_display})
            elif prev_display is None and self.display:
                del(os.environ['DISPLAY'])


class DevWebServer(BackendServer):

    def __init__(self, port=4881, mwdir=None,
                 router='maintenance/dev/includes/router.php'):
        super(DevWebServer, self).__init__()

        self.port = port
        self.mwdir = mwdir
        self.router = router

    def start(self):
        self.log.info('Starting MediaWiki built in webserver')

        if php_is_hhvm():
            server_cmd = ['hhvm', '-m', 'server', '-p', str(self.port)]
            server_cmd.extend([
                # HHVM does not set Content-Type for svg files T195634
                '-d', 'hhvm.static_file.extensions[svg]=image/svg+xml',
                ])
        else:
            server_cmd = ['php', '-S', '127.0.0.1:%s' % self.port]
            if self.router:
                server_cmd.append(
                    os.path.join(self.mwdir, self.router))

        self.server = subprocess.Popen(
            server_cmd,
            cwd=self.mwdir,
            universal_newlines=True,
            bufsize=1,  # line buffered
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=os.environ,
        )
        stream_relay(self.server, self.server.stderr, self.log.info)
        tcp_wait(port=self.port, timeout=5)

    def __str__(self):
        return 'http://127.0.0.1:%s' % self.port

    def __repr__(self):
        return '<DevWebServer :%s %s>' % (self.port, self.mwdir)

    def __del__(self):
        self.stop()


class Xvfb(BackendServer):

    def __init__(self, display=':94'):
        super(Xvfb, self).__init__()
        self.display = display

    def start(self):
        self.log.info('Starting Xvfb on display %s' % self.display)
        self.server = subprocess.Popen([
            'Xvfb', self.display,
            '-screen', '0', '1280x1024x24'
            '-ac',
            '-nolisten', 'tcp'
            ])
