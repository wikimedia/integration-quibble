<?php
# Quibble MediaWiki configuration
# Originally copied from integration/jenkins.git:/mediawiki/conf.d/

/**
 * Process environment variables
 */

// Get configured log directory
if ( getenv( 'MW_LOG_DIR' ) ) {
	$quibbleLogDir = getenv( 'MW_LOG_DIR' );
} elseif ( getenv( 'WORKSPACE' ) ) {
	$quibbleLogDir = getenv( 'WORKSPACE' ) . '/log';
} else {
	$quibbleLogDir = __DIR__ . '/../log';
}

// Ensure MW_INSTALL_PATH is set
if ( !getenv( 'MW_INSTALL_PATH' ) ) {
	if ( is_dir( getenv( 'WORKSPACE' ) . '/src/mediawiki/core' ) ) {
		// The new pattern as of 2014, as used by Zuul cloner in Jenkins,
		// and in Quibble, is to clone MediaWiki at /src/mediawiki/core,
		// aka "/src/$ZUUL_PROJECT".
		putenv( 'MW_INSTALL_PATH='. getenv( 'WORKSPACE' ) . '/src/mediawiki/core' );
	} else {
		// Legacy
		// CI jobs that don't use Zuul cloner, clone core directly at WORKSPACE
		putenv( 'MW_INSTALL_PATH='. getenv( 'WORKSPACE' ) );
	}
}

/**
 * Development settings
 */

// MW_LOG_DIR is used by DevelopmentSettings.php
putenv( "MW_LOG_DIR=$quibbleLogDir" );

// Use MediaWiki's development setting
require_once "$IP/includes/DevelopmentSettings.php";

/**
 * Experimental settings
 *
 * Stricter configurations we're trying out by enforcing in CI first,
 * before they become defaults in MediaWiki core
 */

// Be strict about class name letter-case.
$wgAutoloadAttemptLowercase = false;

/**
 * Settings specifically for testing purposes.
 */

// Enables [[Special:JavaScriptTest]] for QUnit tests.
$wgEnableJavaScriptTest = true;

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

# Set cache directory
$wgCacheDirectory = getenv( 'TMPDIR' );

// Enables the experimental REST API for testing, T235564
$wgEnableRestAPI = true;

// Parsoid does not yet work in Quibble; set Flow's default content format to wikitext to reduce logspam.
$wgFlowContentFormat = 'wikitext';

require_once( __DIR__ . '/LocalSettings-installer.php' );

# Force secret key. This key can be shared with the configuration
# of testing tools, to allow them to perform privileged actions,
# such as running jobs.
$wgSecretKey = 'supercalifragilisticexpialidocious';

// Hack to support Extension:FileImporter browser tests, T190829
$wgEnableUploads = true;

// Hack to support testing Parsoid as an extension, while overriding
// the composer library included with core. (T227352)
$wgParsoidInstallDir = getenv( 'MW_INSTALL_PATH' ) . '/services/parsoid';
if ( is_dir( $wgParsoidInstallDir ) ) {
	AutoLoader::$psr4Namespaces += [
		// Keep this in sync with the "autoload" clause in
		// $PARSOID_INSTALL_DIR/composer.json
		'Wikimedia\\Parsoid\\' => "$wgParsoidInstallDir/src",
	];
	wfLoadExtension( 'Parsoid', "$wgParsoidInstallDir/extension.json" );
}
