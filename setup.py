#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



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

  for package in find_packages('.', exclude=['test_data']):
    packages.append('grr.' + package)

  return packages


grr_data_files_spec = ('grr',
                       ['tools', 'worker'],
                       ['*.py'])

grr_gui_data_files_spec = ('grr.gui',
                           ['static', 'templates'],
                           ['*.css', '*.js', '*.gif', '*.html',
                            '*.jpg', '*.MF', '*.png'])

grr_client_data_files_spec = ('grr.client',
                              [''],
                              ['*.txt'])

setup(name='grr',
      version='0.1',
      description='GRR Rapid Response Framework',
      license='Apache License, Version 2.0',
      url='http://code.google.com/p/grr',
      install_requires=[],
      include_package_data=True,
      packages=GRRFindPackages(),
      package_dir={'grr': '../grr'},
      package_data=GRRFindDataFiles([grr_data_files_spec,
                                     grr_gui_data_files_spec,
                                     grr_client_data_files_spec])
     )
