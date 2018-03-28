<?php
#
# Snippet coming from integration/jenkins.git:/mediawiki/conf.d/
#
# Loads extensions using either:
# - a list of extension names in /extensions_load.txt . They can be either the
#   name of the Gerrit repository (mediawiki/extensions/Foobar) or the basename
#   (Foobar).
# - a scan of the directory /extensions/
#
# It will then load the extension by either:
# - If an extension.json file is present, wfLoadExtension()
# - require the default entry point, Foo/Foo.php

$func_get_exts = function () {
	global $IP;

	if ( !is_dir( $IP ) ) {
		echo "Invalid MediaWiki path '$IP'.\n";
		echo "Aborting\n";
		exit(1);
	}

	$ext_to_load = array(
		'require' => array(),
		'load' => array(),
	);
	$ext_missing = array();
	$ext_candidates = array();

	$loadFile = $IP . '/extensions_load.txt';
	if ( file_exists( $loadFile ) ) {
		$ext_candidates = file( $loadFile,
			FILE_IGNORE_NEW_LINES
			| FILE_SKIP_EMPTY_LINES
		);
		$ext_candidates = array_map( function ( $entry ) {
			return str_replace( 'mediawiki/extensions/', '', $entry );
		}, $ext_candidates );
	} else {
		$ext_candidates = scandir( "${IP}/extensions/" );
	}

	foreach ( $ext_candidates as $extname ) {
		if ( $extname == '.'
			|| $extname == '..'
			|| !is_dir( "{$IP}/extensions/${extname}" )
		) {
			continue;
		}

		// Bug 42960: Ignore empty extensions
		$hasContent = array_diff(
			scandir( "{$IP}/extensions/${extname}" ),
			array( '.', '..' )
		);
		if( !$hasContent ) {
			continue;
		}

		$ext_dir = "{$IP}/extensions/{$extname}";
		if ( file_exists( "{$ext_dir}/extension.json" ) && function_exists( 'wfLoadExtensions' ) ) {
			$ext_to_load['load'][] = $extname;
		} elseif ( file_exists( "{$ext_dir}/$extname.php" ) ) {
			$ext_to_load['require'][] = "{$ext_dir}/$extname.php";
		} else {
			$ext_missing[] = $extname;
		}
	}
	if ( count( $ext_missing ) ) {
		echo "Could not load some extensions because they are missing\n";
		echo "the expected entry point:\n\n";
		echo implode( "\n", $ext_missing );
		echo "\n\nAborting\n";
		exit(1);
	}

	return $ext_to_load;
};

$extensions = $func_get_exts();
if ( $extensions['load'] ) {
	wfLoadExtensions( $extensions['load'] );
}

foreach ( $extensions['require'] as $entrypoint ) {
	require_once $entrypoint;
}
