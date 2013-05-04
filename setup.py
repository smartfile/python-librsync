#!/bin/env python

import os
from distutils.core import setup

name = 'python-librsync'
version = '0.1'
release = '1'
versrel = version + '-' + release
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
long_description = file(readme).read()

setup(
    name = name,
    version = versrel,
    description = 'Python ctypes wrapper for librsync.',
    long_description = long_description,
    author = 'Ben Timby',
    author_email = 'btimby@gmail.com',
    maintainer = 'Ben Timby',
    maintainer_email = 'btimby@gmail.com',
    url = 'http://github.com/smartfile/' + name + '/',
    license = 'MIT',
    requires = [],
    packages = [
        "librsync",
    ],
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
