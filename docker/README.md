# Local development with Docker

Test local Quibble changes against using Docker.

## Build

For every change you do build a new version of the container.

```bash
# Make sure you pull the latest version
docker pull docker-registry.wikimedia.org/releng/quibble-bullseye-php83:latest
docker build --platform linux/amd64 -f docker/Dockerfile.dev -t quibble-dev .
```

## Set up a local git cache

Cloning inside Docker does not work. Clone repos as bare git repos into `ref/`
on the host and mount them into the container.

If you want to run core tests:

```bash
mkdir -p ref/mediawiki/extensions ref/mediawiki/skins
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/core.git ref/mediawiki/core.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/vendor.git ref/mediawiki/vendor.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/skins/Vector.git ref/mediawiki/skins/Vector.git
```

All gated extensions:

```bash
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/AbuseFilter.git ref/mediawiki/extensions/AbuseFilter.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/AntiSpoof.git ref/mediawiki/extensions/AntiSpoof.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Babel.git ref/mediawiki/extensions/Babel.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/BetaFeatures.git ref/mediawiki/extensions/BetaFeatures.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CampaignEvents.git ref/mediawiki/extensions/CampaignEvents.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CheckUser.git ref/mediawiki/extensions/CheckUser.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CirrusSearch.git ref/mediawiki/extensions/CirrusSearch.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Cite.git ref/mediawiki/extensions/Cite.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CiteThisPage.git ref/mediawiki/extensions/CiteThisPage.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/cldr.git ref/mediawiki/extensions/cldr.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CodeEditor.git ref/mediawiki/extensions/CodeEditor.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CommunityConfiguration.git ref/mediawiki/extensions/CommunityConfiguration.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/CommunityConfigurationExample.git ref/mediawiki/extensions/CommunityConfigurationExample.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/ConfirmEdit.git ref/mediawiki/extensions/ConfirmEdit.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/ContentTranslation.git ref/mediawiki/extensions/ContentTranslation.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Disambiguator.git ref/mediawiki/extensions/Disambiguator.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Echo.git ref/mediawiki/extensions/Echo.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Elastica.git ref/mediawiki/extensions/Elastica.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/EventBus.git ref/mediawiki/extensions/EventBus.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/EventLogging.git ref/mediawiki/extensions/EventLogging.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/EventStreamConfig.git ref/mediawiki/extensions/EventStreamConfig.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/FileImporter.git ref/mediawiki/extensions/FileImporter.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Gadgets.git ref/mediawiki/extensions/Gadgets.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/GeoData.git ref/mediawiki/extensions/GeoData.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/GlobalCssJs.git ref/mediawiki/extensions/GlobalCssJs.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/GlobalPreferences.git ref/mediawiki/extensions/GlobalPreferences.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/GrowthExperiments.git ref/mediawiki/extensions/GrowthExperiments.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/GuidedTour.git ref/mediawiki/extensions/GuidedTour.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/ImageMap.git ref/mediawiki/extensions/ImageMap.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/InputBox.git ref/mediawiki/extensions/InputBox.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Interwiki.git ref/mediawiki/extensions/Interwiki.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/IPInfo.git ref/mediawiki/extensions/IPInfo.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/JsonConfig.git ref/mediawiki/extensions/JsonConfig.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Kartographer.git ref/mediawiki/extensions/Kartographer.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Math.git ref/mediawiki/extensions/Math.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/MediaModeration.git ref/mediawiki/extensions/MediaModeration.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/MobileApp.git ref/mediawiki/extensions/MobileApp.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/MobileFrontend.git ref/mediawiki/extensions/MobileFrontend.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/NavigationTiming.git ref/mediawiki/extensions/NavigationTiming.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/PageImages.git ref/mediawiki/extensions/PageImages.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/PageTriage.git ref/mediawiki/extensions/PageTriage.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/PageViewInfo.git ref/mediawiki/extensions/PageViewInfo.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/ParserFunctions.git ref/mediawiki/extensions/ParserFunctions.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/PdfHandler.git ref/mediawiki/extensions/PdfHandler.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Poem.git ref/mediawiki/extensions/Poem.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/ProofreadPage.git ref/mediawiki/extensions/ProofreadPage.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/SandboxLink.git ref/mediawiki/extensions/SandboxLink.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Scribunto.git ref/mediawiki/extensions/Scribunto.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/SiteMatrix.git ref/mediawiki/extensions/SiteMatrix.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/SpamBlacklist.git ref/mediawiki/extensions/SpamBlacklist.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/TemplateData.git ref/mediawiki/extensions/TemplateData.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Thanks.git ref/mediawiki/extensions/Thanks.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/TimedMediaHandler.git ref/mediawiki/extensions/TimedMediaHandler.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Translate.git ref/mediawiki/extensions/Translate.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/UniversalLanguageSelector.git ref/mediawiki/extensions/UniversalLanguageSelector.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/VisualEditor.git ref/mediawiki/extensions/VisualEditor.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/Wikibase.git ref/mediawiki/extensions/Wikibase.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikibaseCirrusSearch.git ref/mediawiki/extensions/WikibaseCirrusSearch.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikibaseMediaInfo.git ref/mediawiki/extensions/WikibaseMediaInfo.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikiEditor.git ref/mediawiki/extensions/WikiEditor.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikiLove.git ref/mediawiki/extensions/WikiLove.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikimediaCampaignEvents.git ref/mediawiki/extensions/WikimediaCampaignEvents.git
git clone --bare https://gerrit.wikimedia.org/r/mediawiki/extensions/WikimediaMessages.git ref/mediawiki/extensions/WikimediaMessages.git
```

##  Prepare folders

Setup the folders needed:

```bash
mkdir -p cache log src
chmod 777 cache log src
```

## Run

Full CI run with mediawiki/core:

```bash
docker run --platform linux/amd64 -it --rm \
  -e ZUUL_PROJECT=mediawiki/core \
  -e CI=true \
  -v "$(pwd)/ref:/srv/git:ro" \
  -v "$(pwd)/cache:/cache" \
  -v "$(pwd)/log:/workspace/log" \
  -v "$(pwd)"/src:/workspace/src \
  quibble-dev
```

Run browser test stage only:

```bash
docker run --platform linux/amd64 -it --rm \
  -e ZUUL_PROJECT=mediawiki/core \
  -e CI=true \
  -v "$(pwd)/ref:/srv/git:ro" \
  -v "$(pwd)/cache:/cache" \
  -v "$(pwd)/log:/workspace/log" \
  -v "$(pwd)"/src:/workspace/src \
  quibble-dev --run selenium
```

## Running browser tests for gated extension selenium tests

Set `EXT_DEPENDENCIES` and `SKIN_DEPENDENCIES` to include additional projects:

```bash
docker run --platform linux/amd64 -it --rm \
  -e ZUUL_PROJECT=mediawiki/core \
  -e CI=true \
  -v "$(pwd)/ref:/srv/git:ro" \
  -v "$(pwd)/cache:/cache" \
  -v "$(pwd)/log:/workspace/log" \
  -v "$(pwd)"/src:/workspace/src \
  -e EXT_DEPENDENCIES='mediawiki/extensions/AbuseFilter\nmediawiki/extensions/AntiSpoof\nmediawiki/extensions/Babel\nmediawiki/extensions/BetaFeatures\nmediawiki/extensions/CampaignEvents\nmediawiki/extensions/CheckUser\nmediawiki/extensions/CirrusSearch\nmediawiki/extensions/Cite\nmediawiki/extensions/CiteThisPage\nmediawiki/extensions/cldr\nmediawiki/extensions/CodeEditor\nmediawiki/extensions/CommunityConfiguration\nmediawiki/extensions/CommunityConfigurationExample\nmediawiki/extensions/ConfirmEdit\nmediawiki/extensions/ContentTranslation\nmediawiki/extensions/Disambiguator\nmediawiki/extensions/Echo\nmediawiki/extensions/Elastica\nmediawiki/extensions/EventBus\nmediawiki/extensions/EventLogging\nmediawiki/extensions/EventStreamConfig\nmediawiki/extensions/FileImporter\nmediawiki/extensions/Gadgets\nmediawiki/extensions/GeoData\nmediawiki/extensions/GlobalCssJs\nmediawiki/extensions/GlobalPreferences\nmediawiki/extensions/GrowthExperiments\nmediawiki/extensions/GuidedTour\nmediawiki/extensions/ImageMap\nmediawiki/extensions/InputBox\nmediawiki/extensions/Interwiki\nmediawiki/extensions/IPInfo\nmediawiki/extensions/JsonConfig\nmediawiki/extensions/Kartographer\nmediawiki/extensions/Math\nmediawiki/extensions/MediaModeration\nmediawiki/extensions/MobileApp\nmediawiki/extensions/MobileFrontend\nmediawiki/extensions/NavigationTiming\nmediawiki/extensions/PageImages\nmediawiki/extensions/PageTriage\nmediawiki/extensions/PageViewInfo\nmediawiki/extensions/ParserFunctions\nmediawiki/extensions/PdfHandler\nmediawiki/extensions/Poem\nmediawiki/extensions/ProofreadPage\nmediawiki/extensions/SandboxLink\nmediawiki/extensions/Scribunto\nmediawiki/extensions/SiteMatrix\nmediawiki/extensions/SpamBlacklist\nmediawiki/extensions/TemplateData\nmediawiki/extensions/Thanks\nmediawiki/extensions/TimedMediaHandler\nmediawiki/extensions/Translate\nmediawiki/extensions/UniversalLanguageSelector\nmediawiki/extensions/VisualEditor\nmediawiki/extensions/Wikibase\nmediawiki/extensions/WikibaseCirrusSearch\nmediawiki/extensions/WikibaseMediaInfo\nmediawiki/extensions/WikiEditor\nmediawiki/extensions/WikiLove\nmediawiki/extensions/WikimediaCampaignEvents\nmediawiki/extensions/WikimediaMessages' \
  -e SKIN_DEPENDENCIES='mediawiki/skins/Vector' \
  quibble-dev --run selenium
```
