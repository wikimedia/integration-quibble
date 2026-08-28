import os.path
import unittest
from unittest import mock

import quibble.mediawiki.registry
from quibble.mediawiki.registry import ExtensionRegistration

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestFromPath(unittest.TestCase):
    def test_on_a_non_existing_path(self):
        with mock.patch('os.path.isdir') as isdir:
            isdir.return_value = False
            with self.assertRaises(NotADirectoryError):
                quibble.mediawiki.registry.from_path('.')

    def test_with_no_registration_file(self):
        with mock.patch('os.path.isdir') as isdir:
            isdir.return_value = True

            with mock.patch('os.path.exists') as exists:
                exists.return_value = False
                reg = quibble.mediawiki.registry.from_path(
                    'path does not matter'
                )
                assert reg.getRequiredRepos() == set()

    def test_bails_out_on_both_ext_and_skin_files(self):
        with mock.patch('os.path.isdir') as isdir:
            isdir.return_value = True

            with mock.patch('os.path.exists') as exists:
                exists.return_value = True
                fake_path = 'path does not matter'
                with self.assertRaisesRegex(
                    Exception,
                    'Found both extension.json and skin.json in %s'
                    % fake_path,
                ):
                    quibble.mediawiki.registry.from_path(fake_path)

    def test_with_an_extension_dir(self):
        reg = quibble.mediawiki.registry.from_path(FIXTURES_DIR)
        expected = {
            'mediawiki/extensions/FakeExtension',
            'mediawiki/extensions/FakeExtension2',
            'mediawiki/skins/FakeSkin',
        }
        assert expected, reg.getRequiredRepos()


class TestRead(unittest.TestCase):
    def test_read_with_a_json_file(self):
        assert 'requires' in quibble.mediawiki.registry._read(
            os.path.join(FIXTURES_DIR, 'extension.json')
        )

    def test_read_with_an_unexisting_file(self):
        with self.assertRaises(FileNotFoundError):
            quibble.mediawiki.registry._read('')


class TestParse:
    def test_without_requires(self):
        assert quibble.mediawiki.registry._parse({}) == set()

    def test_skin_requirement(self):
        subject = {'requires': {'skins': {'FakeSkin': '*'}}}
        assert quibble.mediawiki.registry._parse(subject) == {
            'mediawiki/skins/FakeSkin'
        }

    def test_extension_requirement(self):
        subject = {'requires': {'extensions': {'FakeExtension': '*'}}}
        assert quibble.mediawiki.registry._parse(subject) == {
            'mediawiki/extensions/FakeExtension'
        }


class TestMediaWikiExtensionRegistration:
    # A little bit more higher level
    def test_initialized_from_a_file(self):
        fixture_ext = os.path.join(FIXTURES_DIR, 'extension.json')
        reg = ExtensionRegistration(fixture_ext)

        assert reg.getRequiredRepos() == {
            'mediawiki/extensions/FakeExtension',
            'mediawiki/extensions/FakeExtension2',
            'mediawiki/skins/FakeSkin',
        }
