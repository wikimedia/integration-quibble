# Copyright 2017-2018, Antoine "hashar" Musso
# Copyright 2017, Tyler Cipriani
# Copyright 2017-2018, Wikimedia Foundation Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

FROM docker-registry.wikimedia.org/releng/ci-buster:latest

ARG DEBIAN_FRONTEND=noninteractive

# See <https://docs.npmjs.com/misc/config#environment-variables>
# and <https://docs.npmjs.com/cli/cache>
ENV NPM_CONFIG_CACHE=/cache/npm
ENV BABEL_CACHE_PATH=$XDG_CACHE_HOME/babel-cache.json

# CI utilities
COPY .composer.phar.sha256sum /srv/composer/composer.phar.sha256sum
RUN apt-get update \
    && : "Initial bootstrapping dependencies and composer" \
    && apt-get install -y \
        jq \
        curl \
        zip \
        unzip \
    && cd /srv/composer \
    && curl --silent --fail --output composer.phar https://getcomposer.org/download/1.10.5/composer.phar \
    && sha256sum -c composer.phar.sha256sum \
    && chmod +x /srv/composer/composer.phar \
    && mv /srv/composer/composer.phar /usr/bin/composer

RUN apt-get update \
    && : "Python3 and other Zuul cloner dependencies" \
    && apt-get install -y \
        python3 \
        python3-setuptools \
        python3-pip \
        python3-extras \
        python3-six \
        python3-yaml \
        python3-git \
    && rm -fR /cache/pip

RUN apt-get update \
    && : "Composer/MediaWiki related dependencies" \
    && apt-get install -y \
        php-apcu \
        php-ast \
        php-bcmath \
        php-cli \
        php-curl \
        php-gd \
        php-gmp \
        php-intl \
        php-ldap \
        php-mbstring \
        php-mysql \
        php-pgsql \
        php-sqlite3 \
        php-tidy \
        php-xml \
        php-zip \
        php-wikidiff2 \
        php-fpm \
        djvulibre-bin \
        imagemagick \
        libimage-exiftool-perl \
        mariadb-server \
        nodejs \
        npm \
        supervisor \
        apache2 \
        python \
        ffmpeg \
        build-essential \
        tidy \
    && : "Xvfb" \
    && apt-get install -y \
        xvfb \
        xauth \
    && apt-get purge -y python3-pip \
    && rm -fR /cache/pip

RUN apt-get update \
    && : "Chromium and driver" \
    && apt-get install -y \
        chromium-driver \
        chromium

RUN apt-get update \
    && : "JSDuck and ruby for it" \
    && apt-get install -y \
        ruby \
        ruby-dev \
        build-essential \
    && gem install --no-rdoc --no-ri --clear-sources jsduck \
    && rm -fR /var/lib/gems/*/cache/*.gem \
    && apt -y purge ruby-dev \
    && apt-get -y autoremove --purge \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/quibble

RUN cd /opt/quibble && \
    python3 setup.py install && \
    rm -fR /opt/quibble /cache/pip

# Tell Apache how to process PHP files.
RUN a2enmod proxy_fcgi \
  && a2enmod mpm_event \
  && a2enmod rewrite \
  && a2enmod http2 \
  && a2enmod cache
COPY ./docker/php-fpm/php-fpm.conf /etc/php/7.3/fpm/php-fpm.conf
COPY ./docker/php-fpm/www.conf /etc/php/7.3/fpm/pool.d/www.conf
RUN mkdir /tmp/php && chown -R nobody:nogroup /tmp/php
RUN touch /tmp/php7.3-fpm.log /tmp/php/php7.3-fpm.pid \
  && chown nobody:nogroup /tmp/php7.3-fpm.log /tmp/php/php7.3-fpm.pid

COPY ./docker/php-fpm/php.ini /etc/php/7.3/fpm/php.ini
COPY ./docker/apache/ports.conf /etc/apache2/ports.conf
COPY ./docker/apache/000-default.conf /etc/apache2/sites-available/000-default.conf
COPY ./docker/apache/apache2.conf /etc/apache2/apache2.conf
COPY ./docker/apache/envvars /etc/apache2/envvars
COPY ./docker/entrypoint.sh /entrypoint.sh
COPY ./docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN install --directory /workspace --owner=nobody --group=nogroup

# Unprivileged
USER nobody
WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
