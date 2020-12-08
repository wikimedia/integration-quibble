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


def update(args, mwdir=None):
    log = logging.getLogger('mw.maintenance.update')

    cmd = ['php', 'maintenance/update.php', '--quick']
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

    cmd = ['php', 'maintenance/install.php']
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
    cmd = ['php', 'maintenance/rebuildLocalisationCache.php']
    cmd.extend(['--lang', ','.join(lang)])
    log.info(' '.join(cmd))

    p = subprocess.Popen(cmd, cwd=mwdir)
    p.communicate()
    if p.returncode > 0:
        raise Exception(
            'rebuildLocalisationCache failed with exit code: %s'
            % (p.returncode)
        )
