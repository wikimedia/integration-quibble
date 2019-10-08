# Copyright 2014, 2018 Antoine "hashar" Musso
# Copyright 2014, 2018 Wikimedia Foundation Inc.
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

from contextlib import contextmanager
from functools import lru_cache
import logging
import os
import subprocess
import time


def colored_logging():
    # Color codes http://www.tldp.org/HOWTO/Bash-Prompt-HOWTO/x329.html
    logging.addLevelName(  # cyan
        logging.DEBUG, "\033[36m%s\033[0m" %
        logging.getLevelName(logging.DEBUG))
    logging.addLevelName(  # green
        logging.INFO, "\033[32m%s\033[0m" %
        logging.getLevelName(logging.INFO))
    logging.addLevelName(  # yellow
        logging.WARNING, "\033[33m%s\033[0m" %
        logging.getLevelName(logging.WARNING))
    logging.addLevelName(  # red
        logging.ERROR, "\033[31m%s\033[0m" %
        logging.getLevelName(logging.ERROR))
    logging.addLevelName(  # red background
        logging.CRITICAL, "\033[41m%s\033[0m" %
        logging.getLevelName(logging.CRITICAL))

# Can be used to temporarily alter a logging level.
#
# with logginglevel('root', logging.ERROR):
#     do something silently
#
@contextmanager
def logginglevel(name, new_level):
    logger = logging.getLogger(name)
    prev_level = logger.getEffectiveLevel()
    logger.setLevel(new_level)
    try:
        yield
    finally:
        logger.setLevel(prev_level)


def use_headless():
    log = logging.getLogger('quibble.use_headless')
    log.info("Display: %s", os.environ.get('DISPLAY', '<None>'))

    return not bool(os.environ.get('DISPLAY'))


def chromium_flags():
    args = [os.environ.get('CHROMIUM_FLAGS', '')]

    # play() would fail if the user didn't interact with the document
    # first. The autoplay policy got changed with v66
    # https://goo.gl/xX8pDD and T197687
    args.append('--autoplay-policy=no-user-gesture-required')

    # Chrome throttles calls to history.pushState() which causes the history
    # update to be ignored. T198171
    args.append('--disable-pushstate-throttle')

    if is_in_docker():
        args.append('--no-sandbox')
    if use_headless():
        args.extend([
            '--headless',
            '--disable-gpu',
            '--remote-debugging-port=9222',
        ])

    log = logging.getLogger('quibble.chromium_flags')
    log.debug("Flags: %s", args)
    return ' '.join(args)


def is_in_docker():
    return os.path.exists('/.dockerenv')


@lru_cache(maxsize=1)
def php_is_hhvm():
    return b'HipHop' in subprocess.check_output(['php', '--version'])


@contextmanager
def Chronometer(name, logger):

    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if logger:
            logger('%s finished in %.03f s' % (name, duration))
