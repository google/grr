#!/usr/bin/env python
"""Setup configuration for the python grr modules."""

# pylint: disable=unused-variable
# pylint: disable=g-multiple-import
# pylint: disable=g-import-not-at-top

import glob
import os
import subprocess

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py


class MyBuild(build_py):

  def run(self):
    # Compile the protobufs.
    base_dir = os.getcwd()
    os.chdir("proto")
    subprocess.check_call(["make"], shell=True)
    os.chdir(base_dir)

    build_py.run(self)


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
  package_components = package_name.split(".")

  if len(package_components) > 2:
    package_path_prefix = os.path.join(package_components[1:])
  elif len(package_components) == 2:
    package_path_prefix = package_components[1]
  else:
    package_path_prefix = ""

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

    data_files.setdefault(package_name, [])

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
  packages = ["grr"]

  for package in find_packages("."):
    packages.append("grr." + package)

  return packages


grr_artifact_files = ("grr",
                      ["artifacts"],
                      ["*.yaml"])

grr_gui_data_files = ("grr.gui",
                      ["static", "templates"],
                      ["*.css", "*.js", "*.gif", "*.html",
                       "*.jpg", "*.MF", "*.png", "*.ico",
                       "*.eot", "*.ttf", "*.svg", "*.woff"])

grr_config_defs = ("grr.config",
                   ["local"],
                   ["*.txt"])


grr_client_data_files = ("grr.client",
                         ["local"],
                         ["*.txt"])

grr_client_nanny_files = ("grr.client",
                          ["nanny"],
                          ["*"])

grr_test_data_files = ("grr.test_data",
                       [""],
                       ["*"])

grr_docs_files = ("grr",
                  ["docs"],
                  ["*"])

grr_wsgi_conf = ("grr",
                 ["tools"],
                 ["wsgi.conf"])

grr_proto_defs = ("grr",
                  ["proto"],
                  ["*.proto"])

grr_protobuf_cc = ("grr",
                   ["lib"],
                   ["protobuf.cc"])

grr_data_server = ("grr.server",
                   ["data_server"],
                   ["*"])


grr_all_files = [grr_artifact_files,
                 grr_client_data_files,
                 grr_client_nanny_files,
                 grr_data_server,
                 grr_docs_files,
                 grr_gui_data_files,
                 grr_proto_defs,
                 grr_protobuf_cc,
                 grr_test_data_files,
                 grr_wsgi_conf,
                ]


setup(name="grr",
      version="0.3.0-2",
      description="GRR Rapid Response Framework",
      license="Apache License, Version 2.0",
      url="https://github.com/google/grr",
      install_requires=[],
      packages=GRRFindPackages(),
      package_dir={"grr": "../grr"},
      package_data=GRRFindDataFiles(grr_all_files),
      entry_points={
          "console_scripts": [
              "grr_console = grr.lib.distro_entry:Console",
              "grr_config_updater = grr.lib.distro_entry:ConfigUpdater",
              "grr_server = grr.lib.distro_entry:GrrServer",
              "grr_end_to_end_tests = grr.lib.distro_entry:EndToEndTests",
              "grr_export = grr.lib.distro_entry:Export",
              "grr_client = grr.lib.distro_entry:Client",
              "grr_worker = grr.lib.distro_entry:Worker",
              "grr_enroller = grr.lib.distro_entry:Enroller",
              "grr_admin_ui = grr.lib.distro_entry:AdminUI",
              "grr_fuse = grr.lib.distro_entry:GRRFuse",
              ]
          },
      cmdclass={"build_py": MyBuild})
