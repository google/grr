#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Setup configuration for the python grr modules."""

# pylint: disable=unused-variable
# pylint: disable=g-multiple-import
# pylint: disable=g-import-not-at-top

import glob
import os

try:
  from setuptools import find_packages, setup
except ImportError:
  from distutils.core import find_packages, setup


def GRRFind(path, patterns):
  """Traverses a path to find files matching the specified glob patterns.

  Args:
    path: The path to traverse
    patterns: The list of glob patterns

  Yields:
    A pattern match
  """
  for directory, sub_directories, files in os.walk(path):
    for pattern in patterns:
      directory_pattern = os.path.join(directory, pattern)

      for pattern_match in glob.iglob(directory_pattern):
        if os.path.isfile(pattern_match):
          yield pattern_match


def GRRGetPackagePrefix(package_name):
  """Determine the package path prefix from the package name."""
  package_components = package_name.split('.')

  if len(package_components) > 2:
    package_path_prefix = os.path.join(package_components[1:])
  elif len(package_components) == 2:
    package_path_prefix = package_components[1]
  else:
    package_path_prefix = ''

  return package_path_prefix


def GRRGetPackagePath(package_path_prefix, sub_path):
  """Determine the package path from the package path prefix and sub path."""
  if package_path_prefix and sub_path:
    package_path = os.path.join(package_path_prefix, sub_path)
  elif sub_path:
    package_path = sub_path
  else:
    package_path = package_path_prefix

  return package_path


def GRRGetRelativeFilename(package_path_prefix, filename):
  """Determine the filename relative to the package path prefix."""
  if package_path_prefix:
    filename = os.path.relpath(filename, package_path_prefix)

  return filename


def GRRFindDataFiles(data_files_specs):
  """Find data files as defined by the specifications.

  Args:
    data_files_specs: A list of data files specifications.
    A data file specification consists of a tuple containing:
    * A string containing the package name
    * A list of sub directories relative from the root of the package
    * A list of glob patterns

  Returns:
    A dictionary of the list of data files per package
  """
  data_files = {}

  for package_name, sub_paths, patterns in data_files_specs:
    package_path_prefix = GRRGetPackagePrefix(package_name)

    package_data_files = []

    for sub_path in sub_paths:
      package_path = GRRGetPackagePath(package_path_prefix, sub_path)

      for filename in GRRFind(package_path, patterns):
        package_data_files.append(filename)

    data_files[package_name] = []

    for filename in package_data_files:
      filename = GRRGetRelativeFilename(package_path_prefix, filename)

      data_files[package_name].append(filename)

  return data_files


def GRRFindPackages():
  """Traverses the source tree to find the packages.

  A package is a directory containing the file __init__.py.

  Returns:
    A list of package names
  """
  packages = ['grr']

  for package in find_packages('.'):
    packages.append('grr.' + package)

  return packages


grr_data_files_spec = ('grr',
                       ['tools', 'worker'],
                       ['*.py'])

grr_config_files_spec = ('grr',
                         ['config'],
                         ['*.py', '*.in'])


grr_gui_data_files_spec = ('grr.gui',
                           ['static', 'templates'],
                           ['*.css', '*.js', '*.gif', '*.html',
                            '*.jpg', '*.MF', '*.png'])

grr_client_data_files_spec = ('grr.client',
                              ['local'],
                              ['*.txt', '*.py'])

grr_test_data_files_spec = ('grr.test_data',
                            [''],
                            ['*'])

setup(name='grr',
      version='0.2',
      description='GRR Rapid Response Framework',
      license='Apache License, Version 2.0',
      url='http://code.google.com/p/grr',
      install_requires=[],
      include_package_data=True,
      packages=GRRFindPackages(),
      package_dir={'grr': '../grr'},
      package_data=GRRFindDataFiles([grr_data_files_spec,
                                     grr_gui_data_files_spec,
                                     grr_client_data_files_spec,
                                     grr_test_data_files_spec,
                                     grr_config_files_spec]),
      entry_points={
          'console_scripts': [
              'grr_console = grr.tools.console:ConsoleMain',
              'grr_config_updater = grr.tools.config_updater:ConsoleMain',
              'grr_server = grr.tools.grr_server:ConsoleMain',
              'grr_file_exporter = grr.tools.file_exporter:ConsoleMain',
          ]
      })
