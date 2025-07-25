Quibble changelog
=================

1.14.2 (2025-07-24)
-------------------

Features
~~~~~~~~
* ci-fullrun-extensions: add IPInfo as a dependency
  Antoine Musso
* Accept multiple --run --skip
  Antoine Musso
* Use trailing slash for Parsoid autoload directory
  `T195211 <https://phabricator.wikimedia.org/T195211>`_
  `T400299 <https://phabricator.wikimedia.org/T400299>`_
  C. Scott Ananian

Fixes
~~~~~

* doc: Remove quotes from env var value
  Jakob Warkotsch
* build: raise required python from 3.7 to 3.9
  `T396670 <https://phabricator.wikimedia.org/T396670>`_
  Antoine Musso
* Replace subprocess `universal_newlines` by `text`
  Antoine Musso
* Drop six dependency by using Python 3 dict.items()
  Antoine Musso
* Stop setting EXECUTOR_NUMBER environment variable
  `T399283 <https://phabricator.wikimedia.org/T399283>`_
  Antoine Musso

1.14.1 (2025-05-06)
-------------------

* Ensure environment variables are passed to MediaWiki maintenance scripts.
  Jakob Warkotsch

1.14.0 (2025-04-30)
-------------------

Features
~~~~~~~~
* Update list of phpunit config files to copy to log directory and set
  ``MW_RESULTS_CACHE_SERVER_BASE_URL``.
  `T378797 <https://phabricator.wikimedia.org/T378797>`_
  `T384927 <https://phabricator.wikimedia.org/T384927>`_
  Arthur Taylor
* Add support for OpenSearch. This requires:

  * OpenSearch to be started independently and is expected to be listening on ``127.0.0.1:9200``.
  * ``mediawiki/extensions/CirrusSearch`` to be cloned.
  * Setting an environment variable ``QUIBBLE_OPENSEARCH=true``

  `T386691 <https://phabricator.wikimedia.org/T386691>`_
  Jakob Warkotsch

Fixes
~~~~~
* Fix logging exception when using --resolve-requires.
  Antoine Musso
* Avoid success cache key data collisions using null separator.
  Dan Duvall
* Fix casing in "Run QUnit tests" section label.
  Timo Tijhof

1.13.0 (2025-02-26)
-------------------

Feature
~~~~~~~
* Skip execution upon a success cache hit
  `T383243 <https://phabricator.wikimedia.org/T383243>`_
  Dan Duvall

1.12.0 (2025-01-17)
-------------------

Features
~~~~~~~~
* Remove Python implementation of PhpUnit test suites splitting
  `T365978 <https://phabricator.wikimedia.org/T365978>`_
  Arthur Taylor
* Experimental "success cache" support, intended to short circuit a build when
  the same set of code has been known to already pass.
  `T383243 <https://phabricator.wikimedia.org/T383243>`_
  Dan Duvall

1.11.0 (2024-10-29)
-------------------

Fixes
~~~~~
* Remove update.php --skip-external-dependencies option
  `T370380 <https://phabricator.wikimedia.org/T370380>`_
  Timo Tijhof

Feature
~~~~~~~
* Add support for specifying patchsets when using the `--change`
  command-line argument
  `T376602 <https://phabricator.wikimedia.org/T376602>`_
  Arthur Taylor

1.10.0 (2024-09-17)
-------------------

Feature
~~~~~~~
* Switch to using the composer-native implementation of PHPUnit
  parallel testing. Retain the Python implementation for now in
  case we need to switch back.
  `T365976 <https://phabricator.wikimedia.org/T365976>`_
  Arthur Taylor

1.9.4 (2024-07-19)
------------------

Fixes
~~~~~

* Fix ``--change``, introduced in 1.5.6 in September 2023, which never worked.
  Antoine Musso

* Fix ``MW_SKIP_EXTERNAL_DEPENDENCIES`` which was set whenever
  ``mediawiki/vendor`` was used when it was only to be set for patch targetting
  ``mediawiki/vendor`` itself.
  `T370380 <https://phabricator.wikimedia.org/T370380>`_
  Timo Tijhof

1.9.3 (2024-07-10)
------------------

Fix
~~~

* Fix "Multiple targets are not supported" when running QUnit tests with
  Chrome.
  `T366799 <https://phabricator.wikimedia.org/T366799>`_
  Antoine Musso

1.9.2 (2024-07-03)
------------------

Fixes and cleanups
~~~~~~~~~~~~~~~~~~

For the PHPUnit parallel run:

* Only add the Scribunto Sandbox test to the split groups if
  Scribunto is present.
  `T368783 <https://phabricator.wikimedia.org/T368783>`_
  Arthur Taylor
* Add a log notice to the end of parallel runs to support developers
  who run into issues with the new config.
  `T361190 <https://phabricator.wikimedia.org/T361190>`_
  Arthur Taylor

1.9.1 (2024-06-18)
------------------

Fixes and cleanups
~~~~~~~~~~~~~~~~~~

For the PHPUnit parallel run:

* Copy the cache result files and  generated configuration
  (``phpunit-parallel.xml``) under ``$LOG_DIR`` to allow their archival by CI.
  Kosta Harlan
* Specify ``.json`` suffix for result cache files.
  Kosta Harlan

1.9.0 (2024-06-14)
------------------

Feature
~~~~~~~
* Add support for running some PHPUnit test suites in Parallel. Can be
  enabled for a specific run by setting QUIBBLE_PHPUNIT_PARALLEL, or
  explicitly specifying `phpunit-parallel` in the `--run` list.
  `T361190 <https://phabricator.wikimedia.org/T361190>`_
  Arthur Taylor

1.8.0 (2024-05-30)
------------------

Feature
~~~~~~~
* local_settings: Load DevelopmentSettings.php after setting MW_QUIBBLE_CI
  `T359043 <https://phabricator.wikimedia.org/T359043>`_
  Kosta Harlan

Documentation
~~~~~~~~~~~~~
* Add instructions for debugging Quibble runs.
  Arthur Taylor

1.7.0 (2024-03-25)
------------------

Features
~~~~~~~~
* Add support for ``FORCE_COLOR`` environment variable to enable color output
  even when standard input is not a tty.
  `T236222 <https://phabricator.wikimedia.org/T236222>`_
  Antoine Musso
* Remove `LocalSettings.php` before installing, if it is detected to have been
  generated by Quibble (detected by if a line is ``# Quibble MediaWiki
  configuration``).
  `T218647 <https://phabricator.wikimedia.org/T218647>`_
  Antoine Musso
* Do not capture commands output in interactive mode. This lets bash to start
  an interactive session when using ``quibble -c bash``.
  `T360443 <https://phabricator.wikimedia.org/T360443>`_
  Antoine Musso

Fixes and cleanups
~~~~~~~~~~~~~~~~~~
* Remove support to detect changes made to no more used PHP files extensions
  (``.php5``, ``.inc``, ``.sample``).
  Lucas Werkmeister
* When completing ``mediawiki/vendor`` with development requirements, instruct
  ``composer require`` to run non interactively which lets it move some
  requirements to development requirements.
  `T354141 <https://phabricator.wikimedia.org/T354141>`_
  Mark Hershberger and Antoine Musso
* Force git to fetch tags being updated.
  `T356247 <https://phabricator.wikimedia.org/T356247>`_
  Antoine Musso
* Remove use of `router.php` from PhpWebserver.
  `T357070 <https://phabricator.wikimedia.org/T357070>`_
  Umherirrender

Internal
~~~~~~~~
* Remove ``MW_COMPOSER_MERGE_MW_IN_VENDOR`` which has been used since ~ 2018.
  `T354178 <https://phabricator.wikimedia.org/T354178>`_
  Antoine Musso
* Move LocalSettings template lookup to a method
  Antoine Musso
* Remove obsolete comment about ``--color``
  Antoine Musso

1.6.0 (2023-12-13)
------------------

Breaking changes
~~~~~~~~~~~~~~~~

* Migrate from ``setup.py`` to ``pyproject.toml`` (PEP 517). This requires your
  local copies of ``pip`` and ``setuptools`` to be upgraded to a sufficiently
  recent version.
  `T345093 <https://phabricator.wikimedia.org/T345093>`_

* Require tox version 4, which only affects Quibble developers. One can create
  a local environment using ``tox devenv``. The optimization to share
  environment directories betwen tox test envs have been removed since that is
  no more supported by tox v4.
  `T345695 <https://phabricator.wikimedia.org/T345695>`_
  `T348434 <https://phabricator.wikimedia.org/T348434>`_
  Antoine Musso

Internal
~~~~~~~~
* Move MediaWiki install arguments to a standalone function and add unit
  testing.
  Antoine Musso
* Move ``LocalSettings.template`` logic to a method.
  Antoine Musso
* Skip PostgreSQL test when it is not available.
  Antoine Musso
* Remove unused ``util.php_version()``.
  Antoine Musso
* In the CI full run tests, use a virtualenv to setup Quibble in order to
  upgrade dependencies required to support ``pyproject.toml``
  Antoine Musso
* Add support for ``importlib.resources`` under python 3.9+. The deprecated
  ``pkg_resources`` is still used under python 3.7/3.8.
  Antoine Musso

1.5.6 (2023-09-19)
------------------

Breaking change
~~~~~~~~~~~~~~~
* Remove ``MW_QUIBBLE_CI`` environment variable, introduced in 1.5.3.

  In PHP, check the ``MW_QUIBBLE_CI`` constant instead. This is set
  both during all PHP and non-PHP stages (e.g. QUnit or api-testing),
  except for pure unit tests (where LocalSettings doesn't load).
  Those should not vary by environment.

  To detect Apache from within a Node.js process,
  check the ``QUIBBLE_APACHE=1`` environment variable instead.

Features
~~~~~~~~
* MariaDB now starts with ``--innodb-print-all-deadlocks`` which emit a
  detailled report about database dead locks. Emitted to the error log, the
  output can be found in ``$LOG_DIR/mysql-error.log``.
  `T342088 <https://phabricator.wikimedia.org/T342088>`_
  Antoine Musso
* Replace deprecated setuptools ``license_file`` by ``license_files``.
  Antoine Musso
* Raise ``setuptools-git-versioning`` requirements to at least 1.8.0 and move
  its configuration from ``setup.py``to ``pyproject.toml``.
  `See changelog <https://setuptools-git-versioning.readthedocs.io/en/stable/changelog.html#change-1.8.0>`_
  Antoine Musso
* Remove support for ``--run==all`` to run all stages which is the default.
  Running all stages is now represented internally by an empty list.
  Antoine Musso
* Add experimental ``--change`` to retrieve a change from Wikimedia Gerrit
  instance. The retrieved metadata are used to set ``ZUUL_URL``,
  ``ZUUL_PROJECT``, ``ZUUL_BRANCH`` and ``ZUUL_REF`` which overrides the
  existing environmnent.
  Antoine Musso

Documentation
~~~~~~~~~~~~~
* Document how to test Quibble changes (see "Quick Start" in the readme).
  Timo Tijhof


Internal
~~~~~~~~
* Remove parsoid from ``utils/ci-fullrun-extensions.sh``.
  Antoine Musso
* Remove files remaining after removal of Docker support in 1.4.2.
  Timo Tijhof
* Remove Sphinx setuptools integration (``build_sphinx``) and replace it by
  ``sphinx-build``.
  Antoine Musso
* Refresh Sphinx configuration file removing explicit defaults and comments.
  Antoine Musso

1.5.5 (2023-07-14)
-------------------

Features
~~~~~~~~

* Fix Parsoid CI after changes to use phpunit directly
  `T90875 <https://phabricator.wikimedia.org/T90875>`_
  Subramanya Sastry
* Run PHPUnit unit tests after installing MediaWiki
  `T227900 <https://phabricator.wikimedia.org/T227900>`_
  Daimona Eaytoy

Documentation
~~~~~~~~~~~~~

* commands: Shorten the descriptons of some commands
  James D. Forrester

Internal
~~~~~~~~

* utils: fullrun-extensions: Clone SecurePoll
  `T341840 <https://phabricator.wikimedia.org/T341840>`_
  Taavi Väänänen

1.5.4 (2023-04-03)
-------------------

Features
~~~~~~~~

* Switch generated LocalSettings.php to use ``AutoLoader::registerNamespaces``
  instead of internal ``AutoLoader->psr4Namespaces``.
  `T332930 <https://phabricator.wikimedia.org/T332930>`_
  Arlo Breault
* Set ``--pagepath`` option in the ``maintenance/addSite.php`` call.
  `T331280 <https://phabricator.wikimedia.org/T331280>`_
  Jakob Warkotsch
* Set ``MW_SKIP_EXTERNAL_DEPENDENCIES`` environment variable during
  mediawiki/vendor jobs.
  `T333412 <https://phabricator.wikimedia.org/T333412>`_
  Timo Tijhof

1.5.3 (2023-03-09)
-------------------

Features
~~~~~~~~

* Introduce ``MW_QUIBBLE_CI`` environment variable (value ``1``).
  `T331621 <https://phabricator.wikimedia.org/T331621>`_
  Kosta Harlan

Internal
~~~~~~~~

* Drop support for Python 3.5 and 3.6
* Switch to ``subprocess.Popen()`` for most command invocations,
  instead of ``subprocess.check_call()``
  `T331061 <https://phabricator.wikimedia.org/T331061>`_
  Kosta Harlan & Antoine Musso

1.5.2 (2023-03-06)
-------------------

Internal
~~~~~~~~
* reporting: Include ``pipeline`` in payload
  `T331236 <https://phabricator.wikimedia.org/T331236>`_
  Martin Urbanec
* reporting: Include ``output`` in payload
  `T331061 <https://phabricator.wikimedia.org/T331061>`_
  Kosta Harlan
* reporting: Command name can be a string
  `T323750 <https://phabricator.wikimedia.org/T323750>`_
  Kosta Harlan

1.5.1 (2023-03-01)
-------------------

Features
~~~~~~~~
* reporting: Include ``CalledProcessError.cmd`` in payload
  `T330750 <https://phabricator.wikimedia.org/T330750>`_
  Kosta Harlan

1.5.0 (2023-02-21)
------------------

Features
~~~~~~~~
* Allow sending build failure data to external endpoint
  `T323750 <https://phabricator.wikimedia.org/T323750>`_
  Kosta Harlan
* maintenance: Use run.php if it exists (MW 1.40+)
  `T326333 <https://phabricator.wikimedia.org/T326333>`_
  Antoine Musso, James Forrester
* Warn if files are left over after git clean -xqdf
  `T321795 <https://phabricator.wikimedia.org/T321795>`_
  Antoine Musso

Internal
~~~~~~~~
* Add Python 3.9 testing
* black: Pin major version for black
* black: Apply formatting fixes

1.4.7 (2022-10-25)
------------------

Features
~~~~~~~~
* Set ``QUIBBLE_APACHE=1`` environment variable in the `api-testing` stage as
  well as when running user scripts (`--command`).
  `T320935 <https://phabricator.wikimedia.org/T320935>`_
  Kosta Harlan
* Enhance `--help` usage output by splitting options in different argument
  groups.
  Antoine Musso

Bug fix
~~~~~~~
* Handle invalid Unicode received from tests.
  `T318029 <https://phabricator.wikimedia.org/T318029>`_
  Antoine Musso

1.4.6 (2022-08-31)
-------------------

Features
~~~~~~~~
* Allow overriding the npm command by setting the `NPM_COMMAND`. Currently
  supports https://pnpm.io/.
  `T305525 <https://phabricator.wikimedia.org/T305525>`_
  Kosta Harlan
* Run `maintenance/addSite.php` to enable Wikibase wikis to link to themselves.
  Michael Große
  `T314586 <https://phabricator.wikimedia.org/T314586>`_

Internal
~~~~~~~~
* Change Sphinx documentation default language from `None` to `en`
  Antoine Musso
* Update image names in README
  Lucas Werkmeister

1.4.5 (2022-03-28)
------------------
* In ``phpbench`` use ``git-checkout`` instead of ``git-switch`` which has been
  introduced in Git 2.27 and is not available by default in Debian Buster.
  `T291549 <https://phabricator.wikimedia.org/T291549>`_
  Kosta Harlan

1.4.4 (2022-03-17)
------------------
* Properly setup memcached. The CLI installer automatically set
  ``$wgMemCachedServers = []`` which disabled Memcached configuration. It is
  now set to ``[ '127.0.0.1:11211' ]``.
  `T300340 <https://phabricator.wikimedia.org/T300340>`_
  Kosta Harlan
* Set ``$wgMemCachedPersistent = true``.

1.4.3 (2022-03-03)
------------------
* Fix typo in PHP Constant: ``MW_QIBBLE_CI`` -> ``MW_QUIBBLE_CI``.
  Kosta Harlan

1.4.2 (2022-03-03)
------------------

Features
~~~~~~~~
* Usage of PHP global variable ``$wgWikimediaJenkinsCI`` is now deprecated.
  Code should instead check for existence of PHP constant ``MW_QUIBBLE_CI``.
  Daniel Kinzler

Bug fix
~~~~~~~
* Fix backend teardown when no server exists (such as SQLite).
  `T302226 <https://phabricator.wikimedia.org/T302226>`_
  Kosta Harlan

Internal
~~~~~~~~
* Remove ``Dockerfile``. It was not used for Wikimedia CI, for local
  development one can extend the official images in `integration/config
  <https://gerrit.wikimedia.org/g/integration/config/>`_.
  Kosta Harlan
* In ``utils/ci-full*`` scripts, stop using ``$ZUUL_REF``. It is set by CI and
  we should not override it. That caused build to use obsolete code from our
  Zuul system.
  `T302707 <https://phabricator.wikimedia.org/T302707>`_
  Antoine Musso

1.4.1 (2022-02-16)
------------------
* Stop definining ``MW_INSTALL_PATH`` constant will be defined by MediaWiki
  directly.
  `T300301 <https://phabricator.wikimedia.org/T300301>`_
  Daniel Kinzler

1.4.0 (2022-02-02)
-------------------

Features
~~~~~~~~
* Set Memcached as main cache type if extension is loaded
  `T300340 <https://phabricator.wikimedia.org/T300340>`_
  Kosta Harlan
* phpbench: Support aggregate reports
  `T291549 <https://phabricator.wikimedia.org/T291549>`_
  Kosta Harlan

Internal
~~~~~~~~
* Run post-dependency install, pre-test steps in parallel
  `T225730 <https://phabricator.wikimedia.org/T225730>`_
  Kosta Harlan
* Split extension and skin npm and composer tests
  Adam Wight
* Split core npm and composer tests
  Adam Wight
* BrowserTests: Rework npm parallel install using ParallelCommand
  Kosta Harlan
* Parallelism as a command object
  Adam Wight
* ci-fullrun: Add extension variant
  Kosta Harlan

1.3.0 (2022-01-17)
------------------

Features
~~~~~~~~
* Set ``QUIBBLE_APACHE`` environment variable (value ``1``) when using an
  external web server (``--web-backend=external``). This can be used to skip
  tests that might have issues when web backend requests are run concurrently.
  `T297480 <https://phabricator.wikimedia.org/T297480>`_
  Kosta Harlan
* Option to run ``npm install`` in parallel when running Browsertests:
  ``--parallel-npm-install``. This should cut the overall build time
  significantly.
  `T226869 <https://phabricator.wikimedia.org/T226869>`_
  Kosta Harlan

Documentation
~~~~~~~~~~~~~
* Hide the table of content to reduce clutterness.
  https://doc.wikimedia.org/quibble/
  Antoine Musso
* Move LICENSE out of the main page to its own page.
  Antoine Musso

Internal
~~~~~~~~
* Update NodeJS to version 14 in the example Dockerfile.
  `T294931 <https://phabricator.wikimedia.org/T294931>`_
  Kosta Harlan

Work related to parallelization of the Quibble stages:

* Introduce utilities to redirect stdout and stderr to a logger
  ``quibble.util.redirect_all_streams``
  Adam Wight
* Wrapper to pretty-print parallel job progress
  ``quibble.util.ProgressReporter``
  Adam Wight

1.2.0 (2021-10-25)
-------------------

Features
~~~~~~~~
* Support multiple workers in PHP 7.4+ web server. It already could be set via
  `PHP_CLI_SERVER_WORKERS` environment variable. One can now set it via the
  `--web-php-workers` option.
  `T259456 <https://phabricator.wikimedia.org/T259456>`_
  Antoine Musso

Bug fixes
~~~~~~~~~
* Replace `setuptools_scm` with `setuptools-git-versioning`. Fixes installation
  issue under Python 3.5 or with setuptools 45+.
  `T292772 <https://phabricator.wikimedia.org/T292772>`_
  Antoine Musso
* Fix MySQL user creation on Debian Bullseye.
  Antoine Musso

Misc
~~~~
* Disable PHPUnit Junit report by default. Can be manually enabled with the
  `--phpunit-junit` option if still needed.
  `T256402 <https://phabricator.wikimedia.org/T256402>`_
  Antoine Musso

1.1.1 (2021-10-08)
------------------

Internal
~~~~~~~~
* phpbench: Run composer install first
  `T291549 <https://phabricator.wikimedia.org/T291549>`_
  Kosta Harlan

1.1.0 (2021-10-06)
-------------------

Features
~~~~~~~~
* Add support for executing phpbench tests when repository has `composer phpbench` script defined.
  `T291549 <https://phabricator.wikimedia.org/T291549>`_
  Kosta Harlan

Internal
~~~~~~~~~
* test: fix flappy test for core being cloned first
* setup.cfg: replace dashes with underscores

1.0.1 (2021-07-23)
-------------------
* Revert *Load Parsoid from `vendor` as fallback and set configuration*.
  The feature caused a regression on Wikimedia CI.
  `T287001 <https://phabricator.wikimedia.org/T287001>`_
  C. Scott Ananian

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
* Load Parsoid from `vendor` as fallback and set configuration.
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
