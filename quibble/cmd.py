#!/usr/bin/env python3

import argparse
import json
import logging
import os
import os.path
import subprocess
import tempfile


class QuibbleCmd(object):

    log = logging.getLogger('quibble.cmd')

    def __init__(self):
        self.dependencies = []
        self.extra_dependencies = []

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
            help='Source to install PHP dependencies from.')
        parser.add_argument(
            '--scripts-dir',
            default='/srv/deployment/integration/slave-scripts/bin',
            help='Path to integration/jenkins checkout'
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
                    '/usr/bin/zuul-cloner',
                    '--map', temp_mapfile,
                    '--workspace', os.path.join(self.workspace, 'src'),
                    '--cache-dir', '/srv/git',
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

    def run_script(self, script_name):
        self.log.debug('Running script: %s' % script_name)
        script = os.path.join(self.scripts_dir,
                              os.path.basename(script_name))
        if not os.path.exists(script):
            raise Exception('Script %s does not exist in %s' % (
                            script_name, self.scripts_dir))

        proc = subprocess.Popen(script)
        proc.communicate()

        if proc.returncode > 0:
            raise Exception('Script %s failed with exit code: %s' % (
                script, proc.returncode))

    def mw_install(self):
        self.run_script('global-setup.sh')
        self.run_script('mw-install-mysql.sh')
        self.run_script('mw-apply-settings.sh')
        self.run_script('mw-run-update-script.sh')

    def execute(self):
        logging.basicConfig(level=logging.DEBUG)
        self.args = self.parse_arguments()

        self.scripts_dir = self.args.scripts_dir
        self.workspace = self.args.workspace
        self.mw_install_path = os.path.join(self.workspace, 'src')

        self.setup_environment()
        self.prepare_sources()
        self.generate_extensions_load()
        self.mw_install()

        if self.args.packages_source == 'vendor':
            self.log.info('Requiring composer dev dependencies')
            self.run_script('mw-fetch-composer-dev.sh')

        self.run_script('mw-phpunit.sh')


def main():
    cmd = QuibbleCmd()
    cmd.execute()


if __name__ == '__main__':
    main()
