#!/usr/bin/env python3

import logging
import os
import subprocess
from unittest import mock

from quibble import cli
from quibble.cli import MultipleChoices, default_stages
import quibble.commands

import pytest


class TestMultipleChoices:
    def test_init(self):
        # It is really just like a list
        assert MultipleChoices() == []
        assert MultipleChoices(['a']) == ['a']
        assert MultipleChoices('a') == ['a']

    def test_contains_for_a_single_item(self):
        subject = MultipleChoices(['a', 'b'])
        assert 'a' in subject
        assert 'c' not in subject

    def test_contains_for_matching_list(self):
        subject = MultipleChoices(['a', 'b'])

        # should probably be false but it is a subset
        assert [] in subject

        assert ['a'] in subject
        assert ['b'] in subject
        assert ['a', 'b'] in subject
        assert ['b', 'a'] in subject

    def test_contains_for_mismatching_lists(self):
        subject = MultipleChoices(['a', 'b'])
        assert ['c'] not in subject
        assert ['a' not in 'c'], subject
        assert ['a' not in 'b', 'c'], subject


class TestCli:
    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone(self):
        q = cli.QuibbleCli()
        assert q._repos_to_clone(
            projects=[], zuul_project=None, clone_vendor=False
        ) == [
            'mediawiki/core',
            'mediawiki/skins/Vector',
        ], 'Incorrect repos to clone'

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_with_vendor(self):
        q = cli.QuibbleCli()
        assert q._repos_to_clone(
            projects=[], zuul_project=None, clone_vendor=True
        ) == [
            'mediawiki/core',
            'mediawiki/skins/Vector',
            'mediawiki/vendor',
        ], 'Incorrect repos to clone'

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_appends_projects(self):
        q = cli.QuibbleCli()

        assert q._repos_to_clone(
            projects=[
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
            ],
            zuul_project=None,
            clone_vendor=False,
        ) == [
            'mediawiki/core',
            'mediawiki/extensions/BoilerPlate',
            'mediawiki/extensions/Example',
            'mediawiki/skins/Vector',
        ]

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_deduplicates(self):
        q = cli.QuibbleCli()
        assert q._repos_to_clone(
            projects=[
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
            ],
            zuul_project='mediawiki/extensions/Example',
            clone_vendor=False,
        ) == [
            'mediawiki/core',
            'mediawiki/extensions/BoilerPlate',
            'mediawiki/extensions/Example',
            'mediawiki/skins/Vector',
        ]

    def test_repos_to_clone_with_env(self):
        env = {
            'SKIN_DEPENDENCIES': 'mediawiki/skins/Monobook',
            'EXT_DEPENDENCIES': (
                'mediawiki/extensions/One\\nmediawiki/extensions/Two'
            ),
        }
        with mock.patch.dict('os.environ', env, clear=True):
            q = cli.QuibbleCli()
            assert q._repos_to_clone(
                projects=[], zuul_project=None, clone_vendor=False
            ) == [
                'mediawiki/core',  # must be first
                'mediawiki/extensions/One',
                'mediawiki/extensions/Two',
                'mediawiki/skins/Monobook',
                'mediawiki/skins/Vector',
            ]

    def test_env_dependencies_log_a_warning(self, caplog):
        env = {
            'EXT_DEPENDENCIES': '',
            'SKIN_DEPENDENCIES': '',
        }
        with mock.patch.dict('os.environ', env, clear=True):
            with caplog.at_level(logging.WARNING, logger='quibble.cli'):
                q = cli.QuibbleCli()
                q._repos_to_clone(
                    projects=[], zuul_project=None, clone_vendor=False
                )

        msg = 'env variable is deprecated. Instead pass projects as arguments.'
        assert caplog.record_tuples == [
            ('quibble.cli', logging.WARNING, 'SKIN_DEPENDENCIES ' + msg),
            ('quibble.cli', logging.WARNING, 'EXT_DEPENDENCIES ' + msg),
        ]

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_args_defaults(self, _):
        args = cli._parse_arguments([])

        assert args.git_cache == 'ref'
        assert os.getcwd() == args.workspace
        assert args.log_dir == 'log'

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_args_defaults_in_docker(self, _):
        args = cli._parse_arguments([])

        assert args.git_cache == '/srv/git'
        assert args.workspace == '/workspace'

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment(self):
        q = cli.QuibbleCli()

        with mock.patch('quibble.is_in_docker', return_value=True):
            # In Docker we always use self.workspace
            q._setup_environment(
                workspace='/testworkspace',
                mw_install_path='',
                log_dir='',
                tmp_dir='',
            )
            assert os.environ['WORKSPACE'] == '/testworkspace'
            with mock.patch.dict(
                os.environ, {'WORKSPACE': '/fromenv'}, clear=True
            ):
                # In Docker, ignore $WORKSPACE
                q._setup_environment(
                    workspace='/testworkspace',
                    mw_install_path='',
                    log_dir='',
                    tmp_dir='',
                )
                assert os.environ['WORKSPACE'] == '/testworkspace'

        with mock.patch('quibble.is_in_docker', return_value=False):
            q._setup_environment(
                workspace='/testworkspace',
                mw_install_path='',
                log_dir='',
                tmp_dir='',
            )
            assert os.environ['WORKSPACE'] == '/testworkspace'

            with mock.patch.dict(
                os.environ, {'WORKSPACE': '/fromenv'}, clear=True
            ):
                # When not in Docker, we honor $WORKSPACE
                q._setup_environment(
                    workspace='/testworkspace',
                    mw_install_path='',
                    log_dir='',
                    tmp_dir='',
                )
                assert os.environ['WORKSPACE'] == '/fromenv'

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment_has_log_directories(self):
        q = cli.QuibbleCli()

        q._setup_environment(
            workspace='/workspace',
            mw_install_path='',
            log_dir='/mylog',
            tmp_dir='',
        )

        assert 'LOG_DIR' in os.environ
        assert 'MW_LOG_DIR' in os.environ
        assert os.environ['LOG_DIR'] == '/mylog'
        assert os.environ['MW_LOG_DIR'] == '/mylog'

    def test_should_run_accepts_all_stages_by_default(self):
        q = cli.QuibbleCli()
        args = cli._parse_arguments(args=[])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        assert stages == default_stages, 'must runs all stages by default'

    def test_should_run_skippall_runs_no_stage(self):
        q = cli.QuibbleCli()
        args = cli._parse_arguments(args=['--skip', 'all'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        assert stages == [], '--skip=all skips all stages'

    @mock.patch('quibble.cli.default_stages', ['foo', 'phpunit'])
    def test_should_run_skips_a_stage(self):
        q = cli.QuibbleCli()
        args = cli._parse_arguments(args=['--skip', 'phpunit'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        assert stages == ['foo'], '--skip skips the stage'

    def test_should_run_running_a_single_stage(self):
        q = cli.QuibbleCli()
        args = cli._parse_arguments(args=['--run', 'phpunit'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        assert stages == ['phpunit'], '--run runs exactly the given stage'

    def test_command_skip_all_stages(self):
        q = cli.QuibbleCli()
        args = cli._parse_arguments(args=['-c', '/bin/true'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        assert stages == [], 'User command must skip all stages'

    def test_run_option_is_comma_separated(self):
        args = cli._parse_arguments(args=['--run=phpunit,qunit'])
        assert args.run == ['phpunit', 'qunit']

    def test_run_option_multiple_times(self):
        args = cli._parse_arguments(args=['--run=npm-test', '--run=phpunit'])
        assert args.run == ['npm-test', 'phpunit']

    def test_run_option_does_not_shallow_next_arg(self):
        args = cli._parse_arguments(args=['--run', 'phpunit', 'repo'])
        assert args.run == ['phpunit']
        assert args.projects == ['repo']

    def test_skip_option_is_comma_separated(self):
        args = cli._parse_arguments(args=['--skip=phpunit,qunit'])
        assert args.skip == ['phpunit', 'qunit']

    def test_skip_option_multiple_times(self):
        args = cli._parse_arguments(args=['--skip=qunit', '--skip=selenium'])
        assert args.skip == ['qunit', 'selenium']

    def test_skip_option_does_not_shallow_next_arg(self):
        args = cli._parse_arguments(args=['--skip', 'phpunit', 'repo'])
        assert args.skip == ['phpunit']
        assert args.projects == ['repo']

    def test_command_does_not_shallow_next_arg(self):
        args = cli._parse_arguments(args=['--command', '/bin/true', 'repo'])
        assert args.commands == ['/bin/true']
        assert args.projects == ['repo']

    def test_command_used_multiple_times(self):
        args = cli._parse_arguments(args=['-c', 'true', '-c', 'false'])
        assert args.commands == ['true', 'false']

    @mock.patch.dict('os.environ', {'SHELL': '/bin/somesh'}, clear=True)
    def test_parse_arguments_has_shell_setting_commands(self):
        args = cli._parse_arguments(args=['--shell'])
        assert args.commands == ['/bin/somesh']

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.cli.QuibbleCli')
    def test_shell_option_sets_commands(self, QuibbleCli):
        user_shell = '/bin/magicsh'
        env = {
            'SHELL': user_shell,
        }
        with mock.patch.dict('os.environ', env, clear=True):
            with mock.patch('sys.argv', ['quibble', '--shell']):
                QuibbleCli().build_execution_plan.return_value = ('', [])
                cli.main()

                args = QuibbleCli().build_execution_plan.call_args[0][0]
                assert args.shell == [user_shell]
                assert args.commands == [user_shell]

    @mock.patch('quibble.cli.QuibbleCli')
    def test_shell_option_with_no_shell_enviroment_variable(self, QuibbleCli):
        with mock.patch.dict('os.environ', clear=True):
            with mock.patch('sys.argv', ['quibble', '--shell']):
                QuibbleCli().build_execution_plan.return_value = ('', [])
                cli.main()
                args = QuibbleCli().build_execution_plan.call_args[0][0]
                assert args.shell == ['bash']

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.commands.execute_command')
    def test_user_command_non_zero_exit_status_raises(self, execute_command):
        execute_command.side_effect = subprocess.CalledProcessError(
            3, 'Command failed'
        )
        with mock.patch('sys.argv', ['quibble', '-c', 'somecommand']):
            with pytest.raises(
                subprocess.CalledProcessError,
                match='Command failed',
            ):
                cli.main()

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.commands.execute_command')
    def test_shell_non_zero_exit_status_does_not_raise(self, execute_command):
        execute_command.side_effect = subprocess.CalledProcessError(
            2, 'Shell failed'
        )
        user_shell = '/bin/magicsh'
        env = {
            'SHELL': user_shell,
        }
        with mock.patch.dict('os.environ', env, clear=True):
            with mock.patch('sys.argv', ['quibble', '--shell']):
                cli.main()

    def test_project_branch_arg(self):
        args = cli._parse_arguments(args=[])
        assert args.project_branch == []

    def test_build_execution_plan(self):
        args = cli._parse_arguments(args=[])
        project_dir, plan = cli.QuibbleCli().build_execution_plan(args)

        assert isinstance(plan[0], quibble.commands.ReportDurations)
        assert isinstance(plan[1], quibble.commands.ReportVersions)
        assert isinstance(plan[2], quibble.commands.EnsureDirectory)

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.commands.execute_command')
    def test_main_execute_build_plan_without_dry_run(self, execute_command):
        with mock.patch('sys.argv', ['quibble']):
            cli.main()

        assert (
            execute_command.call_count > 2
        ), 'execute_command must have been called'

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.commands.execute_command')
    def test_main_execute_build_plan_with_dry_run(self, execute_command):
        with mock.patch('sys.argv', ['quibble', '--dry-run']):
            cli.main()
        execute_command.assert_not_called()

    @mock.patch.dict('os.environ', clear=True)
    @mock.patch('quibble.commands.execute_command')
    def test_main_succeed_on_Success_Cache_Hit_exception(
        self, execute_command
    ):
        execute_command.side_effect = quibble.commands.SuccessCache.Hit()
        with mock.patch('sys.argv', ['quibble']):
            cli.main()

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_adds_ZUUL_PROJECT(self, _):
        env = {'ZUUL_PROJECT': 'mediawiki/extensions/ZuulProjectEnvVar'}
        with mock.patch.dict('os.environ', env, clear=True):
            q = cli.QuibbleCli()
            args = cli._parse_arguments(args=['--packages-source=composer'])
            with mock.patch('quibble.commands.ZuulClone') as mock_clone:
                q.build_execution_plan(args)
        assert mock_clone.call_args[1]['projects'] == [
            'mediawiki/core',  # must be first
            'mediawiki/extensions/ZuulProjectEnvVar',
            'mediawiki/skins/Vector',
        ]

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_does_not_duplicate_hardcoded_repos(self, _):
        hardcoded_repos = [
            'mediawiki/core',
            'mediawiki/skins/Vector',
        ]

        for repo in hardcoded_repos:
            q = cli.QuibbleCli()
            args = cli._parse_arguments(args=['--packages-source=composer'])
            with mock.patch.dict(
                'os.environ', {'ZUUL_PROJECT': repo}, clear=True
            ):
                with mock.patch('quibble.commands.ZuulClone') as mock_clone:
                    q.build_execution_plan(args)
            assert mock_clone.call_args[1]['projects'] == [
                'mediawiki/core',  # must be first
                'mediawiki/skins/Vector',
            ]

    def test_build_execution_plan_with_success_cache(self):
        args = cli._parse_arguments(
            args=[
                '--memcached=cache.example:11211',
                '--success-cache-key-data=foo',
            ]
        )
        _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert args.success_cache_key_data == ['foo']
        assert isinstance(plan[5], quibble.commands.SuccessCache.Check)
        assert isinstance(plan[-1], quibble.commands.SuccessCache.Save)
        assert plan[-1].cache.client._client.server == ('cache.example', 11211)

    def test_build_execution_plan_shell_does_not_report_duration(self):
        args = cli._parse_arguments(args=['--shell'])
        _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert quibble.commands.ReportDurations not in [
            type(step) for step in plan
        ]
        assert isinstance(plan[0], quibble.commands.ReportVersions)

    def test_build_execution_plan_user_command_does_report_duration(self):
        args = cli._parse_arguments(args=['-c', '/bin/true'])
        _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert isinstance(plan[0], quibble.commands.ReportDurations)

    @staticmethod
    def _plan_step_types(plan):
        # NpmInstall is appended to a Parallel() block rather than the
        # top-level plan, so walk one level into any step exposing .steps.
        types = []
        for step in plan:
            types.append(type(step))
            types.extend(type(sub) for sub in getattr(step, 'steps', []))
        return types

    def test_user_command_triggers_npm_install(self):
        args = cli._parse_arguments(args=['-c', '/bin/true'])
        _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert quibble.commands.NpmInstall in self._plan_step_types(plan)

    def test_skip_npm_install_removes_npm_install_step(self):
        args = cli._parse_arguments(
            args=['-c', '/bin/true', '--skip-npm-install']
        )
        _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert quibble.commands.NpmInstall not in self._plan_step_types(plan)

    def test_skip_npm_install_keeps_composer_dependencies(self):
        # Unlike --skip-deps, the composer install must remain in the plan.
        args = cli._parse_arguments(
            args=[
                '--packages-source=composer',
                '-c',
                '/bin/true',
                '--skip-npm-install',
            ]
        )
        with mock.patch('quibble.commands.ZuulClone'):
            _, plan = cli.QuibbleCli().build_execution_plan(args)

        assert (
            quibble.commands.NativeComposerDependencies
            in self._plan_step_types(plan)
        )

    def test_skip_lock_check_for_patches_to_vendor(self):
        with mock.patch.dict(
            'os.environ', {'ZUUL_PROJECT': 'mediawiki/vendor'}, clear=True
        ):
            q = cli.QuibbleCli()
            args = cli._parse_arguments(['--packages-source', 'vendor'])
            with mock.patch('quibble.commands.ZuulClone'):
                q.build_execution_plan(args)
            assert 'MW_SKIP_EXTERNAL_DEPENDENCIES' in os.environ
            assert os.environ['MW_SKIP_EXTERNAL_DEPENDENCIES'] == '1'

    def test_skip_lock_check_for_patches_to_core_with_vendor(self):
        with mock.patch.dict(
            'os.environ', {'ZUUL_PROJECT': 'mediawiki/core'}, clear=True
        ):
            q = cli.QuibbleCli()
            args = cli._parse_arguments(['--packages-source', 'vendor'])
            with mock.patch('quibble.commands.ZuulClone'):
                q.build_execution_plan(args)
            assert 'MW_SKIP_EXTERNAL_DEPENDENCIES' not in os.environ

    def test_skip_lock_check_for_patches_to_core_with_composer(self):
        with mock.patch.dict(
            'os.environ', {'ZUUL_PROJECT': 'mediawiki/core'}, clear=True
        ):
            q = cli.QuibbleCli()
            args = cli._parse_arguments(['--packages-source', 'composer'])
            with mock.patch('quibble.commands.ZuulClone'):
                q.build_execution_plan(args)
            assert 'MW_SKIP_EXTERNAL_DEPENDENCIES' not in os.environ
            # Ensure setup_environment applied
            assert 'LOG_DIR' in os.environ

    def test_build_execution_plan_with_change_option_injects_zuul_env(self):
        zuul_env = {
            'ZUUL_URL': 'git://zuulmerger.example.org',
            'ZUUL_PROJECT': 'mediawiki/core',
            'ZUUL_BRANCH': 'tartempion',
            'ZUUL_REF': 'refs/changes/99/12345',
        }
        with mock.patch.dict('os.environ', clear=True):
            q = cli.QuibbleCli()
            args = cli._parse_arguments(['--change', '12345,99'])
            with mock.patch('quibble.util.FetchInfo') as fetchinfo:
                fetchinfo.change.return_value.asZuulEnv.return_value = zuul_env
                q.build_execution_plan(args)
                fetchinfo.change.assert_called_once_with('12345', '99')
            assert dict(os.environ).items() > zuul_env.items()

    def test_execute(self, caplog):
        q = cli.QuibbleCli()

        with caplog.at_level(logging.DEBUG):
            q.execute([], '/workspace/src')

        assert caplog.record_tuples[0] == (
            'quibble.cli',
            logging.DEBUG,
            'Project dir: /workspace/src',
        )

    def test_execute_reraise_SuccessCache_Hit(self):
        q = cli.QuibbleCli()

        successCacheHitCmd = mock.MagicMock()
        successCacheHitCmd.execute.side_effect = (
            quibble.commands.SuccessCache.Hit()
        )

        with pytest.raises(quibble.commands.SuccessCache.Hit):
            q.execute([successCacheHitCmd], '/workspace/src')

    def test_execute_called_process_error_calls_earlywarns(self):
        failingCmd = mock.MagicMock()
        failingCmd.execute.side_effect = subprocess.CalledProcessError(
            42, 'fail'
        )
        failingCmd.__str__.return_value = '<FailingCmdMock>'

        otherCmd = mock.MagicMock()

        plan = [
            failingCmd,
            otherCmd,
        ]

        with pytest.raises(
            subprocess.CalledProcessError,
            match="Command 'fail' returned non-zero exit status 42",
        ):
            with mock.patch('quibble.cli.QuibbleCli.earlywarn'):
                quibbleCmd = cli.QuibbleCli()
                quibbleCmd.execute(plan, '/tmp')
                assert quibbleCmd.earlywarn.assert_called_once()
                assert otherCmd.assert_not_called, 'build plan must be aborted'
