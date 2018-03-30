import json
import os
import subprocess
import tempfile


def clone(repos, workspace, cache_dir):
    if isinstance(repos, str):
        repos = [repos]

    zuul_env = {k: v for k, v in os.environ.items()
                if k.startswith('ZUUL_')}
    zuul_env['PATH'] = os.environ['PATH']

    try:
        temp_mapfile = ''
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as fp:
            temp_mapfile = fp.name
            # Map a repo to a target dir under workspace
            clone_map = json.dumps({'clonemap': [
                {'name': 'mediawiki/core',
                    'dest': '.'},
                {'name': 'mediawiki/vendor',
                    'dest': './vendor'},
                {'name': 'mediawiki/extensions/(.*)',
                    'dest': './extensions/\\1'},
                {'name': 'mediawiki/skins/(.*)',
                    'dest': './skins/\\1'},
                ]
            })
            fp.write(clone_map)
            fp.close()
            cmd = [
                'zuul-cloner',
                '--color',
                '--verbose',
                '--map', temp_mapfile,
                '--workspace', workspace,
                '--cache-dir', cache_dir,
                'https://gerrit.wikimedia.org/r/p',
                ]
            cmd.extend(repos)
            subprocess.check_call(cmd, env=zuul_env)
    finally:
        if temp_mapfile:
            os.remove(temp_mapfile)
