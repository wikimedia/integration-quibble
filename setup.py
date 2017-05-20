#!/usr/bin/env python3

from setuptools import setup

setup(
    name='quibble',
    version='0.1',
    packages=['quibble'],
    entry_points={
        'console_scripts': [
            'quibble = quibble.cmd:main'
        ],
    }
)
