Release check list
==================

List of steps to conduct to release a new version of Quibble:

* Determine the new version number
* Amend ``CHANGELOG.rst`` to replace 'master' with the new version and date
* Verify ``CHANGELOG.rst`` has entries for commits since last version. Can be
  manually checked against: ``git log master..<previous tag>``
* git add, commit, send to review, get it merged
* ``git fetch``
* ``git tag <version>``
* ``git push origin <version>``

* Send announcement to wikitech-l@lists.wikimedia.org and qa@list.wikimedia.org

Then begin a new cycle:

* Amend ``CHANGELOG.rst`` and insert an entry for ``master``.
* git add, commit, send to review, get it merged

