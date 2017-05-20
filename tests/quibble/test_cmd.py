#!/usr/bin/env python3

import unittest

from quibble import cmd


class CmdTest(unittest.TestCase):

    def test_cloner_skins(self):
        self.assertEqual(cmd.getExtraSkins(), [])
