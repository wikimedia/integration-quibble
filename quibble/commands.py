"""Encapsulates each step of a job"""

import quibble.zuul


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
