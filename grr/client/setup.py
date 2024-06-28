#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.

This package needs to stay simple so that it can be installed on windows and
ancient versions of linux to build clients.
"""

from typing import List

import configparser
import os
import platform
import shutil
import subprocess
import sys

from setuptools import find_packages
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# If you run setup.py from the root GRR dir you get very different results since
# setuptools uses the MANIFEST.in from the root dir.  Make sure we are in the
# package dir.
os.chdir(THIS_DIRECTORY)


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
  config.read(ini_path)
  return config


def compile_protos():
  """Builds necessary assets from sources."""
  # Using Popen to effectively suppress the output of the command below - no
  # need to fill in the logs with protoc's help.
  p = subprocess.Popen(
    [sys.executable, "-m", "grpc_tools.protoc", "--help"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )
  p.communicate()
  # If protoc is not installed, install it. This seems to be the only reliable
  # way to make sure that grpcio-tools gets intalled, no matter which Python
  # setup mechanism is used: pip install, pip install -e,
  # python setup.py install, etc.
  if p.returncode != 0:
    # Specifying protobuf dependency right away pins it to the correct
    # version. Otherwise latest protobuf library will be installed with
    # grpcio-tools and then uninstalled when grr-response-proto's setup.py runs
    # and reinstalled to the version required by grr-response-proto.
    subprocess.check_call(
      [sys.executable, "-m", "pip", "install", "--require-hashes", "build_requirements.txt"]
    )

  # If there's no makefile, we're likely installing from an sdist,
  # so there's no need to compile the protos (they should be already
  # compiled).
  if not os.path.exists(os.path.join(THIS_DIRECTORY, "makefile.py")):
    return

  # Only compile protobufs if we're inside GRR source tree.
  subprocess.check_call(
    [sys.executable, "makefile.py", "--clean"], cwd=THIS_DIRECTORY
  )


VERSION = get_config()


def parse_requirements(filename: str) -> List[str]:
  requirements = []
  with open(filename) as file:
    for line in file:
      requirement = line.strip()
      if (comment := requirement.find("#")) >= 0:
        requirement = requirement[:comment].strip()
      requirements.append(requirement)

  return requirements


class Sdist(sdist):
  """Build sdist."""

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
      os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini
    )

  def run(self):
    compile_protos()
    sdist.run(self)


class Develop(develop):

  def run(self):
    compile_protos()
    develop.run(self)


setup_args = dict(
  name="grr-response-client",
  version=VERSION.get("Version", "packageversion"),
  description="The GRR Rapid Response client.",
  license="Apache License, Version 2.0",
  maintainer="GRR Development Team",
  maintainer_email="grr-dev@googlegroups.com",
  url="https://github.com/google/grr",
  entry_points={
    "console_scripts": [
      (
        "grr_fleetspeak_client = "
        "grr_response_client.distro_entry:FleetspeakClient"
      ),
      (
        "fleetspeak_client = "
        "grr_response_client.distro_entry:FleetspeakClientWrapper"
      ),
    ]
  },
  cmdclass={
    "sdist": Sdist,
    "develop": Develop,
  },
  packages=find_packages(),
  include_package_data=True,
  python_requires=">=3.9",
  install_requires=[
    "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
  ],
  data_files=["requirements.in", "requirements_win.in",  "requirements_osx.in", "requirements_ubuntu.in"],
)

setup_args["install_requires"].extend(parse_requirements("requirements.in"))
if platform.system() == "Windows":
  setup_args["install_requires"].extend(parse_requirements("requirements_win.in"))
if platform.system() == "Darwin":
  setup_args["install_requires"].extend(parse_requirements("requirements_osx.in"))
if platform.system() == "Linux":
  setup_args["install_requires"].extend(parse_requirements("requirements_ubuntu.in"))

setup(**setup_args)
