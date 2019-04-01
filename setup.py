#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='quibble',
    packages=find_packages(),
    install_requires=[
        # For zuul-cloner
        'extras',
        'six',
        'PyYAML',
        # 2.1.2 has performances degradation
        # Solved in 2.1.8 but jessie-backports and stretch have 2.1.1
        #
        # zuul dcafeb6038b96a0095976963814cc29f98520995
        # https://github.com/gitpython-developers/GitPython/issues/605
        #
        # So we want either <2.1.2 or >2.1.7
        'GitPython<2.2.0,!=2.1.2,!=2.1.3,!=2.1.4,!=2.1.5,!=2.1.6,!=2.1.7'
        ],
    package_data={
        'quibble.mediawiki': ['*.php'],
    },
    entry_points={
        'console_scripts': [
            'quibble = quibble.cmd:main'
        ],
    }
)
