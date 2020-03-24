#!/usr/bin/env python

from distutils.core import setup, Extension
from catkin_pkg.python_setup import generate_distutils_setup


package_info = generate_distutils_setup(
    packages=['fabmaster'],
    package_dir={'': 'src'}
)

setup(**package_info)
