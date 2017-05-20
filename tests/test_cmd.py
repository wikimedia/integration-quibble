#!/usr/bin/env python3

import os
import unittest

from quibble import cmd


class CmdTest(unittest.TestCase):

    def test_projects_to_clone(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.get_repos_to_clone(),
            ['mediawiki/core'],
            'Incorrect repos to clone')

    def test_projects_to_clone_with_vendor(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.get_repos_to_clone(clone_vendor=True),
            ['mediawiki/core', 'mediawiki/vendor'],
            'Incorrect repos to clone')

    def test_generate_extensions_load(self):
        q = cmd.QuibbleCmd()
        os.makedirs('tests/.tmp/src', exist_ok=True)
        q.workspace = 'tests/.tmp'
        q.extra_dependencies = []
        q.generate_extensions_load()
        with open('tests/.tmp/src/extensions_load.txt') as f:
            self.assertEqual('', f.read())
