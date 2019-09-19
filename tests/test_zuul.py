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

    @mock.patch('quibble.zuul.ThreadPoolExecutor')
    @mock.patch('quibble.zuul.Cloner')
    def test_can_clone_without_mediawiki_core(
        self, mock_cloner, mock_executor
    ):
        repos_to_clone = [
            'mediawiki/skins/Foo',
            'mediawiki/skins/Bar',
        ]
        with mock.patch('quibble.zuul.as_completed'):
            quibble.zuul.clone(
                branch='master', cache_dir='/tmp/cache', project_branch=[],
                # Clone without mediawiki/core
                projects=repos_to_clone,
                workers=2, workspace='/tmp/src',
                zuul_branch=None, zuul_newrev=None, zuul_project=None,
                zuul_ref=None, zuul_url=None)

        # Make sure MediaWiki core does not get cloned
        self.assertNotIn(
            mock.call().prepareRepo('mediawiki/core', mock.ANY),
            mock_cloner.mock_calls
            )

        # Verify the ThreadExecutor that invokes Cloner().prepareRepo has only
        # been given our repositories.
        expected_calls = []
        for expected_repo in repos_to_clone:
            expected_calls.append(
                mock.call().__enter__().submit(
                    quibble.zuul.clone_worker,
                    mock.ANY,  # can_run
                    mock.ANY,  # zuul_cloner
                    expected_repo,
                    mock.ANY  # we don't care about the destination
                    )
            )

        # Wrap with context manager calls to delimit the prepareRepo calls and
        # thus ensure no other repository sneaked in
        expected_calls.insert(0, mock.call().__enter__())
        expected_calls.append(mock.call().__exit__(None, None, None))
        mock_executor.assert_has_calls(expected_calls)

    @mock.patch('quibble.zuul.Cloner')
    def test_mediawiki_core_cloned_first_when_running_in_parallel(
        self, mock_cloner
    ):
        repos_to_clone = [
            'mediawiki/extensions/Bar',
            'mediawiki/skins/Vector',
            'mediawiki/core',
        ]
        quibble.zuul.clone(
            branch='master', cache_dir='/tmp/cache', project_branch=[],
            # Clone without mediawiki/core
            projects=repos_to_clone,
            workers=2, workspace='/tmp/src',
            zuul_branch=None, zuul_newrev=None, zuul_project=None,
            zuul_ref=None, zuul_url=None)
        self.maxDiff = None

        mock_cloner.assert_has_calls([
            # MediaWiki core first
            mock.call().prepareRepo('mediawiki/core', mock.ANY),
            mock.call().log.getChild('mediawiki/extensions/Bar'),
            mock.call().prepareRepo('mediawiki/extensions/Bar', mock.ANY),
            mock.call().log.getChild('mediawiki/skins/Vector'),
            mock.call().prepareRepo('mediawiki/skins/Vector', mock.ANY),
        ])


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
