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
        'GitPython<2.1.2'
        ],

    include_package_data=True,  # See MANIFEST.in

    entry_points={
        'console_scripts': [
            'quibble = quibble.cmd:main'
        ],
    }
)
