<?php
/**
 * Lame MediaWiki.d handler.
 *
 * @copyright Antoine Musso © 2013
 * @copyright Wikimedia Foundation Inc. © 2013
 * @license GPL v2.0
 */

$settingFiles = new GlobIterator( __DIR__ .  '/[0-9][0-9]*.php' );

// Make sure we start by closing LocalSettings.php tag
$content = '?>';

foreach ( $settingFiles as $settingFile ) {

	$fname = $settingFile->getFilename();
	fwrite( STDERR, "Proceeding '$fname'...\n" );

	$source = file_get_contents( $settingFile->getPathname() );

	/* Sanitization */

	// Files must start with T_OPEN_TAG
	$tokens = token_get_all($source);
	if ( $tokens[0][0] !== T_OPEN_TAG ) {
		fwrite( STDERR, "File '$fname' does not start with '<?php' .. skipping.\n" );
		continue;
	}

	// Files must not contains a T_CLOSE_TAG since we are appending them
	$hasCloseTag = false;
	foreach ( $tokens as $token ) {
		if ( $token[0] === T_CLOSE_TAG ) {
			$hasCloseTag = true;
			break;
		}
	}
	if ( $hasCloseTag ) {
		fwrite( STDERR, "File '$fname' contains a closing PHP tag .. skipping.\n" );
		continue;
	}

	// Append with filename and a trailing closing tag
	$content .= $source . "\n?>";
}

// On Wikimedia CI Jenkins, the resulting PHP will be appended to
// LocalSettings.php by the bin/mw-apply-settings.sh script.  That one also runs
// php -l on LocalSettings.php to ensure it is valid.
print $content;
