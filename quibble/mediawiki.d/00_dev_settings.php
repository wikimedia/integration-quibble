<?php
#
# Snippet coming from integration/jenkins.git:/mediawiki/conf.d/
#

if ( getenv( 'MW_LOG_DIR' ) ) {
	$wmgMwLogDir = getenv( 'MW_LOG_DIR' );
} elseif ( getenv( 'WORKSPACE' ) ) {
	$wmgMwLogDir = getenv( 'WORKSPACE' ) . '/log';
} else {
	$wmgMwLogDir = __DIR__ . '/../log';
}

/**
 * Development settings
 */
if ( is_file( "$IP/includes/DevelopmentSettings.php" ) ) {
	putenv( "MW_LOG_DIR=$wmgMwLogDir" );
	require_once "$IP/includes/DevelopmentSettings.php";
} else {
	// Compatibility with older MediaWiki branches

	// Debugging: PHP
	error_reporting( -1 );
	ini_set( 'display_errors', 1 );

	// Debugging: MediaWiki
	$wgDevelopmentWarnings = true;
	$wgShowDBErrorBacktrace = true;
	$wgShowExceptionDetails = true;
	$wgShowSQLErrors = true;
	$wgDebugRawPage = true; // bug 47960

	// Debugging: Logging
	if ( $wgCommandLineMode ) {
		$wgDebugLogFile = "$wmgMwLogDir/mw-debug-cli.log";
	} else {
		$wgDebugLogFile = "$wmgMwLogDir/mw-debug-www.log";
	}
	$wgDebugTimestamps = true;
	$wgDBerrorLog = "$wmgMwLogDir/mw-dberror.log";
	$wgDebugLogGroups['ratelimit'] = "$wmgMwLogDir/mw-ratelimit.log";
	$wgDebugLogGroups['exception'] = "$wmgMwLogDir/mw-exception.log";
	$wgDebugLogGroups['error'] = "$wmgMwLogDir/mw-error.log";
	// Back-compat
	$wgRateLimitLog = $wgDebugLogGroups['ratelimit'];
}

/**
 * Experimental settings that we're trying for Jenkins
 * before they become defaults in MediaWiki core
 */

// Be strict about class name letter-case.
$wgAutoloadAttemptLowercase = false;
