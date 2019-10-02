#!/usr/bin/env python3

import os
import unittest
from unittest import mock

from quibble import cmd
from quibble.cmd import MultipleChoices
import quibble.commands


class MultipleChoicesTest(unittest.TestCase):

    def test_init(self):
        # It is really just like a list
        self.assertEquals([], MultipleChoices())
        self.assertEquals(['a'], MultipleChoices(['a']))
        self.assertEquals(['a'], MultipleChoices('a'))

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
            q.repos_to_clone(),
            ['mediawiki/core', 'mediawiki/skins/Vector'],
            'Incorrect repos to clone')

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_with_vendor(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.repos_to_clone(clone_vendor=True),
            ['mediawiki/core', 'mediawiki/skins/Vector', 'mediawiki/vendor'],
            'Incorrect repos to clone')

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_appends_projects(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.repos_to_clone(projects=[
                'mediawiki/extensions/BoilerPlate',
                'mediawiki/extensions/Example',
                ]),
            ['mediawiki/core',
             'mediawiki/extensions/BoilerPlate',
             'mediawiki/extensions/Example',
             'mediawiki/skins/Vector'])

    @mock.patch.dict('os.environ', clear=True)
    def test_projects_to_clone_deduplicates(self):
        q = cmd.QuibbleCmd()
        self.assertEqual(
            q.repos_to_clone(
                projects=[
                    'mediawiki/extensions/BoilerPlate',
                    'mediawiki/extensions/Example',
                ],
                zuul_project='mediawiki/extensions/Example'),
            ['mediawiki/core',
             'mediawiki/extensions/BoilerPlate',
             'mediawiki/extensions/Example',
             'mediawiki/skins/Vector'])

    def test_repos_to_clone_with_env(self):
        env = {
            'SKIN_DEPENDENCIES': 'mediawiki/skins/Monobook',
            'EXT_DEPENDENCIES':
                'mediawiki/extensions/One\\nmediawiki/extensions/Two',
        }
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            self.assertEqual([
                'mediawiki/core',  # must be first
                'mediawiki/extensions/One',
                'mediawiki/extensions/Two',
                'mediawiki/skins/Monobook',
                'mediawiki/skins/Vector',
                ], q.repos_to_clone())

    def test_env_dependencies_log_a_warning(self):
        env = {
            'EXT_DEPENDENCIES': '',
            'SKIN_DEPENDENCIES': '',
        }
        with mock.patch.dict('os.environ', env, clear=True):
            with self.assertLogs('quibble.cmd', level='WARNING') as log:
                q = cmd.QuibbleCmd()
                q.repos_to_clone()

        self.assertRegex(
            log.output[0],
            '^WARNING:quibble.cmd:SKIN_DEPENDENCIES')
        self.assertRegex(
            log.output[1],
            '^WARNING:quibble.cmd:EXT_DEPENDENCIES')

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_args_defaults(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('ref', args.git_cache)
        self.assertEqual(os.getcwd(), args.workspace)
        self.assertEqual('log', args.log_dir)

    @mock.patch('quibble.is_in_docker', return_value=True)
    def test_args_defaults_in_docker(self, _):
        args = cmd.QuibbleCmd().parse_arguments([])

        self.assertEqual('/srv/git', args.git_cache)
        self.assertEqual('/workspace', args.workspace)

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment(self):
        q = cmd.QuibbleCmd()
        q.workspace = '/testworkspace'
        q.mw_install_path = ''
        q.log_dir = ''

        with mock.patch('quibble.is_in_docker', return_value=True):
            # In Docker we always use self.workspace
            q.setup_environment()
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')
            with mock.patch.dict(os.environ, {'WORKSPACE': '/fromenv'},
                                 clear=True):
                # In Docker, ignore $WORKSPACE
                q.setup_environment()
                self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

        with mock.patch('quibble.is_in_docker', return_value=False):
            q.setup_environment()
            self.assertEqual(os.environ['WORKSPACE'], '/testworkspace')

            with mock.patch.dict(os.environ, {'WORKSPACE': '/fromenv'},
                                 clear=True):
                # When not in Docker, we honor $WORKSPACE
                q.setup_environment()
                self.assertEqual(os.environ['WORKSPACE'], '/fromenv')

    @mock.patch.dict(os.environ, clear=True)
    def test_setup_environment_has_log_directories(self):
        q = cmd.QuibbleCmd()
        q.workspace = '/workspace'
        q.mw_install_path = ''
        q.log_dir = '/mylog'

        q.setup_environment()

        self.assertIn('LOG_DIR', os.environ)
        self.assertIn('MW_LOG_DIR', os.environ)
        self.assertEqual(os.environ['LOG_DIR'], '/mylog')
        self.assertEqual(os.environ['MW_LOG_DIR'], '/mylog')

    def test_should_run_accepts_all_stages_by_default(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=[])
        self.assertTrue(
            all(map(q.should_run, q.stages)),
            'must runs all stages by default')

    def test_should_run_runall_accepts_all_stages(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--run=all'])
        self.assertTrue(
            all(map(q.should_run, q.stages)),
            '--run=all runs all stages')

    def test_should_run_skippall_runs_no_stage(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--skip=all'])
        self.assertFalse(
            any(map(q.should_run, q.stages)),
            '--skip=all skips all stages')

    def test_should_run_skips_a_stage(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--skip=phpunit'])
        self.assertFalse(
            q.should_run('phpunit'),
            '--skip skips the stage')
        stages_to_run = [s for s in q.stages
                         if s != 'phpunit']
        self.assertTrue(
            all(map(q.should_run, stages_to_run)),
            'Must runs all non skipped stages')

    def test_should_run_running_a_single_stage(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--run=phpunit'])
        self.assertTrue(
            q.should_run('phpunit'),
            '--run runs the stage')
        stages_to_skip = [s for s in q.stages
                          if s != 'phpunit']
        self.assertFalse(
            any(map(q.should_run, stages_to_skip)),
            'Must not run any other stages')

    def test_run_option_is_comma_separated(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--run=phpunit,qunit'])
        self.assertEquals(['phpunit', 'qunit'], q.args.run)

    def test_run_option_does_not_shallow_next_arg(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--run', 'phpunit', 'repo'])
        self.assertEquals(['phpunit'], q.args.run)
        self.assertEquals(['repo'], q.args.projects)

    def test_skip_option_is_comma_separated(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--skip=phpunit,qunit'])
        self.assertEquals(['phpunit', 'qunit'], q.args.skip)

    def test_skip_option_does_not_shallow_next_arg(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--skip', 'phpunit', 'repo'])
        self.assertEquals(['phpunit'], q.args.skip)
        self.assertEquals(['repo'], q.args.projects)

    def test_command_skip_all_stages(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--command=/bin/true'])
        self.assertFalse(
            any(map(q.should_run, q.stages)),
            'User command must skip all stages')

    def test_command_does_not_shallow_next_arg(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['--command', '/bin/true', 'repo'])
        self.assertEquals(['/bin/true'], q.args.commands)
        self.assertEquals(['repo'], q.args.projects)

    def test_command_used_multiple_times(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=['-c', 'true', '-c', 'false'])
        self.assertEquals(['true', 'false'], q.args.commands)

    def test_project_branch_arg(self):
        q = cmd.QuibbleCmd()
        q.args = q.parse_arguments(args=[])
        self.assertEquals([], q.args.project_branch)

    @mock.patch('os.makedirs')
    def test_build_execution_plan(self, mock_makedirs):
        q = cmd.QuibbleCmd()

        args = q.parse_arguments(args=[])
        plan = q.build_execution_plan(args)

        self.assertIsInstance(plan[0], quibble.commands.ReportVersions)
        mock_makedirs.assert_any_call(
            os.path.join(args.workspace, 'log'), exist_ok=True)

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_adds_ZUUL_PROJECT(self, _):
        env = {'ZUUL_PROJECT': 'mediawiki/extensions/ZuulProjectEnvVar'}
        with mock.patch.dict('os.environ', env, clear=True):
            q = cmd.QuibbleCmd()
            args = q.parse_arguments(
                args=['--packages-source=composer'])
            q.build_execution_plan(args)
            self.assertEqual([
                'mediawiki/core',  # must be first
                'mediawiki/extensions/ZuulProjectEnvVar',
                'mediawiki/skins/Vector',
                ], q.dependencies)

    @mock.patch('quibble.is_in_docker', return_value=False)
    def test_build_execution_plan_does_not_duplicate_hardcoded_repos(self, _):
        hardcoded_repos = [
            'mediawiki/core',
            'mediawiki/skins/Vector',
            ]

        for repo in hardcoded_repos:
            with mock.patch.dict('os.environ', {'ZUUL_PROJECT': repo},
                                 clear=True):
                q = cmd.QuibbleCmd()
                args = q.parse_arguments(
                    args=['--packages-source=composer'])
                q.build_execution_plan(args)
                self.assertEqual([
                    'mediawiki/core',  # must be first
                    'mediawiki/skins/Vector',
                    ], q.dependencies)
