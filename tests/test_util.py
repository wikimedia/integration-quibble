from unittest import mock

import io
import logging
import pytest
import quibble.util
from quibble.util import (
    FetchInfo,
    isCoreOrVendor,
    isExtOrSkin,
    move_item_to_head,
    strtobool,
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


@mock.patch('quibble.util.FetchInfo.fetch')
def test_FetchInfo_without_patchset(fetch):
    fetch.return_value = {
        'project': 'repo/example',
        'branch': 'master',
        'current_revision': 'deadbeef',  # o=CURRENT_REVISION
        'revisions': {
            'deadbeef': {
                'fetch': {
                    'anonymous http': {
                        'ref': 'refs/changes/45/12345/42',
                        'url': 'https://example.org/r/repo/example',
                    }
                }
            }
        },
    }
    assert FetchInfo.change(12345).asZuulEnv() == {
        'ZUUL_URL': 'https://example.org/r/',
        'ZUUL_PROJECT': 'repo/example',
        'ZUUL_BRANCH': 'master',
        'ZUUL_REF': 'refs/changes/45/12345/42',
    }


@mock.patch('quibble.util.FetchInfo.fetch')
def test_FetchInfo_with_patchset(fetch):
    fetch.return_value = {
        'project': 'repo/example',
        'branch': 'master',
        'revisions': {
            'deadbeef': {
                '_number': 42,  # indice we look with o=ALL_REVISIONS
                'fetch': {
                    'anonymous http': {
                        'ref': 'refs/changes/45/12345/42',
                        'url': 'https://example.org/r/repo/example',
                    }
                },
            }
        },
    }
    assert FetchInfo.change(12345, 42).asZuulEnv() == {
        'ZUUL_URL': 'https://example.org/r/',
        'ZUUL_PROJECT': 'repo/example',
        'ZUUL_BRANCH': 'master',
        'ZUUL_REF': 'refs/changes/45/12345/42',
    }


# The test_strtobool code has been copied from Python which removed it with
# v3.12. There is most probably NO reason to touch this code.
def test_strtobool():
    yes = ('y', 'Y', 'yes', 'True', 't', 'true', 'True', 'On', 'on', '1')
    no = ('n', 'no', 'f', 'false', 'off', '0', 'Off', 'No', 'N')

    for y in yes:
        assert bool(strtobool(y)) is True

    for n in no:
        assert bool(strtobool(n)) is False
