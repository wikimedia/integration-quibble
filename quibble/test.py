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
        composer_test_cmd = ['composer', 'test']
        composer_test_cmd.extend(files)
        subprocess.check_call(composer_test_cmd, cwd=mwdir)


def run_npm_test(mwdir):
    log = logging.getLogger('test.run_npm_test')
    log.info("Running npm test")
    subprocess.check_call(['npm', 'test'], cwd=mwdir)


def run_qunit(mwdir, port=9412):
    localsettings = os.path.join(
        mwdir, 'LocalSettings.php')
    with open(localsettings, 'a') as lf:
        lf.write('<?php $wgEnableJavaScriptTest = true; ?>')

    karma_env = {
         'CHROME_BIN': '/usr/bin/chromium',
         'MW_SERVER': 'http://127.0.0.1:%s' % port,
         'MW_SCRIPT_PATH': '',
         'FORCE_COLOR': '1',  # for 'supports-color'
         }
    karma_env.update(os.environ)
    karma_env.update({'CHROMIUM_FLAGS': quibble.chromium_flags()})

    subprocess.check_call(
        ['./node_modules/.bin/grunt', 'karma:main'],
        cwd=mwdir,
        env=karma_env,
    )


def run_extskin(directory, composer=True, npm=True):
    log = logging.getLogger('test.run_extskin')
    project_name = os.path.basename(directory)

    if composer:
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
                subprocess.check_call(cmd, cwd=directory)

    if npm:
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
                subprocess.check_call(cmd, cwd=directory)

    log.info('%s: git clean -xqdf' % project_name)
    subprocess.check_call(['git', 'clean', '-xqdf'], cwd=directory)


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
    subprocess.check_call(cmd, cwd=mwdir, env={'LANG': 'C.UTF-8'})


def run_phpunit_database(*args, **kwargs):
    kwargs['group'] = ['Database']
    run_phpunit(*args, **kwargs)


def run_phpunit_databaseless(*args, **kwargs):
    kwargs['exclude_group'] = ['Database']
    run_phpunit(*args, **kwargs)


def run_webdriver(mwdir, display, port=9412):
    subprocess.check_call([
        'node_modules/.bin/grunt', 'webdriver:test'],
        cwd=mwdir,
        env={
            'MW_SERVER': 'http://127.0.0.1:%s' % port,
            'MW_SCRIPT_PATH': '',
            'FORCE_COLOR': '1',  # for 'supports-color'
            'MEDIAWIKI_USER': 'WikiAdmin',
            'MEDIAWIKI_PASSWORD': 'testpass',
            'DISPLAY': display,
            })
