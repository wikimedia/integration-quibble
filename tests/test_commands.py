#!/usr/bin/env python3

import contextlib
import hashlib
import io
import logging
import os.path
import pathlib
import pytest
import re
import subprocess
import sys
import unittest
from unittest import mock
from unittest.mock import call

import quibble.commands


broken_on_macos = pytest.mark.skipif(
    sys.platform != 'linux', reason="Broken on MacOS, see T299840"
)

npm_envs_parameters = (
    "npm_command_env, expected_npm_command",
    [
        pytest.param(None, "npm", id="NPM_COMMAND unset > npm"),
        pytest.param("npm", "npm", id="NPM_COMMAND=npm > npm"),
        pytest.param("pnpm", "pnpm", id="NPM_COMMAND=pnpm > pnpm"),
    ],
)


# Used to run tests with various NPM_COMMAND environment variables. To use it
# decorate the test method:
#
#  @pytest.mark.parametrize(*npm_envs_parameters)
#
# Add to the test method as last arguements:
#   npm_command_env, expected_npm_command
#
# In the test method you can then:
#
#   with mock_npm_command_env(npm_command_env):
#       // test code
#
# Then assert a call has been made to 'expected_npm_command'
#
def mock_npm_command_env(env_value):
    if env_value is None:
        return mock.patch.dict('os.environ', clear=True)
    else:
        return mock.patch.dict('os.environ', {'NPM_COMMAND': env_value})


class ExtSkinSubmoduleUpdateTest(unittest.TestCase):
    def test_submodule_update_errors(self):
        c = quibble.commands.ExtSkinSubmoduleUpdate('/tmp')

        with mock.patch('os.walk') as mock_walk:
            mock_walk.side_effect = self.walk_extensions
            with mock.patch('quibble.commands.run') as mock_run:
                # A git command failing aborts.
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, 'git something'
                )
                with self.assertRaises(subprocess.CalledProcessError):
                    c.execute()

                mock_run.assert_called_once_with(
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
            with mock.patch('quibble.commands.run') as mock_run:
                c.execute()

                mock_run.assert_any_call(
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
                    mock_run.call_count,
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


class ExtSkinComposerTestTest(unittest.TestCase):
    @mock.patch(
        'quibble.commands._repo_has_composer_script', return_value=True
    )
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_call, *_):
        quibble.commands.ExtSkinComposerTest('/tmp').execute()
        mock_call.assert_any_call(['composer', '--ansi', 'test'], cwd='/tmp')


class NpmTestTest:
    @mock.patch('quibble.commands.repo_has_npm_script', return_value=True)
    @mock.patch('quibble.commands.run')
    @pytest.mark.parametrize(*npm_envs_parameters)
    def test_execute(
        self, mock_call, mock_has, npm_command_env, expected_npm_command
    ):
        with mock_npm_command_env(npm_command_env):
            quibble.commands.NpmTest('/tmp').execute()
        mock_call.assert_any_call([expected_npm_command, 'test'], cwd='/tmp')


class CoreComposerTestTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch(
        'quibble.gitchangedinhead.GitChangedInHead.changedFiles',
        return_value=['foo.php', 'bar.php'],
    )
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run, *_):
        quibble.commands.CoreComposerTest('/tmp').execute()

        mock_run.assert_any_call(
            ['composer', 'test-some', 'foo.php', 'bar.php'],
            cwd='/tmp',
            env={'somevar': '42', 'COMPOSER_PROCESS_TIMEOUT': mock.ANY},
        )


class VendorComposerDependenciesTest(unittest.TestCase):
    @mock.patch('quibble.util.copylog')
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run, mock_load, *_):
        mock_load.return_value = {
            'require-dev': {
                'justinrainbow/jsonschema': '^1.2.3',
            }
        }

        quibble.commands.VendorComposerDependencies('/tmp', '/log').execute()

        mock_run.assert_any_call(
            [
                'composer',
                'require',
                '--dev',
                '--ansi',
                '--no-progress',
                '--no-interaction',
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


class InstallMediaWikiTest:
    @mock.patch('quibble.mediawiki.maintenance.rebuildLocalisationCache')
    @mock.patch('quibble.backend.get_backend')
    @mock.patch('quibble.mediawiki.maintenance.install')
    @mock.patch('quibble.mediawiki.maintenance.update')
    @mock.patch('quibble.mediawiki.maintenance.addSite')
    def test_execute(
        self,
        mock_addSite,
        mock_update,
        mock_install_script,
        mock_db_factory,
        *_,
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

        install_mw = quibble.commands.InstallMediaWiki(
            '/src', db, url, '/log', '/tmp'
        )

        with mock.patch.object(
            install_mw, '_get_install_args'
        ) as mock_install_args:
            with mock.patch.multiple(
                quibble.commands.InstallMediaWiki,
                _expand_template=mock.DEFAULT,
                _apply_custom_settings=mock.DEFAULT,
            ) as mocks:
                install_mw.execute()
                mock_install_args.assert_called_once()

                mocks['_expand_template'].assert_called_with(
                    'mediawiki/local_settings.php.tpl',
                    settings={
                        'MW_LOG_DIR': '/log',
                        'TMPDIR': '/tmp',
                    },
                )
                mocks['_apply_custom_settings'].assert_called_once()

        mock_update.assert_called_once_with(mwdir='/src')

        mock_addSite.assert_called_once_with(
            args=[
                'testwiki',
                'CI',
                '--filepath=%s/$1' % (url),
                '--pagepath=%s/index.php?title=$1' % (url),
            ],
            mwdir='/src',
        )

    def test_expand_template(self):
        with mock.patch(
            'quibble.commands.InstallMediaWiki._expand_localsettings_template'
        ) as mock_expand_localsettings_template:
            quibble.commands.InstallMediaWiki._expand_template(
                'mediawiki/local_settings.php.tpl',
                settings={
                    'MW_LOG_DIR': '/log',
                    'TMPDIR': '/tmp',
                },
            )
            mock_expand_localsettings_template.assert_called_once_with(
                # Import lib returns a NtPath or PosixPath
                pathlib.Path(
                    # Assuming we run tests from a source tree (and not a
                    # wheel), we already know where the file is.
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'quibble/mediawiki/local_settings.php.tpl',
                    )
                ),
                {'MW_LOG_DIR': '/log', 'TMPDIR': '/tmp'},
            )

    def test_execute_clears_localsettings(self):
        install_mw = quibble.commands.InstallMediaWiki('/somepath', *range(4))

        # Make it an exception to early abort execute() so we don't have to
        # mock everything else.
        with mock.patch.object(
            install_mw, 'clearQuibbleLocalSettings'
        ) as clear:
            clear.side_effect = Exception("clearQuibbleLocalSettings called")
            with pytest.raises(
                Exception, match="clearQuibbleLocalSettings called"
            ):
                install_mw.execute()

    def test_clearQuibbleLocalSettings_skips_non_existing(self):
        install_mw = quibble.commands.InstallMediaWiki('/somepath', *range(4))
        with mock.patch('os.path.exists', return_value=False):
            install_mw.clearQuibbleLocalSettings()

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.unlink')
    def test_clearQuibbleLocalSettings_deletes_file_from_template(
        self, unlink, _
    ):
        install_mw = quibble.commands.InstallMediaWiki('/somepath', *range(4))

        localsettings = quibble.commands.InstallMediaWiki._expand_template(
            'mediawiki/local_settings.php.tpl', {}
        )

        with mock.patch(
            'builtins.open', mock.mock_open(read_data=localsettings)
        ):
            install_mw.clearQuibbleLocalSettings()
            unlink.assert_called_once()

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.unlink')
    def test_clearQuibbleLocalSettings_raises_on_unknown_settings_file(
        self, unlink, _
    ):
        install_mw = quibble.commands.InstallMediaWiki('/somepath', *range(4))
        with mock.patch('builtins.open', mock.mock_open()):
            with pytest.raises(
                Exception,
                match=re.escape(
                    "Unknown configuration file /somepath/LocalSettings.php\n"
                    "Marker not found: '# Quibble MediaWiki configuration\\n'"
                ),
            ):
                install_mw.clearQuibbleLocalSettings()
            unlink.assert_not_called()

    def test__expand_localsettings_template(self):
        template = (
            "# Token replaced by quibble:\n"
            "{{params-declaration}}\n"
            "# End\n"
        )
        with mock.patch('builtins.open', mock.mock_open(read_data=template)):
            InstallMediaWiki = quibble.commands.InstallMediaWiki
            expanded = InstallMediaWiki._expand_localsettings_template(
                'fakefile',
                {
                    'MW_LOG': '/log',
                    'SOMECONST': 'hello world',
                },
            )
            assert expanded == (
                "# Token replaced by quibble:\n"
                "const MW_LOG = '/log';\n"
                "const SOMECONST = 'hello world';\n"
                "# End\n"
            )

    @mock.patch('os.rename')
    @mock.patch('quibble.commands.copylog')
    @mock.patch('subprocess.check_call')
    def test__apply_custom_settings(
        self, mock_check_call, mock_copylog, mock_rename
    ):
        customized_settings = '# Nothing new to see\n'

        with mock.patch('builtins.open', mock.mock_open()) as mock_open:
            quibble.commands.InstallMediaWiki._apply_custom_settings(
                localsettings='/work/LocalSettings.php',
                installed_copy='/work/opt_subdir/CopyOfInstalledSettings.php',
                new_settings=customized_settings,
                log_dir='/LOGS',
            )
        mock_rename.assert_called_once_with(
            '/work/LocalSettings.php',
            '/work/opt_subdir/CopyOfInstalledSettings.php',
        )
        mock_open().write.assert_called_once_with(customized_settings)

        mock_copylog.assert_has_calls(
            [
                call('/work/LocalSettings.php', '/LOGS/LocalSettings.php'),
                call(
                    '/work/opt_subdir/CopyOfInstalledSettings.php',
                    '/LOGS/CopyOfInstalledSettings.php',
                ),
            ]
        )
        mock_check_call.assert_has_calls(
            [
                call(
                    [
                        'php',
                        '-l',
                        '/work/LocalSettings.php',
                        '/work/opt_subdir/CopyOfInstalledSettings.php',
                    ]
                )
            ]
        )

    @mock.patch('quibble.backend.get_backend')
    @pytest.mark.parametrize(
        "db_type,db_specific_args, expected_extras",
        [
            pytest.param(
                'sqlite',
                {
                    'rootdir': '/tmp/db.sqlite',
                },
                ['--dbpath=/tmp/db.sqlite'],
                id='sqlite',
            ),
            pytest.param(
                'mysql',
                {
                    'user': 'USER',
                    'password': 'PASS',
                    'dbserver': 'SERVER',
                },
                ['--dbuser=USER', '--dbpass=PASS', '--dbserver=SERVER'],
                id='mysql',
            ),
            pytest.param(
                'postgres',
                {
                    'user': 'USER',
                    'password': 'PASS',
                    'dbserver': 'SERVER',
                },
                ['--dbuser=USER', '--dbpass=PASS', '--dbserver=SERVER'],
                id='postgres',
            ),
        ],
    )
    def test__get_install_args(
        self, mock_db_factory, db_type, db_specific_args, expected_extras
    ):
        db = mock.MagicMock(
            dbname='testwiki',
            type=db_type,
            **db_specific_args,
        )
        mock_db_factory.return_value = mock.MagicMock(return_value=db)
        url = 'http://192.0.2.1:4321'

        install_mw = quibble.commands.InstallMediaWiki(
            '/src', db, url, '/log', '/tmp'
        )
        assert (
            install_mw._get_install_args()
            == [
                '--scriptpath=',
                '--server=%s' % (url,),
                '--dbtype=%s' % db_type,
                '--dbname=testwiki',
            ]
            + expected_extras
        )

    @mock.patch('quibble.backend.get_backend')
    def test__get_install_args_raises_on_unknown_db_type(
        self, mock_db_factory
    ):
        db = mock.MagicMock(
            dbname='testwiki',
            type='unsupported_db_type',
        )
        mock_db_factory.return_value = db
        install_mw = quibble.commands.InstallMediaWiki(
            '/src', db, 'http://example.org/', '/log', '/tmp'
        )
        with pytest.raises(
            Exception, match='Unsupported database: unsupported_db_type'
        ):
            install_mw._get_install_args()


class PhpUnitPrepareParallelRunComposerTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.commands.copylog')
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run, mock_copylog):
        quibble.commands.PhpUnitPrepareParallelRunComposer(
            mw_install_path='/tmp',
            testsuite='extensions',
            log_dir='/log',
            junit=True,
        ).execute()

        mock_run.assert_called_once_with(
            [
                'composer',
                'phpunit:prepare-parallel:extensions',
            ],
            cwd='/tmp',
            env={'LANG': 'C.UTF-8', 'somevar': '42'},
        )
        mock_copylog.assert_has_calls(
            [
                mock.call(
                    '/tmp/phpunit-database.xml',
                    '/log/phpunit-parallel-database.xml',
                ),
                mock.call(
                    '/tmp/phpunit-databaseless.xml',
                    '/log/phpunit-parallel-databaseless.xml',
                ),
            ]
        )


class PhpUnitDatabaseTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'somevar': '42'}, clear=True)
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run):
        quibble.commands.PhpUnitDatabase(
            mw_install_path='/tmp',
            testsuite='extensions',
            log_dir='/log',
            junit=True,
        ).execute()

        mock_run.assert_called_once_with(
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
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run):
        quibble.commands.PhpUnitDatabaseless(
            mw_install_path='/tmp',
            testsuite='extensions',
            log_dir='/log',
            junit=True,
        ).execute()

        mock_run.assert_called_once_with(
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
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run):
        quibble.commands.PhpUnitStandalone(
            mw_install_path='/tmp',
            testsuite=None,
            log_dir='/log',
            repo_path='../extensions/Scribunto',
            junit=True,
        ).execute()

        mock_run.assert_called_once_with(
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
    @mock.patch('quibble.commands.run')
    def test_execute_no_scripts(self, mock_run, mock_load, *_):
        mock_load.return_value = {"requires": {}}

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp', log_dir='/log'
        ).execute()

        mock_run.assert_not_called()

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('quibble.commands.run')
    def test_execute_has_units(self, mock_run, mock_load, *_):
        mock_load.return_value = {"scripts": {"phpunit:unit": {}}}

        quibble.commands.PhpUnitUnit(
            mw_install_path='/tmp',
            log_dir='/log',
            junit=True,
        ).execute()

        mock_run.assert_called_once_with(
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
    @mock.patch('quibble.commands.run')
    def test_execute(self, mock_run, *_):
        def check_env_for_no_sandbox(cmd, env={}, **_):
            assert 'CHROMIUM_FLAGS' in env
            assert '--no-sandbox' in env['CHROMIUM_FLAGS']

        mock_run.side_effect = check_env_for_no_sandbox

        quibble.commands.QunitTests('/tmp', 'http://192.0.2.1:4321').execute()

        assert mock_run.call_count > 0


class ApiTestingTest:
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    @pytest.mark.parametrize(*npm_envs_parameters)
    def test_project_api_testing(
        self,
        mock_driver,
        mock_server,
        mock_run,
        mock_dump,
        mock_load,
        mock_path_exists,
        npm_command_env,
        expected_npm_command,
    ):
        mock_load.return_value = {'scripts': {'api-testing': 'run tests'}}

        with mock_npm_command_env(npm_command_env):
            c = quibble.commands.ApiTesting(
                '/tmp',
                ['mediawiki/core', 'mediawiki/skins/Vector'],
                'http://192.0.2.1:4321',
                'external',
            )
            c.execute()

        mock_run.assert_any_call(
            [expected_npm_command, 'run', 'api-testing'],
            cwd='/tmp',
            env=mock.ANY,
        )

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_missing_api_testing(
        self,
        mock_driver,
        mock_server,
        mock_run,
        mock_dump,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {'scripts': {'other-test': 'foo'}}

        c = quibble.commands.ApiTesting(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'http://192.0.2.1:4321',
            'external',
        )
        c.execute()

        mock_run.assert_not_called()

    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_not_having_package_json(
        self, mock_driver, mock_server, mock_run, mock_dump, mock_load
    ):
        mock_load.return_value = {}

        c = quibble.commands.ApiTesting(
            '/tmp', ['mediawiki/vendor'], 'http://192.0.2.1:4321', 'external'
        )
        c.execute()
        mock_run.assert_not_called()


class BrowserTestsTest:
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    @pytest.mark.parametrize(*npm_envs_parameters)
    def test_project_selenium(
        self,
        mock_driver,
        mock_server,
        mock_run,
        mock_load,
        mock_path_exists,
        npm_command_env,
        expected_npm_command,
    ):
        mock_load.return_value = {
            'scripts': {'selenium-test': 'run that stuff'}
        }

        with mock_npm_command_env(npm_command_env):
            c = quibble.commands.BrowserTests(
                '/tmp',
                ['mediawiki/core', 'mediawiki/skins/Vector'],
                ':0',
                'http://192.0.2.1:4321',
                'php',
            )
            c.execute()

        mock_run.assert_any_call(
            [expected_npm_command, 'run', 'selenium-test'],
            cwd='/tmp',
            env=mock.ANY,
        )
        mock_run.assert_any_call(
            [expected_npm_command, 'run', 'selenium-test'],
            cwd='/tmp/skins/Vector',
            env=mock.ANY,
        )

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('builtins.open', mock.mock_open())
    @mock.patch('json.load')
    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_missing_selenium(
        self,
        mock_driver,
        mock_server,
        mock_run,
        mock_load,
        mock_path_exists,
    ):
        mock_load.return_value = {'scripts': {'other-test': 'foo'}}

        c = quibble.commands.BrowserTests(
            '/tmp',
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            ':0',
            'http://192.0.2.1:4321',
            'php',
        )
        c.execute()

        mock_run.assert_not_called()

    @mock.patch('quibble.commands.run')
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.backend.ChromeWebDriver')
    def test_project_not_having_package_json(
        self, mock_driver, mock_server, mock_run
    ):
        c = quibble.commands.BrowserTests(
            '/tmp',
            ['mediawiki/vendor'],
            ':0',
            'http://192.0.2.1:4321',
            'external',
        )
        c.execute()
        mock_run.assert_not_called()


class UserScriptsTest(unittest.TestCase):
    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('quibble.commands.run')
    def test_commands(self, mock_run, *_):
        quibble.commands.UserScripts(
            '/tmp', ['true', 'false'], 'http://192.0.2.1:9413', 'external'
        ).execute()

        mock_run.assert_has_calls(
            [
                mock.call('true', cwd='/tmp', shell=True, env=mock.ANY),
                mock.call('false', cwd='/tmp', shell=True, env=mock.ANY),
            ]
        )

    @mock.patch('quibble.backend.PhpWebserver')
    @mock.patch('os.environ', clear=True)
    @mock.patch('quibble.commands.run')
    def test_mediawiki_environment_variables(self, mock_run, *_):
        quibble.commands.UserScripts(
            '/tmp', ['true', 'false'], 'http://192.0.2.1:9413', 'external'
        ).execute()

        (args, kwargs) = mock_run.call_args
        env = kwargs.get('env', {})
        self.assertEqual(
            env,
            {
                'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
                'MEDIAWIKI_USER': 'WikiAdmin',
                'MW_SERVER': 'http://192.0.2.1:9413',
                'MW_SCRIPT_PATH': '/',
                'QUIBBLE_APACHE': '1',
            },
        )

    @mock.patch('quibble.backend.PhpWebserver')
    def test_commands_raises_exception_on_error(self, *_):
        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserScripts(
                '/tmp', ['false'], '', 'external'
            ).execute()

        with self.assertRaises(subprocess.CalledProcessError, msg=''):
            quibble.commands.UserScripts(
                '/tmp', ['true', 'false'], '', 'external'
            ).execute()


class EchoCommand:
    def __init__(self, *, fail=False, number=None):
        self.fail = fail
        self.number = number

    def execute(self):
        logging.error("log line")
        print("stdout line")
        print("stderr line", file=sys.stderr)

        if self.number:
            print("I am {}.".format(self.number))
        if self.fail:
            print("then fail")
            raise Exception("bad")


class InvalidUnicodeCommand:
    invalid_unicode = b"with invalid unicode: \x80abc"

    def execute(self):
        sys.stdout.buffer.write(b"stdout " + self.invalid_unicode)
        sys.stderr.buffer.write(b"stderr " + self.invalid_unicode)


def sequential_pool():
    pool = mock.MagicMock()
    pool.return_value.__enter__.return_value.imap_unordered.side_effect = (
        lambda executor, tasks: [executor(x) for x in tasks]
    )
    return pool


# This is a regular function to benefit from pytest builtin fixtures tmp_path
# and caplog.
@mock.patch('subprocess.check_call')
@mock.patch('subprocess.check_output')
def test_GitClean(check_output, run, tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    # Simulate a dirty git workspace even after git clean ran
    check_output.return_value = '!! composer.lock\n' '!! vendor\n'

    quibble.commands.GitClean(tmp_path).execute()

    run.assert_called_with(['git', 'clean', '-xqdf'], cwd=tmp_path)
    check_output.assert_called_with(
        ['git', 'status', '--ignored', '--porcelain'],
        cwd=tmp_path,
        universal_newlines=True,
    )
    assert [rec.message for rec in caplog.records] == [
        mock.ANY,
        '!! composer.lock',
        '!! vendor',
        mock.ANY,
    ]


@mock.patch('subprocess.Popen')
def test_run_handles_invalid_unicode(mock_popen, capfdbinary):
    invalid_unicode = InvalidUnicodeCommand.invalid_unicode

    context = mock_popen.return_value.__enter__.return_value
    context.stdout = io.BytesIO(InvalidUnicodeCommand.invalid_unicode)
    context.returncode = 1

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        quibble.commands.run('fake', cwd='/tmp')

    assert exc_info.value.output == invalid_unicode.decode(
        errors='backslashreplace'
    ), 'CalledProcessError has backslashed valid unicode output'
    assert (
        capfdbinary.readouterr().out == invalid_unicode
    ), 'raw binary is emitted to stdout'


class ParallelTest(unittest.TestCase):
    def test_init(self):
        p = quibble.commands.Parallel(steps=range(3))
        self.assertEqual(3, len(p.steps))

    @mock.patch('multiprocessing.Pool')
    def test_execute_empty(self, mock_pool):
        quibble.commands.Parallel(steps=[]).execute()
        mock_pool.assert_not_called()

    @mock.patch('multiprocessing.Pool')
    def test_execute_single(self, mock_pool):
        command = mock.MagicMock()
        quibble.commands.Parallel(steps=[command]).execute()
        self.assertTrue(command.execute.called)
        mock_pool.assert_not_called()

    @mock.patch('multiprocessing.Pool', new_callable=sequential_pool)
    def test_execute_parallel(self, mock_pool):
        command1 = mock.MagicMock()
        command1.execute.return_value = None
        command2 = mock.MagicMock()
        command2.execute.return_value = None
        quibble.commands.Parallel(steps=[command1, command2]).execute()
        self.assertTrue(mock_pool.called)
        self.assertTrue(command1.execute.called)
        self.assertTrue(command2.execute.called)

    def test_execute_parallel_error(self):
        command1 = mock.MagicMock()
        command1.execute.return_value = None
        command2 = mock.MagicMock()
        command2.execute.side_effect = Exception("bad")
        with self.assertRaises(Exception, msg="bad"):
            quibble.commands.Parallel(steps=[command1, command2]).execute()
        # TODO: also test that we short-circuit all children after any failure.

    @broken_on_macos
    @mock.patch('quibble.commands.log')
    def test_parallel_captures_logging(self, mock_log):
        quibble.commands.Parallel(
            steps=[
                EchoCommand(number=1),
                EchoCommand(number=2),
                EchoCommand(number=3),
            ]
        ).execute()

        # TODO:
        #  * assert that log level filters are inherited from parent process.
        mock_log.info.assert_any_call(
            "log line\nstdout line\nstderr line\nI am 1.\n"
        )
        mock_log.info.assert_any_call(
            "log line\nstdout line\nstderr line\nI am 2.\n"
        )
        mock_log.info.assert_any_call(
            "log line\nstdout line\nstderr line\nI am 3.\n"
        )

    @broken_on_macos
    @mock.patch('quibble.commands.log')
    def test_parallel_captures_logging_despite_failure(self, mock_log):
        with self.assertRaises(Exception, msg="bad"):
            quibble.commands.Parallel(
                steps=[EchoCommand(), EchoCommand(fail=True)]
            ).execute()

        mock_log.info.assert_any_call(
            "log line\nstdout line\nstderr line\nthen fail\n"
        )

    @mock.patch('quibble.commands.log')
    @broken_on_macos
    def test_parallel_run_child_handles_invalid_unicode(self, mock_log):
        p = quibble.commands.Parallel(
            steps=[
                InvalidUnicodeCommand(),
                InvalidUnicodeCommand(),
            ]
        )
        p.execute()

        mock_log.info.assert_called_with(
            "stdout with invalid unicode: \\x80abc"
            "stderr with invalid unicode: \\x80abc"
        )


class SuccessCacheTest(unittest.TestCase):
    @mock.patch('git.Repo')
    @mock.patch('quibble.zuul.working_trees')
    @mock.patch('quibble.commands.log')
    def test_check_execute_miss(self, mock_log, mock_zuul_trees, mock_repo):
        mock_tree = mock.Mock(return_value=mock.Mock(**{'hexsha': 'abc123'}))
        mock_repo.return_value = mock.Mock(**{'tree': mock_tree})

        mock_zuul_trees.return_value = {
            'extensions/Foo': '/mw/src/extensions/Foo',
        }

        mock_cache_client = mock.Mock(**{'get': mock.Mock(return_value=None)})

        quibble.commands.SuccessCache(
            mock_cache_client,
            '/mw/src',
            ['extensions/Foo'],
            key_data=['foo-key'],
        ).check_command().execute()

        mock_repo.assert_called_with('/mw/src/extensions/Foo')
        mock_tree.assert_called_with('HEAD')

        sha256 = hashlib.new('sha256')
        sha256.update(b'foo-key')
        sha256.update(b'abc123')
        digest = sha256.hexdigest()
        key = 'successcache/%s' % digest

        mock_cache_client.get.assert_called_with(key)
        mock_log.info.assert_any_call('Success cache: MISS')

    @mock.patch('git.Repo')
    @mock.patch('quibble.zuul.working_trees')
    @mock.patch('quibble.commands.log')
    def test_check_execute_hit(self, mock_log, mock_zuul_trees, mock_repo):
        mock_tree = mock.Mock(return_value=mock.Mock(**{'hexsha': 'abc123'}))
        mock_repo.return_value = mock.Mock(**{'tree': mock_tree})

        mock_zuul_trees.return_value = {
            'extensions/Foo': '/mw/src/extensions/Foo',
        }

        mock_cache_client = mock.Mock(**{'get': mock.Mock(return_value='')})

        with pytest.raises(quibble.commands.SuccessCache.Hit):
            quibble.commands.SuccessCache(
                mock_cache_client,
                '/mw/src',
                ['extensions/Foo'],
                key_data=['foo-key'],
            ).check_command().execute()

        mock_repo.assert_called_with('/mw/src/extensions/Foo')
        mock_tree.assert_called_with('HEAD')

        sha256 = hashlib.new('sha256')
        sha256.update(b'foo-key')
        sha256.update(b'abc123')
        digest = sha256.hexdigest()
        key = 'successcache/%s' % digest

        mock_cache_client.get.assert_called_with(key)
        mock_log.info.assert_any_call('Success cache: HIT')

    @mock.patch('git.Repo')
    @mock.patch('quibble.zuul.working_trees')
    def test_save_execute(self, mock_zuul_trees, mock_repo):
        mock_tree = mock.Mock(return_value=mock.Mock(**{'hexsha': 'abc123'}))
        mock_repo.return_value = mock.Mock(**{'tree': mock_tree})

        mock_zuul_trees.return_value = {
            'extensions/Foo': '/mw/src/extensions/Foo',
        }

        mock_cache_client = mock.Mock(**{'set': mock.Mock()})

        quibble.commands.SuccessCache(
            mock_cache_client,
            '/mw/src',
            ['extensions/Foo'],
            key_data=['foo-key'],
        ).save_command().execute()

        mock_repo.assert_called_with('/mw/src/extensions/Foo')
        mock_tree.assert_called_with('HEAD')

        sha256 = hashlib.new('sha256')
        sha256.update(b'foo-key')
        sha256.update(b'abc123')
        digest = sha256.hexdigest()
        key = 'successcache/%s' % digest

        mock_cache_client.set.assert_called_with(key, '')


class ResolveRequires(unittest.TestCase):
    @mock.patch('quibble.mediawiki.registry')
    @mock.patch('quibble.zuul.clone')
    def test_clone_logs_list_of_projects(self, _clone, _registry):
        _registry.from_path.return_value.getRequiredRepos.side_effect = [
            set(['p1']),
            [],
        ]

        zuul_params = {
            'branch': 'master',
            'cache_dir': None,
            'project_branch': None,
            'workers': 7,
            'workspace': '/workspace',
            'zuul_branch': 'master',
            'zuul_newrev': 'C0FFEE',
            'zuul_project': 'mediawiki/core',
            'zuul_ref': 'refs/zuul/Zbaba',
            'zuul_url': 'git://merger.example.org',
        }
        clone = quibble.commands.ResolveRequires(
            '/mw/src',
            ['mediawiki/extensions/CirrusSearch'],
            zuul_params,
        )

        with self.assertLogs('quibble.commands', level='INFO') as log:
            quibble.commands.execute_command(clone)
            print("\n".join(log.output))
            assert '"projects": ["p1"]' in log.records[4].message
