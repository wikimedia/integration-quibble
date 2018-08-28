import os
import unittest
from unittest import mock

import quibble.zuul


class TestClone(unittest.TestCase):

    def test_ref_requires_url_to_fetch_from(self):
        zuul_env = {'PATH': '/usr/bin',
                    'ZUUL_BRANCH': 'features/v1',
                    'ZUUL_REF': 'heads/refs/features/v1',
                    }
        with mock.patch.dict(os.environ, zuul_env, clear=True):
            with self.assertRaisesRegex(
                    Exception, 'Zuul ref requires a Zuul url'):
                quibble.zuul.clone(['project'], '/tmp', '/tmp/cache')

    def test_newrev_requires_a_project(self):
        zuul_env = {'PATH': '/usr/bin',
                    'ZUUL_NEWREV': '1234567789ABCDEF',
                    }
        with mock.patch.dict(os.environ, zuul_env, clear=True):
            with self.assertRaisesRegex(
                    Exception, 'Zuul newrev requires a Zuul project'):
                quibble.zuul.clone(['project'], '/tmp', '/tmp/cache')

    @mock.patch('quibble.zuul.Cloner')
    def test_accepts_strings_as_repos(self, mock_cloner):
        quibble.zuul.clone('project_as_string', '/tmp', '/tmp/cache')

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('projects', kwargs)
        self.assertIsInstance(kwargs['projects'], list)

    @mock.patch('quibble.zuul.Cloner')
    def test_branch(self, mock_cloner):
        quibble.zuul.clone('project', '/workspace', '/cache', branch='REL1_42')

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('branch', kwargs)
        self.assertEquals(kwargs['branch'], 'REL1_42')

    @mock.patch('quibble.zuul.Cloner')
    def test_project_branch(self, mock_cloner):
        quibble.zuul.clone(
            'project', '/workspace', '/cache',
            project_branch=[['mediawiki/core=REL1_42']])

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('mediawiki/core', kwargs['project_branches'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/core'])

    @mock.patch('quibble.zuul.Cloner')
    def test_multiple_project_branch(self, mock_cloner):
        quibble.zuul.clone(
            'project', '/workspace', '/cache',
            project_branch=[
                ['mediawiki/core=REL1_42'],
                ['mediawiki/vendor=REL1_42']])

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('mediawiki/core', kwargs['project_branches'])
        self.assertIn('mediawiki/vendor', kwargs['project_branches'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/core'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/vendor'])


class TestRepoDir(unittest.TestCase):

    def test_maps_mediawiki_core_to_current_directory(self):
        self.assertEqual('.', quibble.zuul.repo_dir('mediawiki/core'))

    def test_maps_mediawiki_vendor_to_vendor_directory(self):
        self.assertEqual('vendor', quibble.zuul.repo_dir('mediawiki/vendor'))

    def test_maps_extensions_to_extensions_directory(self):
        self.assertEqual('extensions/SomeExt',
                         quibble.zuul.repo_dir('mediawiki/extensions/SomeExt'))

    def test_maps_skins_to_extensions_directory(self):
        self.assertEqual('skins/NiceSkin',
                         quibble.zuul.repo_dir('mediawiki/skins/NiceSkin'))
