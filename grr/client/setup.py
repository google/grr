#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.

This package needs to stay simple so that it can be installed on windows and
ancient versions of linux to build clients.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import platform
import shutil
import sys

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
            "grr_client_build = grr_response_client.distro_entry:ClientBuild",
            "grr_pool_client = grr_response_client.distro_entry:PoolClient"
        ]
    },
    cmdclass={"sdist": Sdist},
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "absl-py==0.6.1",
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        # TODO: This is a backport of Python 3.2+ API, should be
        # removed once support for Python 2 is dropped.
        "subprocess32==3.5.3",
        # TODO: 3.4 has a bug that prevents it from being installed
        # on macOS and CentOS [1]. On the other hand, 3.2.1 does not work with
        # Python 3. The issue is already resolved but there has been no release
        # since then.
        #
        # [1]: https://github.com/pyinstaller/pyinstaller/issues/3597
        "pyinstaller==%s" % ("3.2.1" if sys.version_info < (3, 0) else "3.4"),
    ],
    extras_require={
        # The following requirements are needed in Windows.
        ':sys_platform=="win32"': [
            "WMI==1.4.9",
            "pypiwin32==219",
        ],
    },
)

if platform.system() == "Linux":
  setup_args["install_requires"].append("chipsec==1.2.4")

if platform.system() != "Windows":
  setup_args["install_requires"].append("xattr==0.9.2")

setup(**setup_args)
