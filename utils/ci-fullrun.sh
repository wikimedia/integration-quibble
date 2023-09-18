#!/bin/bash
#
# Entry point for a full run of Quibble on CI
#
# https://integration.wikimedia.org/ci/job/integration-quibble-fullrun
#
# Arguments to this script are passed to the Quibble command.

set -eu -o pipefail
set -x

# ZUUL_ parameters passed to Quibble
TEST_PROJECT="mediawiki/core"
MEDIAWIKI_BRANCH=master

# Use the system packages to avoid having to reinstall Quibble requirements and
# upgrade pip & setuptools.
QUIBBLE_VENV=/tmp/quibble
python3 -m venv --system-site-packages $QUIBBLE_VENV

# shellcheck disable=SC1091
source $QUIBBLE_VENV/bin/activate

# Wikimedia CI uses Buster which ships outdated pip 18
pip3 install --upgrade pip

pip3 install "$(realpath "$(dirname "$0")"/../)"

ZUUL_PROJECT=$TEST_PROJECT \
	exec quibble --branch "$MEDIAWIKI_BRANCH" "${@}"
