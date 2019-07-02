#!/usr/bin/env python3
#
# Copyright 2017-2018, Antoine "hashar" Musso
# Copyright 2017, Tyler Cipriani
# Copyright 2017-2018, Wikimedia Foundation Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import argparse
import logging
import os
import sys
import tempfile

import quibble
import quibble.mediawiki.maintenance
import quibble.backend
import quibble.zuul
import quibble.commands
import quibble.util


# Used for add_argument(choices=) let us validate multiple choices at once.
# >>> 'a' in MultipleChoices(['a', 'b', 'c'])
# True
# >>> ['a', 'b'] in MultipleChoices(['a', 'b', 'c'])
# True
class MultipleChoices(list):
    def __contains__(self, item):
        return set(item).issubset(set(self))


class QuibbleCmd(object):

    log = logging.getLogger('quibble.cmd')
    stages = ['phpunit-unit', 'phpunit', 'npm-test', 'composer-test', 'qunit',
              'selenium']
    dump_dir = None
    db_dir = None

    def __init__(self):
        self.dependencies = []
        # Hold backend objects so they do not get garbage collected until end
        # of script.
        self.backends = {}
        self.default_git_cache = ('/srv/git' if quibble.is_in_docker()
                                  else 'ref')
        self.default_workspace = ('/workspace' if quibble.is_in_docker()
                                  else os.getcwd())
        self.default_logdir = 'log'

    def parse_arguments(self, args=sys.argv[1:]):
        return self.get_arg_parser().parse_args(args)

    def get_arg_parser(self):
        """
        Parse arguments
        """
        parser = argparse.ArgumentParser(
            description='Quibble: the MediaWiki test runner',
            prog='quibble',
            )
        parser.add_argument(
            '--packages-source',
            choices=['composer', 'vendor'],
            default='vendor',
            help='Source to install PHP dependencies from. Default: vendor')
        parser.add_argument(
            '--skip-zuul',
            action='store_true',
            help='Do not clone/checkout in workspace')
        parser.add_argument(
            '--resolve-requires',
            action='store_true',
            help='Whether to process extension.json/skin.json and clone extra '
                 'extensions/skins mentioned in the "requires" statement. '
                 'This is done recursively.')
        parser.add_argument(
            '--fail-on-extra-requires',
            action='store_true',
            help='When --resolve-requires caused Quibble to clone extra '
                 'requirements not in the list of projects: fail.'
                 'Can be used to enforce extensions and skins to declare '
                 'their requirements via the extension registry.')
        parser.add_argument(
            '--skip-deps',
            action='store_true',
            help='Do not run composer/npm')
        parser.add_argument(
            '--skip-install',
            action='store_true',
            help='Do not install MediaWiki')
        parser.add_argument(
            '--db',
            choices=['sqlite', 'mysql', 'postgres'],
            default='mysql',
            help='Database backend to use. Default: mysql')
        parser.add_argument(
            '--db-dir',
            default=None,
            help=(
                'Base directory holding database files. A sub directory '
                'prefixed with "quibble-" will be created and deleted '
                'on completion. '
                'If set and relative, relatively to workspace. '
                'Default: %s' % tempfile.gettempdir()
            )
        )
        parser.add_argument(
            '--dump-db-postrun',
            action='store_true',
            help='Dump the db before shutting down the server (mysql only)')
        parser.add_argument(
            '--git-cache',
            default=self.default_git_cache,
            help='Path to bare git repositories to speed up git clone'
                 'operation. Passed to zuul-cloner as --cache-dir. '
                 'In Docker: "/srv/git", else "ref"')
        parser.add_argument(
            '--git-parallel',
            default=4,
            type=int,
            help='Number of workers to clone repositories. Default: 4')
        parser.add_argument(
            '--branch',
            default=None,
            help=('Branch to checkout instead of Zuul selected branch, '
                  'for example to specify an alternate branch to test '
                  'client library compatibility.')
            )
        parser.add_argument(
            '--project-branch', nargs=1, action='append',
            default=[],
            metavar='PROJECT=BRANCH',
            help=('project-specific branch to checkout which takes precedence '
                  'over --branch if it is provided; may be specified multiple '
                  'times.')
            )
        parser.add_argument(
            '--workspace',
            default=self.default_workspace,
            help='Base path to work from. In Docker: "/workspace", '
                 'else current working directory'
            )
        parser.add_argument(
            '--log-dir',
            default=self.default_logdir,
            help='Where logs and artifacts will be written to. '
            'Default: "log" relatively to workspace'
            )
        parser.add_argument(
            'projects', default=[], nargs='*',
            help='MediaWiki extensions and skins to clone. Always clone '
                 'mediawiki/core and mediawiki/skins/Vector. '
                 'If $ZUUL_PROJECT is set, it will be cloned as well.'
            )

        parser.add_argument(
            '-n', '--dry-run',
            action='store_true',
            help='Stop before executing any commands.')

        stages = ', '.join(self.stages)
        stages_args = parser.add_argument_group('stages', description=(
            'Quibble runs all test commands (stages) by default. '
            'Use the --run or --skip options to further refine which commands '
            'will be run. '
            'Available stages are: %s' % stages))

        # Magic type for add_argument so that --foo=a,b,c is magically stored
        # as: foo=['a', 'b', 'c']
        def comma_separated_list(string):
            return string.split(',')

        stages_choices = MultipleChoices(self.stages + ['all'])
        stages_args.add_argument(
            '--run', default=['all'],
            type=comma_separated_list,
            choices=stages_choices, metavar='STAGE[,STAGE ...]',
            help='Tests to run. Comma separated. (default: all).'
        )
        stages_args.add_argument(
            '--skip', default=[],
            type=comma_separated_list,
            choices=stages_choices, metavar='STAGE[,STAGE ...]',
            help='Stages to skip. Comma separated. '
                 'Set to "all" to skip all stages. '
                 '(default: none). '
        )

        command_args = stages_args.add_mutually_exclusive_group()
        command_args.add_argument(
            '-c', '--command', action='append',
            dest='commands', metavar='COMMAND',
            help=(
                'Run given command instead of built-in stages. '
                'Each command is executed relatively to '
                'MediaWiki installation path.'))
        command_args.add_argument(
            '--commands', default=[], nargs='*', metavar='COMMAND',
            help=('DEPRECATED: use -c COMMAND -c COMMAND'))

        parser.add_argument(
            '--phpunit-testsuite', default=None, metavar='pattern',
            help='PHPUnit: filter which testsuite to run')

        return parser

    def setup_environment(self):
        """
        Set and get needed environment variables.
        """
        if 'EXECUTOR_NUMBER' not in os.environ:
            os.environ['EXECUTOR_NUMBER'] = '1'

        if quibble.is_in_docker() or 'WORKSPACE' not in os.environ:
            # Override WORKSPACE in Docker, we really want /workspace or
            # whatever was given from the command line.
            # Else set it, since some code might rely on it being set to detect
            # whether they are under CI.
            os.environ['WORKSPACE'] = self.workspace

        os.environ['MW_INSTALL_PATH'] = self.mw_install_path
        os.environ['MW_LOG_DIR'] = self.log_dir
        os.environ['LOG_DIR'] = self.log_dir
        os.environ['TMPDIR'] = tempfile.gettempdir()

    def _warn_obsolete_env_deps(self, var):
        self.log.warning(
            '%s env variable is deprecated. '
            'Instead pass projects as arguments.' % var)

    def repos_to_clone(self, projects=[], zuul_project=None,
                       clone_vendor=False):
        """
        Find repos to clone basedon passed arguments and environment
        """
        dependencies = []
        # mediawiki/core should be first else git clone will fail because the
        # destination directory already exists.
        dependencies.insert(0, 'mediawiki/core')
        dependencies.append('mediawiki/skins/Vector')
        if clone_vendor:
            self.log.info('Adding mediawiki/vendor')
            dependencies.append('mediawiki/vendor')

        if zuul_project is not None and zuul_project not in dependencies:
            dependencies.append(zuul_project)

        if 'SKIN_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('SKIN_DEPENDENCIES')
            dependencies.extend(
                os.environ.get('SKIN_DEPENDENCIES').split('\\n'))

        if 'EXT_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('EXT_DEPENDENCIES')
            dependencies.extend(
                os.environ.get('EXT_DEPENDENCIES').split('\\n'))

        dependencies.extend(projects)

        self.log.info('Projects: %s'
                      % ', '.join(dependencies))

        return dependencies

    def should_run(self, stage):
        if self.args.commands:
            return False
        if 'all' in self.args.skip:
            return False
        if stage in self.args.skip:
            return False
        if 'all' in self.args.run:
            return True
        return stage in self.args.run

    def build_execution_plan(self, args):
        plan = []

        self.args = args
        self.workspace = self.args.workspace
        self.mw_install_path = os.path.join(self.workspace, 'src')
        self.log_dir = os.path.join(self.workspace, self.args.log_dir)
        if self.args.db_dir is not None:
            self.db_dir = os.path.join(self.workspace, self.args.db_dir)

        os.makedirs(self.log_dir, exist_ok=True)

        if self.args.dump_db_postrun:
            self.dump_dir = self.log_dir

        self.log.debug('Running stages: '
                       + ', '.join(stage for stage in self.stages
                                   if self.should_run(stage)))

        self.setup_environment()

        zuul_project = os.environ.get('ZUUL_PROJECT', None)
        if zuul_project is None:
            # TODO: Isn't this default already covered by quibble.zuul, and we
            # can remove this code?
            self.log.warning('ZUUL_PROJECT not set. Assuming mediawiki/core')
            zuul_project = 'mediawiki/core'
        else:
            self.log.debug("ZUUL_PROJECT=%s" % zuul_project)

        self.dependencies = self.repos_to_clone(
            projects=self.args.projects,
            zuul_project=zuul_project,
            clone_vendor=(self.args.packages_source == 'vendor'))

        if not self.args.skip_zuul:
            zuul_params = {
                'branch': self.args.branch,
                'cache_dir': self.args.git_cache,
                'project_branch': self.args.project_branch,
                'workers': self.args.git_parallel,
                'workspace': os.path.join(self.workspace, 'src'),
                'zuul_branch': os.getenv('ZUUL_BRANCH'),
                'zuul_newrev': os.getenv('ZUUL_NEWREV'),
                'zuul_project': os.getenv('ZUUL_PROJECT'),
                'zuul_ref': os.getenv('ZUUL_REF'),
                'zuul_url': os.getenv('ZUUL_URL'),
            }
            plan.append(quibble.commands.ZuulCloneCommand(
                projects=self.dependencies,
                **zuul_params
            ))

            if self.args.resolve_requires:
                plan.append(quibble.commands.ResolveRequiresCommand(
                    mw_install_path=self.mw_install_path,
                    projects=self.dependencies,
                    zuul_params=zuul_params,
                    fail_on_extra_requires=self.args.fail_on_extra_requires,
                ))

            plan.append(quibble.commands.ExtSkinSubmoduleUpdateCommand(
                self.mw_install_path))

        if quibble.util.isExtOrSkin(zuul_project):
            run_composer = self.should_run('composer-test')
            run_npm = self.should_run('npm-test')
            if run_composer or run_npm:
                project_dir = os.path.join(
                    self.mw_install_path,
                    quibble.zuul.repo_dir(zuul_project))

                plan.append(quibble.commands.ExtSkinComposerNpmTest(
                    project_dir, run_composer, run_npm))

        if not self.args.skip_deps and self.args.packages_source == 'composer':
            plan.append(quibble.commands.CreateComposerLocal(
                self.mw_install_path, self.dependencies))
            plan.append(quibble.commands.NativeComposerDependencies(
                self.mw_install_path))

        if not self.args.skip_install:
            plan.append(quibble.commands.InstallMediaWiki(
                mw_install_path=self.mw_install_path,
                db_engine=self.args.db,
                db_dir=self.db_dir,
                dump_dir=self.dump_dir,
                log_dir=self.log_dir,
                use_vendor=(self.args.packages_source == 'vendor')))

        if not self.args.skip_deps:
            if self.args.packages_source == 'vendor':
                plan.append(quibble.commands.VendorComposerDependencies(
                    self.mw_install_path, self.log_dir))

            plan.append(quibble.commands.NpmInstall(
                self.mw_install_path))

        phpunit_testsuite = None
        if self.args.phpunit_testsuite:
            phpunit_testsuite = self.args.phpunit_testsuite
        elif zuul_project.startswith('mediawiki/extensions/'):
            phpunit_testsuite = 'extensions'
        elif zuul_project.startswith('mediawiki/skins/'):
            phpunit_testsuite = 'skins'

        if self.should_run('phpunit-unit'):
            plan.append(quibble.commands.PhpUnitUnit(
                self.mw_install_path,
                self.log_dir))

        if self.should_run('phpunit'):
            plan.append(quibble.commands.PhpUnitDatabaseless(
                self.mw_install_path,
                phpunit_testsuite,
                self.log_dir))

        if zuul_project == 'mediawiki/core':
            plan.append(quibble.commands.CoreNpmComposerTest(
                self.mw_install_path,
                composer=self.should_run('composer-test'),
                npm=self.should_run('npm-test')))

        display = os.environ.get('DISPLAY', None)

        if self.should_run('qunit'):
            plan.append(quibble.commands.QunitTests(
                self.mw_install_path))

        if self.should_run('selenium'):
            plan.append(quibble.commands.BrowserTests(
                self.mw_install_path,
                quibble.util.move_item_to_head(
                    self.dependencies, zuul_project),
                display))

        if self.should_run('phpunit'):
            plan.append(quibble.commands.PhpUnitDatabase(
                self.mw_install_path,
                phpunit_testsuite,
                self.log_dir))

        if self.args.commands:
            plan.append(quibble.commands.UserCommands(
                self.mw_install_path, self.args.commands))

        return plan

    def execute(self, plan):
        self.log.debug("Execution plan:")
        for cmd in plan:
            self.log.debug(cmd)
        if self.args.dry_run:
            self.log.warning("Exiting without execution: --dry-run")
            return
        for command in plan:
            command.execute()


# FIXME: Don't shadow QuibbleCmd.get_arg_parser
def get_arg_parser():
    """
    Build an argparser with sane default values.

    Intended for documentation generation with sphinx-argparse.
    """
    cmd = QuibbleCmd()
    # FIXME: These both might be redundant.  And why does sphinx need a custom
    # endpoint?
    cmd.default_git_cache = 'ref'
    cmd.default_workspace = '.'

    return cmd.get_arg_parser()


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('quibble').setLevel(logging.DEBUG)
    quibble.colored_logging()

    cmd = QuibbleCmd()
    args = cmd.parse_arguments()
    plan = cmd.build_execution_plan(args)
    cmd.execute(plan)


if __name__ == '__main__':
    main()
