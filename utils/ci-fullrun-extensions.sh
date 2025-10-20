#!/bin/bash
#
# Entry point for a full run of Quibble on CI
#
# https://integration.wikimedia.org/ci/job/integration-quibble-fullrun-extensions
#
# Arguments to this script are passed to the Quibble command.

set -eu -o pipefail
set -x

# ZUUL_ parameters passed to Quibble
TEST_PROJECT="mediawiki/extensions/GrowthExperiments"
EXT_DEPENDENCIES="mediawiki/extensions/CommunityConfiguration\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Echo\nmediawiki/extensions/EventBus\nmediawiki/extensions/EventLogging\nmediawiki/extensions/EventStreamConfig\nmediawiki/extensions/Flow\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/MetricsPlatform\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/PageImages\nmediawiki/extensions/PageViewInfo\nmediawiki/extensions/Thanks\nmediawiki/extensions/WikimediaMessages\nmediawiki/extensions/Elastica"
SKIN_DEPENDENCIES="mediawiki/skins/MinervaNeue"
MEDIAWIKI_BRANCH=master

# Enable parallel test execution for PHPUnit extensions test suite
export QUIBBLE_PHPUNIT_PARALLEL=1
# Set the location of the phpunit results cache server (T384925)
export MW_RESULTS_CACHE_SERVER_BASE_URL="https://phpunit-results-cache.toolforge.org/results"

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
	EXT_DEPENDENCIES=$EXT_DEPENDENCIES \
	SKIN_DEPENDENCIES=$SKIN_DEPENDENCIES \
	exec quibble --branch "$MEDIAWIKI_BRANCH" "${@}"
