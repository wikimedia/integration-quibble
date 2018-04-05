Quibble
-------

Quibble gets MediaWiki, install it and run tests all in one command.

Requirements:

- chromium
- composer
- NodeJS
- npm
- php
- python 3
- Xvfb

TLDR:

	docker build --tag quibble .
	docker run -it --rm quibble --workspace workspace

Which runs tests with php7.0, mysql and using mediawiki/vendor.git.

Or try another set:

    docker run -it quibble  --packages-source composer --db sqlite

Wikimedia maintains a Docker container intended to be used for its continuous
integration system:

 docker pull docker-registry.discovery.wmnet/releng/quibble-stretch:latest


CACHING
-------

To avoid cloning MediaWiki over the network, you should initialize local bare
repositories to be used as a reference for git to copy them from:

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

Commands write logs into `/workspace/log`, you can create one on the host and
mount it in the container:

    mkdir -p workspace/log
    chmod 777 workspace/log

And then pass to docker run: `-v "$(pwd)"/workspace/log:/workspace/log`.

TESTING
-------

Coverage report:

    tox -e cover && open cover/index.html
