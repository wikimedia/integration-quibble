#!/usr/bin/env python3

import argparse
import json
import logging
import os
import os.path
import pkg_resources
from shutil import copyfile
import subprocess
import tempfile

import quibble
import quibble.mediawiki.maintenance
import quibble.backend
import quibble.test


class QuibbleCmd(object):

    log = logging.getLogger('quibble.cmd')

    def __init__(self):
        self.dependencies = []
        self.extra_dependencies = []
        # Hold backend objects so they do not get garbage collected until end
        # of script.
        self.backends = {}

    def parse_arguments(self):
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
            default='composer',
            help='Source to install PHP dependencies from')
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
            default='sqlite',
            help='Database backed to use')
        parser.add_argument(
            '--git-cache',
            default='/srv/git' if quibble.is_in_docker() else 'ref',
            help='Path to bare git repositories to speed up git clone'
                 'operation. Passed to zuul-cloner as --cache-dir. '
                 'In Docker: /srv/git, else ref/'
            )
        parser.add_argument(
            '--workspace',
            default=os.environ.get('WORKSPACE', os.getcwd()),
            help='Base path to work from. Default: $WORKSPACE or $CWD'
            )
        return parser.parse_args()

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

        if 'WORKSPACE' not in os.environ:
            os.environ['WORKSPACE'] = self.workspace

        os.environ['MW_INSTALL_PATH'] = self.mw_install_path
        os.environ['MW_LOG_DIR'] = self.log_dir
        os.environ['TMPDIR'] = '/tmp'

    def get_repos_to_clone(self, clone_vendor=False):
        """
        Find repos to clone basedon passed arguments and environment
        """
        self.dependencies.append('mediawiki/core')
        if clone_vendor:
            self.log.info('Will clone mediawiki/vendor')
            self.dependencies.append('mediawiki/vendor')

        self.log.info('Repositories to clone: %s'
                      % ', '.join(self.dependencies))

        return self.dependencies

    def prepare_sources(self):
        clone_vendor = (self.args.packages_source == 'vendor')
        projects_to_clone = self.get_repos_to_clone(clone_vendor)
        self.clonerepos(projects_to_clone)

    def clonerepos(self, repos):
        zuul_env = {k: v for k, v in os.environ.items()
                    if k.startswith('ZUUL_')}
        zuul_env['PATH'] = os.environ['PATH']

        try:
            temp_mapfile = ''
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as fp:
                temp_mapfile = fp.name
                # Map a repo to a target dir under workspace
                clone_map = json.dumps({'clonemap': [
                    {'name': 'mediawiki/core',
                        'dest': '.'},
                    {'name': 'mediawiki/vendor',
                        'dest': './vendor'},
                    {'name': 'mediawiki/extensions/(.*)',
                        'dest': './extensions/\\1'},
                    {'name': 'mediawiki/skins/(.*)',
                        'dest': './skins/\\1'},
                    ]
                })
                fp.write(clone_map)
                fp.close()
                cmd = [
                    'zuul-cloner',
                    '--color',
                    '--verbose',
                    '--map', temp_mapfile,
                    '--workspace', os.path.join(self.workspace, 'src'),
                    '--cache-dir', self.args.git_cache,
                    'https://gerrit.wikimedia.org/r/p',
                    ]
                cmd.extend(repos)
                subprocess.check_call(cmd, env=zuul_env)
        finally:
            if temp_mapfile:
                os.remove(temp_mapfile)

    def generate_extensions_load(self):
        extension_path = os.path.join(
                self.workspace, 'src', 'extensions_load.txt')
        with open(extension_path, 'w') as f:
            f.writelines(self.extra_dependencies)

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
        for dependency, version in composer['require-dev'].items():
            req = '='.join([dependency, version])
            self.log.debug('composer require %s' % req)
            subprocess.check_call([
                'composer', 'require', '--dev', '--ansi', '--no-progress',
                '--prefer-dist', '-v', req],
                cwd=vendor_dir)
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

        def logdest(fname):
            return os.path.join(self.log_dir, fname)

        copyfile(mw_composer_json,
                 logdest('composer.core.json.txt'))

        copyfile(os.path.join(vendor_dir, 'composer.json'),
                 logdest('composer.vendor.json.txt'))

        copyfile(os.path.join(vendor_dir, 'composer/autoload_files.php'),
                 logdest('composer.autoload_files.php.txt'))

    def execute(self):
        logging.basicConfig(level=logging.DEBUG)
        self.args = self.parse_arguments()

        self.workspace = self.args.workspace
        self.mw_install_path = os.path.join(self.workspace, 'src')
        self.log_dir = os.path.join(self.workspace, 'log')
        os.makedirs(self.log_dir, exist_ok=True)

        self.setup_environment()
        if not self.args.skip_zuul:
            self.prepare_sources()
        self.generate_extensions_load()
        self.mw_install()

        if not self.args.skip_deps:
            if self.args.packages_source == 'vendor':
                self.log.info('Requiring composer dev dependencies')
                self.fetch_composer_dev()

            subprocess.check_call(['npm', 'prune'], cwd=self.mw_install_path)
            subprocess.check_call(['npm', 'install'], cwd=self.mw_install_path)

        self.log.info("PHPUnit without Database group")
        quibble.test.run_phpunit(
            mwdir=self.mw_install_path,
            exclude_group=['Database'])

        with quibble.backend.DevWebServer(
                mwdir=self.mw_install_path,
                port=9412):
            quibble.test.run_qunit(self.mw_install_path)

            with quibble.backend.ChromeWebDriver():
                subprocess.check_call([
                    'node_modules/.bin/grunt', 'webdriver:test'],
                    cwd=self.mw_install_path,
                    env={
                        'MW_SERVER': 'http://127.0.0.1:9412',
                        'MW_SCRIPT_PATH': '',
                        'FORCE_COLOR': '1',  # for 'supports-color'
                        'MEDIAWIKI_USER': 'WikiAdmin',
                        'MEDIAWIKI_PASSWORD': 'testpass',
                        })

        self.log.info("PHPUnit Database group")
        quibble.test.run_phpunit(
            mwdir=self.mw_install_path,
            group=['Database'])


def main():
    cmd = QuibbleCmd()
    cmd.execute()


if __name__ == '__main__':
    main()
