<?php
#
# Snippet coming from integration/jenkins.git:/mediawiki/conf.d/
#

// This is a horrrrible hack to let extensions (such as Wikibase) behave
// differently when being run on Wikimedia Jenkins CI.  That is more or less
// needed when running Wikibase under Apache for QUnit, since the Jenkins
// environnement variables are not available to the Apache process.
$wgWikimediaJenkinsCI = true;
