Reproducing a CI build
----------------------

Quibble allows you to locally replicate test runs as you witnessed them in CI. This can be useful when debugging integration with projects you are not normally involved with and don't keep a local copy of, or other obscure problems.

Create a `.env` file to specify the variables needed to replicate a CI run.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find them in the [Jenkins job parameters](https://integration.wikimedia.org/ci/job/quibble-vendor-mysql-hhvm-docker/9262/parameters/). E.g.::

    EXT_DEPENDENCIES=mediawiki/extensions/BetaFeatures\nmediawiki/extensions/Capiunto\nmediawiki/extensions/CentralAuth\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/Echo\nmediawiki/extensions/EducationProgram\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventLogging\nmediawiki/extensions/GeoData\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/PropertySuggester\nmediawiki/extensions/Scribunto\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SyntaxHighlight_GeSHi\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseLexeme\nmediawiki/extensions/WikibaseQuality\nmediawiki/extensions/WikibaseQualityConstraints\nmediawiki/extensions/WikimediaBadges\nmediawiki/extensions/cldr
    ZUUL_CHANGE=449454
    ZUUL_CHANGE_IDS=449453,1 449454,1
    ZUUL_CHANGES=mediawiki/extensions/WikibaseLexeme:master:refs/changes/53/449453/1^mediawiki/extensions/ContentTranslation:master:refs/changes/54/449454/1
    ZUUL_PATCHSET=1
    ZUUL_REF=refs/zuul/master/Za65b9a0ba15a4c9cad4a8a60a6357f5f
    ZUUL_COMMIT=af14dcbcc39b58d9ae8d06fef6bb0ee997711a3f
    ZUUL_URL=git://contint2001.wikimedia.org
    ZUUL_PROJECT=mediawiki/extensions/ContentTranslation
    MW_COMPOSER_MERGE_MW_IN_VENDOR=1
    ZUUL_BRANCH=master
    PHP_BIN=hhvm

In this example we are testing the integration of many mediawiki extensions, in particular with a change in WikibaseLexeme having an adverse effect on a change in ContentTranslation.

Not all of the variables visible in the Jenkins jobs parameters are needed. The important ones are::

      EXT_DEPENDENCIES
      SKIN_DEPENDENCIES
      ZUUL_PROJECT
      ZUUL_REF
      ZUUL_BRANCH

`EXT_DEPENDENCIES` and `SKIN_DEPENDENCIES` are deprecated and will emit a warning. Instead the list of repositories should be passed to Quibble as arguments::

    quibble mediawiki/extensions/BetaFeatures mediawiki/skins/MinervaNeue [...]

At the moment only builds with one change set can be reproduced locally because git://contint2001.wikimedia.org is not accessible remotely.

Choose the right docker image.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You must also choose the correct quibble image for the base OS and php interpreter to mirror the job:
e.g. Debian Stretch and hhvm::

      docker-registry.wikimedia.org/releng/quibble-stretch-hhvm

You can find the full list of images by looking though those with quibble in the name from the WMF docker registry. e.g.::

      curl -X GET https://docker-registry.wikimedia.org/v2/_catalog | grep quibble

Run quibble with the env file as parameter.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run::

    docker run -it --rm \
      --env-file ./.env \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-stretch-hhvm:latest

Optionally skip (slow) installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For repeated runs of the same change, assuming you have once successfully executed the cloning and installation steps, you can omit them by adding `--skip-zuul --skip-deps`::

    docker run -it --rm \
      --env-file ./.env \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-stretch-hhvm:latest \
      --skip-zuul \
      --skip-deps

Remove LocalSettings.php between runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mediawiki ensures that previous installations are not accidentally destroyed by repeated runs of the installer (overwriting configuration values), so it is up to you to always remove the previous run's configuration file to avoid problems::

    rm src/LocalSettings.php
