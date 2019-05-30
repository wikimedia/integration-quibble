#!/usr/bin/env python3

import subprocess
import unittest
from unittest import mock

import quibble.commands


class ExtSkinSubmoduleUpdateCommandTest(unittest.TestCase):

    def test_submodule_update_errors(self):
        c = quibble.commands.ExtSkinSubmoduleUpdateCommand('/tmp')

        with mock.patch('os.walk') as mock_walk:
            mock_walk.side_effect = self.walk_extensions
            with mock.patch('subprocess.check_call') as mock_check_call:
                # A git command failing aborts.
                mock_check_call.side_effect = subprocess.CalledProcessError(
                    1, 'git something')
                with self.assertRaises(subprocess.CalledProcessError):
                    c.execute()

                mock_check_call.assert_called_once_with(
                    ['git', 'submodule', 'foreach',
                        'git', 'clean', '-xdff', '-q'],
                    cwd='/tmp/extensions/VisualEditor')

    def test_submodule_update(self):
        c = quibble.commands.ExtSkinSubmoduleUpdateCommand('/tmp')

        with mock.patch('os.walk') as mock_walk:
            mock_walk.side_effect = self.walk_extensions
            with mock.patch('subprocess.check_call') as mock_check_call:
                c.execute()

                mock_check_call.assert_any_call(
                    ['git', 'submodule', 'foreach',
                        'git', 'clean', '-xdff', '-q'],
                    cwd='/tmp/extensions/VisualEditor')

                # There should only be three calls, if there are more then we
                # must have recursed into a sub-subdirectory.
                self.assertEquals(
                    3, mock_check_call.call_count,
                    "Stopped after the first level directory")

    @staticmethod
    def walk_extensions(path):
        if path.endswith('/extensions'):
            return [
                ('/tmp/extensions', ['VisualEditor'], []),
                ('/tmp/extensions/VisualEditor', ['includes'],
                    ['.gitmodules']),
            ]
        else:
            return []


class CreateComposerLocalTest(unittest.TestCase):

    def test_execute(self):
        c = quibble.commands.CreateComposerLocal(
            '/tmp',
            ['mediawiki/extensions/Wikibase', 'justinrainbow/jsonschema'])

        with mock.patch('json.dump') as mock_dump:
            c.execute()

            expected = {
                'extra': {
                    'merge-plugin': {
                        'include': ['extensions/Wikibase/composer.json']
                    }
                }
            }
            mock_dump.assert_called_with(expected, mock.ANY)
