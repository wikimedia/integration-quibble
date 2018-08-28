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

import logging
import os

from zuul.lib.cloner import Cloner
from zuul.lib.clonemapper import CloneMapper

CLONE_MAP = [
    {'name': 'mediawiki/core', 'dest': '.'},
    {'name': 'mediawiki/vendor', 'dest': './vendor'},
    {'name': 'mediawiki/extensions/(.*)', 'dest': './extensions/\\1'},
    {'name': 'mediawiki/skins/(.*)', 'dest': './skins/\\1'},
]


def clone(repos, workspace, cache_dir, branch=None, project_branch={}):
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

    project_branches = {}
    for x in project_branch:
        p, p_branch = x[0].split('=')
        project_branches[p] = p_branch

    zuul_cloner = Cloner(
        git_base_url='https://gerrit.wikimedia.org/r/p',
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

    return zuul_cloner.execute()


def repo_dir(repo):
    mapper = CloneMapper(CLONE_MAP, [repo])
    return mapper.expand(workspace='./')[repo]
