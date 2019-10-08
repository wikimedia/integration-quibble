Release check list
==================

List of steps to conduct to release a new version of Quibble:

* Determine the new version number
* Do run Quibble locally with all tests to ensure the basic functionalities do
  work. This step will no more be needed once we have a proper integration
  test that runs it entirely via CI on each patchset proposal (`T235118
  <https://phabricator.wikimedia.org/T235118>`_).
* Amend ``CHANGELOG.rst`` to replace 'master' with the new version and date
* Verify ``CHANGELOG.rst`` has entries for commits since last version. Can be
  manually checked against: ``git log master..<previous tag>``
* git add, commit, send to review, get it merged
* ``git fetch``
* ``git tag <version>``
* ``git push origin <version>``

* In #wikimedia-releng log the new tag and the commit. Optionally poke all
  tasks from previous version to the new version (``git log old..new|grep
  Bug:``)::

    !log Tag Quibble <version> @ <sha1> # T1234 T5666 ...

* Send announcement to wikitech-l@lists.wikimedia.org and qa@list.wikimedia.org

Then begin a new cycle:

* Amend ``CHANGELOG.rst`` and insert an entry for ``master``.
* git add, commit, send to review, get it merged

