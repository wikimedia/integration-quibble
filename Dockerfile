FROM wmfreleng/ci-jessie

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y -t jessie python-pbr \
    && apt-get install -y zuul

# CI utilities
RUN git clone --depth=1 "https://gerrit.wikimedia.org/r/p/integration/composer" "/srv/deployment/integration/composer" && \
    rm -fR /srv/deployment/integration/composer/.git && \
    git clone --depth=1 "https://gerrit.wikimedia.org/r/p/integration/jenkins" "/srv/deployment/integration/slave-scripts" && \
    rm -fR /srv/deployment/integration/slave-scripts/.git && \
	ln -s "/srv/deployment/integration/composer/vendor/bin/composer" "/usr/local/bin/composer"

# Mediawiki related dependencies
RUN apt-get install -y \
    mysql-server \
    php5 php5-mysql \
    php5-gd \
    php5-curl \
    djvulibre-bin \
    nodejs-legacy
# Quibble dependencies
RUN apt-get install -y \
    python3-pip \
    python3-paramiko \
    python3 \
    python3-dev \
    python-tox

COPY . /opt/quibble

RUN cd /opt/quibble && \
    python3 setup.py install && \
    rm -fR /opt/quibble
