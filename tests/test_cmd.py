#!/usr/bin/env python3

import os
import unittest
from unittest import mock

from quibble import cmd


class CmdTest(unittest.TestCase):

    def test_projects_to_clone(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.set_repos_to_clone(),
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'Incorrect repos to clone')

    def test_projects_to_clone_with_vendor(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.set_repos_to_clone(clone_vendor=True),
            ['mediawiki/core', 'mediawiki/skins/Vector', 'mediawiki/vendor'],
            'Incorrect repos to clone')

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

    def test_generate_extensions_load(self):
        q = cmd.QuibbleCmd()
        os.makedirs('tests/.tmp/src', exist_ok=True)
        q.workspace = 'tests/.tmp'
        q.extra_dependencies = []
        q.generate_extensions_load()
        with open('tests/.tmp/src/extensions_load.txt') as f:
            self.assertEqual('', f.read())

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_args_defaults(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('ref', args.git_cache)
        self.assertEqual(os.getcwd(), args.workspace)

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_args_defaults_in_docker(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('/srv/git', args.git_cache)
        self.assertEqual('/workspace', args.workspace)

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
