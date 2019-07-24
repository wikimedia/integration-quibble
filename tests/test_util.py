import quibble.util
from quibble.util import isCoreOrVendor, isExtOrSkin


def test_parallel_run_accepts_an_empty_list_of_tasks():
    quibble.util.parallel_run([])
    assert True


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
