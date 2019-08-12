#!/usr/bin/env python
"""setup.py file for a GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import shutil
import subprocess
import sys

from distutils.command.build_py import build_py

from setuptools import find_packages
from setuptools import setup
from setuptools.command.sdist import sdist

# TODO: Fix this import once support for Python 2 is dropped.
# pylint: disable=g-import-not-at-top
if sys.version_info.major == 2:
  import ConfigParser as configparser
else:
  import configparser
# pylint: enable=g-import-not-at-top


THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

GRPCIO_TOOLS = "grpcio-tools==1.17.1"


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  # In a prebuilt sdist archive, version.ini is copied to the root folder
  # of the archive. When installing in a development mode, version.ini
  # has to be read from the root repository folder (two levels above).
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.SafeConfigParser()
  config.read(ini_path)
  return config


def compile_protos():
  """Builds necessary assets from sources."""
  # Using Popen to effectively suppress the output of the command below - no
  # need to fill in the logs with protoc's help.
  p = subprocess.Popen([sys.executable, "-m", "grpc_tools.protoc", "--help"],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
  p.communicate()
  # If protoc is not installed, install it. This seems to be the only reliable
  # way to make sure that grpcio-tools gets intalled, no matter which Python
  # setup mechanism is used: pip install, pip install -e,
  # python setup.py install, etc.
  if p.returncode != 0:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", GRPCIO_TOOLS])

  # If there's no makefile, we're likely installing from an sdist,
  # so there's no need to compile the protos (they should be already
  # compiled).
  if not os.path.exists(os.path.join(THIS_DIRECTORY, "makefile.py")):
    return

  # Only compile protobufs if we're inside GRR source tree.
  subprocess.check_call(
      ["python", "makefile.py", "--clean"], cwd=THIS_DIRECTORY)


class Build(build_py):

  def find_all_modules(self):
    compile_protos()
    self.packages = find_packages()
    return build_py.find_all_modules(self)


class Sdist(sdist):
  """Build sdist."""

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)

    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


VERSION = get_config()

setup_args = dict(
    name="grr-response-proto",
    version=VERSION.get("Version", "packageversion"),
    description="GRR API client library",
    license="Apache License, Version 2.0",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    url="https://github.com/google/grr/tree/master/proto",
    cmdclass={
        "build_py": Build,
        "sdist": Sdist,
    },
    packages=find_packages(),
    install_requires=[
        "protobuf==3.8.0",
    ],
    setup_requires=[
        GRPCIO_TOOLS,
    ],
    data=["version.ini"])

setup(**setup_args)
