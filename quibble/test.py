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

import quibble
from quibble.gitchangedinhead import GitChangedInHead


def run_composer_test(mwdir):
    log = logging.getLogger('test.run_composer_test')
    files = []
    changed = GitChangedInHead([], cwd=mwdir).changedFiles()
    if 'composer.json' in changed or '.phpcs.xml' in changed:
        log.info(
            'composer.json or .phpcs.xml changed: linting "."')
        # '.' is passed to composer lint which then pass it
        # to parallel-lint and phpcs
        files = ['.']
    else:
        files = GitChangedInHead(
            ['php', 'php5', 'inc', 'sample'],
            cwd=mwdir
            ).changedFiles()

    if not files:
        log.info('Skipping composer test (unneeded)')
    else:
        log.info("Running composer test")

        env = {'COMPOSER_PROCESS_TIMEOUT': '900'}
        env.update(os.environ)

        composer_test_cmd = ['composer', 'test']
        composer_test_cmd.extend(files)
        subprocess.check_call(composer_test_cmd, cwd=mwdir, env=env)


def run_npm_test(mwdir):
    log = logging.getLogger('test.run_npm_test')
    log.info("Running npm test")
    subprocess.check_call(['npm', 'test'], cwd=mwdir, env=os.environ)


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


def run_extskin(directory, composer=True, npm=True):
    if composer:
        run_extskin_composer(directory)
    if npm:
        run_extskin_npm(directory)


def run_extskin_composer(directory):
    log = logging.getLogger('test.run_extskin_composer')
    project_name = os.path.basename(directory)

    if not os.path.exists(os.path.join(directory, 'composer.json')):
        log.warning("%s lacks a composer.json" % project_name)
    else:
        log.info('Running "composer test" for %s' % project_name)
        cmds = [
            ['composer', '--ansi', 'validate', '--no-check-publish'],
            ['composer', '--ansi', 'install', '--no-progress',
             '--prefer-dist', '--profile', '-v'],
            ['composer', '--ansi', 'test'],
        ]
        for cmd in cmds:
            subprocess.check_call(cmd, cwd=directory, env=os.environ)


def run_extskin_npm(directory):
    log = logging.getLogger('test.run_extskin_npm')
    project_name = os.path.basename(directory)

    # XXX copy paste is terrible
    if not os.path.exists(os.path.join(directory, 'package.json')):
        log.warning("%s lacks a package.json" % project_name)
    else:
        log.info('Running "npm test" for %s' % project_name)
        cmds = [
            ['npm', 'prune'],
            ['npm', 'install', '--no-progress'],
            ['npm', 'test'],
        ]
        for cmd in cmds:
            subprocess.check_call(cmd, cwd=directory, env=os.environ)


def run_phpunit(mwdir, group=[], exclude_group=[], testsuite=None,
                junit_file=None):

    log = logging.getLogger('test.run_phpunit')
    always_excluded = ['Broken', 'ParserFuzz', 'Stub']

    cmd = ['php', 'tests/phpunit/phpunit.php', '--debug-tests']
    if testsuite:
        cmd.extend(['--testsuite', testsuite])

    if group:
        cmd.extend(['--group', ','.join(group)])

    cmd.extend(['--exclude-group',
                ','.join(always_excluded + exclude_group)])

    if junit_file:
        cmd.extend('--log-junit', junit_file)
    log.info(' '.join(cmd))

    phpunit_env = {}
    phpunit_env.update(os.environ)
    phpunit_env.update({'LANG': 'C.UTF-8'})

    subprocess.check_call(cmd, cwd=mwdir, env=phpunit_env)


def run_phpunit_database(*args, **kwargs):
    kwargs['group'] = ['Database']
    run_phpunit(*args, **kwargs)


def run_phpunit_databaseless(*args, **kwargs):
    kwargs['exclude_group'] = ['Database']
    run_phpunit(*args, **kwargs)


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
        'MEDIAWIKI_PASSWORD': 'testpass',
        'DISPLAY': display,
    })

    subprocess.check_call([
        'npm', 'run', 'selenium-test'],
        cwd=mwdir,
        env=webdriver_env)
