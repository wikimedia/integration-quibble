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
import threading

from concurrent.futures import ThreadPoolExecutor, as_completed

from zuul.lib.cloner import Cloner
from zuul.lib.clonemapper import CloneMapper

CLONE_MAP = [
    {'name': 'mediawiki/core', 'dest': '.'},
    {'name': 'mediawiki/vendor', 'dest': './vendor'},
    {'name': 'mediawiki/extensions/(.*)', 'dest': './extensions/\\1'},
    {'name': 'mediawiki/skins/(.*)', 'dest': './skins/\\1'},
]


def clone(branch, cache_dir, project_branch, projects, workers, workspace,
          zuul_branch, zuul_newrev, zuul_project, zuul_ref, zuul_url):
    log = logging.getLogger('quibble.zuul.clone')

    if isinstance(projects, str):
        projects = [projects]

    if zuul_ref is not None and zuul_url is None:
        raise Exception('Zuul ref requires a Zuul url')
    if zuul_newrev is not None and zuul_project is None:
        raise Exception('Zuul newrev requires a Zuul project')

    project_branches = {}
    if project_branch:
        for x in project_branch:
            p, p_branch = x[0].split('=')
            project_branches[p] = p_branch

    zuul_cloner = Cloner(
        git_base_url='https://gerrit.wikimedia.org/r',
        projects=projects,
        workspace=workspace,
        zuul_branch=zuul_branch,
        zuul_ref=zuul_ref,
        zuul_url=zuul_url,
        branch=branch,
        project_branches=project_branches,
        cache_dir=cache_dir,
        zuul_newrev=zuul_newrev,
        zuul_project=zuul_project,
        cache_no_hardlinks=False,  # False allows hardlink
        )
    # The constructor expects a file, set the value directly
    zuul_cloner.clone_map = CLONE_MAP

    # Reimplement Cloner.execute() to make sure mediawiki/core is cloned first
    # and clone the rest in parallel.
    mapper = CloneMapper(CLONE_MAP, projects)
    dests = mapper.expand(workspace=workspace)

    if workers == 1:
        return zuul_cloner.execute()

    # Reimplement the cloner execute method with parallelism and logging
    # suitable for multiplexed output.
    log.info("Preparing %d repositories with %s workers",
             len(dests), workers)

    if 'mediawiki/core' in projects:
        mw_git_dir = os.path.join(dests['mediawiki/core'], '.git')
        if not os.path.exists(mw_git_dir):
            log.info("Cloning mediawiki/core first")
            zuul_cloner.prepareRepo('mediawiki/core', dests['mediawiki/core'])
            del(dests['mediawiki/core'])

    can_run = threading.Event()
    can_run.set()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(clone_worker, can_run, zuul_cloner, project, dest)
            for project, dest in dests.items()]
        # Consume results
        for future in as_completed(futures):
            future.result()

    log.info("Prepared all repositories")


def clone_worker(can_run, cloner, project, dest):
    if not can_run.is_set():
        return

    # Forge a new child logger, since repositories might be cloned concurrently
    project_cloner = copy.copy(cloner)
    project_cloner.log = project_cloner.log.getChild(project)
    try:
        project_cloner.prepareRepo(project, dest)
    except Exception as e:
        # Prevent other workers from executing
        can_run.clear()
        raise e


def repo_dir(repo):
    mapper = CloneMapper(CLONE_MAP, [repo])
    return mapper.expand(workspace='./')[repo]
