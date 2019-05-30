"""Encapsulates each step of a job"""

import json
import logging
import os.path
import pkg_resources
from quibble.util import copylog
import quibble.zuul
import subprocess

log = logging.getLogger(__name__)


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
        return "Zuul clone {} with parameters {}".format(
            self.projects,
            self.kwargs)


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
                            "Failed to process git submodules for {}".format(
                                dirpath))
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


class ComposerComposerDependencies:
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

        log.debug('composer require %s' % ' '.join(reqs))
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
        return "Install composer dev-requires"


class NpmInstall:
    def __init__(self, directory):
        self.directory = directory

    def execute(self):
        subprocess.check_call(['npm', 'prune'], cwd=self.directory)
        subprocess.check_call(['npm', 'install'], cwd=self.directory)

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
        # Prepend our custom configuration snippets
        with open(localsettings, 'r+') as lf:
            quibblesettings = pkg_resources.resource_filename(
                __name__, 'mediawiki/local_settings.php')
            with open(quibblesettings) as qf:
                quibble_conf = qf.read()

            installed_conf = lf.read()
            lf.seek(0, 0)
            lf.write(quibble_conf + '\n?>' + installed_conf)
        copylog(localsettings,
                os.path.join(self.log_dir, 'LocalSettings.php'))
        subprocess.check_call(['php', '-l', localsettings])

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
