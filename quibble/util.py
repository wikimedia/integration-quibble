# Copyright 2017-2018, Antoine "hashar" Musso
# Copyright 2017, Tyler Cipriani
# Copyright 2017-2018, Wikimedia Foundation Inc.
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

import contextlib
import logging
import os
import re
from shutil import copyfile
import subprocess
import sys
import threading
import time

from pkg_resources import Requirement
from pkg_resources import parse_version

log = logging.getLogger(__name__)


def copylog(src, dest):
    log.info('Copying %s to %s', src, dest)
    copyfile(src, dest)


def isCoreOrVendor(project):
    """
    project: a gerrit repository name

    Returns boolean, whether the repository is mediawiki/core or
    mediawiki/vendor.
    """
    return project == 'mediawiki/core' or project == 'mediawiki/vendor'


def isExtOrSkin(project):
    """
    project: a gerrit repository name

    Returns boolean, whether the repository is a MediaWiki extension or skin.
    """
    return project.startswith(('mediawiki/extensions/', 'mediawiki/skins/'))


def move_item_to_head(dependencies, project):
    repos = list(dependencies)
    repos.insert(0, repos.pop(repos.index(project)))
    return repos


def php_version(specifier):
    spec = Requirement.parse('PHP%s' % specifier)
    try:
        full_version = subprocess.check_output(
            ['php', '--version'], stderr=None
        )
        m = re.match('PHP (?P<version>.+?) ', full_version)
        if m:
            return parse_version(m.group('version')) in spec

    except subprocess.CalledProcessError:
        pass


@contextlib.contextmanager
def _redirect_stream(source, sink):
    """Redirects at the OS level, so that the new pipes are inherited by
    subprocesses.

    Can't reuse contextlib redirectors here because they only affect the Python
    `std*` globals.
    """
    old_source_fileno = os.dup(source.fileno())
    os.dup2(sink.fileno(), source.fileno())

    yield
    source.flush()

    os.dup2(old_source_fileno, source.fileno())


class BytesStreamHandler(logging.StreamHandler):
    """
    Logging handling converting received strings to bytes

    This is used when redirecting logging to TemporaryFile() which by default
    is a binary file. The write() expects a byte like object.

    Invalid unicode characters are replaced by backslashreplace.

    With Python 3.8 we can remove it and use:

        TemporaryFile(errors='backslashreplace')
    """

    def __init__(self, stream):
        logging.StreamHandler.__init__(self, stream)

    def emit(self, record):
        msg = self.format(record)
        self.stream.write(
            bytes(
                msg + self.terminator,
                encoding='utf-8',
                errors='backslashreplace',
            )
        )
        self.stream.flush()


@contextlib.contextmanager
def _redirect_logging(sink):

    """Redirect logging to a single stream, and reconnect when finished."""
    log_handler = BytesStreamHandler(sink)

    logger = logging.getLogger()
    old_handlers = logger.handlers
    for handler in old_handlers:
        logger.removeHandler(handler)
    logger.addHandler(log_handler)

    yield
    log_handler.flush()

    logger.removeHandler(log_handler)
    for handler in old_handlers:
        logger.addHandler(handler)
    log_handler.close()


@contextlib.contextmanager
def redirect_all_streams(sink):
    """Redirect stdout, stderr, and logging to a single stream."""
    with _redirect_logging(sink), _redirect_stream(
        sys.stdout, sink
    ), _redirect_stream(sys.stderr, sink):
        yield


class ProgressReporter:
    """Report job progress at regular intervals, wraps an iterable and tracks
    how many items have been served from it.

    Inspired by tqdm.
    """

    def __init__(self, *, iterable, desc, sleep_interval, total):
        self.iterable = iterable
        self.desc = desc
        self.completed = 0
        self.total = total
        self.start_time = time.time()
        self.sleep_interval = sleep_interval

        self.monitor = _RepeatingTimer(self.sleep_interval, self._refresh)

    def __iter__(self):
        self.monitor.start()

        for obj in self.iterable:
            yield obj

            self.completed += 1

        self.monitor.cancel()

    def _refresh(self):
        elapsed = int(time.time() - self.start_time)
        log.debug(
            "Waiting for %s: %ss elapsed, %s/%s completed",
            self.desc,
            elapsed,
            self.completed,
            self.total,
        )


class _RepeatingTimer(threading.Timer):
    def __init__(self, *args, **kwargs):
        # This is a daemon thread so that it can be immediately killed if the
        # program crashes before fully consuming the iterator.  Otherwise, the
        # `self.finished` Event might never receive the flag set by
        # `self.monitor.cancel` above.
        super(_RepeatingTimer, self).__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
