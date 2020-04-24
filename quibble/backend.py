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
import sys
import tempfile
import threading
import time

import quibble


def tcp_wait(host, port, timeout=3):
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
            'Could not connect to port %s after %s seconds' % (port, timeout))


def getDBClass(engine):
    this_module = sys.modules[__name__]
    for attr in dir(this_module):
        if engine.lower() == attr.lower():
            engine_class = getattr(this_module, attr)
            if not issubclass(engine_class, DatabaseServer):
                raise Exception(
                    'Requested database engine "%s" '
                    'is not a database server' % engine)
            return engine_class
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
        self.dump_dir = dump_dir
        self._init_rootdir(base_dir)

    def _init_rootdir(self, base_dir):
        # Create a temporary data directory
        prefix = 'quibble-%s-' % self.__class__.__name__.lower()

        if base_dir is not None:
            base_dir = os.path.abspath(base_dir)
            os.makedirs(base_dir, exist_ok=True)

        # Create and hold a reference
        self._tmpdir = tempfile.TemporaryDirectory(
            dir=base_dir, prefix=prefix)
        self.rootdir = self._tmpdir.name
        self.log.debug('Root dir: %s', self.rootdir)

    def stop(self):
        if self.dump_dir:
            self.dump()
        super(DatabaseServer, self).stop()

    def dump(self):
        self.log.warning('%s does not support dumping database',
                         self.__class__.__name__)


class Postgres(DatabaseServer):

    def __init__(self, base_dir=None, dump_dir=None):
        super(Postgres, self).__init__(base_dir, dump_dir)

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


class MySQL(DatabaseServer):

    def __init__(
        self,
        base_dir=None,
        dump_dir=None,
        user='wikiuser',
        password='secret',
        dbname='wikidb',
        hostname='localhost'
    ):
        super(MySQL, self).__init__(base_dir, dump_dir)

        self.user = user
        self.password = password
        self.dbname = dbname
        self.dbtype = 'mysql'

        self.errorlog = os.path.join(self.rootdir, 'error.log')
        self.pidfile = os.path.join(self.rootdir, 'mysqld.pid')
        self.socket = os.path.join(self.rootdir, 'socket')
        self.dbserver = hostname + ':' + self.socket

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

    def dump(self):
        dumpfile = os.path.join(self.dump_dir, 'mysqldump.sql')
        self.log.info('Dumping database to %s', dumpfile)

        mysqldump = open(dumpfile, 'wb')
        subprocess.Popen([
                'mysqldump',
                '--socket=%s' % self.socket,
                '--user=root',
                '--all-databases'
            ],
            stdin=subprocess.PIPE,
            stdout=mysqldump,
            stderr=subprocess.STDOUT,
        ).wait()

    def __str__(self):
        return self.socket

    def __del__(self):
        self.stop()


class MysqlExternal(BackendServer):
    def __init__(
        self,
        base_dir=None,
        dump_dir=None,
        user='wikiuser',
        password='secret',
        dbname='wikidb',
        hostname='database',
        socket=None,
        port=3306
    ):
        super(MysqlExternal, self).__init__()

        self.user = user
        self.password = password
        self.dbname = dbname
        self.dbtype = 'mysql'

        self.dbserver = hostname + ':' + port

    def start(self):
        pass

    # TODO: def dump


class SQLite(DatabaseServer):

    def __init__(self, base_dir=None, dump_dir=None, dbname='wikidb'):
        super(SQLite, self).__init__(base_dir, dump_dir)

        self.dbname = dbname

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

    def __init__(self, host='127.0.0.1', port=4881, mwdir=None,
                 router='maintenance/dev/includes/router.php',
                 webserver='php'):
        super(DevWebServer, self).__init__()

        self.host = host
        self.port = port
        self.mwdir = mwdir
        self.router = router
        self.webserver = webserver

    def start(self):
        if self.webserver == 'none':
            self.log.info('Not starting a webserver.')
            return

        self.log.info('Starting %s webserver', self.webserver)

        if self.webserver == 'php':
            server_cmd = ['php', '-d', 'output_buffering=Off', '-S',
                          '%s:%s' % (self.host, self.port)]
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
        tcp_wait(host=self.host, port=self.port, timeout=5)

    def __str__(self):
        return 'http://%s:%s' % (self.host, self.port)

    def __repr__(self):
        return '<%s DevWebServer %s:%s %s>' %\
            (self.webserver, self.host, self.port, self.mwdir)

    def __del__(self):
        self.stop()


class Xvfb(BackendServer):

    def __init__(self, display=':94'):
        super(Xvfb, self).__init__()
        self.display = display

    def start(self):
        self.log.info('Starting Xvfb on display %s', self.display)
        self.server = subprocess.Popen([
            'Xvfb', self.display,
            '-screen', '0', '1280x1024x24'
            '-ac',
            '-nolisten', 'tcp',
            '-nolisten', 'unix',
            ])
