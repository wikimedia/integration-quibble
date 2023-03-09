#!/usr/bin/env python3

import os
import unittest
from unittest import mock

from quibble import cmd
from quibble.cmd import MultipleChoices, default_stages
import quibble.commands


class MultipleChoicesTest(unittest.TestCase):
    def test_init(self):
        # It is really just like a list
        self.assertEqual([], MultipleChoices())
        self.assertEqual(['a'], MultipleChoices(['a']))
        self.assertEqual(['a'], MultipleChoices('a'))

    def test_contains_for_a_single_item(self):
        subject = MultipleChoices(['a', 'b'])
        self.assertIn('a', subject)
        self.assertNotIn('c', subject)

    def test_contains_for_matching_list(self):
        subject = MultipleChoices(['a', 'b'])

        # should probably be false but it is a subset
        self.assertIn([], subject)

        self.assertIn(['a'], subject)
        self.assertIn(['b'], subject)
        self.assertIn(['a', 'b'], subject)
        self.assertIn(['b', 'a'], subject)

    def test_contains_for_mismatching_lists(self):
        subject = MultipleChoices(['a', 'b'])
        self.assertNotIn(['c'], subject)
        self.assertNotIn(['a', 'c'], subject)
        self.assertNotIn(['a', 'b', 'c'], subject)


class CmdTest(unittest.TestCase):
    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q._repos_to_clone(
                projects=[], zuul_project=None, clone_vendor=False
            ),
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'Incorrect repos to clone',
        )

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_with_vendor(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q._repos_to_clone(
                projects=[], zuul_project=None, clone_vendor=True
            ),
            ['mediawiki/core', 'mediawiki/skins/Vector', 'mediawiki/vendor'],
            'Incorrect repos to clone',
        )

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_appends_projects(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q._repos_to_clone(
                projects=[
                    'mediawiki/extensions/BoilerPlate',
                    'mediawiki/extensions/Example',
                ],
                zuul_project=None,
                clone_vendor=False,
            ),
            [
                'mediawiki/core',
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
                'mediawiki/skins/Vector',
            ],
        )

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_deduplicates(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q._repos_to_clone(
                projects=[
                    'mediawiki/extensions/BoilerPlate',
                    'mediawiki/extensions/Example',
                ],
                zuul_project='mediawiki/extensions/Example',
                clone_vendor=False,
            ),
            [
                'mediawiki/core',
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
                'mediawiki/skins/Vector',
            ],
        )

    def test_repos_to_clone_with_env(self):
        env = {
            'SKIN_DEPENDENCIES': 'mediawiki/skins/Monobook',
            'EXT_DEPENDENCIES': (
                'mediawiki/extensions/One\\nmediawiki/extensions/Two'
            ),
        }
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            self.assertEqual(
                [
                    'mediawiki/core',  # must be first
                    'mediawiki/extensions/One',
                    'mediawiki/extensions/Two',
                    'mediawiki/skins/Monobook',
                    'mediawiki/skins/Vector',
                ],
                q._repos_to_clone(
                    projects=[], zuul_project=None, clone_vendor=False
                ),
            )

    def test_env_dependencies_log_a_warning(self):
        env = {
            'EXT_DEPENDENCIES': '',
            'SKIN_DEPENDENCIES': '',
        }
        with mock.patch.dict('os.environ', env, clear=True):
            with self.assertLogs('quibble.cmd', level='WARNING') as log:
                q = cmd.QuibbleCmd()
                q._repos_to_clone(
                    projects=[], zuul_project=None, clone_vendor=False
                )

        self.assertRegex(
            log.output[0], '^WARNING:quibble.cmd:SKIN_DEPENDENCIES'
        )
        self.assertRegex(
            log.output[1], '^WARNING:quibble.cmd:EXT_DEPENDENCIES'
        )

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_args_defaults(self, _):
        args = cmd._parse_arguments([])

        self.assertEqual('ref', args.git_cache)
        self.assertEqual(os.getcwd(), args.workspace)
        self.assertEqual('log', args.log_dir)

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_args_defaults_in_docker(self, _):
        args = cmd._parse_arguments([])

        self.assertEqual('/srv/git', args.git_cache)
        self.assertEqual('/workspace', args.workspace)

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment_mw_quibble_ci(self):
        q = cmd.QuibbleCmd()
        q._setup_environment(
            workspace='/testworkspace',
            mw_install_path='',
            log_dir='',
            tmp_dir='',
        )
        self.assertEqual(os.environ['MW_QUIBBLE_CI'], '1')

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment(self):
        q = cmd.QuibbleCmd()

        with mock.patch('quibble.is_in_docker', return_value=True):
            # In Docker we always use self.workspace
            q._setup_environment(
                workspace='/testworkspace',
                mw_install_path='',
                log_dir='',
                tmp_dir='',
            )
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')
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
                self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

        with mock.patch('quibble.is_in_docker', return_value=False):
            q._setup_environment(
                workspace='/testworkspace',
                mw_install_path='',
                log_dir='',
                tmp_dir='',
            )
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

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
                self.assertEqual(os.environ['WORKSPACE'], '/fromenv')

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment_has_log_directories(self):
        q = cmd.QuibbleCmd()

        q._setup_environment(
            workspace='/workspace',
            mw_install_path='',
            log_dir='/mylog',
            tmp_dir='',
        )

        self.assertIn('LOG_DIR', os.environ)
        self.assertIn('MW_LOG_DIR', os.environ)
        self.assertEqual(os.environ['LOG_DIR'], '/mylog')
        self.assertEqual(os.environ['MW_LOG_DIR'], '/mylog')

    def test_should_run_accepts_all_stages_by_default(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=[])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual(
            default_stages, stages, 'must runs all stages by default'
        )

    def test_should_run_runall_accepts_all_stages(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['--run', 'all'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual(default_stages, stages, '--run=all runs all stages')

    def test_should_run_skippall_runs_no_stage(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['--skip', 'all'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual([], stages, '--skip=all skips all stages')

    @mock.patch('quibble.cmd.default_stages', ['foo', 'phpunit'])
    def test_should_run_skips_a_stage(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['--skip', 'phpunit'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual(['foo'], stages, '--skip skips the stage')

    def test_should_run_runall_and_skip_play_nice(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['--run', 'all', '--skip', 'phpunit'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        expected_stages = default_stages.copy()
        expected_stages.remove('phpunit')
        self.assertEqual(expected_stages, stages, '--run=all respects --skip')

    def test_should_run_running_a_single_stage(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['--run', 'phpunit'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual(
            ['phpunit'], stages, '--run runs exactly the given stage'
        )

    def test_command_skip_all_stages(self):
        q = cmd.QuibbleCmd()
        args = cmd._parse_arguments(args=['-c', '/bin/true'])
        stages = q._stages_to_run(args.run, args.skip, args.commands)
        self.assertEqual([], stages, 'User command must skip all stages')

    def test_run_option_is_comma_separated(self):
        args = cmd._parse_arguments(args=['--run=phpunit,qunit'])
        self.assertEqual(['phpunit', 'qunit'], args.run)

    def test_run_option_does_not_shallow_next_arg(self):
        args = cmd._parse_arguments(args=['--run', 'phpunit', 'repo'])
        self.assertEqual(['phpunit'], args.run)
        self.assertEqual(['repo'], args.projects)

    def test_skip_option_is_comma_separated(self):
        args = cmd._parse_arguments(args=['--skip=phpunit,qunit'])
        self.assertEqual(['phpunit', 'qunit'], args.skip)

    def test_skip_option_does_not_shallow_next_arg(self):
        args = cmd._parse_arguments(args=['--skip', 'phpunit', 'repo'])
        self.assertEqual(['phpunit'], args.skip)
        self.assertEqual(['repo'], args.projects)

    def test_command_does_not_shallow_next_arg(self):
        args = cmd._parse_arguments(args=['--command', '/bin/true', 'repo'])
        self.assertEqual(['/bin/true'], args.commands)
        self.assertEqual(['repo'], args.projects)

    def test_command_used_multiple_times(self):
        args = cmd._parse_arguments(args=['-c', 'true', '-c', 'false'])
        self.assertEqual(['true', 'false'], args.commands)

    def test_project_branch_arg(self):
        args = cmd._parse_arguments(args=[])
        self.assertEqual([], args.project_branch)

    def test_build_execution_plan(self):
        args = cmd._parse_arguments(args=[])
        project_dir, plan = cmd.QuibbleCmd().build_execution_plan(args)

        self.assertIsInstance(plan[0], quibble.commands.ReportVersions)
        self.assertIsInstance(plan[1], quibble.commands.EnsureDirectory)

    @mock.patch('quibble.commands.execute_command')
    def test_main_execute_build_plan_without_dry_run(self, execute_command):
        with mock.patch('sys.argv', ['quibble']):
            cmd.main()

        self.assertGreater(
            execute_command.call_count,
            2,
            'execute_command must have been called',
        )

    @mock.patch('quibble.commands.execute_command')
    def test_main_execute_build_plan_with_dry_run(self, execute_command):
        with mock.patch('sys.argv', ['quibble', '--dry-run']):
            cmd.main()
        execute_command.assert_not_called()

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_adds_ZUUL_PROJECT(self, _):
        env = {'ZUUL_PROJECT': 'mediawiki/extensions/ZuulProjectEnvVar'}
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            args = cmd._parse_arguments(args=['--packages-source=composer'])
            with mock.patch('quibble.commands.ZuulClone') as mock_clone:
                q.build_execution_plan(args)
        self.assertEqual(
            [
                'mediawiki/core',  # must be first
                'mediawiki/extensions/ZuulProjectEnvVar',
                'mediawiki/skins/Vector',
            ],
            mock_clone.call_args[1]['projects'],
        )

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_does_not_duplicate_hardcoded_repos(self, _):
        hardcoded_repos = [
            'mediawiki/core',
            'mediawiki/skins/Vector',
        ]

        for repo in hardcoded_repos:
            q = cmd.QuibbleCmd()
            args = cmd._parse_arguments(args=['--packages-source=composer'])
            with mock.patch.dict(
                'os.environ', {'ZUUL_PROJECT': repo}, clear=True
            ):
                with mock.patch('quibble.commands.ZuulClone') as mock_clone:
                    q.build_execution_plan(args)
            self.assertEqual(
                [
                    'mediawiki/core',  # must be first
                    'mediawiki/skins/Vector',
                ],
                mock_clone.call_args[1]['projects'],
            )

    def test_execute(self):
        q = cmd.QuibbleCmd()

        with self.assertLogs(level='DEBUG') as log:
            q.execute([], '/workspace/src')

        self.assertRegex(
            log.output[0], "DEBUG:quibble.cmd:Project dir: /workspace/src"
        )
