import unittest
from unittest import mock

import quibble.zuul


class TestClone(unittest.TestCase):

    def test_ref_requires_url_to_fetch_from(self):
        with self.assertRaisesRegex(
                Exception, 'Zuul ref requires a Zuul url'):
            quibble.zuul.clone(
                branch=None, cache_dir='/tmp/cache', project_branch=[],
                projects=['project'], workers=1, workspace='/tmp/src',
                zuul_branch='features/v1', zuul_newrev='1234567789ABCDEF',
                zuul_project=None, zuul_ref='heads/refs/features/v1',
                zuul_url=None)

    def test_newrev_requires_a_project(self):
        with self.assertRaisesRegex(
                Exception, 'Zuul newrev requires a Zuul project'):
            quibble.zuul.clone(
                branch=None, cache_dir='/tmp/cache', project_branch=[],
                projects=['project'], workers=1, workspace='/tmp/src',
                zuul_branch=None, zuul_newrev='1234567789ABCDEF',
                zuul_project=None, zuul_ref=None, zuul_url=None)

    @mock.patch('quibble.zuul.Cloner')
    def test_accepts_strings_as_repos(self, mock_cloner):
        quibble.zuul.clone(
            branch=None, cache_dir='/tmp/cache', project_branch=[],
            projects='project_as_string', workers=1, workspace='/tmp/src',
            zuul_branch=None, zuul_newrev=None, zuul_project=None,
            zuul_ref=None, zuul_url=None)

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('projects', kwargs)
        self.assertIsInstance(kwargs['projects'], list)

    @mock.patch('quibble.zuul.Cloner')
    def test_branch(self, mock_cloner):
        quibble.zuul.clone(
            branch='REL1_42', cache_dir='/tmp/cache', project_branch=[],
            projects='project', workers=1, workspace='/tmp/src',
            zuul_branch=None, zuul_newrev=None, zuul_project=None,
            zuul_ref=None, zuul_url=None)

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('branch', kwargs)
        self.assertEquals(kwargs['branch'], 'REL1_42')

    @mock.patch('quibble.zuul.Cloner')
    def test_project_branch(self, mock_cloner):
        quibble.zuul.clone(
            branch='REL1_42', cache_dir='/tmp/cache',
            project_branch=[['mediawiki/core=REL1_42']], projects='project',
            workers=1, workspace='/tmp/src', zuul_branch=None,
            zuul_newrev=None, zuul_project=None, zuul_ref=None, zuul_url=None)

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('mediawiki/core', kwargs['project_branches'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/core'])

    @mock.patch('quibble.zuul.Cloner')
    def test_multiple_project_branch(self, mock_cloner):
        quibble.zuul.clone(
            branch='REL1_42', cache_dir='/tmp/cache',
            project_branch=[
                ['mediawiki/core=REL1_42'],
                ['mediawiki/vendor=REL1_42']],
            projects='project', workers=1, workspace='/tmp/src',
            zuul_branch=None, zuul_newrev=None, zuul_project=None,
            zuul_ref=None, zuul_url=None)

        (args, kwargs) = mock_cloner.call_args
        self.assertIn('mediawiki/core', kwargs['project_branches'])
        self.assertIn('mediawiki/vendor', kwargs['project_branches'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/core'])
        self.assertEquals('REL1_42',
                          kwargs['project_branches']['mediawiki/vendor'])

    @mock.patch('quibble.zuul.Cloner')
    def test_can_clone_without_mediawiki_core(self, mock_cloner):
        quibble.zuul.clone(
            branch='master', cache_dir='/tmp/cache', project_branch=[],
            # Clone without mediawiki/core
            projects=['mediawiki/skins/Foo', 'mediawiki/skins/Bar'],
            workers=2, workspace='/tmp/src',
            zuul_branch=None, zuul_newrev=None, zuul_project=None,
            zuul_ref=None, zuul_url=None)


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
