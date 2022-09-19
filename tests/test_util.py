from unittest import mock

import io
import logging
import pytest
import quibble.util
from quibble.util import (
    isCoreOrVendor,
    isExtOrSkin,
    move_item_to_head,
    php_version,
)
import sys
import tempfile


# quibble.util.isCoreOrVendor


def test_isCoreOrVendor_matches_core():
    assert isCoreOrVendor('mediawiki/core') is True


def test_isCoreOrVendor_matches_vendor():
    assert isCoreOrVendor('mediawiki/vendor') is True


def test_isCoreOrVendor_mismatches_extensions():
    assert isCoreOrVendor('mediawiki/extensions/Foo') is False


def test_isCoreOrVendor_mismatches_skins():
    assert isCoreOrVendor('mediawiki/skins/Bar') is False


# quibble.util.isExtOrSkin


def test_isExtOrSkin_matches_extensions():
    assert isExtOrSkin('mediawiki/extensions/Foo') is True


def test_isExtOrSkin_matches_skins():
    assert isExtOrSkin('mediawiki/skins/Bar') is True


def test_isExtOrSkin_mismatches_core():
    assert isExtOrSkin('mediawiki/core') is False


def test_isExtOrSkin_mismatches_vendor():
    assert isExtOrSkin('mediawiki/vendor') is False


def test_move_item_to_head_present():
    orig = ['mediawiki/core', 'extensions/foo', 'bar']
    expected = ['extensions/foo', 'mediawiki/core', 'bar']

    reordered = move_item_to_head(orig, 'extensions/foo')
    assert expected == reordered
    assert orig[0] == 'mediawiki/core'


def test_move_item_to_head_absent():
    orig = ['mediawiki/core', 'bar']

    with pytest.raises(ValueError):
        move_item_to_head(orig, 'extensions/foo')


@mock.patch('subprocess.check_output')
def test_php_version(php_output):
    php_output.return_value = (
        'PHP 7.4.21 (cli) (built: Jul  2 2021 03:59:48) ( NTS )'
    )
    assert php_version('>=7.4') is True
    assert php_version('>=7.4.0') is True
    assert php_version('<7.4') is False


def test_redirect_stream():
    with tempfile.TemporaryFile(mode='w+') as stream, tempfile.TemporaryFile(
        mode='w+'
    ) as collector:
        with quibble.util._redirect_stream(stream, collector):
            stream.write("line\n")

        collector.flush()
        collector.seek(0, io.SEEK_SET)
        captured = collector.read()
        assert captured == "line\n"

        stream.flush()
        stream.seek(0, io.SEEK_SET)
        sent = stream.read()
        assert sent == ""


def test_redirect_all_streams():
    """This just proves that the redirect function is trying something
    unsupported in the test context.
    """
    with tempfile.TemporaryFile() as collector:
        with quibble.util.redirect_all_streams(collector):
            print("test out")
            print("test error", file=sys.stderr)
            logging.getLogger().error("test log")

        collector.flush()
        collector.seek(0, io.SEEK_SET)
        captured = collector.read().decode()
        assert captured == "test out\ntest error\ntest log\n"
