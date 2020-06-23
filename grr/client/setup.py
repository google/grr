#!/usr/bin/env python
# Lint as: python3
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.

This package needs to stay simple so that it can be installed on windows and
ancient versions of linux to build clients.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import configparser
import os
import platform
import shutil

from setuptools import find_packages
from setuptools import setup
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

  config = configparser.SafeConfigParser()
  config.read(ini_path)
  return config


VERSION = get_config()


class Sdist(sdist):
  """Build sdist."""

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


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
            "grr_client = grr_response_client.distro_entry:Client",
            ("grr_fleetspeak_client = "
             "grr_response_client.distro_entry:FleetspeakClient"),
            "grr_pool_client = grr_response_client.distro_entry:PoolClient"
        ]
    },
    cmdclass={"sdist": Sdist},
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[
        "absl-py==0.9.0",
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "PyInstaller==3.6",
        "libfsntfs-python==20200506",
    ],
    extras_require={
        # The following requirements are needed in Windows.
        ':sys_platform=="win32"': [
            "WMI==1.5.1",
            "pywin32==228",
        ],
    },
)

if platform.system() == "Linux":
  setup_args["install_requires"].append("chipsec==1.5.1")

if platform.system() != "Windows":
  setup_args["install_requires"].append("xattr==0.9.7")

setup(**setup_args)
