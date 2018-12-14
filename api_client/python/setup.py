#!/usr/bin/env python
"""setup.py file for a GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import shutil
import sys

from setuptools import find_packages
from setuptools import setup
from setuptools.command.sdist import sdist

# TODO(hanuszczak): Fix this import once support for Python 2 is dropped.
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
  # TODO(hanuszczak): See comment in `setup.py` for `grr-response-proto`.
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.SafeConfigParser()
  config.read(ini_path)
  return config


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
    name="grr-api-client",
    version=VERSION.get("Version", "packageversion"),
    description="GRR API client library",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr/tree/master/api_client/python",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    cmdclass={
        "sdist": Sdist,
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": ["grr_api_shell = grr_api_client.api_shell:main",]
    },
    install_requires=[
        "future==0.16.0",
        "grr_response_proto==%s" % VERSION.get("Version", "packagedepends"),
        "cryptography==2.3",
        "ipython==5.0.0",
        "protobuf==3.3.0",
        "requests==2.21.0",
        "Werkzeug==0.11.3",
    ],
    data=["version.ini"])

setup(**setup_args)
