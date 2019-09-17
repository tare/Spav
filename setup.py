#!/usr/bin/env python

import os

from distutils.core import setup

import spav

# read the long description
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)),'README.md'),encoding='utf-8') as f:
    long_description = f.read()

# read the package requirements
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)),'requirements.txt'),encoding='utf-8') as f:
    install_requires = f.read().splitlines()

setup(name='Spav',
      version=spav.__version__,
      description='A tool for visualizing Splotch results',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author=spav.__author__,
      author_email=spav.__email__,
      url='https://github.com/tare/Spav',
      license=spav.__license__,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD 3-Clause "New" or "Revised" License (BSD-3-Clause)',
          'Programming Language :: Python :: 3'],
      packages=['spav'],
      scripts=['bin/spav_prepare_data'],
      install_requires=install_requires,
)
