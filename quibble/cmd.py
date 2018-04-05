#!/usr/bin/env python3

import argparse
from contextlib import ExitStack
import json
import logging
import os
import os.path
import pkg_resources
from shutil import copyfile
import subprocess
import sys

import quibble
from quibble.gitchangedinhead import GitChangedInHead
import quibble.mediawiki.maintenance
import quibble.backend
import quibble.test
import quibble.zuul


class QuibbleCmd(object):

    log = logging.getLogger('quibble.cmd')

    def __init__(self):
        self.dependencies = []
        self.extra_dependencies = []
        # Hold backend objects so they do not get garbage collected until end
        # of script.
        self.backends = {}

    def parse_arguments(self, args=sys.argv[1:]):
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
            choices=['sqlite', 'mysql'],
            default='mysql',
            help='Database backed to use. Default: mysql')
        parser.add_argument(
            '--git-cache',
            default='/srv/git' if quibble.is_in_docker() else 'ref',
            help='Path to bare git repositories to speed up git clone'
                 'operation. Passed to zuul-cloner as --cache-dir. '
                 'In Docker: "/srv/git", else "ref"')
        parser.add_argument(
            '--workspace',
            default='/workspace' if quibble.is_in_docker() else os.getcwd(),
            help='Base path to work from. In Docker: "/workspace", '
                 'else current working directory'
            )
        parser.add_argument(
            'projects', default=[], nargs='*',
            help='MediaWiki extensions and skins to clone'
            )

        return parser.parse_args(args)

    def copylog(self, src, dest):
        dest = os.path.join(self.log_dir, dest)
        self.log.info('Copying %s to %s' % (src, dest))
        copyfile(src, dest)

    def setup_environment(self):
        """
        Set and get needed environment variables.
        """
        if 'SKIN_DEPENDENCIES' in os.environ:
            self.dependencies.extend(
                os.environ.get('SKIN_DEPENDENCIES').split('\\n'))

        if 'EXT_DEPENDENCIES' in os.environ:
            self.extra_dependencies = os.environ.get(
                'EXT_DEPENDENCIES').split('\\n')
            self.dependencies.extend(self.extra_dependencies)

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
        os.environ['TMPDIR'] = '/tmp'

    def set_repos_to_clone(self, projects=[], clone_vendor=False):
        """
        Find repos to clone basedon passed arguments and environment
        """
        self.dependencies.append('mediawiki/core')
        self.dependencies.append('mediawiki/skins/Vector')
        if clone_vendor:
            self.log.info('Adding mediawiki/vendor')
            self.dependencies.append('mediawiki/vendor')

        self.dependencies.extend(projects)

        self.log.info('Projects: %s'
                      % ', '.join(self.dependencies))

        return self.dependencies

    def clone(self, projects):
        quibble.zuul.clone(
            projects,
            workspace=os.path.join(self.workspace, 'src'),
            cache_dir=self.args.git_cache)

    # Used to be bin/mw-create-composer-local.py
    def create_composer_local(self):
        self.log.info('composer.local.json for merge plugin')
        extensions = [ext.strip()[len('mediawiki/'):] + '/composer.json'
                      for ext in self.dependencies
                      if ext.strip().startswith('mediawiki/extensions/')]
        out = {
            'extra': {
                'merge-plugin': {'include': extensions}
                }
            }
        composer_local = os.path.join(self.mw_install_path,
                                      'composer.local.json')
        with open(composer_local, 'w') as f:
            json.dump(out, f)
        self.log.info('Created composer.local.json')

    def mw_install(self):
        dbclass = quibble.backend.getDBClass(engine=self.args.db)
        db = dbclass()
        self.backends['db'] = db  # hold a reference to prevent gc
        db.start()

        install_args = [
            '--scriptpath=',
            '--dbtype=%s' % self.args.db,
            '--dbname=%s' % db.dbname,
        ]
        if self.args.db == 'sqlite':
            install_args.extend([
                '--dbpath=%s' % db.datadir,
            ])
        elif self.args.db == 'mysql':
            install_args.extend([
                '--dbuser=%s' % db.user,
                '--dbpass=%s' % db.password,
                '--dbserver=localhost:%s' % db.socket,
            ])
        else:
            raise Exception('Unsupported database: %s' % self.args.db)

        quibble.mediawiki.maintenance.install(
            args=install_args,
            mwdir=self.mw_install_path
        )

        localsettings = os.path.join(self.mw_install_path, 'LocalSettings.php')
        with open(localsettings, 'a') as lf:
            extra_conf = subprocess.check_output([
                'php',
                pkg_resources.resource_filename(
                    __name__, 'mediawiki.d/_join.php')
                ])
            lf.write(extra_conf.decode())
        subprocess.check_call(['php', '-l', localsettings])
        self.copylog(localsettings, 'LocalSettings.php')

        update_args = []
        if (self.args.packages_source == 'vendor'):
            # When trying to update a library in mediawiki/core and
            # mediawiki/vendor, a circular dependency is produced as both
            # patches depend upon each other.
            #
            # All non-mediawiki/vendor jobs will skip checking for matching
            # versions and continue "at their own risk". mediawiki/vendor will
            # still check versions to make sure it stays in sync with MediaWiki
            # core.
            #
            # T88211
            self.log.info('mediawiki/vendor used. '
                          'Skipping external dependencies')
            update_args.append('--skip-external-dependencies')

        quibble.mediawiki.maintenance.update(
            args=update_args,
            mwdir=self.mw_install_path
        )

    def fetch_composer_dev(self):
        mw_composer_json = os.path.join(self.mw_install_path, 'composer.json')
        vendor_dir = os.path.join(self.mw_install_path, 'vendor')
        with open(mw_composer_json, 'r') as f:
            composer = json.load(f)

        reqs = ['='.join([dependency, version])
                for dependency, version in composer['require-dev'].items()]

        self.log.debug('composer require %s' % ' '.join(reqs))
        composer_require = ['composer', 'require', '--dev', '--ansi',
                            '--no-progress', '--prefer-dist', '-v']
        composer_require.extend(reqs)

        subprocess.check_call(composer_require, cwd=vendor_dir)

        if self.args.packages_source == 'vendor':
            # Point composer-merge-plugin to mediawiki/core.
            # That let us easily merge autoload-dev section and thus complete
            # the autoloader.
            # T158674
            subprocess.check_call([
                'composer', 'config',
                'extra.merge-plugin.include', mw_composer_json],
                cwd=vendor_dir)

        # FIXME integration/composer used to be outdated and broke the
        # autoloader. Since composer 1.0.0-alpha11 the following might not
        # be needed anymore.
        subprocess.check_call([
            'composer', 'dump-autoload', '--optimize'],
            cwd=vendor_dir)

        self.copylog(mw_composer_json, 'composer.core.json.txt')
        self.copylog(os.path.join(vendor_dir, 'composer.json'),
                     'composer.vendor.json.txt')
        self.copylog(os.path.join(vendor_dir, 'composer/autoload_files.php'),
                     'composer.autoload_files.php.txt')

    def isCoreOrVendor(self, project):
        return project == 'mediawiki/core' or project == 'mediawiki/vendor'

    def isExtOrSkin(self, project):
        return project.startswith(
            ('mediawiki/extensions/', 'mediawiki/skins/')
        )

    def execute(self):
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('quibble').setLevel(logging.DEBUG)
        quibble.colored_logging()

        self.args = self.parse_arguments()

        self.workspace = self.args.workspace
        self.mw_install_path = os.path.join(self.workspace, 'src')
        self.log_dir = os.path.join(self.workspace, 'log')
        os.makedirs(self.log_dir, exist_ok=True)

        self.setup_environment()

        projects_to_clone = self.set_repos_to_clone(
            projects=self.args.projects,
            clone_vendor=(self.args.packages_source == 'vendor'))

        if not self.args.skip_zuul:
            self.clone(projects_to_clone)

        zuul_project = os.environ.get('ZUUL_PROJECT', None)
        if zuul_project is None:
            self.log.warning('ZUUL_PROJECT not set. Assuming mediawiki/core')
            zuul_project = 'mediawiki/core'
        else:
            self.log.debug("ZUUL_PROJECT=%s" % zuul_project)

        if self.isExtOrSkin(zuul_project):
            project_dir = os.path.join(
                self.mw_install_path,
                quibble.zuul.repo_dir(os.environ['ZUUL_PROJECT']))
            quibble.test.run_extskin(directory=project_dir)

        if not self.args.skip_deps and self.args.packages_source == 'composer':
            self.create_composer_local()
            self.log.info('Running "composer update for mediawiki/core')
            cmd = ['composer', 'update',
                   '--ansi', '--no-progress', '--prefer-dist',
                   '--profile', '-v',
                   ]
            subprocess.check_call(cmd, cwd=self.mw_install_path)

        self.mw_install()

        if not self.args.skip_deps:
            if self.args.packages_source == 'vendor':
                self.log.info('vendor.git used. '
                              'Requiring composer dev dependencies')
                self.fetch_composer_dev()

            subprocess.check_call(['npm', 'prune'], cwd=self.mw_install_path)
            subprocess.check_call(['npm', 'install'], cwd=self.mw_install_path)

        if self.isCoreOrVendor(zuul_project):
            self.log.info("PHPUnit without Database group")
            quibble.test.run_phpunit(
                mwdir=self.mw_install_path,
                exclude_group=['Database'])
        elif self.isExtOrSkin(zuul_project):
            testsuite = None
            if zuul_project.startswith('mediawiki/extensions/'):
                testsuite = 'extensions'
            elif zuul_project.startswith('mediawiki/skins/'):
                testsuite = 'skins'
            if testsuite is None:
                raise Exception('Could not find a PHPUnit testsuite '
                                'for %s' % zuul_project)

            self.log.info('PHPUnit %s testsuite' % testsuite)
            # XXX might want to run the triggered extension first then the
            # other tests.
            # XXX some mediawiki/core smoke PHPunit tests should probably be
            # run as well.
            quibble.test.run_phpunit(
                mwdir=self.mw_install_path,
                testsuite=testsuite)
        else:
            raise Exception('Unrecognized zuul_project: %s' % zuul_project)

        if zuul_project == 'mediawiki/core':
            files = []
            changed = GitChangedInHead(
                    [],
                    cwd=self.mw_install_path).changedFiles()
            if 'composer.json' in changed or '.phpcs.xml' in changed:
                self.log.info(
                    'composer.json or .phpcs.xml changed: linting "."')
                # '.' is passed to composer lint which then pass it
                # to parallel-lint and phpcs
                files = ['.']
            else:
                files = GitChangedInHead(
                    ['php', 'php5', 'inc', 'sample'],
                    cwd=self.mw_install_path
                    ).changedFiles()

            if not files:
                self.log.info('Skipping composer test (unneeded)')
            else:
                composer_test_cmd = ['composer', 'test']
                composer_test_cmd.extend(files)
                subprocess.check_call(composer_test_cmd,
                                      cwd=self.mw_install_path)

            self.log.info("Running npm test")
            subprocess.check_call(['npm', 'test'], cwd=self.mw_install_path)

        with quibble.backend.DevWebServer(
                mwdir=self.mw_install_path,
                port=9412):
            quibble.test.run_qunit(self.mw_install_path)

            with ExitStack() as stack:
                display = os.environ.get('DISPLAY', None)
                if not display:
                    display = ':94'  # XXX racy when run concurrently!
                    self.log.info("No DISPLAY, using Xvfb.")
                    stack.enter_context(quibble.backend.Xvfb(display=display))

                with quibble.backend.ChromeWebDriver(display=display):
                    quibble.test.run_webdriver(
                        mwdir=self.mw_install_path,
                        display=display)

        if self.isCoreOrVendor(zuul_project):
            self.log.info("PHPUnit Database group")
            quibble.test.run_phpunit(
                mwdir=self.mw_install_path,
                group=['Database'])


def main():
    cmd = QuibbleCmd()
    cmd.execute()


if __name__ == '__main__':
    main()
