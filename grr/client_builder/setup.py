#!/usr/bin/env python
"""Setup configuration for the grr-response-client-builder package."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
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
  """Custom sdist class that bundles GRR's version.ini."""

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


# TODO: Clean up str() call after Python 2 support is
# dropped ('data_files' elements have to be bytes in Python 2).
data_files = [str("version.ini")]

setup_args = dict(
    name="grr-response-client-builder",
    version=VERSION.get("Version", "packageversion"),
    description="GRR Rapid Response",
    license="Apache License, Version 2.0",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    url="https://github.com/google/grr",
    entry_points={
        "console_scripts": [
            "grr_client_build = %s" %
            ("grr_response_client_builder.distro_entry:ClientBuild"),
        ]
    },
    cmdclass={"sdist": Sdist},
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=2.7.11",
    install_requires=[
        "absl-py==0.6.1",
        "grr-response-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        # TODO: 3.4 has a bug that prevents it from being installed
        # on macOS and CentOS [1]. On the other hand, 3.2.1 does not work with
        # Python 3. The issue is already resolved but there has been no release
        # since then.
        #
        # [1]: https://github.com/pyinstaller/pyinstaller/issues/3597
        "pyinstaller==%s" % ("3.2.1" if sys.version_info < (3, 0) else "3.4"),
    ],

    # Data files used by GRR. Access these via the config_lib "resource" filter.
    data_files=data_files)

setup(**setup_args)
