#!/usr/bin/env python3
#
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

import logging
import os
import subprocess
from multiprocessing import Pool

import quibble


def task_wrapper(args):
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


# TODO: Move to util?
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
        return all(pool.imap_unordered(task_wrapper, tasks))


def run_qunit(mwdir, port=9412):
    karma_env = {
         'CHROME_BIN': '/usr/bin/chromium',
         'MW_SERVER': 'http://127.0.0.1:%s' % port,
         'MW_SCRIPT_PATH': '/',
         'FORCE_COLOR': '1',  # for 'supports-color'
         }
    karma_env.update(os.environ)
    karma_env.update({'CHROMIUM_FLAGS': quibble.chromium_flags()})

    subprocess.check_call(
        ['./node_modules/.bin/grunt', 'qunit'],
        cwd=mwdir,
        env=karma_env,
    )


def commands(cmds, cwd):
    log = logging.getLogger('test.commands')
    log.info('working directory: %s' % cwd)

    for cmd in cmds:
        log.info(cmd)
        subprocess.check_call(cmd, shell=True, cwd=cwd)

    return True


def run_webdriver(mwdir, display, port=9412):
    webdriver_env = {}
    webdriver_env.update(os.environ)
    webdriver_env.update({
        'MW_SERVER': 'http://127.0.0.1:%s' % port,
        'MW_SCRIPT_PATH': '/',
        'FORCE_COLOR': '1',  # for 'supports-color'
        'MEDIAWIKI_USER': 'WikiAdmin',
        'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
        'DISPLAY': display,
    })

    subprocess.check_call([
        'npm', 'run', 'selenium-test'],
        cwd=mwdir,
        env=webdriver_env)
