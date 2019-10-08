# Copyright 2017-2018, Antoine "hashar" Musso
# Copyright 2017, Tyler Cipriani
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

import logging
from multiprocessing import Pool
from shutil import copyfile

log = logging.getLogger(__name__)


def copylog(src, dest):
    log.info('Copying %s to %s', src, dest)
    copyfile(src, dest)


def task_wrapper(args):
    """
    Helper for multiprocessing.Pool.imap_unordered.

    The first argument is a function to call.  Rest of the arguments are passed
    to the function.
    """

    func = args[0]
    func_args = args[1:]
    ret = func(*func_args)

    if ret is None:
        return True
    else:
        return ret


def parallel_run(tasks):
    """
    Tasks is an iterable of bound functions.  The wrapper makes it easy for us
    to run a list of different functions, rather than one function over a list
    of inputs.
    """
    workers = max(1, len(tasks))
    with Pool(processes=workers) as pool:
        # As soon as any one task fails, the `all()` drops us out of the Pool's
        # context manager, and any remaining threads are terminated.
        return all(pool.imap_unordered(task_wrapper, tasks))


def isCoreOrVendor(project):
    """
    project: a gerrit repository name

    Returns boolean, whether the repository is mediawiki/core or
    mediawiki/vendor.
    """
    return project == 'mediawiki/core' or project == 'mediawiki/vendor'


def isExtOrSkin(project):
    """
    project: a gerrit repository name

    Returns boolean, whether the repository is a MediaWiki extension or skin.
    """
    return project.startswith(
        ('mediawiki/extensions/', 'mediawiki/skins/')
    )


def move_item_to_head(dependencies, project):
    repos = list(dependencies)
    repos.insert(0, repos.pop(repos.index(project)))
    return repos
