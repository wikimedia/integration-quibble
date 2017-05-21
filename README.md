TLDR:

	docker build --tag quibble .
	docker run -it --rm quibble bash

Then run the quibble command:

	service mysql start
	ZUUL_URL=https://gerrit.wikimedia.org/r/p ZUUL_BRANCH=master ZUUL_REF=master quibble --packages-source vendor --workspace /workspace

TESTING
-------

Coverage report:

    tox -e cover && open cover/index.html
