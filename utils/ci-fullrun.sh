#!/bin/bash
#
# Entry point for a full run of Quibble on CI
#
# https://integration.wikimedia.org/ci/job/integration-quibble-fullrun
#
# Arguments to this script are passed to the Quibble command.

set -eu -o pipefail
set -x

# ZUUL_ parameters passed to Quibble
TEST_PROJECT=mediawiki/core
TEST_BRANCH=master
TEST_REF=master

QUIBBLE_INSTALL_DIR=/tmp/quibble

# Find python version
_py3_bin=$(which python3)
_py3_real=$(readlink -f "$_py3_bin")
py3_version=$(basename "$_py3_real")

PYTHONPATH="$QUIBBLE_INSTALL_DIR/lib/$py3_version/site-packages"
export PYTHONPATH
mkdir -p "$PYTHONPATH"
python3 -s -c 'import pprint,sys; pprint.pprint(sys.path)'

python3 -s setup.py install --prefix "$QUIBBLE_INSTALL_DIR"

ZUUL_PROJECT=$TEST_PROJECT \
	ZUUL_BRANCH=$TEST_BRANCH \
	ZUUL_REF=$TEST_REF \
	exec python3 -s "$QUIBBLE_INSTALL_DIR"/bin/quibble "${@}"
