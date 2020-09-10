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

log = logging.getLogger('quibble.cmd')
known_stages = ['all',
                'phpunit-unit', 'phpunit', 'phpunit-standalone',
                'npm-test', 'composer-test',
                'qunit', 'selenium', 'api-testing']
default_stages = ['phpunit-unit', 'phpunit', 'phpunit-standalone',
                  'npm-test', 'composer-test',
                  'qunit', 'selenium', 'api-testing']


# Used for add_argument(choices=) let us validate multiple choices at once.
# >>> 'a' in MultipleChoices(['a', 'b', 'c'])
# True
# >>> ['a', 'b'] in MultipleChoices(['a', 'b', 'c'])
# True
class MultipleChoices(list):
    def __contains__(self, item):
        return set(item).issubset(set(self))


class QuibbleCmd(object):

    def setup_environment(self, workspace, mw_install_path, log_dir):
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
            os.environ['WORKSPACE'] = workspace

        os.environ['MW_INSTALL_PATH'] = mw_install_path
        os.environ['MW_LOG_DIR'] = log_dir
        os.environ['LOG_DIR'] = log_dir
        os.environ['TMPDIR'] = tempfile.gettempdir()

    def _warn_obsolete_env_deps(self, var):
        log.warning(
            '%s env variable is deprecated. '
            'Instead pass projects as arguments.', var)

    def repos_to_clone(self, projects, zuul_project, clone_vendor):
        """
        Find repos to clone basedon passed arguments and environment
        """
        dependencies = set()
        dependencies.add('mediawiki/skins/Vector')
        if clone_vendor:
            log.info('Adding mediawiki/vendor')
            dependencies.add('mediawiki/vendor')

        # TODO: Remove this and build a list of additional dependencies.
        if zuul_project is not None:
            dependencies.add(zuul_project)

        if 'SKIN_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('SKIN_DEPENDENCIES')
            dependencies.update(
                os.environ.get('SKIN_DEPENDENCIES').split('\\n'))

        if 'EXT_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('EXT_DEPENDENCIES')
            dependencies.update(
                os.environ.get('EXT_DEPENDENCIES').split('\\n'))

        dependencies.update(projects)

        # mediawiki/core should be first else git clone will fail because the
        # destination directory already exists.
        if 'mediawiki/core' in dependencies:
            dependencies.remove('mediawiki/core')
        dependencies = sorted(dependencies)
        dependencies.insert(0, 'mediawiki/core')

        log.info('Projects: %s', ', '.join(dependencies))

        return dependencies

    def stages_to_run(self, run, skip, commands):
        if commands or 'all' in skip:
            return []

        stages = default_stages
        if skip:
            stages = [s for s in stages if s not in skip]
        if 'all' in run:
            return stages
        if run:
            stages = run
        return stages

    def build_execution_plan(self, args):
        plan = []

        workspace = args.workspace
        mw_install_path = os.path.join(workspace, 'src')
        log_dir = os.path.join(workspace, args.log_dir)
        if args.db_dir is not None:
            db_dir = os.path.join(workspace, args.db_dir)
        else:
            db_dir = None

        if args.dump_db_postrun:
            dump_dir = log_dir
        else:
            dump_dir = None

        stages = self.stages_to_run(args.run, args.skip, args.commands)
        log.debug('Running stages: %s', ', '.join(stages))

        self.setup_environment(workspace, mw_install_path, log_dir)

        zuul_project = os.environ.get('ZUUL_PROJECT', None)
        if zuul_project is None:
            # TODO: Isn't this default already covered by quibble.zuul, and we
            # can remove this code?
            log.warning('ZUUL_PROJECT not set. Assuming mediawiki/core')
            zuul_project = 'mediawiki/core'
        else:
            log.debug("ZUUL_PROJECT=%s", zuul_project)

        dependencies = self.repos_to_clone(
            projects=args.projects,
            zuul_project=zuul_project,
            clone_vendor=(args.packages_source == 'vendor'))

        plan.append(quibble.commands.ReportVersions())

        plan.append(quibble.commands.EnsureDirectory(log_dir))

        if not args.skip_zuul:
            zuul_params = {
                'branch': args.branch,
                'cache_dir': args.git_cache,
                'project_branch': args.project_branch,
                'workers': args.git_parallel,
                'workspace': os.path.join(workspace, 'src'),
                'zuul_branch': os.getenv('ZUUL_BRANCH'),
                'zuul_newrev': os.getenv('ZUUL_NEWREV'),
                'zuul_project': os.getenv('ZUUL_PROJECT'),
                'zuul_ref': os.getenv('ZUUL_REF'),
                'zuul_url': os.getenv('ZUUL_URL'),
            }

            plan.append(quibble.commands.ZuulClone(
                projects=dependencies,
                **zuul_params
            ))

            if args.resolve_requires:
                plan.append(quibble.commands.ResolveRequires(
                    mw_install_path=mw_install_path,
                    projects=dependencies,
                    zuul_params=zuul_params,
                    fail_on_extra_requires=args.fail_on_extra_requires,
                ))

            plan.append(quibble.commands.ExtSkinSubmoduleUpdate(
                mw_install_path))

        if quibble.util.isExtOrSkin(zuul_project):
            run_composer = 'composer-test' in stages
            run_npm = 'npm-test' in stages
            if run_composer or run_npm:
                project_dir = os.path.join(
                    mw_install_path,
                    quibble.zuul.repo_dir(zuul_project))

                plan.append(quibble.commands.ExtSkinComposerNpmTest(
                    project_dir, run_composer, run_npm))

        if not args.skip_deps and args.packages_source == 'composer':
            plan.append(quibble.commands.CreateComposerLocal(
                mw_install_path, dependencies))
            plan.append(quibble.commands.NativeComposerDependencies(
                mw_install_path))

        if not args.skip_install:
            database_backend = quibble.backend.getDatabase(
                args.db, db_dir, dump_dir)

            plan.append(quibble.commands.InstallMediaWiki(
                mw_install_path=mw_install_path,
                db=database_backend,
                web_url=args.web_url,
                log_dir=log_dir,
                use_vendor=(args.packages_source == 'vendor')))

        if not args.skip_deps:
            if args.packages_source == 'vendor':
                plan.append(quibble.commands.VendorComposerDependencies(
                    mw_install_path, log_dir))

            plan.append(quibble.commands.NpmInstall(
                mw_install_path))

        phpunit_testsuite = None
        if args.phpunit_testsuite:
            phpunit_testsuite = args.phpunit_testsuite
        elif zuul_project.startswith('mediawiki/extensions/'):
            phpunit_testsuite = 'extensions'
        elif zuul_project.startswith('mediawiki/skins/'):
            phpunit_testsuite = 'skins'

        if 'phpunit-unit' in stages:
            plan.append(quibble.commands.PhpUnitUnit(
                mw_install_path,
                log_dir))

        if 'phpunit' in stages:
            plan.append(quibble.commands.PhpUnitDatabaseless(
                mw_install_path,
                phpunit_testsuite,
                log_dir))

        if('phpunit-standalone' in stages
           and quibble.util.isExtOrSkin(zuul_project)
           ):
            plan.append(quibble.commands.PhpUnitStandalone(
                mw_install_path,
                None,
                log_dir,
                repo_path=quibble.zuul.repo_dir(zuul_project)
                ))

        if zuul_project == 'mediawiki/core':
            plan.append(quibble.commands.CoreNpmComposerTest(
                mw_install_path,
                composer='composer-test' in stages,
                npm='npm-test' in stages))

        display = os.environ.get('DISPLAY', None)

        if 'qunit' in stages:
            plan.append(quibble.commands.QunitTests(
                mw_install_path, args.web_url, args.web_backend))

        if 'selenium' in stages:
            plan.append(quibble.commands.BrowserTests(
                mw_install_path,
                quibble.util.move_item_to_head(
                    dependencies, zuul_project),
                display, args.web_url, args.web_backend))

        if 'api-testing' in stages:
            plan.append(quibble.commands.ApiTesting(
                mw_install_path,
                quibble.util.move_item_to_head(
                    dependencies, zuul_project),
                args.web_url,
                args.web_backend))

        if 'phpunit' in stages:
            plan.append(quibble.commands.PhpUnitDatabase(
                mw_install_path,
                phpunit_testsuite,
                log_dir))

        if args.commands:
            plan.append(quibble.commands.UserScripts(
                mw_install_path,
                args.commands,
                args.web_url,
                args.web_backend))

        return plan

    def execute(self, plan, dry_run=False):
        log.debug("Execution plan:")
        for cmd in plan:
            log.debug(cmd)
        if dry_run:
            log.warning("Exiting with execution: --dry-run")
            return
        for command in plan:
            quibble.commands.execute_command(command)


def parse_arguments(args):
    return get_arg_parser().parse_args(args)


def get_arg_parser():
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
        default='/srv/git' if quibble.is_in_docker() else 'ref',
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
        '--web-url',
        default='http://127.0.0.1:9412',
        help='Base URL where MediaWiki can be accessed.')
    parser.add_argument(
        '--web-backend',
        choices=['php', 'external'],
        default='php',
        help='Web server to use. Default to PHP\'s built-in. '
             '"external" assumes that the local MediaWiki site can be accessed'
             ' via an already running web server.')
    parser.add_argument(
        '--workspace',
        default='/workspace' if quibble.is_in_docker() else os.getcwd(),
        help='Base path to work from. In Docker: "/workspace", '
             'else current working directory'
        )
    parser.add_argument(
        '--log-dir',
        default='log',
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
        '--color', dest='color', action='store_true',
        help='Enable colorful output.')
    parser.add_argument(
        '--no-color', dest='color', action='store_false',
        help='Disable colorful output.')
    # Disable by default for Jenkins to avoid triggering a bug in
    # the "Console Section" plugin which gets confused if a line
    # starts with color code (T236222).
    parser.set_defaults(color=sys.stdin.isatty())

    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help='Stop before executing any commands.')

    stages_args = parser.add_argument_group('stages', description=(
        'Quibble runs all test commands (stages) by default. '
        'Use the --run or --skip options to further refine which commands '
        'will be run. '
        'Available stages are: %s' % ', '.join(known_stages)))

    # Magic type for add_argument so that --foo=a,b,c is magically stored
    # as: foo=['a', 'b', 'c']
    def comma_separated_list(string):
        return string.split(',')

    stages_choices = MultipleChoices(known_stages)
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


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('quibble').setLevel(logging.DEBUG)

    args = parse_arguments(sys.argv[1:])

    if args.color:
        quibble.colored_logging()

    cmd = QuibbleCmd()
    plan = cmd.build_execution_plan(args)
    cmd.execute(plan, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
