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
from multiprocessing import Pool
import os
import re
from shutil import copyfile
import subprocess
import sys

from pkg_resources import Requirement
from pkg_resources import parse_version

log = logging.getLogger(__name__)


def copylog(src, dest):
    log.info('Copying %s to %s', src, dest)
    copyfile(src, dest)


def _task_wrapper(args):
    """
    Helper for multiprocessing.Pool.imap_unordered.

    The first argument is a function to call.  Rest of the arguments are passed
    to the function.
    """

    func = args[0]
    func_args = args[1:]
    ret = func(*func_args)

    if ret is None:
        return True
    else:
        return ret


def parallel_run(tasks):
    """
    Tasks is an iterable of bound functions.  The wrapper makes it easy for us
    to run a list of different functions, rather than one function over a list
    of inputs.
    """
    workers = max(1, len(tasks))
    with Pool(processes=workers) as pool:
        # As soon as any one task fails, the `all()` drops us out of the Pool's
        # context manager, and any remaining threads are terminated.
        return all(pool.imap_unordered(_task_wrapper, tasks))


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


@contextlib.contextmanager
def _redirect_logging(sink):
    """Redirect logging to a single stream, and reconnect when finished."""
    log_handler = logging.StreamHandler(sink)

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
