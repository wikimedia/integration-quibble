import logging
import os

from zuul.lib.cloner import Cloner


def clone(repos, workspace, cache_dir):
    logging.getLogger('zuul').setLevel(logging.DEBUG)

    if isinstance(repos, str):
        repos = [repos]

    zuul_env = {k: v for k, v in os.environ.items()
                if k.startswith('ZUUL_')}
    zuul_env['PATH'] = os.environ['PATH']

    # Ripped off from zuul/cmd/cloner.py
    if 'ZUUL_REF' in zuul_env and 'ZUUL_URL' not in zuul_env:
        raise Exception('Zuul ref requires a Zuul url')
    if 'ZUUL_NEWREV' in zuul_env and 'ZUUL_PROJECT' not in zuul_env:
        raise Exception('Zuul newrev requires a Zuul project')

    zuul_cloner = Cloner(
        git_base_url='https://gerrit.wikimedia.org/r/p',
        projects=repos,
        workspace=workspace,
        zuul_branch=zuul_env.get('ZUUL_BRANCH'),
        zuul_ref=zuul_env.get('ZUUL_REF'),
        zuul_url=zuul_env.get('ZUUL_URL'),
        branch=None,
        cache_dir=cache_dir,
        zuul_newrev=zuul_env.get('ZUUL_NEWREV'),
        zuul_project=zuul_env.get('ZUUL_PROJECT'),
        cache_no_hardlinks=False,  # False allows hardlink
        )
    # The constructor expects a file, set the value directly
    zuul_cloner.clone_map = [
        {'name': 'mediawiki/core', 'dest': '.'},
        {'name': 'mediawiki/vendor', 'dest': './vendor'},
        {'name': 'mediawiki/extensions/(.*)', 'dest': './extensions/\\1'},
        {'name': 'mediawiki/skins/(.*)', 'dest': './skins/\\1'},
        ]
    # XXX color and logging.DEBUG

    zuul_cloner.execute()
