import os
import quibble
import unittest
from unittest import mock


class QuibbleTest(unittest.TestCase):

    @mock.patch.dict(os.environ, {'DISPLAY': ':0'})
    def test_use_headless__display_set(self):
        self.assertEqual(
            False, quibble.use_headless(),
            'Do not use headless when a DISPLAY is provided')

    @mock.patch.dict(os.environ, {'DISPLAY': ''})
    def test_use_headless__empty_display(self):
        self.assertEqual(
            True, quibble.use_headless(),
            'Use headless mode when DISPLAY is an empty string')

    @mock.patch.dict(os.environ, clear=True)
    def test_use_headless__unset_display(self):
            self.assertNotIn('DISPLAY', os.environ)
            self.assertEqual(
                True, quibble.use_headless(),
                'Use headless mode when DISPLAY is not set')

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_chrome_in_docker_does_not_use_sandbox(self, mock):
        self.assertIn('--no-sandbox', quibble.chromium_flags())

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_chrome_outside_docker_uses_sandbox(self, mock):
        self.assertNotIn('--no-sandbox', quibble.chromium_flags())

    @mock.patch('quibble.use_headless', return_value=True)
    def test_chrome_headless_arg(self, mock):
        self.assertIn('--headless', quibble.chromium_flags())

    @mock.patch('quibble.use_headless', return_value=False)
    def test_chrome_no_headless_arg(self, mock):
        self.assertNotIn('--headless', quibble.chromium_flags())

    # https://developers.google.com/web/updates/2017/09/autoplay-policy-changes
    # T197687
    def test_chrome_autoplay_does_not_require_user_gesture(self):
        self.assertIn('--autoplay-policy=no-user-gesture-required',
                      quibble.chromium_flags())
