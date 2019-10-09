Quibble changelog
=================

master ()
---------

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
