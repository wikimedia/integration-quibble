FROM wmfreleng/ci-jessie

ARG DEBIAN_FRONTEND=noninteractive

# CI utilities
RUN git clone --depth=1 "https://gerrit.wikimedia.org/r/p/integration/composer" "/srv/deployment/integration/composer" && \
    rm -fR /srv/deployment/integration/composer/.git && \
    git clone --depth=1 "https://gerrit.wikimedia.org/r/p/integration/jenkins" "/srv/deployment/integration/slave-scripts" && \
    rm -fR /srv/deployment/integration/slave-scripts/.git && \
	ln -s "/srv/deployment/integration/composer/vendor/bin/composer" "/usr/local/bin/composer"

RUN apt-get update \
    && : "Zuul installation" \
    && apt-get install -y -t jessie python-pbr \
    && apt-get install -y zuul \
    && : "Quibble dependencies" \
    && apt-get install -y \
        python3 \
        python3-setuptools \
    && : "MediaWiki related dependencies" \
    && apt-get install -y \
        php5 php5-sqlite \
        php5-gd \
        php5-curl \
        djvulibre-bin \
        nodejs-legacy \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/quibble

RUN cd /opt/quibble && \
    python3 setup.py install && \
    rm -fR /opt/quibble
