#!/usr/bin/env python3

import contextlib
import logging
import subprocess
import unittest
from unittest import mock
from .util import run_sequentially

import quibble.commands


class ExtSkinSubmoduleUpdateTest(unittest.TestCase):
    def test_submodule_update_errors(self):
        c = quibble.commands.ExtSkinSubmoduleUpdate('/tmp')

        with mock.patch('os.walk') as mock_walk:
            mock_walk.side_effect = self.walk_extensions
            with mock.patch('subprocess.check_call') as mock_check_call:
                # A git command failing aborts.
                mock_check_call.side_effect = subprocess.CalledProcessError(
                    1, 'git something'
                )
                with self.assertRaises(subprocess.CalledProcessError):
                    c.execute()

                mock_check_call.assert_called_once_with(
                    [
                        'git',
                        'submodule',
                        'foreach',
                        'git',
                        'clean',
                        '-xdff',
                        '-q',
                    ],
                    cwd='/tmp/extensions/VisualEditor',
                )

    def test_submodule_update(self):
        c = quibble.commands.ExtSkinSubmoduleUpdate('/tmp')

        with mock.patch('os.walk') as mock_walk:
            mock_walk.side_effect = self.walk_extensions
            with mock.patch('subprocess.check_call') as mock_check_call:
                c.execute()

                mock_check_call.assert_any_call(
                    [
                        'git',
                        'submodule',
                        'foreach',
                        'git',
                        'clean',
                        '-xdff',
                        '-q',
                    ],
                    cwd='/tmp/extensions/VisualEditor',
                )

                # There should only be three calls, if there are more then we
                # must have recursed into a sub-subdirectory.
                self.assertEqual(
                    3,
                    mock_check_call.call_count,
                    "Stopped after the first level directory",
                )

    @staticmethod
    def walk_extensions(path):
        if path.endswith('/extensions'):
            return [
                ('/tmp/extensions', ['VisualEditor'], []),
                (
                    '/tmp/extensions/VisualEditor',
                    ['includes'],
                    ['.gitmodules'],
                ),
            ]
        else:
            return []


class CreateComposerLocalTest(unittest.TestCase):
    @mock.patch('json.dump')
    def test_execute(self, mock_dump):
        quibble.commands.CreateComposerLocal(
            '/tmp',
            [
                'mediawiki/extensions/Wikibase',
                'mediawiki/skins/Vector',
                'justinrainbow/jsonschema',
            ],
        ).execute()

        mock_dump.assert_any_call(
            {
                'extra': {
                    'merge-plugin': {
                        'include': [
                            'extensions/*/composer.json',
                            'skins/*/composer.json',
                        ]
                    }
                }
            },
            mock.ANY,
        )


class ExtSkinComposerNpmTestTest(unittest.TestCase):
    @mock.patch('quibble.commands.parallel_run', side_effect=run_sequentially)
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_execute_all(self, mock_call, *_):
        quibble.commands.ExtSkinComposerNpmTest('/tmp', True, True).execute()

        mock_call.assert_any_call(['composer', '--ansi', 'test'], cwd='/tmp')
        mock_call.assert_any_call(['npm', 'test'], cwd='/tmp')

    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('quibble.commands.parallel_run', side_effect=run_sequentially)
    @mock.patch('subprocess.check_call')
    def test_execute_none(self, mock_call, *_):
        quibble.commands.ExtSkinComposerNpmTest('/tmp', True, True).execute()

        mock_call.assert_called_once_with(
            ['git', 'clean', '-xqdf'], cwd='/tmp'
        )


class CoreNpmComposerTestTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.commands.parallel_run', side_effect=run_sequentially)
    @mock.patch(
        'quibble.gitchangedinhead.GitChangedInHead.changedFiles',
        return_value=['foo.php', 'bar.php'],
    )
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call, *_):
        quibble.commands.CoreNpmComposerTest('/tmp', True, True).execute()

        mock_check_call.assert_any_call(
            ['composer', 'test-some', 'foo.php', 'bar.php'],
            cwd='/tmp',
            env={'somevar': '42', 'COMPOSER_PROCESS_TIMEOUT': mock.ANY},
        )

        mock_check_call.assert_any_call(['npm', 'test'], cwd='/tmp')


class VendorComposerDependenciesTest(unittest.TestCase):
    @mock.patch('quibble.util.copylog')
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call, mock_load, *_):
        mock_load.return_value = {
            'require-dev': {
                'justinrainbow/jsonschema': '^1.2.3',
            }
        }

        quibble.commands.VendorComposerDependencies('/tmp', '/log').execute()

        mock_check_call.assert_any_call(
            [
                'composer',
                'require',
                '--dev',
                '--ansi',
                '--no-progress',
                '--prefer-dist',
                '-v',
                'justinrainbow/jsonschema=^1.2.3',
            ],
            cwd='/tmp/vendor',
        )


class StartBackendsTest(unittest.TestCase):
    def test_execute(self):
        context_stack = contextlib.ExitStack()

        @contextlib.contextmanager
        def mock_backend():
            log = logging.getLogger('quibble.commands')
            log.info("Started mock.")
            yield
            log.info("Stopped mock.")

        cmd = quibble.commands.StartBackends(context_stack, [mock_backend()])

        with self.assertLogs(level='DEBUG') as log, context_stack:
            cmd.execute()

        self.assertRegex(log.output[0], "Started mock.")
        self.assertRegex(log.output[1], "Shutting down backends:.*contextlib")
        self.assertRegex(log.output[2], "Stopped mock.")


class InstallMediaWikiTest(unittest.TestCase):
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('os.rename')
    @mock.patch('quibble.mediawiki.maintenance.rebuildLocalisationCache')
    @mock.patch('quibble.util.copylog')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.get_backend')
    @mock.patch('quibble.mediawiki.maintenance.install')
    @mock.patch('quibble.mediawiki.maintenance.update')
    def test_execute(
        self, mock_update, mock_install_script, mock_db_factory, *_
    ):
        db = mock.MagicMock(
            dbname='testwiki',
            user='USER',
            password='PASS',
            dbserver='SERVER',
            type='mysql',
        )
        mock_db_factory.return_value = mock.MagicMock(return_value=db)
        url = 'http://192.0.2.1:4321'

        quibble.commands.InstallMediaWiki(
            '/src', db, url, '/log', '/tmp', True
        ).execute()

        # TODO: Assert that localsettings is edited correctly.

        mock_install_script.assert_called_once_with(
            args=[
                '--scriptpath=',
                '--server=%s' % (url,),
                '--dbtype=mysql',
                '--dbname=testwiki',
                '--dbuser=USER',
                '--dbpass=PASS',
                '--dbserver=SERVER',
            ],
            mwdir='/src',
        )

        mock_update.assert_called_once_with(
            args=['--skip-external-dependencies'], mwdir='/src'
        )


class PhpUnitDatabaseTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call):
        quibble.commands.PhpUnitDatabase(
            mw_install_path='/tmp', testsuite='extensions', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            [
                'php',
                'tests/phpunit/phpunit.php',
                '--testsuite',
                'extensions',
                '--group',
                'Database',
                '--exclude-group',
                'Broken,ParserFuzz,Stub,Standalone',
                '--log-junit',
                '/log/junit-db.xml',
            ],
            cwd='/tmp',
            env={'LANG': 'C.UTF-8', 'somevar': '42'},
        )


class PhpUnitDatabaselessTest(unittest.TestCase):
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call):
        quibble.commands.PhpUnitDatabaseless(
            mw_install_path='/tmp', testsuite='extensions', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            [
                'php',
                'tests/phpunit/phpunit.php',
                '--testsuite',
                'extensions',
                '--exclude-group',
                'Broken,ParserFuzz,Stub,Database,Standalone',
                '--log-junit',
                '/log/junit-dbless.xml',
            ],
            cwd='/tmp',
            env=mock.ANY,
        )


class PhpUnitStandaloneTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call):
        quibble.commands.PhpUnitStandalone(
            mw_install_path='/tmp',
            testsuite=None,
            log_dir='/log',
            repo_path='../extensions/Scribunto',
        ).execute()

        mock_check_call.assert_called_once_with(
            [
                'php',
                'tests/phpunit/phpunit.php',
                '../extensions/Scribunto',
                '--group',
                'Standalone',
                '--exclude-group',
                'Broken,ParserFuzz,Stub',
                '--log-junit',
                '/log/junit-standalone.xml',
            ],
            cwd='/tmp',
            env={'LANG': 'C.UTF-8', 'somevar': '42'},
        )


class PhpUnitUnitTest(unittest.TestCase):
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    def test_execute_no_scripts(self, mock_check_call, mock_load, *_):
        mock_load.return_value = {"requires": {}}

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp', log_dir='/log'
        ).execute()

        mock_check_call.assert_not_called()

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    def test_execute_has_units(self, mock_check_call, mock_load, *_):
        mock_load.return_value = {"scripts": {"phpunit:unit": {}}}

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            [
                'composer',
                'phpunit:unit',
                '--',
                '--exclude-group',
                'Broken,ParserFuzz,Stub',
                '--log-junit',
                '/log/junit-unit.xml',
            ],
            cwd='/tmp',
            env=mock.ANY,
        )


class QunitTestsTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call, *_):
        def check_env_for_no_sandbox(cmd, env={}, **_):
            assert 'CHROMIUM_FLAGS' in env
            assert '--no-sandbox' in env['CHROMIUM_FLAGS']

        mock_check_call.side_effect = check_env_for_no_sandbox

        quibble.commands.QunitTests('/tmp', 'http://192.0.2.1:4321').execute()

        assert mock_check_call.call_count > 0


class ApiTestingTest(unittest.TestCase):
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_api_testing(
        self,
        mock_driver,
        mock_server,
        mock_check_call,
        mock_dump,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {'scripts': {'api-testing': 'run tests'}}

        c = quibble.commands.ApiTesting(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'http://192.0.2.1:4321',
        )
        c.execute()

        mock_check_call.assert_any_call(
            ['npm', 'run', 'api-testing'], cwd='/tmp', env=mock.ANY
        )

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_missing_api_testing(
        self,
        mock_driver,
        mock_server,
        mock_check_call,
        mock_dump,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {'scripts': {'other-test': 'foo'}}

        c = quibble.commands.ApiTesting(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'http://192.0.2.1:4321',
        )
        c.execute()

        mock_check_call.assert_not_called()

    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_not_having_package_json(
        self, mock_driver, mock_server, mock_check_call, mock_dump, mock_load
    ):
        mock_load.return_value = {}

        c = quibble.commands.ApiTesting(
            '/tmp', ['mediawiki/vendor'], 'http://192.0.2.1:4321'
        )
        c.execute()
        mock_check_call.assert_not_called()


class BrowserTestsTest(unittest.TestCase):
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_selenium(
        self,
        mock_driver,
        mock_server,
        mock_check_call,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {
            'scripts': {'selenium-test': 'run that stuff'}
        }

        c = quibble.commands.BrowserTests(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            ':0',
            'http://192.0.2.1:4321',
        )
        c.execute()

        mock_check_call.assert_any_call(
            ['npm', 'run', 'selenium-test'], cwd='/tmp', env=mock.ANY
        )
        mock_check_call.assert_any_call(
            ['npm', 'run', 'selenium-test'],
            cwd='/tmp/skins/Vector',
            env=mock.ANY,
        )

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_missing_selenium(
        self,
        mock_driver,
        mock_server,
        mock_check_call,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {'scripts': {'other-test': 'foo'}}

        c = quibble.commands.BrowserTests(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            ':0',
            'http://192.0.2.1:4321',
        )
        c.execute()

        mock_check_call.assert_not_called()

    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_not_having_package_json(
        self, mock_driver, mock_server, mock_check_call
    ):
        c = quibble.commands.BrowserTests(
            '/tmp', ['mediawiki/vendor'], ':0', 'http://192.0.2.1:4321'
        )
        c.execute()
        mock_check_call.assert_not_called()


class UserScriptsTest(unittest.TestCase):
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('subprocess.check_call')
    def test_commands(self, mock_check_call, *_):
        quibble.commands.UserScripts(
            '/tmp', ['true', 'false'], 'http://192.0.2.1:9413'
        ).execute()

        mock_check_call.assert_has_calls(
            [
                mock.call('true', cwd='/tmp', shell=True, env=mock.ANY),
                mock.call('false', cwd='/tmp', shell=True, env=mock.ANY),
            ]
        )

    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('os.environ', clear=True)
    @mock.patch('subprocess.check_call')
    def test_mediawiki_environment_variables(self, mock_check_call, *_):
        quibble.commands.UserScripts(
            '/tmp', ['true', 'false'], 'http://192.0.2.1:9413'
        ).execute()

        (args, kwargs) = mock_check_call.call_args
        env = kwargs.get('env', {})
        self.assertEqual(
            env,
            {
                'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
                'MEDIAWIKI_USER': 'WikiAdmin',
                'MW_SERVER': 'http://192.0.2.1:9413',
                'MW_SCRIPT_PATH': '/',
            },
        )

    @mock.patch('quibble.backend.PhpWebserver')
    def test_commands_raises_exception_on_error(self, *_):
        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserScripts('/tmp', ['false'], '').execute()

        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserScripts(
                '/tmp', ['true', 'false'], ''
            ).execute()
