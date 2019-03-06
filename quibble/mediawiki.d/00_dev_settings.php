<?php
# Quibble MediaWiki configuration
# Originally copied from integration/jenkins.git:/mediawiki/conf.d/

if ( getenv( 'MW_LOG_DIR' ) ) {
	$quibbleLogDir = getenv( 'MW_LOG_DIR' );
} elseif ( getenv( 'WORKSPACE' ) ) {
	$quibbleLogDir = getenv( 'WORKSPACE' ) . '/log';
} else {
	$quibbleLogDir = __DIR__ . '/../log';
}

/**
 * Development settings
 */
if ( is_file( "$IP/includes/DevelopmentSettings.php" ) ) {
	putenv( "MW_LOG_DIR=$quibbleLogDir" );
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
		$wgDebugLogFile = "$quibbleLogDir/mw-debug-cli.log";
	} else {
		$wgDebugLogFile = "$quibbleLogDir/mw-debug-www.log";
	}
	$wgDebugTimestamps = true;
	$wgDBerrorLog = "$quibbleLogDir/mw-dberror.log";
	$wgDebugLogGroups['ratelimit'] = "$quibbleLogDir/mw-ratelimit.log";
	$wgDebugLogGroups['exception'] = "$quibbleLogDir/mw-exception.log";
	$wgDebugLogGroups['error'] = "$quibbleLogDir/mw-error.log";
	// Back-compat
	$wgRateLimitLog = $wgDebugLogGroups['ratelimit'];
}

/**
 * Experimental settings that we're trying for Jenkins
 * before they become defaults in MediaWiki core
 */

// Be strict about class name letter-case.
$wgAutoloadAttemptLowercase = false;
