Quibble changelog
=================

master (UNRELEASED)
-------------------
* …

1.0.0 (2021-07-16)
------------------

Features
~~~~~~~~
* Add skins for composer merge plugin
  `T280506 <https://phabricator.wikimedia.org/T280506>`_
  Spotted by Lens0021
  Antoine Musso
* Use glob pattern when generating `composer.local.json`.

  We previously forged the `composer.json` by explicitly referencing
  `composer.json` files to load based on the list of repositories to clone and
  the deprecated `EXT_DEPENDENCIES`/`SKIN_DEPENDENCIES` environment variable.

  With globbing, it makes it easier to reuse an existing workspace without
  having to relist  all the dependencies.
  Kosta Harlan.
* Introduce composer `phpunit:entrypoint` script to run the MediaWiki core
  PHPUnit tests. If not present (for example in old release branches) we still
  fallback to `maintenance/phpunit.php`).
  `T90875 <https://phabricator.wikimedia.org/T90875>`_
  Kosta Harlan
* Add support for connecting to already running MySQL.
  Use `--db-is-external` would cause Quibble to not spawn a one off MySQL, it
  will instead attempt to connect to localhost with the default credentials:
  `root` user with no password.

  The option is MySQL specific, it is silently ignored for SQLite or PostgreSQL.

  NOTE: the `wikidb` database is now dropped if it exists.
  Kosta Harlan
* Load Parsoid from `vendor.git` as fallback and set configuration.
  `T218534 <https://phabricator.wikimedia.org/T218534>`_
  `T227352 <https://phabricator.wikimedia.org/T227352>`_
  Kosta Harlan

Internal
~~~~~~~~
* Add a few more directories to git/docker/tox ignore lists
  Kosta Harlan

0.0.47 (2021-05-05)
-------------------

Features
~~~~~~~~
* Test Parsoid as if it were an extension
  `T271863 <https://phabricator.wikimedia.org/T271863>`_
  C. Scott Ananian
* Run `composer test-some` with paths. A new CI entry point which expect a list
  of files to be passed as argument. Quibble passes the list of files that have
  changed in HEAD.
  `T199403 <https://phabricator.wikimedia.org/T199403>`_
  James D. Forrester
* When running a user script (`quibble -c <command>`), inject MediaWiki
  environment variables (`MW_SERVER`, `MW_SCRIPT_PATH`, `MEDIAWIKI_USER` and
  `MEDIAWIKI_PASSWORD`).
  Antoine Musso

Bug fixes
~~~~~~~~~
* Under Python 3.5, do not use setuptools_scm 6 which fix installation under
  Debian Stretch.
  Antoine Musso

Internal
~~~~~~~~
* Make `black` to show the actual errors (`--diff`).
  Antoine Musso
* Use class name for MySQL str
  Antoine Musso

0.0.46 (2020-01-07)
-------------------

Highlights
~~~~~~~~~~

Python 3.5+ and 3.8
^^^^^^^^^^^^^^^^^^^

Explicitly require Python 3.5 or later which has been included in Debian since
2017 (Stretch) and Ubuntu 2016 (Xenial).

Python 3.8 is supported.

Apache support
^^^^^^^^^^^^^^

Since its conception Quibble has been using a PHP built-in server which until
PHP 7.4 serves requests serially and lacks extended configuration that could be
find in other web servers.  This release bring in support to point Quibble to
an external managed web server exposing MediaWiki.

This is done by using `--web-backend=external` and setting `--web-url` to the
base of the MediaWiki installation (without `index.php`). See `./docker` for an
example of how to spawn Apache and php-fpm using supervisord which is used by
the example `/DockerFile`.

`T225218 <https://phabricator.wikimedia.org/T225218>`_
Adam Wight && Kosta Harlan

Features
~~~~~~~~
* Recognizes `podman <https://podman.io/>`_ as a container environment.
  Marius Hoch
* Run phpunit-unit stage before MediaWiki installation.
  `T266441 <https://phabricator.wikimedia.org/T266441>`_
  Kosta Harlan

Bug fixes
~~~~~~~~~
* Fix regression which made us run linters for repositories besides MediaWiki
  extensions or skins (eg: mediawiki/services/parsoid).
  `T263500 <https://phabricator.wikimedia.org/T263500>`_
  Antoine Musso
* Fix Xvfb options which were improperly concatenated and thus ignored:
  * Drop `-ac` (disable host-based access control mechanisms) since it was
  never taken in account.
  * Framebuffer is now explicitly set to Xvfb default: display `:0` and
  `1280x1024x24`.
  Adam Wight && Antoine Musso
* Mute zuul.CloneMapper logging when running browser tests.
  Antoine Musso

Internal
~~~~~~~~
* Use `black <https://black.readthedocs.io/>`_ for code formatting.
  Kosta Harlan && Adam Wight && Antoine Musso
* Enhance code to more closely match PEP8.
  Adam Wight
* Enhance the example `Dockerfile`:
  * Drop an unused FROM
  * Collapse build steps to minimize intermediate layers
  * Fix a typo that prevented deletion of `/var/lib/apt/lists`
  * Spawn Apache2 with supervisor and change the entrypoint to use it as the
  web backend.
  Adam Wight
* Fix rst links in the changelog.
  Antoine Musso
* Enhance how options are passed to `pg_virtualenv`
  Antoine Musso
* Add CI test environment for Python 3.8.
  Antoine Musso
* Run `flake8 <https://flake8.pycqa.org/>`_ against all supported Python
  versions.
  Antoine Musso

0.0.45 (2020-09-18)
-------------------
* Fix database dumping `--dump-db-postrun`.
  `T239396 <https://phabricator.wikimedia.org/T239396>`_
  Antoine Musso
* Load mediawiki/services/parsoid as an extension.
  `T227352 <https://phabricator.wikimedia.org/T227352>`_
  C. Scott Ananian
* Remove hardcoded MediaWiki settings which were kept to support MediaWiki
  before 1.30 and cleanup settings that are now the default.
  Timo Tijhof
* Add support to point to an existing webserver instead of relying on the
  internally PHP built-in web server. Can be enabled with
  `--web-server=external`. The web host and port are configurable by passing
  the URL to `--web-url`.
  `T225218 <https://phabricator.wikimedia.org/T225218>`_
  Adam Wight
* Report python version.
  Adam Wight

Packaging
~~~~~~~~~
* Define python modules dependencies in setup.cfg instead of requirements.txt.
  `T235118 <https://phabricator.wikimedia.org/T235118>`_
  Antoine Musso
* Updated releasing documentation (`RELEASING.rst`).
  Antoine Musso

Internal
~~~~~~~~
* Delay database initialization until it is actually started.
  Adam Wight
* General cleanups in `QuibbleCmd.build_execution_plan` grouping all variables
  at the top of the method, using variables to avoid repeating methods calls.
  Adam Wight
* Manage database and web backends outside of commands. They are now in an
  ExitStack() context manager which is entered just before executing the plan.
  `T225218 <https://phabricator.wikimedia.org/T225218>`_
  Adam Wight

Testing
~~~~~~~
* Migrate the internal testsuite from Nose to pytest
  Antoine Musso
  `T254610 <https://phabricator.wikimedia.org/T254610>`_
* Add high level tests for building the execution plan which would have helped
  caught two reverts we did in 0.0.44. See `tests/plans/` which can then be run
  using: `tox -e unit -- tests/tests_plans.py`.
  Antoine Musso
  `T211702 <https://phabricator.wikimedia.org/T211702>`_
* Add an entry point for CI to run Quibble: `utils/ci-fullrun.sh`.
  `T235118 <https://phabricator.wikimedia.org/T235118>`_
  Antoine Musso
* Run tests in CI with python 3.5, 3.6, 3.7 and describe all tox virtualenv.
  The `unit` virtualenv has been renamed `py3-unit`.
  Antoine Musso

0.0.44 (2020-06-04)
-------------------

Misc
~~~~
* Output mysql/mariadb and postgresql version
  Reedy
* Do not create log directory when building the plan
  Antoine Musso
* Revert "Remove deprecated dump-autoload"
  Adam Wight
* Revert "Wipe repo with non-git commands"
  Antoine Musso
* Revert "Clone only the target project at first"
  Antoine Musso
* Revert "Drop --dry-run parameter"
  Antoine Musso

0.0.43 (2020-05-05)
-------------------

Misc
~~~~
* Remove deprecated dump-autoload
  Adam Wight
  `T181940 <https://phabricator.wikimedia.org/T181940>`_
* Wipe repo with non-git commands
  Adam Wight
  `T211702 <https://phabricator.wikimedia.org/T211702>`_

0.0.42 (2020-04-16)
-------------------

Features
~~~~~~~~
* Exclude phpunit group Standalone from the Database run
  James D. Forrester
* Clone only the target project at first
  Adam Wight
  `T211702 <https://phabricator.wikimedia.org/T211702>`_
* Docker: Migrate local docker to buster/php73/node10
  James D. Forrester

Misc
~~~~
* Remove redundant logging
  Adam Wight
* Extract git_clean into a function
  Adam Wight
* Drop redundant "Command" suffix
  Adam Wight
* Map mediawiki/services/parsoid to /workspace/src/services/parsoid
  C. Scott Ananian
* Extract execution decorator
  Adam Wight
* Provide GitClean as a command
  Adam Wight
* Logspam: Set Flow's default content format to wikitext
  Kosta Harlan

0.0.41 (2020-04-08)
-------------------

Features
~~~~~~~~
* Prefer 'npm ci' instead of 'npm prune' + 'npm install'
  Timo Tijhof
  `T234738 <https://phabricator.wikimedia.org/T234738>`_
* Add phpunit-standalone, for phpunit --group Standalone
  James D. Forrester
  `T225068 <https://phabricator.wikimedia.org/T225068>`_

Misc
~~~~
* RELEASING: Drop reference to now-shut qa mailing list
  James D. Forrester
* Split default_stages out into known_stages
  James D. Forrester

0.0.40 (2020-01-08)
-------------------

Features
~~~~~~~~
* Disable color codes around log level words in CI
  Timo Tijhof
  `T236222 <https://phabricator.wikimedia.org/T236222>`_
* Update Quibble to use api-testing npm package
  Clara Andrew-Wani
  `T236680 <https://phabricator.wikimedia.org/T236680>`_
* phpunit: Drop --debug-tests command, killed off in PHPUnit 8
  James D. Forrester
  `T192167 <https://phabricator.wikimedia.org/T192167>`_

Misc
~~~~
* Chronometer emits folding markers
  Adam Wight
  `T220586 <https://phabricator.wikimedia.org/T220586>`_
* Drop HHVM support
  Adam Wight
  `T236019 <https://phabricator.wikimedia.org/T236019>`_
* Drop --dry-run parameter
  Adam Wight

0.0.39 (2019-10-18)
-------------------

Features
~~~~~~~~
* Enable MediaWiki REST API for testing (/rest.php).
  Clara Andrew-Wani
  `T235564 <https://phabricator.wikimedia.org/T235564>`_

Misc
~~~~
* Ensure consistency between ``$wgServer`` and ``MW_SERVER`` environment
  variable.
  Antoine Musso
  `T235023 <https://phabricator.wikimedia.org/T235023>`_

0.0.38 (2019-10-09)
-------------------

Bug fix
~~~~~~~
* Set ``$wgServer`` to ``127.0.0.1`` instead of ``localhost`` to be consistent
  with the server name testsuite receive via ``MW_SERVER``. Else session is
  lost when a user get redirected after logging to ``localhost`` when the
  session has been created via ``127.0.0.1``.
  Antoine Musso
  `T235023 <https://phabricator.wikimedia.org/T235023>`_

0.0.37 (2019-10-09)
-------------------

Bug fix
~~~~~~~
* Fix missing quibble/mediawiki/local_settings.php

0.0.36 (2019-10-08)
-------------------

Features
~~~~~~~~
* Set ``$wgServer`` when installing.
  Antoine Musso
  `T233140 <https://phabricator.wikimedia.org/T233140>`_
* Display the time it took for a stage to complete.
  Adam Wight
* Log version of external commands we rely on (composer, npm, php..)
  Adam Wight
  `T181942 <https://phabricator.wikimedia.org/T181942>`_
* Allow appending values to MediaWiki generated ``LocalSettings.php``, now
  renamed to ``LocalSettings-installer.php`` and included. That allows us to
  easily insert settings either before or after the original settings file.
  Daniel Kinzler and Adam Wight
* Set ``$wgSecretKey`` to an arbitrary value, overriding the one set by
  the MediaWiki installer. Lets one run jobs via ``Special::RunJobs``.
  Daniel Kinzler
  `T230340 <https://phabricator.wikimedia.org/T230340>`_
* Set ``$wgEnableUploads = true``, overriding the value set by the MediaWiki
  installer.
  Adam Wight
  `T190829 <https://phabricator.wikimedia.org/T190829>`_
  and `T199939 <https://phabricator.wikimedia.org/T199939>`_


Bug fixes
~~~~~~~~~
* Exit on git clone failure.
  Antoine Musso
  `T233143 <https://phabricator.wikimedia.org/T233143>`_

Misc
~~~~
* Migrate the Python module to use ``setup.cfg``. Add pypi metadata. Use
  ``setuptools_scm`` to determine the version.
  Antoine Musso
* Determine application version using
  `setuptools_scm <https://pypi.org/project/setuptools-scm/>`_.
  Antoine Musso
* Use lazy formattiing for logging calls.
  Antoine Musso
* Release check list documented in ``RELEASING.rst``.
  Antoine Musso

0.0.35 (2019-09-17)
-------------------

Features
~~~~~~~~
* Set cache directory (``$wgCacheDirectory``). Notably switches
  LocalisationCache from database to cdb files making tests faster.
  Amir Sarabadani
  `T225730 <https://phabricator.wikimedia.org/T225730>`_

Bug fixes
~~~~~~~~~
* Fix default logdir that had double `workspace` prefixes.
  Adam Wight
* Deduplicate projects which caused Selenium tests for a repository having them   to be run twice.
  Adam Wight
  `T231862 <https://phabricator.wikimedia.org/T231862>`_
* Disable php output buffering in DevWebServer which aligns it with production
  usage and makes Fresnel performance reports more real.
  Amir Sarabadani
  `T219694 <https://phabricator.wikimedia.org/T219694>`_

Misc
~~~~
* Reduce side-effects and make code easier to understand.
  Adam Wight
  `T231862 <https://phabricator.wikimedia.org/T231862>`_

0.0.34 (2019-07-25)
-------------------

Bug fixes
~~~~~~~~~
* ``--packages-source=vendor`` caused selenium-test to fail since vendor.git
  lacks a package.json.
  Antoine Musso
  `T229020 <https://phabricator.wikimedia.org/T229020>`_

0.0.33 (2019-07-25)
-------------------

Features
~~~~~~~~
* Options to clone requirements from extension registration informations. When
  passing ``--resolve-requires``, Quibble will parse extension registration
  files (``extension.json`` and ``skin.json``) to find dependencies that needs
  to be cloned.

  With the addition of ``--fail-on-extra-requires``, Quibble would fail when
  the list of repositories cloned with ``--resolve-requires`` does not match
  the repositories passed to the command line. Can be used to ensure an
  integration job has the propeer set of dependencies hardcoded in.

  Antoine Musso
  `T193824 <https://phabricator.wikimedia.org/T193824>`_

* ``npm install`` now uses ``--prefer--offline`` to skip staleness checks for
  packages already present in the local cache (`npm documentation
  <https://docs.npmjs.com/misc/config#prefer-offline>`_).

* Support running PHPUnit unit tests. The ``phpunit-unit`` stage runs MediaWiki
  PHPUnit tests which do not require a MediaWiki installation.
  Kosta Harlan
  `T87781 <https://phabricator.wikimedia.org/T87781>`_

* Run node based Selenium tests in each repo.
  Adam Wight
  `T199116 <https://phabricator.wikimedia.org/T199116>`_

0.0.32 (2019-06-24)
-------------------

Features
~~~~~~~~
* Default to use 4 git workers when cloning repositories. Can be changed via
  ``--git-parallel``.
  Antoine Musso
  `T211701 <https://phabricator.wikimedia.org/T211701>`_

* Separate planning and execution phases. The commands to run have been
  extracted to standalone classes, the commands to run are now appended to a
  list to build an execution plan which is later executed. The execution plan
  can be inspected withouth execution by using ``--dry-run``.
  Adam Wight
  `T223752 <https://phabricator.wikimedia.org/T223752>`_

* ``--skip-install`` skips MediaWiki installation entirely. Can be used for
  example to run a statistical analysis.
  Kosta Harlan

Bug fixes
~~~~~~~~~
* Better argument handling, several options accepted multiple values
  (``nargs='*'``) which could result in unexpected behaviors such as a project
  to clone to be considered as a stage to build. The proper way was to use a
  double dash (``--``) to delimitate between options and arguments, but that is
  often forgotten. Instead:

  * ``--run`` and ``--skip`` are now comma separated values.

  * ``--commands`` is deprecated in favor of passing multiple ``--command``
    (short aliased with ``-c``).

  Antoine Musso
  `T218357 <https://phabricator.wikimedia.org/T218357>`_

Misc
~~~~
* ``EXT_DEPENDENCIES`` and ``SKIN_DEPENDENCIES`` are deprecated and Quibble
  emits a warnings when one of those environement variables is set. The
  repositories should be passed as command line arguments.
  Antoine Musso
  `T220199 <https://phabricator.wikimedia.org/T220199>`_

0.0.31 and earlier
------------------

See git changelog.
