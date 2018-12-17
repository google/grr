#!/usr/bin/env python
"""Setup configuration for the python grr modules."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# TODO(hanuszczak): Add support for unicode literals in `setup.py` file.

# pylint: disable=unused-variable
# pylint: disable=g-multiple-import
# pylint: disable=g-import-not-at-top
import ConfigParser
import itertools
import os
import shutil
import subprocess

from setuptools import find_packages, setup, Extension
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

  subprocess.check_call(["python", "makefile.py"],
                        cwd="grr_response_core/artifacts")


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = ConfigParser.SafeConfigParser()
  config.read(ini_path)
  return config


VERSION = get_config()


class Develop(develop):

  def run(self):
    sync_artifacts()

    develop.run(self)


class Sdist(sdist):
  """Build sdist."""

  user_options = sdist.user_options + [
      ("no-sync-artifacts", None,
       "Don't sync the artifact repo. This is unnecessary for "
       "clients and old client build OSes can't make the SSL connection."),
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
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


data_files = list(
    itertools.chain(
        find_data_files("executables"),
        find_data_files("install_data"),
        find_data_files("scripts"),
        find_data_files("grr_response_core/artifacts"),
        ["version.ini"],
    ))

setup_args = dict(
    name="grr-response-core",
    version=VERSION.get("Version", "packageversion"),
    description="GRR Rapid Response",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    python_requires=">=2.7.11",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    ext_modules=[
        Extension("grr_response_core._semantic", ["accelerated/accelerated.c"])
    ],
    cmdclass={
        "develop": Develop,
        "install": install,
        "sdist": Sdist,
    },
    install_requires=[
        "binplist==0.1.4",
        "configparser==3.5.0",
        "cryptography==2.3",
        "fleetspeak==0.1.1",
        "future==0.16.0",
        "grr-response-proto==%s" % VERSION.get("Version", "packagedepends"),
        "ipaddr==2.2.0",
        "ipython==5.0.0",
        "pip>=8.1.1",
        "psutil==5.4.3",
        "python-crontab==2.0.1",
        "python-dateutil==2.6.1",
        "pytsk3==20170802",
        "pytz==2017.3",
        "PyYAML==3.12",
        "requests==2.21.0",
        "typing==3.6.4",
        "virtualenv==15.0.3",
        "wheel==0.32.3",
        "yara-python==3.6.3",
    ],

    # Data files used by GRR. Access these via the config_lib "resource" filter.
    data_files=data_files)

setup(**setup_args)
