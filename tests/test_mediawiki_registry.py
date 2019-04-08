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
                    'path does not matter')
                self.assertSetEqual(set(), reg.getRequiredRepos())

    def test_bails_out_on_both_ext_and_skin_files(self):
        with mock.patch('os.path.isdir') as isdir:
            isdir.return_value = True

            with mock.patch('os.path.exists') as exists:
                exists.return_value = True
                fake_path = 'path does not matter'
                with self.assertRaisesRegex(
                    Exception,
                    'Found both extension.json and skin.json in %s' % fake_path
                ):
                    quibble.mediawiki.registry.from_path(fake_path)

    def test_with_an_extension_dir(self):
        reg = quibble.mediawiki.registry.from_path(FIXTURES_DIR)
        expected = {
            'mediawiki/extensions/FakeExtension',
            'mediawiki/extensions/FakeExtension2',
            'mediawiki/skins/FakeSkin',
        }
        self.assertSetEqual(expected, reg.getRequiredRepos())


class TestRead(unittest.TestCase):

    def test_read_with_a_json_file(self):
        self.assertIn(
            'requires',
            quibble.mediawiki.registry.read(
                os.path.join(FIXTURES_DIR, 'extension.json')))

    def test_read_with_an_unexisting_file(self):
        with self.assertRaises(FileNotFoundError):
            quibble.mediawiki.registry.read('')


class TestParse(unittest.TestCase):

    def test_without_requires(self):
        self.assertSetEqual(
            set(), quibble.mediawiki.registry.parse({}))

    def test_skin_requirement(self):
        subject = {
            'requires':
            {'skins': {'FakeSkin': '*'}}
        }
        self.assertSetEqual(
            {'mediawiki/skins/FakeSkin'},
            quibble.mediawiki.registry.parse(subject))

    def test_extension_requirement(self):
        subject = {
            'requires':
            {'extensions': {'FakeExtension': '*'}}
        }
        self.assertSetEqual(
            {'mediawiki/extensions/FakeExtension'},
            quibble.mediawiki.registry.parse(subject))


class TestMediaWikiExtensionRegistration(unittest.TestCase):

    # A little bit more higher level
    def test_initialized_from_a_file(self):
        fixture_ext = os.path.join(FIXTURES_DIR, 'extension.json')
        reg = ExtensionRegistration(fixture_ext)

        expected = {
            'mediawiki/extensions/FakeExtension',
            'mediawiki/extensions/FakeExtension2',
            'mediawiki/skins/FakeSkin',
        }
        self.assertSetEqual(expected, reg.getRequiredRepos())
