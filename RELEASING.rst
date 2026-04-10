Release check list
==================

List of steps to conduct to release a new version of Quibble:

* Determine the new version number
* Amend ``CHANGELOG.rst`` to replace 'master' with the new version and date
* Verify ``CHANGELOG.rst`` has entries for commits since last version. Can be
  manually checked against: ``git log --reverse <previous tag>..master``
* Check the rendered changelog, notably links to Phabricator tasks::

    tox -e doc && xdg-open doc/build/html/changelog.html

* git add, commit, send to review
* Verify the CI job that runs all tests does work properly. That at least cover
  the most basic functionalities.
* Get the change merged and then:
* ``git pull``
* ``export QUIBBLE_RELEASE_VERSION="<version>"``
* ``git tag -s $QUIBBLE_RELEASE_VERSION -m "Signed $QUIBBLE_RELEASE_VERSION release"``
* ``git push origin $QUIBBLE_RELEASE_VERSION``

* In #wikimedia-releng log the new tag and the commit. Optionally poke all
  tasks from previous version to the new version (``git log old..new|grep
  Bug:``)::

    !log Tag Quibble <version> @ <sha1> # T1234 T5666 ...

* Send announcement to wikitech-l@lists.wikimedia.org

Then begin a new cycle:

* Amend ``CHANGELOG.rst`` and insert an entry for ``master``.
* git add, commit, send to review, get it merged

To deploy the new release on the Wikimedia CI infrastructure, continue with the
wiki documentation: `Creating and deploying a new Quibble release
<https://www.mediawiki.org/wiki/Quibble#Creating_and_deploying_a_new_Quibble_release>`_.
