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
if ( is_file( "$IP/includes/DevelopmentSettings.php" ) ) {
	putenv( "MW_LOG_DIR=$quibbleLogDir" );
	require_once "$IP/includes/DevelopmentSettings.php";
} else {
	// Support: Mediawiki 1.30 and earlier
	error_reporting( -1 );
	ini_set( 'display_errors', 1 );
	$wgDevelopmentWarnings = true;
	$wgShowDBErrorBacktrace = true;
	$wgShowExceptionDetails = true;
	$wgShowSQLErrors = true;
	$wgDebugRawPage = true;
	if ( $wgCommandLineMode ) {
		$wgDebugLogFile = "$quibbleLogDir/mw-debug-cli.log";
	} else {
		$wgDebugLogFile = "$quibbleLogDir/mw-debug-www.log";
	}
	$wgDebugTimestamps = true;
	$wgDBerrorLog = "$quibbleLogDir/mw-dberror.log";
	$wgDebugLogGroups['ratelimit'] = "$quibbleLogDir/mw-ratelimit.log";
	$wgDebugLogGroups['exception'] = "$quibbleLogDir/mw-exception.log";
	$wgDebugLogGroups['error'] = "$quibbleLogDir/mw-error.log";
	$wgRateLimitLog = $wgDebugLogGroups['ratelimit'];
}

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

require_once( __DIR__ . '/LocalSettings-installer.php' );

# Force secret key. This key can be shared with the configuration
# of testing tools, to allow them to perform privileged actions,
# such as running jobs.
$wgSecretKey = 'supercalifragilisticexpialidocious';

// Hack to support Extension:FileImporter browser tests, T190829
$wgEnableUploads = true;
