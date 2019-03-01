# Copyright 2018 Antoine "hashar" Musso
# Copyright 2018 Wikimedia Foundation Inc.
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

import copy
import logging
import os

from concurrent.futures import ThreadPoolExecutor

from zuul.lib.cloner import Cloner
from zuul.lib.clonemapper import CloneMapper

CLONE_MAP = [
    {'name': 'mediawiki/core', 'dest': '.'},
    {'name': 'mediawiki/vendor', 'dest': './vendor'},
    {'name': 'mediawiki/extensions/(.*)', 'dest': './extensions/\\1'},
    {'name': 'mediawiki/skins/(.*)', 'dest': './skins/\\1'},
]


def clone(repos, workspace, cache_dir, branch=None, project_branch=[],
          workers=1):
    log = logging.getLogger('quibble.zuul.clone')

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

    project_branches = {}
    if project_branch:
        for x in project_branch:
            p, p_branch = x[0].split('=')
            project_branches[p] = p_branch

    zuul_cloner = Cloner(
        git_base_url='https://gerrit.wikimedia.org/r',
        projects=repos,
        workspace=workspace,
        zuul_branch=zuul_env.get('ZUUL_BRANCH'),
        zuul_ref=zuul_env.get('ZUUL_REF'),
        zuul_url=zuul_env.get('ZUUL_URL'),
        branch=branch,
        project_branches=project_branches,
        cache_dir=cache_dir,
        zuul_newrev=zuul_env.get('ZUUL_NEWREV'),
        zuul_project=zuul_env.get('ZUUL_PROJECT'),
        cache_no_hardlinks=False,  # False allows hardlink
        )
    # The constructor expects a file, set the value directly
    zuul_cloner.clone_map = CLONE_MAP

    # Reimplement Cloner.execute() to make sure mediawiki/core is cloned first
    # and clone the rest in parallel.
    mapper = CloneMapper(CLONE_MAP, repos)
    dests = mapper.expand(workspace=workspace)

    if workers == 1:
        return zuul_cloner.execute()

    # Reimplement the cloner execute method with parallelism and logging
    # suitable for multiplexed output.
    log.info("Preparing %s repositories with %s workers" % (
             len(dests), workers))

    mw_git_dir = os.path.join(dests['mediawiki/core'], '.git')
    if not os.path.exists(mw_git_dir):
        log.info("Cloning mediawiki/core first")
        zuul_cloner.prepareRepo('mediawiki/core', dests['mediawiki/core'])
        del(dests['mediawiki/core'])

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for project, dest in dests.items():
            # Copy and hijack the logger
            project_cloner = copy.copy(zuul_cloner)
            project_cloner.log = project_cloner.log.getChild(project)

            executor.submit(project_cloner.prepareRepo, project, dest)

    log.info("Prepared all repositories")


def repo_dir(repo):
    mapper = CloneMapper(CLONE_MAP, [repo])
    return mapper.expand(workspace='./')[repo]
