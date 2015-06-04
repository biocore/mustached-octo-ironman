#!/usr/bin/env python

# -----------------------------------------------------------------------------
# Copyright (c) 2013, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
import re
import ast
from setuptools import setup


# version parsing from __init__ pulled from Flask's setup.py
# https://github.com/mitsuhiko/flask/blob/master/setup.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('moi/__init__.py', 'rb') as f:
    hit = _version_re.search(f.read().decode('utf-8')).group(1)
    version = str(ast.literal_eval(hit))


classes = """
    Development Status :: 4 - Beta
    License :: OSI Approved :: BSD License
    Topic :: Software Development :: Libraries :: Python Modules
    Programming Language :: Python
    Programming Language :: Python :: 2.7
    Programming Language :: Python :: Implementation :: CPython
    Operating System :: OS Independent
    Operating System :: POSIX :: Linux
    Operating System :: MacOS :: MacOS X
"""

long_description = """MOI: compute like a mustached octo ironman"""

classifiers = [s.strip() for s in classes.split('\n') if s]

setup(name='moi',
      version=version,
      long_description=long_description,
      license="BSD",
      description='Compute ninja',
      author="Qiita development team",
      author_email="mcdonadt@colorado.edu",
      url='http://github.com/biocore/mustached-octo-ironman',
      test_suite='nose.collector',
      packages=['moi'],
      extras_require={'test': ["nose >= 0.10.1", "pep8", 'mock']},
      install_requires=['future==0.13.0', 'tornado==3.1.1', 'toredis', 'redis',
                        'ipython[all]', 'click >= 3.3',
                        'python-dateutil==2.2'],
      classifiers=classifiers,
      package_data={'moi': ['support_files/moi.js',
                            'support_files/moi_list.js']},
      scripts=['scripts/moi']
      )
