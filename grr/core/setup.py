#!/usr/bin/env python
"""Setup configuration for the python grr modules."""

from typing import List

import configparser
import itertools
import os
import shutil
import subprocess
import sys

from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.sdist import sdist

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
os.chdir(THIS_DIRECTORY)


def find_data_files(source, ignore_dirs=None):
  ignore_dirs = ignore_dirs or []
  result = []
  for directory, dirnames, files in os.walk(source):
    dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

    files = [os.path.join(directory, x) for x in files]
    result.append((directory, files))

  return result


def sync_artifacts():
  """Sync the artifact repo with upstream for distribution."""

  subprocess.check_call(
    [sys.executable, "makefile.py"], cwd="grr_response_core/artifacts"
  )


def get_config():
  """Get relative path to version.ini file and the INI parser with its data."""
  rel_ini_path = "version.ini"
  ini_path = os.path.join(THIS_DIRECTORY, rel_ini_path)
  if not os.path.exists(ini_path):
    rel_ini_path = os.path.join("..", "..", "version.ini")
    ini_path = os.path.join(THIS_DIRECTORY, rel_ini_path)
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
  config.read(ini_path)
  return rel_ini_path, config


REL_INI_PATH, VERSION = get_config()


def parse_requirements(filename: str) -> List[str]:
  requirements = []
  with open(filename) as file:
    for line in file:
      requirement = line.strip()
      if (comment := requirement.find("#")) >= 0:
        requirement = requirement[:comment].strip()
      requirements.append(requirement)

  return requirements


class Develop(develop):

  def run(self):
    sync_artifacts()

    develop.run(self)


class Sdist(sdist):
  """Build sdist."""

  user_options = sdist.user_options + [
    (
      "no-sync-artifacts",
      None,
      "Don't sync the artifact repo. This is unnecessary for "
      "clients and old client build OSes can't make the SSL connection.",
    ),
  ]

  def initialize_options(self):
    self.no_sync_artifacts = None

    sdist.initialize_options(self)

  def run(self):
    if not self.no_sync_artifacts:
      sync_artifacts()

    sdist.run(self)

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
      os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini
    )


data_files = list(
  itertools.chain(
    find_data_files("executables"),
    find_data_files("install_data"),
    find_data_files("scripts"),
    find_data_files("grr_response_core/artifacts"),
    [REL_INI_PATH],
    ["requirements.in"],
  )
)

setup_args = dict(
  name="grr-response-core",
  version=VERSION.get("Version", "packageversion"),
  description="GRR Rapid Response",
  license="Apache License, Version 2.0",
  url="https://github.com/google/grr",
  maintainer="GRR Development Team",
  maintainer_email="grr-dev@googlegroups.com",
  python_requires=">=3.6",
  packages=find_packages(),
  zip_safe=False,
  include_package_data=True,
  ext_modules=[
    Extension(
      name="grr_response_core._semantic",
      sources=["accelerated/accelerated.c"],
    )
  ],
  cmdclass={
    "develop": Develop,
    "install": install,
    "sdist": Sdist,
  },
  install_requires=[
    "grr-response-proto==%s" % VERSION.get("Version", "packagedepends"),
  ]
  + parse_requirements("requirements.in"),
  # Data files used by GRR. Access these via the config_lib "resource" filter.
  data_files=data_files,
)

setup(**setup_args)
