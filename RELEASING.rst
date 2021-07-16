Release check list
==================

List of steps to conduct to release a new version of Quibble:

* Determine the new version number
* Amend ``CHANGELOG.rst`` to replace 'master' with the new version and date
* Verify ``CHANGELOG.rst`` has entries for commits since last version. Can be
  manually checked against: ``git log master..<previous tag>``
* Check the rendered changelog, notably links to Phabricator tasks::

    tox -e doc && xdg-open doc/build/html/changelog.html

* git add, commit, send to review
* Verify the CI job that runs all tests does work properly. That at least cover
  the most basic functionalities.
* Get the change merged and then:
* ``git pull``
* ``git tag -s <version>``
* ``git push origin <version>``

* In #wikimedia-releng log the new tag and the commit. Optionally poke all
  tasks from previous version to the new version (``git log old..new|grep
  Bug:``)::

    !log Tag Quibble <version> @ <sha1> # T1234 T5666 ...

* Send announcement to wikitech-l@lists.wikimedia.org

Then begin a new cycle:

* Amend ``CHANGELOG.rst`` and insert an entry for ``master``.
* git add, commit, send to review, get it merged
