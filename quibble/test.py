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
         'DISPLAY': os.environ['DISPLAY'],
         'MW_SERVER': 'http://127.0.0.1:9412',
         'MW_SCRIPT_PATH': '',
         'FORCE_COLOR': '1',  # for 'supports-color'
         }
    karma_env.update(os.environ)
    qunit = subprocess.Popen(
        ['./node_modules/.bin/grunt', 'karma:main'],
        cwd=mwdir,
        env=karma_env,
    )
    qunit.communicate()
    if qunit.returncode > 0:
        raise Exception('Qunit failed :(')
