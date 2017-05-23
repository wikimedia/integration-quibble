TLDR:

	docker build --tag quibble .
	docker run -it --rm quibble bash

Then run the quibble command:

	service mysql start
	ZUUL_URL=https://gerrit.wikimedia.org/r/p ZUUL_BRANCH=master ZUUL_REF=master quibble --packages-source vendor --workspace /workspace

CACHING
-------

To avoid cloning MediaWiki over the network, you should initialize local bare
repositories to be used as cache to copy from:

  mkdir -p ref/mediawiki
  git clone --bare mediawiki/core ref/mediawiki/core.git
  git clone --bare mediawiki/vendor ref/mediawiki/vendor.git

Then bindmount it READ-ONLY as /srv/git:

  docker run -it --rm -v `pwd`/ref:/srv/git:ro quibble bash

TESTING
-------

Coverage report:

    tox -e cover && open cover/index.html
