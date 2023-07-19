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
EXT_DEPENDENCIES="mediawiki/extensions/AbuseFilter\nmediawiki/extensions/AntiSpoof\nmediawiki/extensions/ArticlePlaceholder\nmediawiki/extensions/BetaFeatures\nmediawiki/extensions/CentralAuth\nmediawiki/extensions/CheckUser\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/CodeEditor\nmediawiki/extensions/ConfirmEdit\nmediawiki/extensions/Disambiguator\nmediawiki/extensions/Echo\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventBus\nmediawiki/extensions/EventLogging\nmediawiki/extensions/EventStreamConfig\nmediawiki/extensions/FlaggedRevs\nmediawiki/extensions/Flow\nmediawiki/extensions/GeoData\nmediawiki/extensions/Graph\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/ImageMap\nmediawiki/extensions/JsonConfig\nmediawiki/extensions/Kartographer\nmediawiki/extensions/MobileApp\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/PageImages\nmediawiki/extensions/PageViewInfo\nmediawiki/extensions/ParserFunctions\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/Poem\nmediawiki/extensions/PropertySuggester\nmediawiki/extensions/Renameuser\nmediawiki/extensions/Scribunto\nmediawiki/extensions/SecurePoll\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SyntaxHighlight_GeSHi\nmediawiki/extensions/TemplateData\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseCirrusSearch\nmediawiki/extensions/WikibaseLexeme\nmediawiki/extensions/WikibaseMediaInfo\nmediawiki/extensions/WikibaseQualityConstraints\nmediawiki/extensions/WikimediaBadges\nmediawiki/extensions/WikimediaEvents\nmediawiki/extensions/WikimediaMessages\nmediawiki/extensions/cldr"
SKIN_DEPENDENCIES="mediawiki/skins/MinervaNeue"
MEDIAWIKI_BRANCH=master

QUIBBLE_INSTALL_DIR=/tmp/quibble

# Find python version
_py3_bin=$(which python3)
_py3_real=$(readlink -f "$_py3_bin")
py3_version=$(basename "$_py3_real")

PYTHONPATH="$QUIBBLE_INSTALL_DIR/lib/$py3_version/site-packages"
export PYTHONPATH
mkdir -p "$PYTHONPATH"
python3 -s -c 'import pprint,sys; pprint.pprint(sys.path)'

python3 -s setup.py install --prefix "$QUIBBLE_INSTALL_DIR"

ZUUL_PROJECT=$TEST_PROJECT \
	EXT_DEPENDENCIES=$EXT_DEPENDENCIES \
	SKIN_DEPENDENCIES=$SKIN_DEPENDENCIES \
	exec python3 -s "$QUIBBLE_INSTALL_DIR"/bin/quibble --branch "$MEDIAWIKI_BRANCH" "${@}"
