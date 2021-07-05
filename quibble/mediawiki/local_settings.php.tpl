<?php
# Quibble MediaWiki configuration
# Originally copied from integration/jenkins.git:/mediawiki/conf.d/

/**
 * Process environment variables
 */

// Set environment from quibble, leaving the ability to override.
// TODO: Deprecate environment variables in code under test.
{{params-declaration}}

/**
 * Development settings
 */

// MW_LOG_DIR is used by DevelopmentSettings.php
putenv( "MW_LOG_DIR=" . MW_LOG_DIR );

// Use MediaWiki's development setting
require_once "$IP/includes/DevelopmentSettings.php";

/**
 * CI-specific settings and hacks
 *
 * Do not add "experimental" or "strict" settings here.
 * Settings that are useful during development or that may become
 * the default one day, should go to DevelopmentSettings.php
 * in MediaWiki core instead.
 */

// This is a horrrrible hack to let extensions (such as Wikibase) behave
// differently when being run on Wikimedia Jenkins CI.  That is more or less
// needed when running Wikibase under Apache for QUnit, since the Jenkins
// environment variables are not available to the Apache process.
$wgWikimediaJenkinsCI = true;

// Configure $wgDjvu for the MediaWiki core DJVU unit tests
$wgDjvuDump = '/usr/bin/djvudump';
$wgDjvuRenderer = '/usr/bin/ddjvu';
$wgDjvuToXML = '/usr/bin/djvutoxml';
$wgDjvuTxt = '/usr/bin/djvutxt';

// Set cache directory
$wgCacheDirectory = TMPDIR;

// Enables the experimental REST API for testing, T235564
$wgEnableRestAPI = true;

// Parsoid does not yet work in Quibble; set Flow's default content format to wikitext to reduce logspam.
$wgFlowContentFormat = 'wikitext';

require_once __DIR__ . '/LocalSettings-installer.php';

# Force secret key. This key can be shared with the configuration
# of testing tools, to allow them to perform privileged actions,
# such as running jobs.
$wgSecretKey = 'supercalifragilisticexpialidocious';

// Hack to support Extension:FileImporter browser tests, T190829
$wgEnableUploads = true;

// Hack to support testing Parsoid as an extension, while overriding
// the composer library included with core. (T227352)
$parsoidDir = MW_INSTALL_PATH . '/services/parsoid';
if ( !is_dir( $parsoidDir ) ) {
    // Fallback to version included in core if not cloned into /services/parsoid.
    $parsoidDir = "$IP/vendor/wikimedia/parsoid";
}
AutoLoader::$psr4Namespaces += [
	// Keep this in sync with the "autoload" clause in
	// $PARSOID_INSTALL_DIR/composer.json
	'Wikimedia\\Parsoid\\' => "$parsoidDir/src",
];
wfLoadExtension( 'Parsoid', "$parsoidDir/extension.json" );
// Don't use Parsoid auto-config, which only works on REL1_36.
$wgVisualEditorParsoidAutoConfig = false;
$wgParsoidSettings = [
	'useSelser' => true,
	'rtTestMode' => false,
	'linting' => false,
];
$wgVirtualRestConfig['modules']['parsoid'] = [];
unset( $parsoidDir );
