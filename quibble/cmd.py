#!/usr/bin/env python3

import argparse
import logging
import os
import os.path
import subprocess

import zuul.lib.cloner


class QuibbleCmd():

    log = logging.getLogger('quibble.cmd')

    def parse_arguments(self):
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
            default='/srv/deployment/integration/slave-scripts',
            help='Path to integration/jenkins checkout'
            )
        parser.add_argument(
            '--workspace',
            default=os.environ.get('WORKSPACE', '.'),
            help='Base path to work from. Default: $WORKSPACE or .'
            )
        return parser.parse_args()

    def execute(self):
        logging.basicConfig(level=logging.DEBUG)
        args = self.parse_arguments()

        self.scripts_dir = args.scripts_dir

        self.prepare_sources(args)
        self.generate_extensions_load()
        self.mw_install()

    def getExtraSkins(self):
        if 'SKIN_DEPENDENCIES' not in os.environ:
            return []
        return os.environ.get('SKIN_DEPENDENCIES').split('\\n')

    def getExtraExtensions(self):
        if 'EXT_DEPENDENCIES' not in os.environ:
            return []
        return os.environ.get('EXT_DEPENDENCIES').split('\\n')

    def prepare_sources(self, args):
        projects_to_clone = ['mediawiki/core']
        if args.packages_source == 'vendor':
            self.log.info('Will clone mediawiki/vendor')
            projects_to_clone.append('mediawiki/vendor')

        projects_to_clone.extend(self.getExtraSkins())
        projects_to_clone.extend(self.getExtraExtensions())

        self.log.info('Repositories to clone: %s'
                      % ', '.join(projects_to_clone))
        #self.clonerepos(projects_to_clone)

    def clonerepos(self, repos):
        cloner = zuul.lib.cloner.Cloner(
            git_base_url='https://gerrit.wikimedia.org/r/p',
            projects=repos,
            workspace='src',
            zuul_branch=os.environ['ZUUL_BRANCH'],
            zuul_ref=os.environ['ZUUL_REF'],
            zuul_url=os.environ['ZUUL_URL'],
            cache_dir='/srv/git',
        )
        # Map a repo to a target dir under workspace
        cloner.clone_map([
            {'name': 'mediawiki/core',
             'dest': '.'},
            {'name': 'mediawiki/vendor',
             'dest': './vendor'},
            {'name': 'mediawiki/extensions/(.*)',
             'dest': './extensions/\\1'},
            {'name': 'mediawiki/skins/(.*)',
             'dest': './skins/\\1'},
        ])
        cloner.execute()

    def generate_extensions_load(self):
        with open('src/extensions_load.txt', 'w') as f:
            f.writelines(self.getExtraExtensions())

    def run_script(self, script_name):
        self.log.debug('Running script: %s' % script_name)
        script = os.path.join(self.scripts_dir,
                              os.path.basename(script_name))
        if not os.path.exists(script):
            raise Exception('Script %s does not exist in %s' % (
                            script_name, self.scripts_dir))

        proc = subprocess.Popen(script, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        proc.communicate()

        if proc.returncode > 0:
            raise Exception('Script %s failed with exit code: %s' % (
                script, proc.returncode))

    def mw_install(self):
        proc = subprocess.Popen([ 'php', 'maintenance/install.php' ],
            cwd=''
        )

if __name__ == '__main__':
    cmd = QuibbleCmd()
    cmd.execute()
