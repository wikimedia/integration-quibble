FROM debian:jessie

RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python-tox

RUN apt-get install -y python3-pip git python3-paramiko
RUN mkdir -p /srv/git/mediawiki && \
    mkdir -p /srv/deployment/integration && \
    git clone --bare "https://gerrit.wikimedia.org/r/p/mediawiki/core" "/srv/git/mediawiki/core.git" && \
    git clone --bare "https://gerrit.wikimedia.org/r/p/mediawiki/vendor" "/srv/git/mediawiki/vendor.git" && \
    git clone "https://gerrit.wikimedia.org/r/p/integration/jenkins" "/srv/deployment/integration/slave-scripts"

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server php5 php5-mysql php5-gd php5-curl djvulibre-bin nodejs-legacy && \
    /usr/sbin/service mysql start

RUN git clone "https://gerrit.wikimedia.org/r/p/integration/composer" "/srv/deployment/integration/composer" && \
	ln -s "/srv/deployment/integration/composer/vendor/bin/composer" "/usr/local/bin/composer"

# Some of Zuul dependencies. Would be better done by install the zuul.deb package from apt.wikimedia.org
RUN apt-get install -y \
    python3-pbr \
    python3-yaml \
    python3-paste \
    python3-webob \
    python3-paramiko \
    python3-prettytable \
    python3-extras \
    python3-voluptuous \
    python3-six \
    python3-tz \
    python3-docutils \
    python3-babel

COPY . /opt/quibble

RUN cd /opt/quibble && \
    pip3 install -rrequirements.txt && \
    python3 setup.py install && \
    rm -fR /opt/quibble
