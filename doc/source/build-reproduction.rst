Reproducing a CI build
----------------------

Quibble allows you to locally replicate test runs as you witnessed them in CI. This can be useful when debugging integration with projects you are not normally involved with and don't keep a local copy of, or other obscure problems.

Create a `.env` file to specify the variables needed to replicate a CI run.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find them in the Jenkins job parameters, [for example](https://phab.wmfusercontent.org/file/data/intwp5iddudl53ec24uu/PHID-FILE-4h2a5udx4sjoodnitahl/jenkins_params.png)::

    BASE_LOG_PATH=67/545967/1
    EXT_DEPENDENCIES=mediawiki/extensions/AbuseFilter\nmediawiki/extensions/AntiSpoof\nmediawiki/extensions/Babel\nmediawiki/extensions/CheckUser\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/CiteThisPage\nmediawiki/extensions/CodeEditor\nmediawiki/extensions/ConfirmEdit\nmediawiki/extensions/ContentTranslation\nmediawiki/extensions/Echo\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventLogging\nmediawiki/extensions/FileImporter\nmediawiki/extensions/Flow\nmediawiki/extensions/Gadgets\nmediawiki/extensions/GeoData\nmediawiki/extensions/GlobalCssJs\nmediawiki/extensions/GlobalPreferences\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/ImageMap\nmediawiki/extensions/InputBox\nmediawiki/extensions/Interwiki\nmediawiki/extensions/JsonConfig\nmediawiki/extensions/MobileApp\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/NavigationTiming\nmediawiki/extensions/ParserFunctions\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/Poem\nmediawiki/extensions/SandboxLink\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SpamBlacklist\nmediawiki/extensions/TemplateData\nmediawiki/extensions/Thanks\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/Translate\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseCirrusSearch\nmediawiki/extensions/WikibaseMediaInfo\nmediawiki/extensions/cldr
    EXT_NAME=MobileFrontend
    LOG_PATH=67/545967/1/test/wmf-quibble-vendor-mysql-php72-docker/55820fc
    MW_COMPOSER_MERGE_MW_IN_VENDOR=1
    SKIN_DEPENDENCIES=mediawiki/skins/MinervaNeue\nmediawiki/skins/Vector
    ZUUL_CHANGE=545967
    ZUUL_CHANGE_IDS=545967,1
    ZUUL_CHANGES=mediawiki/extensions/MobileFrontend:master:refs/changes/67/545967/1
    ZUUL_COMMIT=c28d0377ea56884905e57cf81ca422cac07ece98
    ZUUL_PATCHSET=1
    ZUUL_PIPELINE=test
    ZUUL_PROJECT=mediawiki/extensions/MobileFrontend
    ZUUL_REF=refs/zuul/master/Zbe0ebb207a1d4c33935e2a0cf8db9a1c
    ZUUL_URL=git://contint2001.wikimedia.org
    ZUUL_UUID=55820fcebdae4c4291e95f01d4b3f987
    ZUUL_VOTING=1

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
e.g. Debian Stretch and php 7.2::

      docker-registry.wikimedia.org/releng/quibble-stretch-php72

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
      docker-registry.wikimedia.org/releng/quibble-stretch-php72:latest

Optionally skip (slow) installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For repeated runs of the same change, assuming you have once successfully executed the cloning and installation steps, you can omit them by adding `--skip-zuul --skip-deps`::

    docker run -it --rm \
      --env-file ./.env \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-stretch-php72:latest \
      --skip-zuul \
      --skip-deps

Remove LocalSettings.php between runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mediawiki ensures that previous installations are not accidentally destroyed by repeated runs of the installer (overwriting configuration values), so it is up to you to always remove the previous run's configuration file to avoid problems::

    rm src/LocalSettings.php
