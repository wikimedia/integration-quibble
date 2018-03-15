import logging
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

    p = subprocess.Popen(cmd, cwd=mwdir)
    p.communicate()
    if p.returncode > 0:
        raise Exception(
            'Install failed with exit code: %s' % p.returncode)
