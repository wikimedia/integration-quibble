import logging
import os
import os.path
import subprocess


def run_qunit(mwdir):
    localsettings = os.path.join(
        mwdir, 'LocalSettings.php')
    with open(localsettings, 'a') as lf:
        lf.write('<?php $wgEnableJavaScriptTest = true; ?>')

    karma_env = {
         'CHROME_BIN': '/usr/bin/chromium',
         'MW_SERVER': 'http://127.0.0.1:9412',
         'MW_SCRIPT_PATH': '',
         'FORCE_COLOR': '1',  # for 'supports-color'
         }
    karma_env.update(os.environ)

    chromium_flags = os.environ.get('CHROMIUM_FLAGS', '')
    if 'DISPLAY' not in os.environ:
        # Run Chromium in headless mode
        chromium_flags += ' ' + ' '.join([
            '--headless',
            '--disable-gpu',
            '--remote-debugging-port=9222',
            ])
    if os.path.exists('/.dockerenv'):
        chromium_flags += ' --no-sandbox'
    karma_env.update({'CHROMIUM_FLAGS': chromium_flags})

    qunit = subprocess.Popen(
        ['./node_modules/.bin/grunt', 'karma:main'],
        cwd=mwdir,
        env=karma_env,
    )
    qunit.communicate()
    if qunit.returncode > 0:
        raise Exception('Qunit failed :(')


def run_phpunit(mwdir, group=[], exclude_group=[], testsuite=None,
                junit_file=None):

    log = logging.getLogger('test.run_phpunit')
    always_excluded = ['Broken', 'ParserFuzz', 'Stub']

    cmd = ['php', 'tests/phpunit/phpunit.php', '--debug-tests']
    if group:
        cmd.extend(['--group', ','.join(group)])

    cmd.extend(['--exclude-group',
                ','.join(always_excluded + exclude_group)])

    if junit_file:
        cmd.extend('--log-junit', junit_file)
    log.info(' '.join(cmd))
    phpunit = subprocess.Popen(cmd, cwd=mwdir, env={'LANG': 'C.UTF-8'})
    phpunit.communicate()
    if phpunit.returncode > 0:
        raise Exception('phpunit failed :(')
