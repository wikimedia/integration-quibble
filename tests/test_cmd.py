#!/usr/bin/env python3

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
