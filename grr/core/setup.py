#!/usr/bin/env python
"""Setup configuration for the python grr modules."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

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

# TODO: Fix this import once support for Python 2 is dropped.
# pylint: disable=g-import-not-at-top
if sys.version_info.major == 2:
  import ConfigParser as configparser
else:
  import configparser
# pylint: enable=g-import-not-at-top

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

  config = configparser.SafeConfigParser()
  config.read(ini_path)
  return config


VERSION = get_config()


class Develop(develop):

  def run(self):
    sync_artifacts()

    develop.run(self)


class Sdist(sdist):
  """Build sdist."""

  # TODO: Option name must be a byte string in Python 2. Remove
  # this call once support for Python 2 is dropped.
  user_options = sdist.user_options + [
      (str("no-sync-artifacts"), None,
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
        # TODO: For some reason, this path cannot be unicode string
        # or else installation fails for Python 2 (with "too many values to
        # unpack" error). This call should be removed once support for Python 2
        # is dropped.
        [str("version.ini")],
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
        Extension(
            # TODO: In Python 2, extension name and sources have to
            # be of type `bytes`. These calls should be removed once support for
            # Python 2 is dropped.
            name=str("grr_response_core._semantic"),
            sources=[str("accelerated/accelerated.c")])
    ],
    cmdclass={
        "develop": Develop,
        "install": install,
        "sdist": Sdist,
    },
    install_requires=[
        "biplist==1.0.3",
        "configparser==3.5.0",
        "cryptography==2.4.2",
        "fleetspeak==0.1.2",
        "future==0.16.0",
        "grr-response-proto==%s" % VERSION.get("Version", "packagedepends"),
        "ipaddr==2.2.0",
        "ipaddress==1.0.22",
        "ipython==%s" % ("5.0.0" if sys.version_info < (3, 0) else "7.2.0"),
        "pexpect==4.6.0",
        "pip>=8.1.1",
        "psutil==5.4.3",
        "python-crontab==2.0.1",
        "python-dateutil==2.6.1",
        "pytsk3==20190507",
        "pytz==2017.3",
        "PyYAML==5.1",
        "requests==2.21.0",
        "typing==3.6.4",
        "virtualenv==15.0.3",
        "wheel==0.32.3",
        "yara-python==3.8.1",
    ],

    # Data files used by GRR. Access these via the config_lib "resource" filter.
    data_files=data_files)

setup(**setup_args)
