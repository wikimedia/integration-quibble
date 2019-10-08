Quibble: a test runner for MediaWiki
====================================

Quibble will clone the specific repository being tested, MediaWiki, and any
dependencies. Then all available tests are run, beginning with basic lint
checks and culminating in browser tests for each MediaWiki extension. Specific
tests can be included or excluded as needed.

Everything is performed by a single command, `quibble`.

Running quibble requires python 3 and the following tools, or you can run in
the provided docker image.

- Chromium
- composer
- NodeJS
- npm
- php
- Xvfb

Quick Start
-----------

Full build and run, with no caching::

    docker build --tag quibble .
    docker run -it --rm quibble

Which runs tests with php7.0, MariaDB and using mediawiki/vendor.git to
provide PHP libraries.

You could instead run tests with dependencies provided by `composer install`
and use SQLite as a database backend::

    docker run -it quibble  --packages-source composer --db sqlite

Wikimedia maintains Docker containers intended to be used for its continuous
integration system, for example::

    docker pull docker-registry.wikimedia.org/releng/quibble-stretch-php72:latest

The source is on Gerrit https://gerrit.wikimedia.org/g/integration/config
under the `dockerfiles` directory, where you'll also find other images with
slight variations such as other PHP versions.

Further documentation can be found on https://doc.wikimedia.org/quibble/ .


Setup
-----

Docker container
~~~~~~~~~~~~~~~~

Get the latest image being run by Wikimedia CI::

  docker pull docker-registry.wikimedia.org/releng/quibble-stretch-php72:latest

Quibble clones the repositories from Gerrit, and may load additional
dependencies using composer and npm. At the end of the run, the container will
be removed as well as all of the downloaded content. To make it faster, you
should provide local copies of the git repositories as a volume attached to the
container.

To avoid cloning MediaWiki over the network, you should initialize local
bare git repositories to be used as a reference for git to copy them from::

    mkdir -p ref/mediawiki/skins
    git clone --bare https://gerrit.wikimedia.org/r/mediawiki/core ref/mediawiki/core.git
    git clone --bare https://gerrit.wikimedia.org/r/mediawiki/vendor ref/mediawiki/vendor.git
    git clone --bare https://gerrit.wikimedia.org/r/mediawiki/skins/Vector ref/mediawiki/skins/Vector.git

The Docker containers have ``XDG_CACHE_HOME=/cache`` set which is recognized by
package managers.  Create a cache directory writable by any user::

    mkdir cache
    chmod 777 cache

Commands write logs into ``/workspace/log``, you can create one on the host and
mount it in the container::

    mkdir -p log
    chmod 777 log

You might also want to reuse the installed sources between runs. The container
has the source repository under ``/workspace/src``::

   mkdir -p src
   chmod 777 src

The directory tree on the host will looks like::

    .
    ├── cache/
    ├── log/
    ├── src/
    └── ref/
        └── mediawiki/
            ├── core.git/
            ├── skins/
            │   └── Vector.git/
            └── vendor.git/


When running the Docker container, mount the directories from the host:

============ ================== ================================
Host dir     Container dir      Docker run argument
============ ================== ================================
``./cache/`` ``/cache``         ``-v "$(pwd)"/cache:/cache``
``./log/``   ``/workspace/log`` ``-v "$(pwd)"/log:/workspace/log``
``./ref/``   ``/srv/git``       ``-v "$(pwd)"/ref:/srv/git:ro``
``./src/``   ``/workspace/src`` ``-v "$(pwd)"/src:/workspace/src``
============ ================== ================================

The final command::

    docker run -it --rm \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/workspace/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-stretch-php72:latest

Quibble will then do the initial cloning of repositories reusing bare
repositories from ``ref``, being local it is arguably faster than transferring
everything from Gerrit. The ``composer install`` and ``npm install`` will save
the downloaded packages to ``cache`` which speed up the next run.

Finally, having ``/src`` mounted from the host, lets one reuse the installed
wiki. One can later skip cloning/checking out the repositories by passing
``--skip-zuul`` and skip installing composer and npm dependencies with
``--skip-deps``. For other options see: :doc:`usage`.

TESTING
-------

Coverage report::

    tox -e cover && open cover/index.html

LICENSE
-------

Files under zuul comes from Zuul "A Project Gating System":

Copyright 2012 Hewlett-Packard Development Company, L.P.
Copyright 2013-2014 OpenStack Foundation
Copyright 2013-2018 Antoine Musso
Copyright 2014-2018 Wikimedia Foundation Inc.
Copyright 2015 Rackspace Australia

quibble/gitchangedinhead.py comes from Wikimedia CI scripts:

Copyright 2013, 2018, Antoine Musso
Copyright 2017, Kunal Mehta
Copyright 2017, 2018, Wikimedia Foundation Inc.


Other files are:

Copyright 2017-2018, Antoine Musso
Copyright 2017, Tyler Cipriani


Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
