#!/usr/bin/env python
"""Setup script for fabmaster package."""

from setuptools import setup, Extension
import os
import sys

# Read version from setting.py
def get_version():
    """Extract version from setting.py."""
    setting_path = os.path.join(os.path.dirname(__file__), 'src', 'fabmaster', 'setting.py')
    with open(setting_path, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")
    return "0.0.1"

# Read requirements from dependencies used in the code
def get_requirements():
    """Extract dependencies from source files."""
    return [
        'numpy',
        'numpy-stl',
        'svgwrite',
        'Pillow',
        'pyassimp',
    ]

# C++ extension module - supports both Unix and Windows
geometry_extension = Extension(
    '_geometry',
    sources=['src/wrapper.cpp', 'include/earcut.hpp'],
    include_dirs=['include'],
    library_dirs=[],
    libraries=[],
    extra_compile_args=['-O2', '-std=c++11'],
    extra_link_args=[],
)

setup(
    name='fabmaster',
    version=get_version(),
    description='Allegro CAD file parser and 3D PCB/components models generator',
    author='Jimmy Li',
    author_email='ljzljm@163.com',
    license='MIT',
    packages=['fabmaster'],
    package_dir={'': 'src'},
    install_requires=get_requirements(),
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    ext_modules=[geometry_extension] if geometry_extension else [],
)
