<?php
#
# Snippet coming from integration/jenkins.git:/mediawiki/conf.d/
#

// Set MW_INSTALL_PATH to appropriate MediaWiki core directory under WORKSPACE
// Legacy usage was to clone core directly in the WORKSPACE
// New usage is to put it in /src/mediawiki/core (aka /src/$ZUUL_PROJECT)

// The Wikidata extension has its extensions under /extensions/Wikidata/vendor/*
// That causes a bunch of issues when using relative paths.

if ( ! getenv( 'MW_INSTALL_PATH' ) ) {
	if ( is_dir( getenv( 'WORKSPACE' ) . '/src/mediawiki/core' ) ) {
		putenv( 'MW_INSTALL_PATH='. getenv( 'WORKSPACE' ) . '/src/mediawiki/core' );
	} else {
		// Legacy
		putenv( 'MW_INSTALL_PATH='. getenv( 'WORKSPACE' ) );
	}
}
