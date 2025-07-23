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

// This allows MediaWiki core and extensions to behave
// differently when being run on Wikimedia Jenkins CI. That is more or less
// needed when running Wikibase under Apache for QUnit, since the Jenkins
// environment variables are not available to the Apache process.
define( 'MW_QUIBBLE_CI', true ); // since Quibble 1.4.3
$wgWikimediaJenkinsCI = true; // deprecated since Quibble 1.4.3

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

$wgLocalDatabases = [ $wgDBname ];

// Caching settings.
if ( extension_loaded( 'memcached' ) ) {
    $wgMainCacheType = CACHE_MEMCACHED;
    $wgMemCachedServers = [ '127.0.0.1:11211' ];
    $wgMemCachedPersistent = true;
}

# Force secret key. This key can be shared with the configuration
# of testing tools, to allow them to perform privileged actions,
# such as running jobs.
$wgSecretKey = 'supercalifragilisticexpialidocious';

// Hack to support Extension:FileImporter browser tests, T190829
$wgEnableUploads = true;

// Hack to support testing Parsoid as an extension, while overriding
// the composer library included with core. (T227352)
function wfInterceptParsoidLoading( $className ) {
    // Only intercept Parsoid namespace classes
    if ( preg_match( '/(MW|Wikimedia\\\\)Parsoid\\\\/', $className ) ) {
       $fileName = Autoloader::find( $className );
       if ( $fileName !== null ) {
           require $fileName;
       }
    }
}

$parsoidDir = $IP . '/services/parsoid';
if ( is_dir( $parsoidDir ) ) {
    spl_autoload_register( 'wfInterceptParsoidLoading', true, true );
    // Keep this in sync with the "autoload" clause in
    // $PARSOID_INSTALL_DIR/composer.json
    $parsoidNamespace = [ 'Wikimedia\\Parsoid\\' => "$parsoidDir/src/" ];
    if ( method_exists( 'AutoLoader', 'registerNamespaces' ) ) {
        AutoLoader::registerNamespaces( $parsoidNamespace );
    } else {
        AutoLoader::$psr4Namespaces += $parsoidNamespace;
    }
    wfLoadExtension( 'Parsoid', "$parsoidDir/extension.json" );
}
unset( $parsoidDir );
