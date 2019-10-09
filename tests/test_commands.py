#!/usr/bin/env python3

import subprocess
import unittest
from unittest import mock
from .util import run_sequentially

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

    @mock.patch('json.dump')
    def test_execute(self, mock_dump):
        quibble.commands.CreateComposerLocal(
            '/tmp',
            ['mediawiki/extensions/Wikibase', 'justinrainbow/jsonschema']
        ).execute()

        mock_dump.assert_any_call(
            {
                'extra': {
                    'merge-plugin': {
                        'include': ['extensions/Wikibase/composer.json']
                    }
                }
            }, mock.ANY)


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
            ['git', 'clean', '-xqdf'], cwd='/tmp')


class CoreNpmComposerTestTest(unittest.TestCase):

    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.commands.parallel_run', side_effect=run_sequentially)
    @mock.patch('quibble.gitchangedinhead.GitChangedInHead.changedFiles',
                return_value=['foo.php', 'bar.php'])
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call, *_):
        quibble.commands.CoreNpmComposerTest('/tmp', True, True).execute()

        mock_check_call.assert_any_call(
            ['composer', 'test', 'foo.php', 'bar.php'],
            cwd='/tmp',
            env={'somevar': '42', 'COMPOSER_PROCESS_TIMEOUT': mock.ANY})

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
            ['composer', 'require', '--dev', '--ansi', '--no-progress',
             '--prefer-dist', '-v', 'justinrainbow/jsonschema=^1.2.3'],
            cwd='/tmp/vendor')


class InstallMediaWikiTest(unittest.TestCase):

    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('os.rename')
    @mock.patch('quibble.mediawiki.maintenance.rebuildLocalisationCache')
    @mock.patch('quibble.util.copylog')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.getDBClass')
    @mock.patch('quibble.mediawiki.maintenance.install')
    @mock.patch('quibble.mediawiki.maintenance.update')
    def test_execute(self, mock_update, mock_install_script,
                     mock_db_factory, *_):
        db = mock.MagicMock(
            dbname='testwiki',
            user='USER',
            password='PASS',
            dbserver='SERVER')
        mock_db_factory.return_value = mock.MagicMock(return_value=db)

        quibble.commands.InstallMediaWiki(
            '/tmp', 'mysql', '/db', '/dump', '/log', True
        ).execute()

        # TODO: Assert that localsettings is edited correctly.

        mock_install_script.assert_called_once_with(
            args=['--scriptpath=',
                  '--server=http://%s:%s' % (
                      quibble.commands.HTTP_HOST,
                      quibble.commands.HTTP_PORT
                  ),
                  '--dbtype=mysql', '--dbname=testwiki',
                  '--dbuser=USER', '--dbpass=PASS', '--dbserver=SERVER'],
            mwdir='/tmp')

        mock_update.assert_called_once_with(
            args=['--skip-external-dependencies'],
            mwdir='/tmp')


class PhpUnitDatabaseTest(unittest.TestCase):

    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call):
        quibble.commands.PhpUnitDatabase(
            mw_install_path='/tmp', testsuite='extensions', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            ['php', 'tests/phpunit/phpunit.php', '--debug-tests',
             '--testsuite', 'extensions', '--group', 'Database',
             '--exclude-group', 'Broken,ParserFuzz,Stub', '--log-junit',
             '/log/junit-db.xml'],
            cwd='/tmp',
            env={'LANG': 'C.UTF-8', 'somevar': '42'})


class PhpUnitDatabaselessTest(unittest.TestCase):

    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call):
        quibble.commands.PhpUnitDatabaseless(
            mw_install_path='/tmp', testsuite='extensions', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            ['php', 'tests/phpunit/phpunit.php', '--debug-tests',
             '--testsuite', 'extensions', '--exclude-group',
             'Broken,ParserFuzz,Stub,Database', '--log-junit',
             '/log/junit-dbless.xml'],
            cwd='/tmp',
            env=mock.ANY)


class PhpUnitUnitTest(unittest.TestCase):

    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    def test_execute_no_scripts(self, mock_check_call, mock_load, *_):
        mock_load.return_value = {
            "requires": {}
        }

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp', log_dir='/log'
        ).execute()

        mock_check_call.assert_not_called()

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    def test_execute_has_units(self, mock_check_call, mock_load, *_):
        mock_load.return_value = {
            "scripts": {
                "phpunit:unit": {}
            }
        }

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp', log_dir='/log'
        ).execute()

        mock_check_call.assert_called_once_with(
            ['composer', 'phpunit:unit', '--',
             '--exclude-group', 'Broken,ParserFuzz,Stub',
             '--log-junit', '/log/junit-unit.xml'],
            cwd='/tmp',
            env=mock.ANY)


class QunitTestsTest(unittest.TestCase):

    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.backend.DevWebServer')
    @mock.patch('quibble.is_in_docker', return_value=True)
    @mock.patch('subprocess.check_call')
    def test_execute(self, mock_check_call, *_):
        def check_env_for_no_sandbox(cmd, env={}, **_):
            assert 'CHROMIUM_FLAGS' in env
            assert '--no-sandbox' in env['CHROMIUM_FLAGS']

        mock_check_call.side_effect = check_env_for_no_sandbox

        quibble.commands.QunitTests('/tmp').execute()

        assert mock_check_call.call_count > 0


class BrowserTestsTest(unittest.TestCase):

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.DevWebServer')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_selenium(self, mock_driver, mock_server, mock_check_call,
                              mock_load, mock_path_exists):
        mock_load.return_value = {
            'scripts': {
                'selenium-test': 'run that stuff'
            }
        }

        c = quibble.commands.BrowserTests(
                '/tmp', ['mediawiki/core', 'mediawiki/skins/Vector'], ':0')
        c.execute()

        mock_check_call.assert_any_call(
            ['npm', 'run', 'selenium-test'],
            cwd='/tmp', env=mock.ANY)
        mock_check_call.assert_any_call(
            ['npm', 'run', 'selenium-test'],
            cwd='/tmp/skins/Vector', env=mock.ANY)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.DevWebServer')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_missing_selenium(self, mock_driver, mock_server,
                                      mock_check_call, mock_load,
                                      mock_path_exists):
        mock_load.return_value = {
            'scripts': {
                'other-test': 'foo'
            }
        }

        c = quibble.commands.BrowserTests(
                '/tmp', ['mediawiki/core', 'mediawiki/skins/Vector'], ':0')
        c.execute()

        mock_check_call.assert_not_called()

    @mock.patch('subprocess.check_call')
    @mock.patch('quibble.backend.DevWebServer')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_not_having_package_json(self, mock_driver, mock_server,
                                             mock_check_call):
        c = quibble.commands.BrowserTests('/tmp', ['mediawiki/vendor'], ':0')
        c.execute()
        mock_check_call.assert_not_called()


class UserCommandsTest(unittest.TestCase):

    @mock.patch('quibble.backend.DevWebServer')
    @mock.patch('subprocess.check_call')
    def test_commands(self, mock_check_call, *_):
        quibble.commands.UserCommands('/tmp', ['true', 'false']).execute()

        mock_check_call.assert_has_calls([
            mock.call('true', cwd='/tmp', shell=True),
            mock.call('false', cwd='/tmp', shell=True)])

    @mock.patch('quibble.backend.DevWebServer')
    def test_commands_raises_exception_on_error(self, *_):
        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserCommands('/tmp', ['false']).execute()

        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserCommands('/tmp', ['true', 'false']).execute()
