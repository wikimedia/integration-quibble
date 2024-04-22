Reproducing a CI build
----------------------

Quibble allows you to locally replicate test runs as you witnessed them in CI. This can be useful when debugging integration with projects you are not normally involved with and don't keep a local copy of, or other obscure problems.

Create a `.env` file to specify the variables needed to replicate a CI run.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find them in the Jenkins job parameters, `for example <https://phab.wmfusercontent.org/file/data/intwp5iddudl53ec24uu/PHID-FILE-4h2a5udx4sjoodnitahl/jenkins_params.png>`_::

    BASE_LOG_PATH=67/545967/1
    EXT_DEPENDENCIES=mediawiki/extensions/AbuseFilter\nmediawiki/extensions/AntiSpoof\nmediawiki/extensions/Babel\nmediawiki/extensions/CheckUser\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/CiteThisPage\nmediawiki/extensions/CodeEditor\nmediawiki/extensions/ConfirmEdit\nmediawiki/extensions/ContentTranslation\nmediawiki/extensions/Echo\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventLogging\nmediawiki/extensions/FileImporter\nmediawiki/extensions/Flow\nmediawiki/extensions/Gadgets\nmediawiki/extensions/GeoData\nmediawiki/extensions/GlobalCssJs\nmediawiki/extensions/GlobalPreferences\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/ImageMap\nmediawiki/extensions/InputBox\nmediawiki/extensions/Interwiki\nmediawiki/extensions/JsonConfig\nmediawiki/extensions/MobileApp\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/NavigationTiming\nmediawiki/extensions/ParserFunctions\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/Poem\nmediawiki/extensions/SandboxLink\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SpamBlacklist\nmediawiki/extensions/TemplateData\nmediawiki/extensions/Thanks\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/Translate\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseCirrusSearch\nmediawiki/extensions/WikibaseMediaInfo\nmediawiki/extensions/cldr
    EXT_NAME=MobileFrontend
    LOG_PATH=67/545967/1/test/wmf-quibble-vendor-mysql-php74-docker/55820fc
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

Choose the right Docker image.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You must also choose the correct quibble image for the base OS and php interpreter to mirror the job:
e.g. Debian Buster and php 7.4::

      docker-registry.wikimedia.org/releng/quibble-buster-php74

You can find the full name of the image associated with a job run by looking through the Jenkins Console Log for the build in question and searching for ``docker`` invocations. Somewhere in the first 10 seconds of logs you should see a docker invocation to run the associated container::

      13:05:00 + exec docker run --entrypoint=quibble-with-supervisord
      --tmpfs /workspace/db:size=320M --volume /srv/jenkins/workspace/
      quibble-composer-mysql-php74-noselenium/src:/workspace/src
      --volume /srv/jenkins/workspace/quibble-composer-mysql-php74-
      noselenium/cache:/cache --volume /srv/jenkins/workspace/quibble-
      composer-mysql-php74-noselenium/log:/workspace/log --volume
      /srv/git:/srv/git:ro --security-opt seccomp=unconfined --init
      --rm --label jenkins.job=quibble-composer-mysql-php74-noselenium
      --label jenkins.build=53 --env-file /dev/fd/63
      docker-registry.wikimedia.org/releng/quibble-buster-php74:1.7.0-s1
     --reporting-url=https://earlywarningbot.toolforge.org --packages
     -source composer --db mysql --db-dir /workspace/db --git-parallel=8
     --reporting-url=https://earlywarningbot.toolforge.org --skip
     selenium,npm-test,phpunit-standalone,api-testing

(in this case `docker-registry.wikimedia.org/releng/quibble-buster-php74:1.7.0-s1`). Alternatively, you can find the full list of images at the `Wikimedia Docker Registry <https://docker-registry.wikimedia.org/>`_. Or look at the `CI configuration <https://gerrit.wikimedia.org/g/integration/config/+/refs/heads/master/jjb/mediawiki.yaml>`_ to see which image is currently defined.

Run quibble with the env file as parameter.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run::

    docker run -it --rm \
      --env-file ./.env \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-buster-php74:latest

Optionally skip (slow) installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For repeated runs of the same change, assuming you have once successfully executed the cloning and installation steps, you can omit them by adding `--skip-zuul --skip-deps`::

    docker run -it --rm \
      --env-file ./.env \
      -v "$(pwd)"/cache:/cache \
      -v "$(pwd)"/log:/log \
      -v "$(pwd)"/ref:/srv/git:ro \
      -v "$(pwd)"/src:/workspace/src \
      docker-registry.wikimedia.org/releng/quibble-buster-php74:latest \
      --skip-zuul \
      --skip-deps

Remove LocalSettings.php between runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mediawiki ensures that previous installations are not accidentally destroyed by repeated runs of the installer (overwriting configuration values), so it is up to you to always remove the previous run's configuration file to avoid problems::

    rm src/LocalSettings.php

Attaching a debugger to the CI Run
-----------------------------------

One of the massive advantages of running CI images locally is that you can attach a debugger to the running tests to find out what is happening in the container. The Quibble docker images are build with XDebug support for PHP Debugging, and the Mediawiki that Quibble tests against can be accessed directly with the browser for interactive Javascript debugging.

Connecting with XDebug and PHPStorm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To connect to the running image with PHPStorm, you need to enable XDebug in the container and point it at the IDE. On Linux, you can add the lines::

      XDEBUG_CONFIG=client_host=172.17.0.1 output_dir=/workspace/src
      XDEBUG_MODE=develop,debug
      PHP_IDE_CONFIG="serverName=Local Server"

to the `--env-file` that you are using to launch your docker image (replacing "Local Server" here with the name of the server you are about to create in PHPStorm). In PHPStorm, you will need to define a new local PHP Server so that PHPStorm can map the source files and find the breakpoints. The server should include a source mapping from `/workspace/src` to the `src` folder on your local machine / in the current working directory. You can also define an HTTP Server at this point - this will be handy if we later expose the Quibble HTTP Server for interactive debugging.

At this point you should be able to set a breakpoint in the debugger and launch Quibble and see that the run pauses when the breakpoint is hit. If you want to be very sure that the integration is working, you can set the `XDEBUG_TRIGGER` environment variable to any value, and the IDE should stop whenever a PHP script launches. Note that this will breakpoint for all composer invocations - you will need to hit play on your debugger a couple of times to make progress with the Quibble run.

Interacting with local Quibble runs
-----------------------------------

Once you have the same failure on your local machine as you see in CI, you are probably going to want to make some changes to the code and see what difference it makes. Unfortunately, the Quibble container exits when the tests complete, so the window for making changes and interacting with the container is quite limited.

Fortunately, Quibble allows us to specify an arbitrary test command. If we run `docker` interactively and provide `bash` as the test command, Quibble will run an interactive shell in the CI environment with the backend services (MySQL, an httpd) running, the database configured and the Mediawiki ready to use::

        $ docker run -it  \
           --tmpfs /workspace/db:size=320M \
           --volume "$(pwd)"/src:/workspace/src \
           --volume "$(pwd)"/cache:/cache \
           --volume "$(pwd)"/log:/workspace/log \
           --volume "$(pwd)"/ref:/srv/git:ro \
           --security-opt seccomp=unconfined \
           --env-file=env-wmf-quibble-vendor-mysql-php74-docker \
           --init --rm \
           docker-registry.wikimedia.org/releng/quibble-buster-php74:1.6.0-s6ubuntu1 \
           --packages-source composer \
           --db mysql --db-dir /workspace/db \
           --git-parallel=8 \
           --git-cache /srv/git/ \
           --phpunit-testsuite=extensions \
           -c bash

Supplying the `--skip-zuul` and `--skip-deps` arguments will prevent your changes to the `src` folder from being overridden the next time Quibble runs.

Running tests manually
~~~~~~~~~~~~~~~~~~~~~~

The commands for executing the individual build steps can also be copied from the CI job console log output (in this case from the `/workspace/src` folder). From inside the interactive shell, you can launch the steps manually::

      $ composer run --timeout=0 phpunit:entrypoint \
        -- --testsuite extensions --exclude-group \
        Broken,ParserFuzz,Stub,Database,Standalone

You should now see the tests run in an environment that is more or less identical to the CI setup. If the command hangs, check to see if `XDEBUG_TRIGGER` is set or if your IDE has paused the execution at a breakpoint.

Interactively browsing the Quibble Mediawiki
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For some purposes (e.g. manually running QUnit tests, or reproducing UX issues), you make want to interactively browse the MediaWiki that Quibble creates. To do this, simply export the browser port to your local machine by exposing the port in the docker invocation (add `-p9413:9413`). Now you should be able to reach the running MediaWiki at `http://localhost:9413 <http://localhost:9413>`_). If you added the matching Local Server to your PHPStorm setup and are using the modified docker image with XDebug, you should also be able to breakpoint requests in the usual way in the IDE.

Modifying the Quibble Docker image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may find that you want to make changes to the Quibble Docker image itself for your testing purposes. The source for the docker images the `integration-config <https://gerrit.wikimedia.org/r/plugins/gitiles/integration/config>`_ repository. Clone the repository, and install the `docker-pkg <https://pypi.org/project/docker-pkg/>`_ software to be able to make changes to the images. You may also want to install `dch <https://packages.debian.org/sid/devscripts>`_ to be able to make Debian-format changelog updates (if not, you will have to make the changes manually with an editor)::

      $ sudo apt install devscripts    # optional
      $ git clone https://gerrit.wikimedia.org/r/integration/config integration-config
      $ cd integration-config
      $ pipenv install docker-pkg
      $ pipenv shell

Next, you will need to update the Dockerfile for the image that you are using. You will find a Dockerfile.template file in the dockerfiles folder corresponding to the image that you are working with. Once you have made whatever changes you want to make to the template, you will then need to bump the changelog so that docker-pkg notices that something has changed. If you have dch installed, simply run::

      $ dch -i -c changelog

in the folder of the Dockerfile that you have changed and enter a comment. Alternatively, edit the changelog by hand. Now you should be able to run::

      $ cd ${workdir}/integration-config/dockerfiles
      $ docker-pkg build .

and `docker-pkg` should build and tag a new version of the docker image for you. Note the version of this image - you will need that in order to run the new container.
