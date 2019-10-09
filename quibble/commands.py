"""Encapsulates each step of a job"""

from contextlib import ExitStack
import json
import logging
import os
import os.path
import pkg_resources
from quibble.gitchangedinhead import GitChangedInHead
from quibble.util import copylog, parallel_run, isExtOrSkin
import quibble.mediawiki.registry
import quibble.zuul
import shutil
import subprocess

log = logging.getLogger(__name__)
HTTP_HOST = '127.0.0.1'
HTTP_PORT = 9412


def server_url():
    return 'http://%s:%s' % (HTTP_HOST, HTTP_PORT)


class ReportVersions:
    def execute(self):
        commands = [
            ['chromedriver', '--version'],
            ['chromium', '--version'],
            ['composer', '--version'],
            ['node', '--version'],
            ['npm', '--version'],
            ['php', '--version'],
        ]
        for cmd in commands:
            self.logged_call(cmd)

    def logged_call(self, cmd):
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            message = '{}: {}'.format(
                ' '.join(cmd),
                res.strip().decode('utf-8'))
            for line in message.split('\n'):
                log.info(line)
        except subprocess.CalledProcessError:
            log.error('Failed to run command: %s', ' '.join(cmd))
        except FileNotFoundError:
            log.error('Command not found: %s', ' '.join(cmd))

    def __str__(self):
        return 'Report package versions'


class ZuulCloneCommand:
    def __init__(self, branch, cache_dir, project_branch, projects, workers,
                 workspace, zuul_branch, zuul_newrev, zuul_project, zuul_ref,
                 zuul_url):
        self.branch = branch
        self.cache_dir = cache_dir
        self.project_branch = project_branch
        self.projects = projects
        self.workers = workers
        self.workspace = workspace
        self.zuul_branch = zuul_branch
        self.zuul_newrev = zuul_newrev
        self.zuul_project = zuul_project
        self.zuul_ref = zuul_ref
        self.zuul_url = zuul_url

    def execute(self):
        quibble.zuul.clone(
            self.branch, self.cache_dir, self.project_branch, self.projects,
            self.workers, self.workspace, self.zuul_branch, self.zuul_newrev,
            self.zuul_project, self.zuul_ref, self.zuul_url)

    def __str__(self):
        pruned_params = {k: v for k, v in self.__dict__.items()
                         if v is not None and v != []}
        return "Zuul clone with parameters {}".format(
            json.dumps(pruned_params))


class ResolveRequiresCommand:

    def __init__(
        self, mw_install_path, projects, zuul_params,
        fail_on_extra_requires=False
    ):
        """
        mw_install_path: root dir of MediaWiki
        projects: list of Gerrit projects to initially clone
        zuul_params: other parameters for ZuulCloneCommand
        fail_on_extra_requires: if any repositories has been cloned and has
        not been given in the initial list of projects, raise an exception.
        """
        self.mw_install_path = mw_install_path
        self.projects = projects
        self.zuul_params = zuul_params
        if 'projects' in self.zuul_params:
            del(self.zuul_params['projects'])
        self.fail_on_extra_requires = fail_on_extra_requires

    def execute(self):
        log.info('Recursively processing registration dependencies')

        ext_cloned = set(filter(isExtOrSkin, self.projects))
        with quibble.logginglevel('zuul.CloneMapper', logging.WARNING):
            required = self.clone_requires(ext_cloned, ext_cloned)
        extras = set(required) - set(self.projects)

        msg = 'Found extra requirements: %s' % ', '.join(extras)
        if extras and self.fail_on_extra_requires:
            raise Exception(msg)
        else:
            log.warning(msg)

        log.info('Done preparing registration dependencies')

    def clone_requires(self, new_projects, cloned):
        to_be_cloned = new_projects - cloned
        if to_be_cloned:
            log.info('Cloning: %s', ', '.join(to_be_cloned))
            ZuulCloneCommand(
                projects=to_be_cloned,
                **self.zuul_params
            ).execute()

        found = set()
        for project in sorted(new_projects):
            log.info('Looking for requirements of %s', project)

            project_dir = os.path.join(
                self.mw_install_path,
                quibble.zuul.repo_dir(project))
            deps = quibble.mediawiki.registry.from_path(project_dir)
            found.update(deps.getRequiredRepos())

        if not found:
            log.debug('No additional requirements from %s',
                      ', '.join(new_projects))
            return set()

        if found:
            log.info('Found requirement(s): %s', ', '.join(found))
            return found.union(self.clone_requires(found, cloned))

    def __str__(self):
        return (
            'Recursively process registration dependencies. '
            'Fails on extra requires: %s' % self.fail_on_extra_requires)


class ExtSkinSubmoduleUpdateCommand:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        log.info('Updating git submodules of extensions and skins')

        cmds = [
            ['git', 'submodule', 'foreach', 'git', 'clean', '-xdff', '-q'],
            ['git', 'submodule', 'update', '--init', '--recursive'],
            ['git', 'submodule', 'status'],
        ]

        tops = [os.path.join(self.mw_install_path, top)
                for top in ['extensions', 'skins']]

        for top in tops:
            for dirpath, dirnames, filenames in os.walk(top):
                if dirpath not in tops:
                    # Only look at the first level
                    dirnames[:] = []
                if '.gitmodules' not in filenames:
                    continue

                for cmd in cmds:
                    try:
                        subprocess.check_call(cmd, cwd=dirpath)
                    except subprocess.CalledProcessError as e:
                        log.error(
                            "Failed to process git submodules for %s",
                            dirpath)
                        raise e

    def __str__(self):
        # TODO: Would be nicer to extract the directory crawl into a subroutine
        # and print the analysis here.
        return "Extension and skin submodule update under MediaWiki root {}"\
            .format(self.mw_install_path)


# Used to be bin/mw-create-composer-local.py
class CreateComposerLocal:
    def __init__(self, mw_install_path, dependencies):
        self.mw_install_path = mw_install_path
        self.dependencies = dependencies

    def execute(self):
        log.info('composer.local.json for merge plugin')
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
        log.info('Created composer.local.json')

    def __str__(self):
        return "Create composer.local.json with dependencies {}".format(
            self.dependencies)


class ExtSkinComposerNpmTest:
    def __init__(self, directory, composer, npm):
        self.directory = directory
        self.composer = composer
        self.npm = npm

    def execute(self):
        tasks = []
        if self.composer:
            tasks.append((self.run_extskin_composer, ))
        if self.npm:
            tasks.append((self.run_extskin_npm, ))

        # TODO: Split these tasks and move parallelism into calling logic.
        parallel_run(tasks)

        log.info('%s: git clean -xqdf', self.directory)
        subprocess.check_call(['git', 'clean', '-xqdf'],
                              cwd=self.directory)

    def run_extskin_composer(self):
        project_name = os.path.basename(self.directory)

        if not os.path.exists(os.path.join(self.directory, 'composer.json')):
            log.warning("%s lacks a composer.json", project_name)
            return

        log.info('Running "composer test" for %s', project_name)
        cmds = [
            ['composer', '--ansi', 'validate', '--no-check-publish'],
            ['composer', '--ansi', 'install', '--no-progress',
             '--prefer-dist', '--profile', '-v'],
            ['composer', '--ansi', 'test'],
        ]
        for cmd in cmds:
            subprocess.check_call(cmd, cwd=self.directory)

    def run_extskin_npm(self):
        project_name = os.path.basename(self.directory)

        # FIXME: copy paste is terrible
        # TODO: Detect test existence in an earlier phase.
        if not os.path.exists(os.path.join(self.directory, 'package.json')):
            log.warning("%s lacks a package.json", project_name)
            return

        log.info('Running "npm test" for %s', project_name)
        cmds = [
            ['npm', 'prune'],
            ['npm', 'install', '--no-progress', '--prefer-offline'],
            ['npm', 'test'],
        ]
        for cmd in cmds:
            subprocess.check_call(cmd, cwd=self.directory)

    def __str__(self):
        tests = []
        if self.composer:
            tests.append("composer")
        if self.npm:
            tests.append("npm")
        return "Extension and skin tests: {}".format(", ".join(tests))


class CoreNpmComposerTest:
    def __init__(self, mw_install_path, composer, npm):
        self.mw_install_path = mw_install_path
        self.composer = composer
        self.npm = npm

    def execute(self):
        tasks = []
        if self.composer:
            tasks.append((self.run_composer_test, ))
        if self.npm:
            tasks.append((self.run_npm_test, ))

        # TODO: Split these tasks and move parallelism into calling logic.
        parallel_run(tasks)

    def run_composer_test(self):
        files = []
        changed = GitChangedInHead([], cwd=self.mw_install_path).changedFiles()
        if 'composer.json' in changed or '.phpcs.xml' in changed:
            log.info(
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
            log.info('Skipping composer test (unneeded)')
        else:
            log.info("Running composer test")

            env = {'COMPOSER_PROCESS_TIMEOUT': '900'}
            env.update(os.environ)

            composer_test_cmd = ['composer', 'test']
            composer_test_cmd.extend(files)
            subprocess.check_call(
                composer_test_cmd, cwd=self.mw_install_path, env=env)

    def run_npm_test(self):
        log.info("Running npm test")
        subprocess.check_call(['npm', 'test'], cwd=self.mw_install_path)

    def __str__(self):
        tests = []
        if self.composer:
            tests.append("composer")
        if self.npm:
            tests.append("npm")
        return "Run tests in mediawiki/core: {}".format(", ".join(tests))


class NativeComposerDependencies:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        log.info('Running "composer update" for mediawiki/core')
        cmd = ['composer', 'update',
               '--ansi', '--no-progress', '--prefer-dist',
               '--profile', '-v',
               ]
        subprocess.check_call(cmd, cwd=self.mw_install_path)

    def __str__(self):
        return "Run composer update for mediawiki/core"


class VendorComposerDependencies:
    def __init__(self, mw_install_path, log_dir):
        self.mw_install_path = mw_install_path
        self.log_dir = log_dir

    def execute(self):
        log.info('vendor.git used. '
                 'Requiring composer dev dependencies')
        mw_composer_json = os.path.join(self.mw_install_path, 'composer.json')
        vendor_dir = os.path.join(self.mw_install_path, 'vendor')
        with open(mw_composer_json, 'r') as f:
            composer = json.load(f)

        reqs = ['='.join([dependency, version])
                for dependency, version in composer['require-dev'].items()]

        log.debug('composer require %s', ' '.join(reqs))
        composer_require = ['composer', 'require', '--dev', '--ansi',
                            '--no-progress', '--prefer-dist', '-v']
        composer_require.extend(reqs)

        subprocess.check_call(composer_require, cwd=vendor_dir)

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

        copylog(mw_composer_json,
                os.path.join(self.log_dir, 'composer.core.json.txt'))
        copylog(os.path.join(vendor_dir, 'composer.json'),
                os.path.join(self.log_dir, 'composer.vendor.json.txt'))
        copylog(os.path.join(vendor_dir, 'composer/autoload_files.php'),
                os.path.join(self.log_dir, 'composer.autoload_files.php.txt'))

    def __str__(self):
        return "Install composer dev-requires for vendor.git"


class NpmInstall:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        subprocess.check_call(['npm', 'prune'], cwd=self.directory)
        subprocess.check_call(
            ['npm', 'install', '--no-progress', '--prefer-offline'],
            cwd=self.directory)

    def __str__(self):
        return "npm install in {}".format(self.directory)


class InstallMediaWiki:

    db_backend = None

    def __init__(self, mw_install_path, db_engine, db_dir, dump_dir,
                 log_dir, use_vendor):
        self.mw_install_path = mw_install_path
        self.db_engine = db_engine
        self.db_dir = db_dir
        self.dump_dir = dump_dir
        self.log_dir = log_dir
        self.use_vendor = use_vendor

    def execute(self):
        dbclass = quibble.backend.getDBClass(engine=self.db_engine)
        db = dbclass(base_dir=self.db_dir, dump_dir=self.dump_dir)
        # hold a reference to prevent gc
        InstallMediaWiki.db_backend = db
        db.start()

        # TODO: Better if we can calculate the install args before
        # instantiating the database.
        install_args = [
            '--scriptpath=',
            '--server=%s' % server_url(),
            '--dbtype=%s' % self.db_engine,
            '--dbname=%s' % db.dbname,
        ]
        if self.db_engine == 'sqlite':
            install_args.extend([
                '--dbpath=%s' % db.rootdir,
            ])
        elif self.db_engine in ('mysql', 'postgres'):
            install_args.extend([
                '--dbuser=%s' % db.user,
                '--dbpass=%s' % db.password,
                '--dbserver=%s' % db.dbserver,
            ])
        else:
            raise Exception('Unsupported database: %s' % self.db_engine)

        quibble.mediawiki.maintenance.install(
            args=install_args,
            mwdir=self.mw_install_path
        )

        localsettings = os.path.join(self.mw_install_path, 'LocalSettings.php')
        localsettings_installer = \
            os.path.join(self.mw_install_path, 'LocalSettings-installer.php')
        quibblesettings = pkg_resources.resource_filename(
            __name__, 'mediawiki/local_settings.php')

        os.rename(localsettings, localsettings_installer)
        shutil.copyfile(quibblesettings, localsettings)

        copylog(localsettings,
                os.path.join(self.log_dir, 'LocalSettings.php'))
        copylog(localsettings_installer,
                os.path.join(self.log_dir, 'LocalSettings-installer.php'))
        subprocess.check_call(
            ['php', '-l', localsettings, localsettings_installer])

        update_args = []
        if self.use_vendor:
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
            log.info('mediawiki/vendor used. '
                     'Skipping external dependencies')
            update_args.append('--skip-external-dependencies')

        quibble.mediawiki.maintenance.update(
            args=update_args,
            mwdir=self.mw_install_path
        )
        quibble.mediawiki.maintenance.rebuildLocalisationCache(
            lang=['en'], mwdir=self.mw_install_path)

    def __str__(self):
        return "Install MediaWiki, db={} db_dir={} vendor={}".format(
            self.db_engine, self.db_dir, self.use_vendor)


class AbstractPhpUnit:
    def run_phpunit(self, group=[], exclude_group=[], cmd=None):
        log.info(self)

        always_excluded = ['Broken', 'ParserFuzz', 'Stub']
        if not cmd:
            cmd = ['php', 'tests/phpunit/phpunit.php', '--debug-tests']
        if self.testsuite:
            cmd.extend(['--testsuite', self.testsuite])

        if group:
            cmd.extend(['--group', ','.join(group)])

        cmd.extend(['--exclude-group',
                    ','.join(always_excluded + exclude_group)])

        if self.junit_file:
            cmd.extend(['--log-junit', self.junit_file])
        log.info(' '.join(cmd))

        phpunit_env = {}
        phpunit_env.update(os.environ)
        phpunit_env.update({'LANG': 'C.UTF-8'})

        subprocess.check_call(cmd, cwd=self.mw_install_path, env=phpunit_env)


class PhpUnitDatabaseless(AbstractPhpUnit):
    def __init__(self, mw_install_path, testsuite, log_dir):
        self.mw_install_path = mw_install_path
        self.testsuite = testsuite
        self.log_dir = log_dir
        self.junit_file = os.path.join(self.log_dir, 'junit-dbless.xml')

    def execute(self):
        # XXX might want to run the triggered extension first then the
        # other tests.
        # XXX some mediawiki/core smoke PHPunit tests should probably
        # be run as well.
        self.run_phpunit(exclude_group=['Database'])

    def __str__(self):
        return "PHPUnit {} suite (without database)".format(
            self.testsuite or 'default')


class PhpUnitUnit(AbstractPhpUnit):
    def __init__(self, mw_install_path, log_dir):
        self.mw_install_path = mw_install_path
        self.log_dir = log_dir
        self.testsuite = None
        self.junit_file = os.path.join(self.log_dir, 'junit-unit.xml')

    def execute(self):
        if repo_has_composer_script(self.mw_install_path, 'phpunit:unit'):
            self.run_phpunit(cmd=['composer', 'phpunit:unit', '--'])
        else:
            log.debug('skipping phpunit:unit stage, script is not present')
            return

    def __str__(self):
        return "PHPUnit unit tests"


class PhpUnitDatabase(AbstractPhpUnit):
    def __init__(self, mw_install_path, testsuite, log_dir):
        self.mw_install_path = mw_install_path
        self.testsuite = testsuite
        self.log_dir = log_dir
        self.junit_file = os.path.join(self.log_dir, 'junit-db.xml')

    def execute(self):
        self.run_phpunit(group=['Database'])

    def __str__(self):
        return "PHPUnit {} suite (with database)".format(
            self.testsuite or 'default')


class QunitTests:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        with quibble.backend.DevWebServer(
                mwdir=self.mw_install_path,
                host=HTTP_HOST,
                port=HTTP_PORT):
            self.run_qunit()

    def run_qunit(self):
        karma_env = {
             'CHROME_BIN': '/usr/bin/chromium',
             'MW_SERVER': server_url(),
             'MW_SCRIPT_PATH': '/',
             'FORCE_COLOR': '1',  # for 'supports-color'
             }
        karma_env.update(os.environ)
        karma_env.update({'CHROMIUM_FLAGS': quibble.chromium_flags()})

        subprocess.check_call(
            ['./node_modules/.bin/grunt', 'qunit'],
            cwd=self.mw_install_path,
            env=karma_env,
        )

    def __str__(self):
        return "Run Qunit tests"


class BrowserTests:
    def __init__(self, mw_install_path, projects, display):
        self.mw_install_path = mw_install_path
        self.projects = projects
        self.display = display

    def execute(self):
        with quibble.backend.DevWebServer(
                mwdir=self.mw_install_path,
                host=HTTP_HOST,
                port=HTTP_PORT):
            self.run_selenium()

    def run_selenium(self):
        with ExitStack() as stack:
            if not self.display:
                self.display = ':94'  # XXX racy when run concurrently!
                log.info("No DISPLAY, using Xvfb.")
                stack.enter_context(
                    quibble.backend.Xvfb(display=self.display))

            with quibble.backend.ChromeWebDriver(display=self.display):
                for project in self.projects:
                    project_dir = os.path.normpath(os.path.join(
                        self.mw_install_path,
                        quibble.zuul.repo_dir(project)))
                    if repo_has_npm_script(project_dir, 'selenium-test'):
                        self.run_webdriver(project_dir)

    def run_webdriver(self, project_dir):
        log.info('Running webdriver test in %s', project_dir)
        webdriver_env = {}
        webdriver_env.update(os.environ)
        webdriver_env.update({
            'MW_SERVER': server_url(),
            'MW_SCRIPT_PATH': '/',
            'FORCE_COLOR': '1',  # for 'supports-color'
            'MEDIAWIKI_USER': 'WikiAdmin',
            'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
            'DISPLAY': self.display,
        })

        subprocess.check_call(
            ['npm', 'install', '--prefer-offline'],
            cwd=project_dir)
        subprocess.check_call(
            ['npm', 'run', 'selenium-test'],
            cwd=project_dir,
            env=webdriver_env)

    def __str__(self):
        return "Browser tests using DISPLAY={}, for projects {}".format(
            self.display or "Xvfb",
            ", ".join(self.projects))


class UserCommands:
    def __init__(self, mw_install_path, commands):
        self.mw_install_path = mw_install_path
        self.commands = commands

    def execute(self):
        log.info('User commands')
        with quibble.backend.DevWebServer(
                mwdir=self.mw_install_path,
                host=HTTP_HOST,
                port=HTTP_PORT):
            log.info('working directory: %s', self.mw_install_path)

            for cmd in self.commands:
                log.info(cmd)
                subprocess.check_call(
                    cmd, shell=True, cwd=self.mw_install_path)

    def __str__(self):
        return "User commands: {}".format(", ".join(self.commands))


def repo_has_composer_script(project_dir, script_name):
    composer_path = os.path.join(project_dir, 'composer.json')
    return json_has_script(composer_path, script_name)


def repo_has_npm_script(project_dir, script_name):
    package_path = os.path.join(project_dir, 'package.json')
    return json_has_script(package_path, script_name)


def json_has_script(json_file, script_name):
    if not os.path.exists(json_file):
        return False
    with open(json_file) as f:
        spec = json.load(f)
    return ('scripts' in spec
            and script_name in spec['scripts'])
