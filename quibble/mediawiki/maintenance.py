# Copyright 2018, Antoine "hashar" Musso
# Copyright 2018, Wikimedia Foundation Inc.
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


# Compatibility with MW < 1.40; to remove once 1.39 is not CI-tested
def getMaintenanceScript(script, args=[]):
    """
    Return a sequence of command arguments to run a maintenance script

    Since MediaWiki 1.40, instead of invoking maintenance script directly, one
    should use `maintenance/run.php` and pass the basename of the script:

      php maintenance/run.php update

    Will run `maintenance/update.php`. This command takes care of back
    compatibility with older MediaWiki versions which do not have
    `maintenance/run.php`.
    """
    subprocess.Popen
    (basename, ext) = os.path.splitext(script)

    if isinstance(args, str):
        args = [args]

    if os.path.exists('maintenance/run.php'):
        cmd = ['php', 'maintenance/run.php', basename]
    else:
        if ext == '':
            cmd = ['php', 'maintenance/%s.php' % basename]
        else:
            cmd = ['php', 'maintenance/%s' % script]
    cmd.extend(args)
    return cmd


def update(args, mwdir=None):
    log = logging.getLogger('mw.maintenance.update')

    cmd = getMaintenanceScript('update', '--quick')
    cmd.extend(args)
    log.info(' '.join(cmd))

    update_env = {}
    update_env.update(os.environ)
    if mwdir is not None:
        update_env['MW_INSTALL_PATH'] = mwdir

    p = subprocess.Popen(cmd, cwd=mwdir, env=update_env)
    p.communicate()
    if p.returncode > 0:
        raise Exception('Update failed with exit code: %s' % p.returncode)


def install(args, mwdir=None):
    log = logging.getLogger('mw.maintenance.install')

    cmd = getMaintenanceScript('install')
    cmd.extend(args)
    cmd.extend(
        [
            '--with-extensions',  # T189567
            '--pass=testwikijenkinspass',
            'TestWiki',
            'WikiAdmin',
        ]
    )
    log.info(' '.join(cmd))

    install_env = {}
    install_env.update(os.environ)

    # LANG is passed to $wgShellLocale
    install_env.update({'LANG': 'C.UTF-8'})

    p = subprocess.Popen(cmd, cwd=mwdir, env=install_env)
    p.communicate()
    if p.returncode > 0:
        raise Exception('Install failed with exit code: %s' % p.returncode)


def rebuildLocalisationCache(lang=['en'], mwdir=None):
    log = logging.getLogger('mw.maintenance.rebuildLocalisationCache')

    cmd = getMaintenanceScript('rebuildLocalisationCache')
    cmd.extend(['--lang', ','.join(lang)])
    log.info(' '.join(cmd))

    p = subprocess.Popen(cmd, cwd=mwdir)
    p.communicate()
    if p.returncode > 0:
        raise Exception(
            'rebuildLocalisationCache failed with exit code: %s'
            % (p.returncode)
        )


def addSite(args, mwdir=None):
    log = logging.getLogger('mw.maintenance.addSite')

    cmd = getMaintenanceScript('addSite')
    cmd.extend(args)
    log.info(' '.join(cmd))

    addSite_env = {}
    if mwdir is not None:
        addSite_env['MW_INSTALL_PATH'] = mwdir

    p = subprocess.Popen(cmd, cwd=mwdir, env=addSite_env)
    p.communicate()
    if p.returncode > 0:
        raise Exception('addSite failed with exit code: %s' % p.returncode)
