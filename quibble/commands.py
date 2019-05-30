"""Encapsulates each step of a job"""

import logging
import os.path
import quibble.zuul
import subprocess

log = logging.getLogger(__name__)


class ZuulCloneCommand:
    def __init__(self, branch, cache_dir, project_branch, projects, workers,
                 workspace, zuul_branch, zuul_newrev, zuul_project, zuul_ref,
                 zuul_url):
        self.branch = branch
        self.cache_dir = cache_dir
        self.project_branch = project_branch
        self.projects = projects
        self.workers = workers
        self.workspace = workspace
        self.zuul_branch = zuul_branch
        self.zuul_newrev = zuul_newrev
        self.zuul_project = zuul_project
        self.zuul_ref = zuul_ref
        self.zuul_url = zuul_url

    def execute(self):
        quibble.zuul.clone(
            self.branch, self.cache_dir, self.project_branch, self.projects,
            self.workers, self.workspace, self.zuul_branch, self.zuul_newrev,
            self.zuul_project, self.zuul_ref, self.zuul_url)

    def __str__(self):
        return "Zuul clone {} with parameters {}".format(
            self.projects,
            self.kwargs)


class ExtSkinSubmoduleUpdateCommand:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        log.info('Updating git submodules of extensions and skins')

        cmds = [
            ['git', 'submodule', 'foreach', 'git', 'clean', '-xdff', '-q'],
            ['git', 'submodule', 'update', '--init', '--recursive'],
            ['git', 'submodule', 'status'],
        ]

        tops = [os.path.join(self.mw_install_path, top)
                for top in ['extensions', 'skins']]

        for top in tops:
            for dirpath, dirnames, filenames in os.walk(top):
                if dirpath not in tops:
                    # Only look at the first level
                    dirnames[:] = []
                if '.gitmodules' not in filenames:
                    continue

                for cmd in cmds:
                    try:
                        subprocess.check_call(cmd, cwd=dirpath)
                    except subprocess.CalledProcessError as e:
                        log.error(
                            "Failed to process git submodules for {}".format(
                                dirpath))
                        raise e

    def __str__(self):
        # TODO: Would be nicer to extract the directory crawl into a subroutine
        # and print the analysis here.
        return "Extension and skin submodule update under MediaWiki root {}"\
            .format(self.mw_install_path)
