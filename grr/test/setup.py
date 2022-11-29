#!/usr/bin/env python
"""This is the setup.py file for the GRR response test code.

This package contains all the test data and test runners required to be able to
run GRR tests.

If you want to do any development, you probably want this.

"""

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
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = configparser.ConfigParser()
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
    name="grr-response-test",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response test suite.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    install_requires=[
        "absl-py==1.2.0",
        "flaky==3.6.1",
        "pytest==6.2.2",
        "responses==0.12.1",
        "selenium==3.141.0",
        "google-api-python-client==1.9.3",
        "grr-api-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-server==%s" % VERSION.get("Version", "packagedepends"),
    ],
    cmdclass={"sdist": Sdist},
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "grr_end_to_end_tests = "
            "grr_response_test.distro_entry:EndToEndTests",
            "grr_api_regression_generate = "
            "grr_response_test.distro_entry:ApiRegressionTestsGenerate",
            "grr_dump_mysql_schema = "
            "grr_response_test.distro_entry:DumpMySQLSchema"
        ]
    })

setup(**setup_args)
