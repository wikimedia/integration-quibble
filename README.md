TLDR:

	docker build --tag quibble .
	docker run -it --entrypoint=/bin/bash --rm quibble

Then run the quibble command:

    quibble --packages-source vendor --db mysql

CACHING
-------

To avoid cloning MediaWiki over the network, you should initialize local bare
repositories to be used as a reference for git to copy from:

    mkdir -p ref/mediawiki/skins
    git clone --bare mediawiki/core ref/mediawiki/core.git
    git clone --bare mediawiki/vendor ref/mediawiki/vendor.git
    git clone --bare mediawiki/skins/Vector ref/mediawiki/skins/Vector.git

We have `XDG_CACHE_HOME=/cache` set which is recognized by package managers.
Create a cache directory writable by any user:

    install --directory --mode 777 cache

When running in a Docker container, mount the git repositories as a READ-ONLY
volume as `/srv/git` and the `cache` dir in read-write mode:

    docker run -it --rm -v "$(pwd)"/ref:/srv/git:ro -v "$(pwd)"/cache:/cache quibble

You can get log with:

    mkdir -p workspace/log
    chmod 777 workspace/log

And then passing `-v "$(pwd)"/workspace/log:/workspace/log`.

TESTING
-------

Coverage report:

    tox -e cover && open cover/index.html
