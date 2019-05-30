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
from contextlib import ExitStack
import logging
import os
import subprocess
import sys
import tempfile

import quibble
import quibble.mediawiki.maintenance
import quibble.backend
import quibble.test
import quibble.zuul
import quibble.commands


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
    stages = ['phpunit', 'npm-test', 'composer-test', 'qunit', 'selenium']
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
            '--skip-deps',
            action='store_true',
            help='Do not run composer/npm')
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
            default=os.path.join(self.default_workspace, 'log'),
            help='Where logs and artifacts will be written to. '
            'Default: "log" relatively to workspace'
            )
        parser.add_argument(
            'projects', default=[], nargs='*',
            help='MediaWiki extensions and skins to clone. Always clone '
                 'mediawiki/core and mediawiki/skins/Vector. '
                 'If $ZUUL_PROJECT is set, it will be cloned as well.'
            )

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

    def set_repos_to_clone(self, projects=[], clone_vendor=False):
        """
        Find repos to clone basedon passed arguments and environment
        """
        # mediawiki/core should be first else git clone will fail because the
        # destination directory already exists.
        self.dependencies.insert(0, 'mediawiki/core')
        self.dependencies.append('mediawiki/skins/Vector')
        if clone_vendor:
            self.log.info('Adding mediawiki/vendor')
            self.dependencies.append('mediawiki/vendor')

        if 'ZUUL_PROJECT' in os.environ:
            zuul_project = os.environ.get('ZUUL_PROJECT')
            if zuul_project not in self.dependencies:
                self.dependencies.append(zuul_project)

        if 'SKIN_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('SKIN_DEPENDENCIES')
            self.dependencies.extend(
                os.environ.get('SKIN_DEPENDENCIES').split('\\n'))

        if 'EXT_DEPENDENCIES' in os.environ:
            self._warn_obsolete_env_deps('EXT_DEPENDENCIES')
            self.dependencies.extend(
                os.environ.get('EXT_DEPENDENCIES').split('\\n'))

        self.dependencies.extend(projects)

        self.log.info('Projects: %s'
                      % ', '.join(self.dependencies))

        return self.dependencies

    def clone(self, projects):
        quibble.commands.ZuulCloneCommand(
            branch=self.args.branch,
            cache_dir=self.args.git_cache,
            project_branch=self.args.project_branch,
            projects=projects,
            workers=self.args.git_parallel,
            workspace=os.path.join(self.workspace, 'src'),
            zuul_branch=os.getenv('ZUUL_BRANCH'),
            zuul_newrev=os.getenv('ZUUL_NEWREV'),
            zuul_project=os.getenv('ZUUL_PROJECT'),
            zuul_ref=os.getenv('ZUUL_REF'),
            zuul_url=os.getenv('ZUUL_URL')
        ).execute()

    def mw_install(self):
        quibble.commands.InstallMediaWiki(
            mw_install_path=self.mw_install_path,
            db_engine=self.args.db,
            db_dir=self.db_dir,
            dump_dir=self.dump_dir,
            log_dir=self.log_dir,
            use_vendor=(self.args.packages_source == 'vendor')).execute()

    def isCoreOrVendor(self, project):
        return project == 'mediawiki/core' or project == 'mediawiki/vendor'

    def isExtOrSkin(self, project):
        return project.startswith(
            ('mediawiki/extensions/', 'mediawiki/skins/')
        )

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

    def execute(self):
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('quibble').setLevel(logging.DEBUG)
        quibble.colored_logging()

        self.args = self.parse_arguments()

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
            self.log.warning('ZUUL_PROJECT not set. Assuming mediawiki/core')
            zuul_project = 'mediawiki/core'
        else:
            self.log.debug("ZUUL_PROJECT=%s" % zuul_project)

        projects_to_clone = self.set_repos_to_clone(
            projects=self.args.projects,
            clone_vendor=(self.args.packages_source == 'vendor'))

        if not self.args.skip_zuul:
            self.clone(projects_to_clone)
            quibble.commands.ExtSkinSubmoduleUpdateCommand(
                self.mw_install_path).execute()

        if self.isExtOrSkin(zuul_project):
            run_composer = self.should_run('composer-test')
            run_npm = self.should_run('npm-test')
            if run_composer or run_npm:
                project_dir = os.path.join(
                    self.mw_install_path,
                    quibble.zuul.repo_dir(os.environ['ZUUL_PROJECT']))

                quibble.test.run_extskin(directory=project_dir,
                                         composer=run_composer, npm=run_npm)

                self.log.info('%s: git clean -xqdf' % project_dir)
                subprocess.check_call(['git', 'clean', '-xqdf'],
                                      cwd=project_dir)

        if not self.args.skip_deps and self.args.packages_source == 'composer':
            quibble.commands.CreateComposerLocal(
                self.mw_install_path, self.dependencies).execute()
            quibble.commands.ComposerComposerDependencies(
                self.mw_install_path).execute()

        self.mw_install()

        if not self.args.skip_deps:
            if self.args.packages_source == 'vendor':
                quibble.commands.VendorComposerDependencies(
                    self.mw_install_path, self.log_dir).execute()

            quibble.commands.NpmInstall(
                self.mw_install_path).execute()

        phpunit_testsuite = None
        if self.args.phpunit_testsuite:
            phpunit_testsuite = self.args.phpunit_testsuite
        elif zuul_project.startswith('mediawiki/extensions/'):
            phpunit_testsuite = 'extensions'
        elif zuul_project.startswith('mediawiki/skins/'):
            phpunit_testsuite = 'skins'

        if self.should_run('phpunit'):
            self.log.info("PHPUnit%swithout Database group" % (
                ' %s suite ' % (phpunit_testsuite or ' ')))
            # XXX might want to run the triggered extension first then the
            # other tests.
            # XXX some mediawiki/core smoke PHPunit tests should probably
            # be run as well.
            junit_dbless_file = os.path.join(
                self.log_dir, 'junit-dbless.xml')
            quibble.test.run_phpunit_databaseless(
                mwdir=self.mw_install_path,
                testsuite=phpunit_testsuite,
                junit_file=junit_dbless_file)

        if zuul_project == 'mediawiki/core':
            quibble.test.run_core(
                self.mw_install_path,
                composer=self.should_run('composer-test'),
                npm=self.should_run('npm-test')
            )

        http_port = 9412
        if self.should_run('qunit') or self.should_run('selenium'):
            with quibble.backend.DevWebServer(
                    mwdir=self.mw_install_path,
                    port=http_port):
                if self.should_run('qunit'):
                    quibble.test.run_qunit(self.mw_install_path,
                                           port=http_port)

                # Webdriver.io Selenium tests available since 1.29
                if self.should_run('selenium') and \
                        os.path.exists(os.path.join(
                            self.mw_install_path, 'tests/selenium')):
                    with ExitStack() as stack:
                        display = os.environ.get('DISPLAY', None)
                        if not display:
                            display = ':94'  # XXX racy when run concurrently!
                            self.log.info("No DISPLAY, using Xvfb.")
                            stack.enter_context(
                                quibble.backend.Xvfb(display=display))

                        with quibble.backend.ChromeWebDriver(display=display):
                            quibble.test.run_webdriver(
                                mwdir=self.mw_install_path,
                                port=http_port,
                                display=display)

        if self.should_run('phpunit'):
            self.log.info("PHPUnit%sDatabase group" % (
                ' %s suite ' % (phpunit_testsuite or ' ')))
            junit_db_file = os.path.join(
                self.log_dir, 'junit-db.xml')
            quibble.test.run_phpunit_database(
                mwdir=self.mw_install_path,
                testsuite=phpunit_testsuite,
                junit_file=junit_db_file)

        if self.args.commands:
            self.log.info('User commands')
            with quibble.backend.DevWebServer(
                    mwdir=self.mw_install_path,
                    port=http_port):
                quibble.test.commands(
                    self.args.commands,
                    cwd=self.mw_install_path)


def get_arg_parser():
    """
    Build an argparser with sane default values.

    Intended for documentation generation with sphinx-argparse.
    """
    cmd = QuibbleCmd()
    cmd.default_git_cache = 'ref'
    cmd.default_workspace = '.'
    cmd.default_logdir = './log'

    return cmd.get_arg_parser()


def main():
    cmd = QuibbleCmd()
    cmd.execute()


if __name__ == '__main__':
    main()
