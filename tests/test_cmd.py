#!/usr/bin/env python3

import os
import unittest
from unittest import mock

from quibble import cmd


class CmdTest(unittest.TestCase):

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.set_repos_to_clone(),
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'Incorrect repos to clone')

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_with_vendor(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.set_repos_to_clone(clone_vendor=True),
            ['mediawiki/core', 'mediawiki/skins/Vector', 'mediawiki/vendor'],
            'Incorrect repos to clone')

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_appends_projects(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.set_repos_to_clone(projects=[
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
                ]),
            ['mediawiki/core', 'mediawiki/skins/Vector',
             'mediawiki/extensions/BoilerPlate',
             'mediawiki/extensions/Example'])

    def test_set_repos_to_clone_with_env(self):
        env = {
            'SKIN_DEPENDENCIES': 'mediawiki/skins/Monobook',
            'EXT_DEPENDENCIES':
                'mediawiki/extensions/One\\nmediawiki/extensions/Two',
        }
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            self.assertEqual([
                'mediawiki/core',  # must be first
                'mediawiki/skins/Vector',
                'mediawiki/skins/Monobook',
                'mediawiki/extensions/One',
                'mediawiki/extensions/Two',
                ], q.set_repos_to_clone())

    def test_set_repos_to_clone_adds_ZUUL_PROJECT(self):
        env = {'ZUUL_PROJECT': 'mediawiki/extensions/ZuulProjectEnvVar'}
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            self.assertEqual([
                'mediawiki/core',  # must be first
                'mediawiki/skins/Vector',
                'mediawiki/extensions/ZuulProjectEnvVar',
                ], q.set_repos_to_clone())

    def test_set_repos_to_clone_does_not_duplicate_hardcoded_repos(self):
        hardcoded_repos = [
            'mediawiki/core',
            'mediawiki/skins/Vector',
            ]

        for repo in hardcoded_repos:
            with mock.patch.dict('os.environ', {'ZUUL_PROJECT': repo},
                                 clear=True):
                q = cmd.QuibbleCmd()
                self.assertEqual([
                    'mediawiki/core',  # must be first
                    'mediawiki/skins/Vector',
                    ], q.set_repos_to_clone())

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_args_defaults(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('ref', args.git_cache)
        self.assertEqual(os.getcwd(), args.workspace)
        self.assertEqual('log', args.log_dir)

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_args_defaults_in_docker(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('/srv/git', args.git_cache)
        self.assertEqual('/workspace', args.workspace)
        self.assertEqual('/log', args.log_dir)

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment(self):
        q = cmd.QuibbleCmd()
        q.workspace = '/testworkspace'
        q.mw_install_path = ''
        q.log_dir = ''

        with mock.patch('quibble.is_in_docker', return_value=True):
            # In Docker we always use self.workspace
            q.setup_environment()
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')
            with mock.patch.dict(os.environ, {'WORKSPACE': '/fromenv'},
                                 clear=True):
                # In Docker, ignore $WORKSPACE
                q.setup_environment()
                self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

        with mock.patch('quibble.is_in_docker', return_value=False):
            q.setup_environment()
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

            with mock.patch.dict(os.environ, {'WORKSPACE': '/fromenv'},
                                 clear=True):
                # When not in Docker, we honor $WORKSPACE
                q.setup_environment()
                self.assertEqual(os.environ['WORKSPACE'], '/fromenv')

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment_has_log_directories(self):
        q = cmd.QuibbleCmd()
        q.workspace = '/workspace'
        q.mw_install_path = ''
        q.log_dir = '/mylog'

        q.setup_environment()

        self.assertIn('LOG_DIR', os.environ)
        self.assertIn('MW_LOG_DIR', os.environ)
        self.assertEqual(os.environ['LOG_DIR'], '/mylog')
        self.assertEqual(os.environ['MW_LOG_DIR'], '/mylog')

    def test_isCoreOrVendor(self):
        q = cmd.QuibbleCmd()
        self.assertTrue(q.isCoreOrVendor('mediawiki/core'))
        self.assertTrue(q.isCoreOrVendor('mediawiki/vendor'))
        self.assertFalse(q.isCoreOrVendor('mediawiki/extensions/Foo'))
        self.assertFalse(q.isCoreOrVendor('mediawiki/skins/Bar'))

    def test_isExtOrSkin(self):
        q = cmd.QuibbleCmd()
        q.isExtOrSkin
        self.assertTrue(q.isExtOrSkin('mediawiki/extensions/Foo'))
        self.assertTrue(q.isExtOrSkin('mediawiki/skins/Bar'))
        self.assertFalse(q.isExtOrSkin('mediawiki/core'))
        self.assertFalse(q.isExtOrSkin('mediawiki/vendor'))
