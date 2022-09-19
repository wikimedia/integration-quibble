"""Encapsulates each step of a job"""

import contextlib
import io
import json
import logging
import multiprocessing
import os
import os.path
import pkg_resources
from quibble.gitchangedinhead import GitChangedInHead
from quibble.util import copylog, isExtOrSkin, ProgressReporter
import quibble.mediawiki.registry
import quibble.zuul
import subprocess
import sys
import tempfile

log = logging.getLogger(__name__)
monitor_interval = 10


def execute_command(command):
    '''Shared decorator for execution'''
    with quibble.Chronometer(str(command), log.info):
        command.execute()


def _npm_install(project_dir):
    if _repo_has_npm_lock(project_dir):
        cmd = 'ci'
        if quibble.get_npm_command() == 'pnpm':
            cmd = 'install'
        subprocess.check_call(
            [quibble.get_npm_command(), cmd], cwd=project_dir
        )
    else:
        subprocess.check_call(
            [quibble.get_npm_command(), 'prune'], cwd=project_dir
        )
        subprocess.check_call(
            [
                quibble.get_npm_command(),
                'install',
                '--no-progress',
                '--prefer-offline',
            ],
            cwd=project_dir,
        )


class ReportVersions:
    def execute(self):
        log.info("Python version: %s", sys.version)

        commands = [
            ['chromedriver', '--version'],
            ['chromium', '--version'],
            ['composer', '--version'],
            ['mysql', '--version'],
            ['psql', '--version'],
            # ['sqlite', '--version'], php-sqlite3 doesn't provide a CLI
            ['node', '--version'],
            [quibble.get_npm_command(), '--version'],
            ['php', '--version'],
        ]
        for cmd in commands:
            self._logged_call(cmd)

    def _logged_call(self, cmd):
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            message = '{}: {}'.format(
                ' '.join(cmd), res.strip().decode('utf-8')
            )
            for line in message.split('\n'):
                log.info(line)
        except subprocess.CalledProcessError:
            log.warning('Failed to run command: %s', ' '.join(cmd))
        except FileNotFoundError:
            log.warning('Command not found: %s', ' '.join(cmd))

    def __str__(self):
        return 'Report package versions'


class ZuulClone:
    def __init__(
        self,
        branch,
        cache_dir,
        project_branch,
        projects,
        workers,
        workspace,
        zuul_branch,
        zuul_newrev,
        zuul_project,
        zuul_ref,
        zuul_url,
    ):
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
            self.branch,
            self.cache_dir,
            self.project_branch,
            self.projects,
            self.workers,
            self.workspace,
            self.zuul_branch,
            self.zuul_newrev,
            self.zuul_project,
            self.zuul_ref,
            self.zuul_url,
        )

    def __str__(self):
        pruned_params = {
            k: v for k, v in self.__dict__.items() if v is not None and v != []
        }
        return "Zuul clone with parameters {}".format(
            json.dumps(pruned_params, sort_keys=True)
        )


class ResolveRequires:
    def __init__(
        self,
        mw_install_path,
        projects,
        zuul_params,
        fail_on_extra_requires=False,
    ):
        """
        mw_install_path: root dir of MediaWiki
        projects: list of Gerrit projects to initially clone
        zuul_params: other parameters for ZuulClone
        fail_on_extra_requires: if any repositories has been cloned and has
        not been given in the initial list of projects, raise an exception.
        """
        self.mw_install_path = mw_install_path
        self.projects = projects
        self.zuul_params = zuul_params
        if 'projects' in self.zuul_params:
            del self.zuul_params['projects']
        self.fail_on_extra_requires = fail_on_extra_requires

    def execute(self):
        ext_cloned = set(filter(isExtOrSkin, self.projects))
        with quibble.logginglevel('zuul.CloneMapper', logging.WARNING):
            required = self._clone_requires(ext_cloned, ext_cloned)
        extras = set(required) - set(self.projects)

        msg = 'Found extra requirements: %s' % ', '.join(extras)
        if extras and self.fail_on_extra_requires:
            raise Exception(msg)
        else:
            log.warning(msg)

    def _clone_requires(self, new_projects, cloned):
        to_be_cloned = new_projects - cloned
        if to_be_cloned:
            log.info('Cloning: %s', ', '.join(to_be_cloned))
            execute_command(
                ZuulClone(projects=to_be_cloned, **self.zuul_params)
            )

        found = set()
        for project in sorted(new_projects):
            log.info('Looking for requirements of %s', project)

            project_dir = os.path.join(
                self.mw_install_path, quibble.zuul.repo_dir(project)
            )
            deps = quibble.mediawiki.registry.from_path(project_dir)
            found.update(deps.getRequiredRepos())

        if not found:
            log.debug(
                'No additional requirements from %s', ', '.join(new_projects)
            )
            return set()

        if found:
            log.info('Found requirement(s): %s', ', '.join(found))
            return found.union(self._clone_requires(found, cloned))

    def __str__(self):
        return (
            'Recursively process registration dependencies. '
            'Fails on extra requires: %s' % self.fail_on_extra_requires
        )


class ExtSkinSubmoduleUpdate:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        log.info('Updating git submodules of extensions and skins')

        cmds = [
            ['git', 'submodule', 'foreach', 'git', 'clean', '-xdff', '-q'],
            ['git', 'submodule', 'update', '--init', '--recursive'],
            ['git', 'submodule', 'status'],
        ]

        tops = [
            os.path.join(self.mw_install_path, top)
            for top in ['extensions', 'skins']
        ]

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
                            "Failed to process git submodules for %s", dirpath
                        )
                        raise e

    def __str__(self):
        # TODO: Would be nicer to extract the directory crawl into a subroutine
        # and print the analysis here.
        return (
            "Extension and skin submodule update under MediaWiki root {}"
        ).format(self.mw_install_path)


# Used to be bin/mw-create-composer-local.py
class CreateComposerLocal:
    def __init__(self, mw_install_path, dependencies):
        self.mw_install_path = mw_install_path
        self.dependencies = dependencies

    def execute(self):
        log.info('composer.local.json for merge plugin')
        composer_local = os.path.join(
            self.mw_install_path, 'composer.local.json'
        )
        with open(composer_local, 'w') as f:
            json.dump(
                {
                    "extra": {
                        "merge-plugin": {
                            "include": [
                                "extensions/*/composer.json",
                                "skins/*/composer.json",
                            ]
                        }
                    }
                },
                f,
            )
        log.info('Created composer.local.json')

    def __str__(self):
        return "Create composer.local.json with dependencies {}".format(
            self.dependencies
        )


class ExtSkinComposerTest:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        if _repo_has_composer_script(self.directory, 'test'):
            cmds = [
                ['composer', '--ansi', 'validate', '--no-check-publish'],
                [
                    'composer',
                    '--ansi',
                    'install',
                    '--no-progress',
                    '--prefer-dist',
                    '--profile',
                    '-v',
                ],
                ['composer', '--ansi', 'test'],
            ]
            for cmd in cmds:
                subprocess.check_call(cmd, cwd=self.directory)

    def __str__(self):
        return "composer test in {}".format(self.directory)


class NpmTest:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        if repo_has_npm_script(self.directory, 'test'):
            _npm_install(self.directory)
            subprocess.check_call(
                [quibble.get_npm_command(), 'test'], cwd=self.directory
            )
        else:
            log.warning("%s lacks a package.json", self.directory)

    def __str__(self):
        return "npm test in {}".format(self.directory)


class CoreComposerTest:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        files = []
        changed = GitChangedInHead([], cwd=self.mw_install_path).changedFiles()
        if 'composer.json' in changed or '.phpcs.xml' in changed:
            log.info('composer.json or .phpcs.xml changed: linting "."')
            # '.' is passed to composer lint which then pass it
            # to parallel-lint and phpcs
            files = ['.']
        else:
            files = GitChangedInHead(
                ['php', 'php5', 'inc', 'sample'], cwd=self.mw_install_path
            ).changedFiles()

        if not files:
            log.info('Skipping composer test (unneeded)')
        else:
            log.info("Running composer test for changed files")

            env = {'COMPOSER_PROCESS_TIMEOUT': '900'}
            env.update(os.environ)

            composer_test_cmd = ['composer', 'test-some']
            composer_test_cmd.extend(files)
            subprocess.check_call(
                composer_test_cmd, cwd=self.mw_install_path, env=env
            )

    def __str__(self):
        return "Run composer test in mediawiki/core"


class NativeComposerDependencies:
    def __init__(self, mw_install_path):
        self.mw_install_path = mw_install_path

    def execute(self):
        log.info('Running "composer update" for mediawiki/core')
        cmd = [
            'composer',
            'update',
            '--ansi',
            '--no-progress',
            '--prefer-dist',
            '--profile',
            '-v',
        ]
        subprocess.check_call(cmd, cwd=self.mw_install_path)

    def __str__(self):
        return "Run composer update for mediawiki/core"


class VendorComposerDependencies:
    def __init__(self, mw_install_path, log_dir):
        self.mw_install_path = mw_install_path
        self.log_dir = log_dir

    def execute(self):
        log.info('vendor.git used. ' 'Requiring composer dev dependencies')
        mw_composer_json = os.path.join(self.mw_install_path, 'composer.json')
        vendor_dir = os.path.join(self.mw_install_path, 'vendor')
        with open(mw_composer_json, 'r') as f:
            composer = json.load(f)

        reqs = [
            '='.join([dependency, version])
            for dependency, version in composer['require-dev'].items()
        ]

        log.debug('composer require %s', ' '.join(reqs))
        composer_require = [
            'composer',
            'require',
            '--dev',
            '--ansi',
            '--no-progress',
            '--prefer-dist',
            '-v',
        ]
        composer_require.extend(reqs)

        subprocess.check_call(composer_require, cwd=vendor_dir)

        # Point composer-merge-plugin to mediawiki/core.
        # That let us easily merge autoload-dev section and thus complete
        # the autoloader.
        # T158674
        subprocess.check_call(
            [
                'composer',
                'config',
                'extra.merge-plugin.include',
                mw_composer_json,
            ],
            cwd=vendor_dir,
        )

        # FIXME integration/composer used to be outdated and broke the
        # autoloader. Since composer 1.0.0-alpha11 the following might not
        # be needed anymore.
        subprocess.check_call(
            ['composer', 'dump-autoload', '--optimize'], cwd=vendor_dir
        )

        copylog(
            mw_composer_json,
            os.path.join(self.log_dir, 'composer.core.json.txt'),
        )
        copylog(
            os.path.join(vendor_dir, 'composer.json'),
            os.path.join(self.log_dir, 'composer.vendor.json.txt'),
        )
        copylog(
            os.path.join(vendor_dir, 'composer/autoload_files.php'),
            os.path.join(self.log_dir, 'composer.autoload_files.php.txt'),
        )

    def __str__(self):
        return "Install composer dev-requires for vendor.git"


class NpmInstall:
    def __init__(
        self, mw_install_path, project=None, with_package_command=None
    ):
        if not project:
            self.directory = mw_install_path
        else:
            self.directory = quibble.commands.get_project_dir(
                mw_install_path, project
            )
        self.with_package_command = with_package_command
        self.project = project

    def execute(self):
        if (
            self.with_package_command
            and not quibble.commands.repo_has_npm_script(
                self.directory, self.with_package_command
            )
        ):
            log.info(
                '%s command does not exist in project %s package.json, '
                'skipping npm install',
                self.with_package_command,
                self.project,
            )
            return
        _npm_install(self.directory)

    def __str__(self):
        return "npm install in {}".format(self.directory)


class StartBackends:
    """Start backends and add to a global context stack, to be destroyed in
    reverse order before application exit.
    """

    def __init__(self, context_stack, backends):
        self.context_stack = context_stack
        self.backends = backends

    def execute(self):
        """Atomically start each backend and add it to the shutdown stack."""
        for context in self.backends + [self._exit()]:
            self.context_stack.enter_context(context)

    def _service_names(self):
        return " ".join([str(backend) for backend in self.backends])

    @contextlib.contextmanager
    def _exit(self):
        """List which backends will be shut down.  This is run before the other
        shutdown tasks.
        """
        yield
        log.info("Shutting down backends: %s", self._service_names())

    def __str__(self):
        return "Start backends, {}".format(self._service_names())


class InstallMediaWiki:
    def __init__(
        self, mw_install_path, db, web_url, log_dir, tmp_dir, use_vendor
    ):
        self.mw_install_path = mw_install_path
        self.db = db
        self.web_url = web_url
        self.log_dir = log_dir
        self.tmp_dir = tmp_dir
        self.use_vendor = use_vendor

    def execute(self):
        # TODO: Better if we can calculate the install args before
        # instantiating the database.
        install_args = [
            '--scriptpath=',
            '--server=%s' % self.web_url,
            '--dbtype=%s' % self.db.type,
            '--dbname=%s' % self.db.dbname,
        ]
        if self.db.type == 'sqlite':
            install_args.extend(
                [
                    '--dbpath=%s' % self.db.rootdir,
                ]
            )
        elif self.db.type in ('mysql', 'postgres'):
            install_args.extend(
                [
                    '--dbuser=%s' % self.db.user,
                    '--dbpass=%s' % self.db.password,
                    '--dbserver=%s' % self.db.dbserver,
                ]
            )
        else:
            raise Exception('Unsupported database: %s' % self.db.type)

        quibble.mediawiki.maintenance.install(
            args=install_args, mwdir=self.mw_install_path
        )

        localsettings = os.path.join(self.mw_install_path, 'LocalSettings.php')
        localsettings_installer = os.path.join(
            self.mw_install_path, 'LocalSettings-installer.php'
        )
        quibblesettings = pkg_resources.resource_filename(
            __name__, 'mediawiki/local_settings.php.tpl'
        )

        # Wire variables into settings template.
        with open(quibblesettings, "r") as f:
            params = {
                'MW_LOG_DIR': self.log_dir,
                'TMPDIR': self.tmp_dir,
            }
            params_declaration = "\n".join(
                "const {} = '{}';".format(key, value)
                for (key, value) in params.items()
            )
            customsettings = f.read().replace(
                '{{params-declaration}}', params_declaration
            )

        os.rename(localsettings, localsettings_installer)
        with open(localsettings, "w") as f:
            f.write(customsettings)

        copylog(localsettings, os.path.join(self.log_dir, 'LocalSettings.php'))
        copylog(
            localsettings_installer,
            os.path.join(self.log_dir, 'LocalSettings-installer.php'),
        )
        subprocess.check_call(
            ['php', '-l', localsettings, localsettings_installer]
        )

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
            log.info(
                'mediawiki/vendor used. ' 'Skipping external dependencies'
            )
            update_args.append('--skip-external-dependencies')

        quibble.mediawiki.maintenance.addSite(
            args=[
                self.db.dbname,  # globalid
                'CI',  # site-group
                '--filepath=%s/$1' % self.web_url,
            ],
            mwdir=self.mw_install_path,
        )
        quibble.mediawiki.maintenance.update(
            args=update_args, mwdir=self.mw_install_path
        )
        quibble.mediawiki.maintenance.rebuildLocalisationCache(
            lang=['en'], mwdir=self.mw_install_path
        )

    def __str__(self):
        return "Install MediaWiki, db={} vendor={}".format(
            self.db, self.use_vendor
        )


class Phpbench:
    """
    See https://github.com/phpbench/phpbench / T291549
    """

    def __init__(self, directory, composer_install=False, aggregate=False):
        self.directory = directory
        self.composer_install = composer_install
        self.aggregate = aggregate

    def execute(self):
        log.info(self)
        if not _repo_has_composer_script(self.directory, 'phpbench'):
            log.info('No phpbench entry found in composer.json')
            return
        log.info('Running "composer phpbench" in %s', self.directory)
        if self.composer_install:
            cmd = [
                'composer',
                '--ansi',
                'install',
                '--no-progress',
                '--prefer-dist',
                '--profile',
                '-v',
            ]
            subprocess.check_call(cmd, cwd=self.directory)

        if not self.aggregate:
            subprocess.check_call(
                ['composer', '--ansi', 'phpbench'], cwd=self.directory
            )
        else:
            subprocess.check_call(
                ['git', 'checkout', 'HEAD~1'], cwd=self.directory
            )
            if _repo_has_composer_script(self.directory, 'phpbench'):
                cmds = [
                    ['composer', '--ansi', 'phpbench', '--', '--tag=original'],
                    # Checkout patch branch again so we can compare against
                    # the HEAD~1 commit
                    ['git', 'checkout', '-'],
                    [
                        'composer',
                        '--ansi',
                        'phpbench',
                        '--',
                        '--ref=original',
                        '--report=aggregate',
                    ],
                ]

                for cmd in cmds:
                    subprocess.check_call(cmd, cwd=self.directory)
            else:
                # HEAD~1 doesn't have phpbench in composer.json, so switch back
                # to the patch, eventually returning exit code 0
                subprocess.check_call(
                    ['git', 'checkout', '-'], cwd=self.directory
                )

        if self.composer_install:
            GitClean(self.directory).execute()

    def __str__(self):
        return "Run phpbench"


class AbstractPhpUnit:
    def get_phpunit_command(self, repo_path=None):
        if _repo_has_composer_script(
            self.mw_install_path, 'phpunit:entrypoint'
        ):
            phpunit_command = [
                'composer',
                'run',
                '--timeout=0',
                'phpunit:entrypoint',
                '--',
            ]
        else:
            phpunit_command = ['php', 'tests/phpunit/phpunit.php']
        if repo_path:
            phpunit_command.append(repo_path)
        return phpunit_command

    def _run_phpunit(self, group=[], exclude_group=[], cmd=None):
        log.info(self)

        always_excluded = ['Broken', 'ParserFuzz', 'Stub']
        if not cmd:
            cmd = self.get_phpunit_command()
        if self.testsuite:
            cmd.extend(['--testsuite', self.testsuite])

        if group:
            cmd.extend(['--group', ','.join(group)])

        cmd.extend(
            ['--exclude-group', ','.join(always_excluded + exclude_group)]
        )

        if self.junit and self.junit_file:
            cmd.extend(['--log-junit', self.junit_file])
        log.info(' '.join(cmd))

        phpunit_env = {}
        phpunit_env.update(os.environ)
        phpunit_env.update({'LANG': 'C.UTF-8'})

        subprocess.check_call(cmd, cwd=self.mw_install_path, env=phpunit_env)


class PhpUnitDatabaseless(AbstractPhpUnit):
    def __init__(self, mw_install_path, testsuite, log_dir, junit=False):
        self.mw_install_path = mw_install_path
        self.testsuite = testsuite
        self.log_dir = log_dir
        self.junit_file = os.path.join(self.log_dir, 'junit-dbless.xml')
        self.junit = junit

    def execute(self):
        # XXX might want to run the triggered extension first then the
        # other tests.
        # XXX some mediawiki/core smoke PHPunit tests should probably
        # be run as well.
        self._run_phpunit(exclude_group=['Database', 'Standalone'])

    def __str__(self):
        return "PHPUnit {} suite (without database or standalone)".format(
            self.testsuite or 'default'
        )


class PhpUnitStandalone(AbstractPhpUnit):
    def __init__(
        self, mw_install_path, testsuite, log_dir, repo_path, junit=False
    ):
        self.mw_install_path = mw_install_path
        self.testsuite = testsuite
        self.log_dir = log_dir
        self.repo_path = repo_path
        self.junit_file = os.path.join(self.log_dir, 'junit-standalone.xml')
        self.junit = junit

    def execute(self):
        self._run_phpunit(
            group=['Standalone'],
            cmd=self.get_phpunit_command(self.repo_path),
        )

    def __str__(self):
        return "PHPUnit {} standalone suite on {}".format(
            self.testsuite or 'default', self.repo_path
        )


class PhpUnitUnit(AbstractPhpUnit):
    def __init__(self, mw_install_path, log_dir, junit=False):
        self.mw_install_path = mw_install_path
        self.log_dir = log_dir
        self.testsuite = None
        self.junit_file = os.path.join(self.log_dir, 'junit-unit.xml')
        self.junit = junit

    def execute(self):
        if _repo_has_composer_script(self.mw_install_path, 'phpunit:unit'):
            self._run_phpunit(cmd=['composer', 'phpunit:unit', '--'])
        else:
            log.debug('skipping phpunit:unit stage, script is not present')
            return

    def __str__(self):
        return "PHPUnit unit tests"


class PhpUnitDatabase(AbstractPhpUnit):
    def __init__(self, mw_install_path, testsuite, log_dir, junit=False):
        self.mw_install_path = mw_install_path
        self.testsuite = testsuite
        self.log_dir = log_dir
        self.junit_file = os.path.join(self.log_dir, 'junit-db.xml')
        self.junit = junit

    def execute(self):
        self._run_phpunit(group=['Database'], exclude_group=['Standalone'])

    def __str__(self):
        return "PHPUnit {} suite (with database)".format(
            self.testsuite or 'default'
        )


class QunitTests:
    def __init__(self, mw_install_path, web_url):
        self.mw_install_path = mw_install_path
        self.web_url = web_url

    def execute(self):
        karma_env = {
            'CHROME_BIN': '/usr/bin/chromium',
            'MW_SERVER': self.web_url,
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


class ApiTesting:
    def __init__(self, mw_install_path, projects, url):
        self.mw_install_path = mw_install_path
        self.projects = projects
        self.url = url

    def execute(self):
        settings_in_path = (
            self.mw_install_path
            + "/tests/api-testing/.api-testing-quibble.json"
        )
        settings_out_path = self.mw_install_path + "/api-testing-quibble.json"
        with open(settings_in_path) as settings_in:
            api_settings = json.load(settings_in)

        api_settings['base_uri'] = self.url + "/"

        with open(settings_out_path, "w") as settings_out:
            json.dump(api_settings, settings_out)
        quibble_testing_config = {
            "API_TESTING_CONFIG_FILE": self.mw_install_path
            + "/api-testing-quibble.json"
        }
        quibble_testing_config.update(os.environ)

        for project in self.projects:
            project_dir = os.path.normpath(
                os.path.join(
                    self.mw_install_path, quibble.zuul.repo_dir(project)
                )
            )
            if repo_has_npm_script(project_dir, 'api-testing'):
                _npm_install(project_dir)
                subprocess.check_call(
                    [quibble.get_npm_command(), 'run', 'api-testing'],
                    cwd=project_dir,
                    env=quibble_testing_config,
                )

    def __str__(self):
        return "Run API-Testing"


class BrowserTests:
    def __init__(
        self,
        mw_install_path,
        projects,
        display,
        web_url,
        web_backend,
        parallel_npm_install=False,
    ):
        self.mw_install_path = mw_install_path
        self.projects = projects
        self.display = display
        self.web_url = web_url
        self.web_backend = web_backend
        self.parallel_npm_install = parallel_npm_install

    def execute(self):
        for project in self.projects:
            project_dir = get_project_dir(self.mw_install_path, project)
            if repo_has_npm_script(project_dir, 'selenium-test'):
                self._run_webdriver(project_dir)

    def _run_webdriver(self, project_dir):
        log.info('Running webdriver test in %s', project_dir)
        webdriver_env = {}
        webdriver_env.update(os.environ)
        webdriver_env.update(
            {
                'MW_SERVER': self.web_url,
                'MW_SCRIPT_PATH': '/',
                'FORCE_COLOR': '1',  # for 'supports-color'
                'MEDIAWIKI_USER': 'WikiAdmin',
                'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
                'DISPLAY': self.display,
            }
        )
        if self.web_backend == 'external':
            webdriver_env.update({'QUIBBLE_APACHE': '1'})

        if not self.parallel_npm_install:
            _npm_install(project_dir)
        subprocess.check_call(
            [quibble.get_npm_command(), 'run', 'selenium-test'],
            cwd=project_dir,
            env=webdriver_env,
        )

    def __str__(self):
        return "Browser tests for projects {}".format(", ".join(self.projects))


class UserScripts:
    def __init__(self, mw_install_path, commands, web_url):
        self.mw_install_path = mw_install_path
        self.commands = commands
        self.web_url = web_url

    def execute(self):
        log.info('User commands, working directory: %s', self.mw_install_path)
        userscripts_env = {}
        userscripts_env.update(os.environ)
        userscripts_env.update(
            {
                'MW_SERVER': self.web_url,
                'MW_SCRIPT_PATH': '/',
                'MEDIAWIKI_USER': 'WikiAdmin',
                'MEDIAWIKI_PASSWORD': 'testwikijenkinspass',
            }
        )

        for cmd in self.commands:
            log.info(cmd)
            subprocess.check_call(
                cmd,
                shell=True,
                cwd=self.mw_install_path,
                env=userscripts_env,
            )

    def __str__(self):
        return "User commands: {}".format(", ".join(self.commands))


class EnsureDirectory:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        os.makedirs(self.directory, exist_ok=True)

    def __str__(self):
        return "Ensure we have the directory '{}'".format(self.directory)


class GitClean:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        subprocess.check_call(['git', 'clean', '-xqdf'], cwd=self.directory)

    def __str__(self):
        return "Revert to git clean -xqdf in {}".format(self.directory)


class Parallel:
    """Run subcommands in parallel.

    Steps are an iterable of command objects, to be evaluated
    immediately.

    Subprocess stdout and stderr, and logging are piped to an interleaved
    capture buffer and logged by the parent as each child completes.

    Any exceptions are bubbled up.
    """

    def __init__(self, *, name=None, steps):
        self.name = name or "parallel steps"
        self.steps = list(steps)

        self.workers = max(1, min(len(self.steps), os.cpu_count()))

    def execute(self):
        # Short-circuit if there aren't enough steps to run in parallel.
        if len(self.steps) == 0:
            return
        elif len(self.steps) == 1:
            return execute_command(self.steps[0])

        with multiprocessing.Pool(processes=self.workers) as pool:
            results = pool.imap_unordered(self._run_child, self.steps)
            results_in_progress = ProgressReporter(
                desc=self.name,
                iterable=results,
                sleep_interval=monitor_interval,
                total=len(self.steps),
            )
            for error, capture in results_in_progress:
                log.info(capture)
                if error:
                    raise error

    @staticmethod
    def _run_child(command):
        """Run a command and return its output

        This is executed in the child process context, and pipes all of its own
        output streams to a single collector.  This collected output and any
        error are returned in a serializable format.

        The child outputs are read as bytes and decoded to Unicode replacing
        any potential invalid characters with their hexadecimal form.

        Returns
        -------
        tuple
            error : Exception or None
            captured : text
                Output of the command, with stdout, stderr, and log lines
                interleaved.
        """
        with tempfile.TemporaryFile() as collector, \
                quibble.util.redirect_all_streams(collector):  # fmt: skip
            try:
                execute_command(command)
                error = None
            except Exception as ex:
                error = ex
            finally:
                collector.flush()
                collector.seek(0, io.SEEK_SET)
                # With Python 3.8 we could use:
                #   TemporaryFile(errors='backslashreplace')
                captured = collector.read().decode(errors='backslashreplace')

        return (error, captured)

    def __str__(self):
        return "Run {} in parallel (concurrency={}):".format(
            self.name, self.workers
        ) + "".join(["\n* " + step for step in map(str, self.steps)])


def _repo_has_composer_script(project_dir, script_name):
    composer_path = os.path.join(project_dir, 'composer.json')
    return _json_has_script(composer_path, script_name)


def _repo_has_npm_lock(project_dir):
    lock_path = os.path.join(project_dir, 'package-lock.json')
    return os.path.exists(lock_path)


def repo_has_npm_script(project_dir, script_name):
    package_path = os.path.join(project_dir, 'package.json')
    return _json_has_script(package_path, script_name)


def get_project_dir(mw_install_path, project):
    """Get the normalized path for a Zuul project."""
    with quibble.logginglevel('zuul.CloneMapper', logging.WARNING):
        repo_dir = quibble.zuul.repo_dir(project)
    return os.path.normpath(os.path.join(mw_install_path, repo_dir))


def _json_has_script(json_file, script_name):
    if not os.path.exists(json_file):
        return False
    with open(json_file) as f:
        spec = json.load(f)
    return 'scripts' in spec and script_name in spec['scripts']
