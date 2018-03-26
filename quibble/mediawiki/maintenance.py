import logging
import os
import subprocess


def install(args, mwdir=None):
    log = logging.getLogger('mw.maintenance.install')

    cmd = ['php', 'maintenance/install.php']
    cmd.extend(args)
    cmd.extend([
        '--pass=testpass',
        'TestWiki',
        'WikiAdmin'
    ])

    log.info(' '.join(cmd))

    # LANG is passed to $wgShellLocale
    p = subprocess.Popen(cmd, cwd=mwdir,
                         env={'LANG': 'C.UTF-8'}.update(os.environ))
    p.communicate()
    if p.returncode > 0:
        raise Exception(
            'Install failed with exit code: %s' % p.returncode)
