#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='quibble',
    version='0.1',
    packages=find_packages(),

    include_package_data=True,  # See MANIFEST.in

    entry_points={
        'console_scripts': [
            'quibble = quibble.cmd:main'
        ],
    }
)
