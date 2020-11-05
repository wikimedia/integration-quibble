# Copyright 2017-2018, Antoine "hashar" Musso
# Copyright 2017, Kunal Mehta
# Copyright 2017-2018, Wikimedia Foundation Inc.
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

"""
git-changed-in-head : list changed files in HEAD matching a file extension

This script list any added, copied or modified file in the current directory
and filters out by extension.

The current directory must be a git repository.

USAGE:
 git-changed-in-head [extension..]

EXAMPLE:

 List files ending with .php, .php5 or .inc
   git-changed-in-head php php5 inc

 List any file changed (no filtering):
  git-changed-in-head


Copyright © 2013-2018, Antoine Musso
Copyright © 2013, Wikimedia Foundation Inc.
Copyright © 2017, Kunal Mehta

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import subprocess


class GitChangedInHead:
    def __init__(self, args, cwd=None):
        self.cwd = cwd
        self.path_args = []
        for arg in args:
            # Put a dot in front for file extensions
            self.path_args.append('.{}'.format(arg))

    def changedFiles(self):
        return [f for f in self._get_changed_files()]

    def _get_changed_files(self):
        # Some explanations for the git command below:
        # HEAD^ will not exist for an initial commit, we thus need `git show`
        # --name-only: strip patch payload, only report the file being altered
        # --diff-filter=ACM: only care about files Added, Copied or Modified
        # --find-renames=100%: renamed files that had a slight change would be
        #                      considered modified and thus included.
        # -m: show differences for merge commits ...
        # --first-parent: ... but only follow the first parent commit
        # --format=format: : strip out the commit summary
        cmd = [
            'git', 'show', 'HEAD',
            '--name-only',
            '--diff-filter=ACM',
            '--find-renames=100%',
            '-m',
            '--first-parent',
            '--format=format:',
        ]
        out = subprocess.check_output(cmd, cwd=self.cwd).decode()
        for line in out.splitlines():
            # If matching on file extensions, filter that out
            if self.path_args and not line.endswith(tuple(self.path_args)):
                continue
            elif line.endswith('autoload_static.php'):
                # T136021: Don't lint composer/autoload_static.php.
                continue
            yield line
