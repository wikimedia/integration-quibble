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
EXT_DEPENDENCIES="mediawiki/extensions/AbuseFilter\nmediawiki/extensions/AntiSpoof\nmediawiki/extensions/ArticlePlaceholder\nmediawiki/extensions/BetaFeatures\nmediawiki/extensions/CentralAuth\nmediawiki/extensions/CheckUser\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/CodeEditor\nmediawiki/extensions/CommunityConfiguration\nmediawiki/extensions/ConfirmEdit\nmediawiki/extensions/Disambiguator\nmediawiki/extensions/Echo\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventBus\nmediawiki/extensions/EventLogging\nmediawiki/extensions/EventStreamConfig\nmediawiki/extensions/FlaggedRevs\nmediawiki/extensions/Flow\nmediawiki/extensions/GeoData\nmediawiki/extensions/Graph\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/ImageMap\nmediawiki/extensions/JsonConfig\nmediawiki/extensions/Kartographer\nmediawiki/extensions/MobileApp\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/PageImages\nmediawiki/extensions/PageViewInfo\nmediawiki/extensions/ParserFunctions\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/Poem\nmediawiki/extensions/PropertySuggester\nmediawiki/extensions/Renameuser\nmediawiki/extensions/Scribunto\nmediawiki/extensions/SecurePoll\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SyntaxHighlight_GeSHi\nmediawiki/extensions/TemplateData\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseCirrusSearch\nmediawiki/extensions/WikibaseLexeme\nmediawiki/extensions/WikibaseMediaInfo\nmediawiki/extensions/WikibaseQualityConstraints\nmediawiki/extensions/WikimediaBadges\nmediawiki/extensions/WikimediaEvents\nmediawiki/extensions/WikimediaMessages\nmediawiki/extensions/cldr"
SKIN_DEPENDENCIES="mediawiki/skins/MinervaNeue"
MEDIAWIKI_BRANCH=master

# Enable parallel test execution for PHPUnit extensions test suite
export QUIBBLE_PHPUNIT_PARALLEL=1

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
