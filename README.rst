Quibble: a test runner for MediaWiki
====================================

Quibble will clone the specific repository being tested, MediaWiki, and any
dependencies. Then all available tests are run, beginning with basic lint
checks and culminating in browser tests for each MediaWiki extension. Specific
tests can be included or excluded as needed.

Everything is performed by a single command, `quibble`.

Running quibble requires Python 3 and the following tools, or you can run in
the provided docker image.

- Chromium
- composer
- NodeJS
- npm
- php
- Xvfb

The source of the Docker container that runs Quibble in Wikimedia CI is in
Gerrit at https://gerrit.wikimedia.org/g/integration/config under the `dockerfiles`
directory, where you'll also find other images with slight variations such as
different PHP versions.

Further documentation can be found on https://doc.wikimedia.org/quibble/ .

How it works in Wikimedia CI
----------------------------

*To locally reproduce a build, see: :doc:`build-reproduction`.*

Get the latest image being run by Wikimedia CI::

  docker pull docker-registry.wikimedia.org/releng/quibble-buster-php74:latest

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
      docker-registry.wikimedia.org/releng/quibble-buster-php74:latest

Quibble will then do the initial cloning of repositories reusing bare
repositories from ``ref``, being local it is arguably faster than transferring
everything from Gerrit. The ``composer install`` and ``npm install`` will save
the downloaded packages to ``cache`` which speed up the next run.

Finally, having ``/src`` mounted from the host, lets one reuse the installed
wiki. One can later skip cloning/checking out the repositories by passing
``--skip-zuul`` and skip installing composer and npm dependencies with
``--skip-deps``. For other options see: :doc:`usage`.

Quick Start
-----------

To test a change to Quibble itself, it is recommended that you run it with
a modified version of the same Docker image as used by Wikimedia CI.

Prerequisites from <https://www.mediawiki.org/wiki/Continuous_integration/Docker>:
* Docker
* docker-pkg
* clone of `integration/config <https://gerrit.wikimedia.org/g/integration/config>`_ from Gerrit

To modify and run the image locally:

* Submit your patch to Gerrit for review. It does not need to be merged yet,
  but this allows the existing logic to fetch and install your version
  in the container.
* Edit `dockerfiles/quibble-buster/Dockerfile.template` and specify
  your commit hash in the `QUIBBLE_VERSION` assignment.
* Make a temporary bump in the quibble-buster and quibble-buster-php74 changelogs.
  Use a version like `-dev1` rather than regular semver versions as those builds
  may remain in your local cache and complicate future testing on your machine).
* Run `dockerfiles/config.yaml build --select '*/quibble-buster:*' dockerfiles/`


TESTING
-------

Coverage report::

    tox -e cover && open cover/index.html

quibble.yaml
------------

Since version 1.5.0, Quibble will look for a ``quibble.yaml`` file in the root
of the project it is testing.

The current supported configuration options are:

.. code-block:: yaml

  # "early warning" related functionality, when Quibble fails a job
  # (e.g. 'composer-test' or 'npm-test' exit with a non-zero code)
  # Quibble will read this configuration to send to an external
  # HTTP endpoint. See also the --reporting-url option.
  earlywarning:
      # Quibble passes both the "should_vote" and "should_comment"
      # values to an external HTTP endpoint. An application at
      # that endpoint can then potentially make a comment in
      # a code review system with a verification vote and/or
      # a comment with the status of the failed job.
      should_vote: 1
      should_comment: 1

