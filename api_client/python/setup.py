#!/usr/bin/env python
"""setup.py file for a GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import configparser
import os
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
  # TODO(hanuszczak): See comment in `setup.py` for `grr-response-proto`.
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
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
        "grr_response_proto==%s" % VERSION.get("Version", "packagedepends"),
        "cryptography==2.9.2",
        "requests==2.23.0",
        "Werkzeug>=0.16.0,<=1.0.1",
    ],
    extra_requires={
        "shell": ["ipython==7.15.0",],
    },
    data=["version.ini"])

setup(**setup_args)
