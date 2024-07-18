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
import contextlib
import logging
import os
import subprocess
import sys
import tempfile

import quibble
import quibble.mediawiki.maintenance
import quibble.backend
import quibble.zuul
import quibble.commands
import quibble.util

log = logging.getLogger('quibble.cmd')
known_stages = [
    'all',
    'phpunit-unit',
    'phpbench',
    'phpunit',
    'phpunit-standalone',
    'phpunit-parallel',
    'npm-test',
    'composer-test',
    'qunit',
    'selenium',
    'api-testing',
]
default_stages = [
    'phpunit-unit',
    'phpbench',
    'phpunit',
    'phpunit-standalone',
    'npm-test',
    'composer-test',
    'qunit',
    'selenium',
    'api-testing',
]


# Used for add_argument(choices=) let us validate multiple choices at once.
# >>> 'a' in MultipleChoices(['a', 'b', 'c'])
# True
# >>> ['a', 'b'] in MultipleChoices(['a', 'b', 'c'])
# True
class MultipleChoices(list):
    def __contains__(self, item):
        return set(item).issubset(set(self))


class QuibbleCmd(object):
    def __init__(self):
        self._context_stack = contextlib.ExitStack()

    def _setup_environment(
        self,
        workspace,
        mw_install_path,
        log_dir,
        tmp_dir,
        use_vendor=False,
        zuul_env={},
    ):
        """
        Set and get needed environment variables.

        TODO: Can we deprecate any of these in favor of explicit
        parameters?
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
        os.environ['TMPDIR'] = tmp_dir

        # In the mediawiki/vendor update workflow, we patch vendor (and its
        # lock file) first, and update the mediawiki/core composer.json after.
        # As such, when testing mediawiki/vendor, it's normal that its lock
        # file doesn't match mediawiki/core. This is tested by the
        # mediawiki/core commit instead.
        #
        # T333412
        if use_vendor:
            os.environ['MW_SKIP_EXTERNAL_DEPENDENCIES'] = '1'

        if zuul_env:
            os.environ.update(zuul_env)

    def _warn_obsolete_env_deps(self, var):
        log.warning(
            '%s env variable is deprecated. '
            'Instead pass projects as arguments.',
            var,
        )

    def _repos_to_clone(self, projects, zuul_project, clone_vendor):
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
                os.environ.get('SKIN_DEPENDENCIES').split('\\n')
            )

        if 'EXT_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('EXT_DEPENDENCIES')
            dependencies.update(
                os.environ.get('EXT_DEPENDENCIES').split('\\n')
            )

        dependencies.update(projects)

        # mediawiki/core should be first else git clone will fail because the
        # destination directory already exists.
        if 'mediawiki/core' in dependencies:
            dependencies.remove('mediawiki/core')
        dependencies = sorted(dependencies)
        dependencies.insert(0, 'mediawiki/core')

        log.info('Projects: %s', ', '.join(dependencies))

        return dependencies

    def _stages_to_run(self, run, skip, commands):
        if commands or 'all' in skip:
            return []

        stages = default_stages
        if skip:
            stages = [s for s in stages if s not in skip]
        if len(run) > 0:
            stages = run
        if os.getenv('QUIBBLE_PHPUNIT_PARALLEL') and 'phpunit' in stages:
            stages.append('phpunit-parallel')
        return stages

    def build_execution_plan(self, args):
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

        tmp_dir = tempfile.gettempdir()

        # Set ZUUL variables when given `--change ###`
        zuul_env = (
            quibble.util.FetchInfo.change(args.change).asZuulEnv()
            if args.change
            else {}
        )

        self._setup_environment(
            workspace, mw_install_path, log_dir, tmp_dir, zuul_env=zuul_env
        )

        zuul_project = os.environ.get('ZUUL_PROJECT', None)
        if zuul_project is None:
            # TODO: Isn't this default already covered by quibble.zuul, and we
            # can remove this code?
            log.warning('ZUUL_PROJECT not set. Assuming mediawiki/core')
            zuul_project = 'mediawiki/core'
        else:
            log.debug("ZUUL_PROJECT=%s", zuul_project)

        is_core = zuul_project == 'mediawiki/core'
        is_extension = (
            zuul_project.startswith('mediawiki/extensions/')
            or zuul_project == 'mediawiki/services/parsoid'
        )
        is_skin = zuul_project.startswith('mediawiki/skins/')

        use_composer = args.packages_source == 'composer'
        use_vendor = args.packages_source == 'vendor'

        self._setup_environment(
            workspace, mw_install_path, log_dir, tmp_dir, use_vendor
        )

        dependencies = self._repos_to_clone(
            projects=args.projects,
            zuul_project=zuul_project,
            clone_vendor=use_vendor,
        )

        dependencies_with_project_first = quibble.util.move_item_to_head(
            dependencies, zuul_project
        )

        repo_path = quibble.zuul.repo_dir(zuul_project)

        stages = self._stages_to_run(args.run, args.skip, args.commands)
        log.debug('Running stages: %s', ', '.join(stages))
        log.debug(
            'QUIBBLE_PHPUNIT_PARALLEL: %s',
            os.getenv('QUIBBLE_PHPUNIT_PARALLEL'),
        )

        run_composer = 'composer-test' in stages
        run_npm = 'npm-test' in stages

        database_backend = quibble.backend.getDatabase(
            args.db, db_dir, dump_dir, log_dir
        )

        web_backend_args = {}
        if args.web_backend == 'php' and args.web_php_workers:
            web_backend_args = {
                'workers': args.web_php_workers,
            }

        web_backend = quibble.backend.getWebserver(
            args.web_backend, mw_install_path, args.web_url, web_backend_args
        )

        plan = []
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

            plan.append(
                quibble.commands.ZuulClone(
                    projects=dependencies, **zuul_params
                )
            )

            if args.resolve_requires:
                plan.append(
                    quibble.commands.ResolveRequires(
                        mw_install_path=mw_install_path,
                        projects=dependencies,
                        zuul_params=zuul_params,
                        fail_on_extra_requires=args.fail_on_extra_requires,
                    )
                )

            plan.append(
                quibble.commands.ExtSkinSubmoduleUpdate(mw_install_path)
            )

        # Assume project dir is mediawiki/core by default
        project_dir = mw_install_path

        if is_extension or is_skin:
            project_dir = os.path.join(mw_install_path, repo_path)

            parallel_steps = []
            if run_composer:
                parallel_steps.append(
                    quibble.commands.ExtSkinComposerTest(project_dir)
                )
            if run_npm:
                parallel_steps.append(quibble.commands.NpmTest(project_dir))
            if parallel_steps:
                plan.extend(
                    [
                        quibble.commands.Parallel(
                            name="npm and composer tests, if present",
                            steps=parallel_steps,
                        ),
                        quibble.commands.GitClean(project_dir),
                    ]
                )

        if not args.skip_deps and use_composer:
            plan.append(
                quibble.commands.CreateComposerLocal(
                    mw_install_path, dependencies
                )
            )
            plan.append(
                quibble.commands.NativeComposerDependencies(mw_install_path)
            )

        if not args.skip_deps:
            # NPM install is done after MediaWiki installation.
            if use_vendor:
                plan.append(
                    quibble.commands.VendorComposerDependencies(
                        mw_install_path, log_dir
                    )
                )

        # Post dependency setup, pre database dependent phase.
        parallel_steps = []

        if not args.skip_install:
            if not args.db_is_external:
                plan.append(
                    quibble.commands.StartBackends(
                        self._context_stack, [database_backend]
                    )
                )

            parallel_steps.append(
                quibble.commands.InstallMediaWiki(
                    mw_install_path=mw_install_path,
                    db=database_backend,
                    web_url=web_backend.url,
                    log_dir=log_dir,
                    tmp_dir=tmp_dir,
                    use_vendor=use_vendor,
                )
            )

        if not args.skip_deps:
            parallel_steps.append(quibble.commands.NpmInstall(mw_install_path))

        plan.append(
            quibble.commands.Parallel(
                name="Post-dependency install, pre-database dependent steps",
                steps=parallel_steps,
            )
        )

        # phpunit-unit needs LocalSettings.php, see T227900#9014246
        if 'phpunit-unit' in stages:
            plan.append(
                quibble.commands.PhpUnitUnit(
                    mw_install_path, log_dir, args.phpunit_junit
                )
            )

        phpunit_testsuite = None
        if args.phpunit_testsuite:
            phpunit_testsuite = args.phpunit_testsuite
        elif is_extension:
            phpunit_testsuite = 'extensions'
        elif is_skin:
            phpunit_testsuite = 'skins'

        if phpunit_testsuite != 'extensions' and 'phpunit-parallel' in stages:
            log.warning(
                'phpunit-parallel in stages, but only currently supported for'
                'extensions test suite - reverting to serial run'
            )
            stages.remove('phpunit-parallel')

        if 'phpunit-parallel' in stages:
            plan.append(
                quibble.commands.PhpUnitPrepareParallelRun(
                    mw_install_path,
                    phpunit_testsuite,
                    log_dir,
                    args.phpunit_junit,
                )
            )
            plan.append(
                quibble.commands.PhpUnitDatabaselessParallel(
                    mw_install_path,
                    phpunit_testsuite,
                    log_dir,
                    args.phpunit_junit,
                ).generate_parallel_command()
            )

        if 'phpunit' in stages and 'phpunit-parallel' not in stages:
            plan.append(
                quibble.commands.PhpUnitDatabaseless(
                    mw_install_path,
                    phpunit_testsuite,
                    log_dir,
                    args.phpunit_junit,
                )
            )

        if 'phpunit-standalone' in stages and (is_extension or is_skin):
            plan.append(
                quibble.commands.PhpUnitStandalone(
                    mw_install_path,
                    None,
                    log_dir,
                    repo_path,
                    args.phpunit_junit,
                )
            )

        if 'phpbench' in stages:
            project_dir = mw_install_path
            if is_extension or is_skin:
                project_dir = os.path.join(mw_install_path, repo_path)
            plan.append(
                quibble.commands.Phpbench(
                    project_dir,
                    composer_install=is_extension or is_skin,
                    aggregate=args.phpbench_aggregate,
                )
            )

        if is_core:
            parallel_steps = []
            label = []
            if run_composer:
                label.append("'composer test'")
                parallel_steps.append(
                    quibble.commands.CoreComposerTest(mw_install_path)
                )
            if run_npm:
                label.append("'npm test'")
                parallel_steps.append(
                    quibble.commands.NpmTest(mw_install_path)
                )
            if parallel_steps:
                plan.append(
                    quibble.commands.Parallel(
                        name=" and ".join(label), steps=parallel_steps
                    )
                )

        if (
            set(['qunit', 'selenium', 'api-testing']) & set(stages)
            or args.commands
        ):
            backends = [web_backend]

            display = os.environ.get('DISPLAY', None)

            if not display:
                display = ':94'
                backends.append(quibble.backend.Xvfb(display))

            backends.append(quibble.backend.ChromeWebDriver(display))

            plan.append(
                quibble.commands.StartBackends(self._context_stack, backends)
            )

        if 'qunit' in stages:
            plan.append(
                quibble.commands.QunitTests(mw_install_path, web_backend.url)
            )

        if 'selenium' in stages:
            selenium_steps = []
            if args.parallel_npm_install:
                parallel_steps = []
                """
                Parallelize the execution of npm install for all browser tests.
                Ideally, we'd parallelize the Selenium test execution too, but
                since that is going to require quite a bit more work (T226869),
                let's start with the part that can be done now.
                Note that his has the potential to increase the build time for
                projects where a test failure occurs early on (i.e. in core, or
                in AbuseFilter), because the tests don't run until npm install
                completes for all projects that have browser tests. But for the
                common scenario where the tests pass for all repos, this should
                result in reducing build time.
                """
                for project in dependencies_with_project_first:
                    parallel_steps.append(
                        quibble.commands.NpmInstall(
                            mw_install_path=mw_install_path,
                            project=project,
                            with_package_command='selenium-test',
                        )
                    )

                selenium_steps.append(
                    quibble.commands.Parallel(
                        name="Parallel npm install for projects with "
                        "'selenium-test' in package.json",
                        steps=parallel_steps,
                    )
                )

            selenium_steps.append(
                quibble.commands.BrowserTests(
                    mw_install_path,
                    dependencies_with_project_first,
                    display,
                    web_backend.url,
                    args.web_backend,
                    args.parallel_npm_install,
                )
            )
            plan.extend(selenium_steps)

        if 'api-testing' in stages:
            plan.append(
                quibble.commands.ApiTesting(
                    mw_install_path,
                    dependencies_with_project_first,
                    web_backend.url,
                    args.web_backend,
                )
            )

        if 'phpunit' in stages and 'phpunit-parallel' not in stages:
            plan.append(
                quibble.commands.PhpUnitDatabase(
                    mw_install_path,
                    phpunit_testsuite,
                    log_dir,
                    args.phpunit_junit,
                )
            )

        if 'phpunit-parallel' in stages:
            plan.append(
                quibble.commands.PhpUnitDatabaseParallel(
                    mw_install_path,
                    phpunit_testsuite,
                    log_dir,
                    args.phpunit_junit,
                ).generate_parallel_command()
            )

        if args.commands:
            plan.append(
                quibble.commands.UserScripts(
                    mw_install_path,
                    args.commands,
                    web_backend.url,
                    args.web_backend,
                )
            )

        if 'phpunit-parallel' in stages:
            plan.append(quibble.commands.PhpUnitParallelNotice())

        return project_dir, plan

    def execute(self, plan, project_dir, reporting_url=None, dry_run=False):
        log.debug("Project dir: %s", project_dir)
        log.debug("Reporting URL: %s", reporting_url or "not specified")
        log.debug("Execution plan:")
        for cmd in plan:
            log.debug(cmd)
        if dry_run:
            log.warning("Exiting without execution: --dry-run")
            return

        with self._context_stack:
            for command in plan:
                try:
                    quibble.commands.execute_command(command)
                except subprocess.CalledProcessError as called_process_error:
                    # If a command failed, check to see if the repository
                    # is configured so that Quibble should transmit error
                    # data to an endpoint for further processing.
                    if not quibble.commands.repo_has_quibble_config(
                        project_dir
                    ):
                        log.debug('No quibble.yaml in %s', project_dir)
                        raise called_process_error
                    if not reporting_url:
                        log.debug('No reporting URL specified.')
                        raise called_process_error
                    config = quibble.commands.repo_load_quibble_config(
                        project_dir
                    )
                    if not config.get('earlywarning'):
                        log.debug(
                            'No earlywarning section found in quibble.yaml'
                        )
                        raise called_process_error

                    called_process_error_cmd = called_process_error.cmd
                    if isinstance(called_process_error_cmd, list):
                        called_process_error_cmd = " ".join(
                            called_process_error_cmd
                        )
                    quibble.commands.transmit_error(
                        should_comment=config.get('earlywarning').get(
                            'should_comment', 0
                        ),
                        should_vote=config.get('earlywarning').get(
                            'should_vote', 0
                        ),
                        phase=str(command),
                        command=called_process_error_cmd,
                        reporting_url=reporting_url,
                        api_key=os.getenv("QUIBBLE_API_KEY"),
                        called_process_error=called_process_error,
                    )
                    raise called_process_error


def _parse_arguments(args):
    return get_arg_parser().parse_args(args)


def get_arg_parser():
    """
    Parse arguments
    """
    parser = argparse.ArgumentParser(
        description='Quibble: the MediaWiki test runner',
        prog='quibble',
        add_help=False,  # added back in the global_opts below
    )

    global_opts = parser.add_argument_group('Global options')
    global_opts.add_argument(
        '-h',
        '--help',
        action='help',
    )
    global_opts.add_argument(
        '--color',
        dest='color',
        action='store_true',
        help=(
            'Enable colorful output '
            '(or set the FORCE_COLOR environment variable)'
        ),
    )
    global_opts.add_argument(
        '--no-color',
        dest='color',
        action='store_false',
        help='Disable colorful output.',
    )
    global_opts.set_defaults(
        color=sys.stdin.isatty() or os.getenv('FORCE_COLOR')
    )

    global_opts.add_argument(
        '-n',
        '--dry-run',
        action='store_true',
        help='Stop before executing any commands.',
    )
    global_opts.add_argument(
        '--workspace',
        default='/workspace' if quibble.is_in_docker() else os.getcwd(),
        help='Base path to work from. In Docker: "/workspace", '
        'else current working directory',
    )
    global_opts.add_argument(
        '--log-dir',
        default='log',
        help='Where logs and artifacts will be written to. '
        'Default: "log" relatively to workspace',
    )
    global_opts.add_argument(
        '--reporting-url',
        default=None,
        help='HTTP endpoint that Quibble will POST error '
        'messages to, for configured repositories.',
    )

    git_ops = parser.add_argument_group('Git operations')
    git_ops.add_argument(
        '--skip-zuul',
        action='store_true',
        help='Do not clone/checkout in workspace',
    )
    git_ops.add_argument(
        '--change',
        help=(
            'Gerrit Change[,patchset] to act on. Will fetch the change '
            'latest patchset (or the specified one). Overrides ZUUL '
            'environment variables'
        ),
    )
    git_ops.add_argument(
        '--git-cache',
        default='/srv/git' if quibble.is_in_docker() else 'ref',
        help='Path to bare git repositories to speed up git clone'
        'operation. Passed to zuul-cloner as --cache-dir. '
        'In Docker: "/srv/git", else "ref"',
    )
    git_ops.add_argument(
        '--git-parallel',
        default=4,
        type=int,
        help='Number of workers to clone repositories. Default: 4',
    )
    git_ops.add_argument(
        '--branch',
        default=None,
        help=(
            'Branch to checkout instead of Zuul selected branch, '
            'for example to specify an alternate branch to test '
            'client library compatibility.'
        ),
    )
    git_ops.add_argument(
        '--project-branch',
        nargs=1,
        action='append',
        default=[],
        metavar='PROJECT=BRANCH',
        help=(
            'project-specific branch to checkout which takes precedence '
            'over --branch if it is provided; may be specified multiple '
            'times.'
        ),
    )

    deps = parser.add_argument_group('Libraries dependencies')
    deps.add_argument(
        '--skip-deps',
        action='store_true',
        help='Do not run composer/npm installs',
    )
    deps.add_argument(
        '--packages-source',
        choices=['composer', 'vendor'],
        default='vendor',
        help='Source to install PHP dependencies from. Default: vendor',
    )
    deps.add_argument(
        '--parallel-npm-install',
        action='store_true',
        help='Whether to run "npm install" in parallel for all projects at '
        'the beginning of the BrowserTest stage.',
    )

    install = parser.add_argument_group('MediaWiki install')
    install.add_argument(
        '--skip-install', action='store_true', help='Do not install MediaWiki'
    )
    install.add_argument(
        '--db',
        choices=['sqlite', 'mysql', 'postgres'],
        default='mysql',
        help='Database backend to use. Default: mysql',
    )
    install.add_argument(
        '--db-dir',
        default=None,
        help=(
            'Base directory holding database files. A sub directory '
            'prefixed with "quibble-" will be created and deleted '
            'on completion. '
            'If set and relative, relatively to workspace. '
            'Default: %s' % tempfile.gettempdir()
        ),
    )
    install.add_argument(
        '--db-is-external',
        action='store_true',
        help='If the database is managed externally and not by Quibble. '
        'Default: managed by Quibble',
    )
    install.add_argument(
        '--dump-db-postrun',
        action='store_true',
        help='Dump the db before shutting down the server (mysql only)',
    )

    ext_requires = parser.add_argument_group('MediaWiki extension requires')
    ext_requires.add_argument(
        '--resolve-requires',
        action='store_true',
        help='Whether to process extension.json/skin.json and clone extra '
        'extensions/skins mentioned in the "requires" statement. '
        'This is done recursively.',
    )
    ext_requires.add_argument(
        '--fail-on-extra-requires',
        action='store_true',
        help='When --resolve-requires caused Quibble to clone extra '
        'requirements not in the list of projects: fail.'
        'Can be used to enforce extensions and skins to declare '
        'their requirements via the extension registry.',
    )

    tests = parser.add_argument_group('Stages options')
    tests.add_argument(
        '--phpbench-aggregate',
        action='store_true',
        help='If this argument is set, then Quibble will run phpbench in '
        'aggregate mode, comparing the previous commit with the '
        'current one.',
    )
    tests.add_argument(
        '--phpunit-testsuite',
        default=None,
        metavar='pattern',
        help='PHPUnit: filter which testsuite to run',
    )
    tests.add_argument(
        '--phpunit-junit',
        default=False,
        action='store_true',
        help='PHPUnit: enable Junit reporting to LOG_DIR',
    )

    web = parser.add_argument_group('Web server')
    web.add_argument(
        '--web-backend',
        choices=['php', 'external'],
        default='php',
        help='Web server to use. Default to PHP\'s built-in. '
        '"external" assumes that the local MediaWiki site can be accessed'
        ' via an already running web server.',
    )
    web.add_argument(
        '--web-php-workers',
        type=int,
        help='Number of workers for the php built-in webserver, '
        'or set PHP_CLI_SERVER_WORKERS environment variable. '
        'Requires PHP 7.4+',
    )
    web.add_argument(
        '--web-url', help='Base URL where MediaWiki can be accessed.'
    )
    parser.add_argument(
        'projects',
        default=[],
        nargs='*',
        help='MediaWiki extensions and skins to clone. Always clone '
        'mediawiki/core and mediawiki/skins/Vector. '
        'If $ZUUL_PROJECT is set, it will be cloned as well.',
    )

    stages_args = parser.add_argument_group(
        'Stages',
        description=(
            'Quibble runs all test commands (stages) by default. '
            'Use the --run or --skip options to further refine which commands '
            'will be run. '
            'Available stages are: %s' % ', '.join(known_stages)
        ),
    )

    # Magic type for add_argument so that --foo=a,b,c is magically stored
    # as: foo=['a', 'b', 'c']
    def comma_separated_list(string):
        return string.split(',')

    stages_choices = MultipleChoices(known_stages)
    stages_args.add_argument(
        '--run',
        default=[],
        type=comma_separated_list,
        choices=stages_choices,
        metavar='STAGE[,STAGE ...]',
        help='Tests to run. Comma separated. (default: run all stages).',
    )
    stages_args.add_argument(
        '--skip',
        default=[],
        type=comma_separated_list,
        choices=stages_choices,
        metavar='STAGE[,STAGE ...]',
        help='Stages to skip. Comma separated. '
        'Set to "all" to skip all stages. '
        '(default: none). ',
    )

    command_args = stages_args.add_mutually_exclusive_group()
    command_args.add_argument(
        '-c',
        '--command',
        action='append',
        dest='commands',
        metavar='COMMAND',
        help=(
            'Run given command instead of built-in stages. '
            'Each command is executed relatively to '
            'MediaWiki installation path.'
        ),
    )
    command_args.add_argument(
        '--commands',
        default=[],
        nargs='*',
        metavar='COMMAND',
        help=('DEPRECATED: use -c COMMAND -c COMMAND'),
    )

    return parser


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('quibble').setLevel(logging.DEBUG)

    args = _parse_arguments(sys.argv[1:])

    if args.color:
        quibble.colored_logging()

    cmd = QuibbleCmd()
    project_dir, plan = cmd.build_execution_plan(args)

    cmd.execute(
        plan,
        project_dir=project_dir,
        reporting_url=args.reporting_url,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
