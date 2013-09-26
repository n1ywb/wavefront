#!/usr/bin/env python

from setuptools import setup, find_packages

from Cython.Build import cythonize

from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(
    cmdclass = {'build_ext': build_ext},
    name = "wavefront",
    version = "0.1",
    packages = find_packages(),
    scripts = [],

    install_requires = ['sphinxcontrib-plantuml'],

    setup_requires = ['docutils', 'sphinxcontrib-plantuml'],

    package_data = {
    },

    ext_modules =
        cythonize('wavefront/*.pyx')
    , # accepts a glob pattern

    # metadata for upload to PyPI
    author = "UCSD Array Network Facility",
    author_email = "anf@ucsd.edu",
    description = "Antelope Waveform Server",
    license = "BSD",
    keywords = "",
    url = "",

    # could also include long_description, download_url, classifiers, etc.
)
