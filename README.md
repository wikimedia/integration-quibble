TLDR:

	docker build quibble .
	docker run -it --rm quibble bash

Then run the quibble command???

	ZUUL_REF=master ZUUL_BRANCH=master ZUUL_URL=https://gerrit.wikimedia.org/r/p tox -e venv --sitepackages -- python quibble/cmd.py --packages-source vendor --workspace /workspace
