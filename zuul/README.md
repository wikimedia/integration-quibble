Embedded zuul-cloner
--------------------

Saves us from having to install the whole Zuul and all its dependencies. The
files here are copied from
https://gerrit.wikimedia.org/r/p/integration/zuul.git using the
`patch-queue/debian/jessie-wikimedia` branch.

zuul/merger/merger.py is edited to get rid of the Merger class and its required
zuul.model import.
