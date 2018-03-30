# Copyright 2012 Hewlett-Packard Development Company, L.P.
# Copyright 2013-2014 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import git
import os
import logging


def reset_repo_to_head(repo):
    # This lets us reset the repo even if there is a file in the root
    # directory named 'HEAD'.  Currently, GitPython does not allow us
    # to instruct it to always include the '--' to disambiguate.  This
    # should no longer be necessary if this PR merges:
    #   https://github.com/gitpython-developers/GitPython/pull/319
    try:
        repo.git.reset('--hard', 'HEAD', '--')
    except git.GitCommandError as e:
        # git nowadays may use 1 as status to indicate there are still unstaged
        # modifications after the reset
        if e.status != 1:
            raise


class ZuulReference(git.Reference):
    _common_path_default = "refs/zuul"
    _points_to_commits_only = True


class Repo(object):
    log = logging.getLogger("zuul.Repo")

    def __init__(self, remote, local, email, username):
        self.remote_url = remote
        self.local_path = local
        self.email = email
        self.username = username
        self._initialized = False
        try:
            self._ensure_cloned()
        except Exception:
            self.log.exception("Unable to initialize repo for %s" % remote)

    def _ensure_cloned(self):
        repo_is_cloned = os.path.exists(os.path.join(self.local_path, '.git'))
        if self._initialized and repo_is_cloned:
            return
        # If the repo does not exist, clone the repo.
        if not repo_is_cloned:
            self.log.debug("Cloning from %s to %s" % (self.remote_url,
                                                      self.local_path))
            git.Repo.clone_from(self.remote_url, self.local_path)
        repo = git.Repo(self.local_path)
        if self.email:
            repo.config_writer().set_value('user', 'email',
                                           self.email)
        if self.username:
            repo.config_writer().set_value('user', 'name',
                                           self.username)
        config_writer = repo.config_writer()
        try:
            # GitConfigParser.write() acquires a lock but does not release it.
            # The lock is released in the object's __del__ method, which is
            # invoked when the object is about to be dereferenced. This is not
            # a reliable means of ensuring the lock is released, because it can
            # break if there is a circular reference keeping the object alive,
            # or if another GitConfigParser object for the same repository is
            # initiated while a reference to the existing one is still held.
            config_writer.write()
        finally:
            config_writer._lock._release_lock()
        self._initialized = True

    def isInitialized(self):
        return self._initialized

    def createRepoObject(self):
        try:
            self._ensure_cloned()
            repo = git.Repo(self.local_path)
        except Exception:
            self.log.exception("Unable to initialize repo for %s" %
                               self.local_path)
        return repo

    def reset(self):
        self.log.debug("Resetting repository %s" % self.local_path)
        self.update()
        repo = self.createRepoObject()
        origin = repo.remotes.origin
        for ref in origin.refs:
            if ref.remote_head == 'HEAD':
                continue
            repo.create_head(ref.remote_head, ref, force=True)

        # try reset to remote HEAD (usually origin/master)
        # If it fails, pick the first reference
        try:
            repo.head.reference = origin.refs['HEAD']
        except IndexError:
            repo.head.reference = origin.refs[0]
        reset_repo_to_head(repo)
        repo.git.clean('-x', '-f', '-d')

    def prune(self):
        repo = self.createRepoObject()
        origin = repo.remotes.origin
        stale_refs = origin.stale_refs
        if stale_refs:
            self.log.debug("Pruning stale refs: %s", stale_refs)
            git.refs.RemoteReference.delete(repo, *stale_refs)

    def getBranchHead(self, branch):
        repo = self.createRepoObject()
        branch_head = repo.heads[branch]
        return branch_head.commit

    def hasBranch(self, branch):
        repo = self.createRepoObject()
        origin = repo.remotes.origin
        return branch in origin.refs

    def getCommitFromRef(self, refname):
        repo = self.createRepoObject()
        if refname not in repo.refs:
            return None
        ref = repo.refs[refname]
        return ref.commit

    def checkout(self, ref):
        repo = self.createRepoObject()
        self.log.debug("Checking out %s" % ref)
        repo.head.reference = ref
        reset_repo_to_head(repo)
        return repo.head.commit

    def cherryPick(self, ref):
        repo = self.createRepoObject()
        self.log.debug("Cherry-picking %s" % ref)
        self.fetch(ref)
        repo.git.cherry_pick("FETCH_HEAD")
        return repo.head.commit

    def merge(self, ref, strategy=None):
        repo = self.createRepoObject()
        args = []
        if strategy:
            args += ['-s', strategy]
        args.append('FETCH_HEAD')
        self.fetch(ref)
        self.log.debug("Merging %s with args %s" % (ref, args))
        repo.git.merge(*args)
        return repo.head.commit

    def fetch(self, ref):
        repo = self.createRepoObject()
        # The git.remote.fetch method may read in git progress info and
        # interpret it improperly causing an AssertionError. Because the
        # data was fetched properly subsequent fetches don't seem to fail.
        # So try again if an AssertionError is caught.
        origin = repo.remotes.origin
        try:
            origin.fetch(ref)
        except AssertionError:
            origin.fetch(ref)

    def fetchFrom(self, repository, refspec):
        repo = self.createRepoObject()
        repo.git.fetch(repository, refspec)

    def createZuulRef(self, ref, commit='HEAD'):
        repo = self.createRepoObject()
        self.log.debug("CreateZuulRef %s at %s on %s" % (ref, commit, repo))
        ref = ZuulReference.create(repo, ref, commit)
        return ref.commit

    def push(self, local, remote):
        repo = self.createRepoObject()
        self.log.debug("Pushing %s:%s to %s" % (local, remote,
                                                self.remote_url))
        repo.remotes.origin.push('%s:%s' % (local, remote))

    def update(self):
        repo = self.createRepoObject()
        self.log.debug("Updating repository %s" % self.local_path)
        origin = repo.remotes.origin
        if repo.git.version_info[:2] < (1, 9):
            # Before 1.9, 'git fetch --tags' did not include the
            # behavior covered by 'git --fetch', so we run both
            # commands in that case.  Starting with 1.9, 'git fetch
            # --tags' is all that is necessary.  See
            # https://github.com/git/git/blob/master/Documentation/RelNotes/1.9.0.txt#L18-L20
            origin.fetch()
        origin.fetch(tags=True)
