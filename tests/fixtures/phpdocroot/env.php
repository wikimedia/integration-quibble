<?php
print json_encode([
	'MW_INSTALL_PATH' => getenv('MW_INSTALL_PATH'),
	'MW_LOG_DIR' => getenv('MW_LOG_DIR'),
	'LOG_DIR' => getenv('LOG_DIR'),
]);
