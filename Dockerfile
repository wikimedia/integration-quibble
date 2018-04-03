FROM docker-registry.wikimedia.org/releng/npm-stretch:latest as npm-stretch
FROM docker-registry.wikimedia.org/releng/ci-stretch:latest

ARG DEBIAN_FRONTEND=noninteractive

# See <https://docs.npmjs.com/misc/config#environment-variables>
# and <https://docs.npmjs.com/cli/cache>
ENV NPM_CONFIG_CACHE=/cache/npm
ENV BABEL_CACHE_PATH=$XDG_CACHE_HOME/babel-cache.json

# CI utilities
RUN git clone --depth=1 "https://gerrit.wikimedia.org/r/p/integration/composer" "/srv/deployment/integration/composer" && \
    rm -fR /srv/deployment/integration/composer/.git && \
	ln -s "/srv/deployment/integration/composer/vendor/bin/composer" "/usr/local/bin/composer"

RUN apt-get update \
    && apt-get install -y python3 python3-setuptools python3-pip

RUN apt-get update \
    && : "Zuul cloner dependencies" \
    && apt-get install -y \
        python3-extras \
        python3-six \
        python3-yaml \
        python3-git \
    && rm -fR /cache/pip

RUN apt-get update \
    && : "Composer/MediaWiki related dependencies" \
    && apt-get install -y \
        php-apcu \
        php-cli \
        php-curl \
        php-gd \
        php-intl \
        php-mbstring \
        php-mysql \
        php-sqlite3 \
        php-tidy \
        php-xml \
        php-zip \
        djvulibre-bin \
        imagemagick \
        libimage-exiftool-perl \
        mariadb-server \
        nodejs-legacy \
        tidy \
    && : "Xvfb" \
    && apt-get install -y \
        xvfb \
        xauth \
    && apt-get purge -y python3-pip \
    && rm -fR /cache/pip

COPY --from=npm-stretch /usr/local/lib/node_modules/npm/ /usr/local/lib/node_modules/npm/
# Manually link since COPY copies symlink destination instead of the actual symlink
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

RUN apt-get update \
    && apt-get install -y \
        chromedriver \
        chromium

RUN apt-get autoremove -y --purge \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/quibble

RUN cd /opt/quibble && \
    python3 setup.py install && \
    rm -fR /opt/quibble /cache/pip

# Unprivileged
RUN install --directory /workspace --owner=nobody --group=nogroup
USER nobody
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/quibble"]
