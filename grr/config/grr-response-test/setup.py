#!/usr/bin/env python
"""This is the setup.py file for the GRR response test code.

This package contains all the test data and test runners required to be able to
run GRR tests.

If you want to do any development, you probably want this.

"""
import ConfigParser
import os
import shutil
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
    ini_path = os.path.join(THIS_DIRECTORY, "../../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = ConfigParser.SafeConfigParser()
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
        os.path.join(THIS_DIRECTORY, "../../../version.ini"), sdist_version_ini)


def find_data_files(source):
  result = []
  for directory, _, files in os.walk(source):
    files = [os.path.join(directory, x) for x in files]
    result.append((directory, files))

  return result


if "VIRTUAL_ENV" not in os.environ:
  print "*****************************************************"
  print "  WARNING: You are not installing in a virtual"
  print "  environment. This configuration is not supported!!!"
  print "  Expect breakage."
  print "*****************************************************"

setup_args = dict(name="grr-response-test",
                  version=VERSION.get("Version", "packageversion"),
                  description="The GRR Rapid Response test suite.",
                  license="Apache License, Version 2.0",
                  url="https://github.com/google/grr",
                  install_requires=[
                      "mock==1.3.0",
                      "mox==0.5.3",
                      "selenium==2.50.1",
                      "grr-response-server==%s" %
                      VERSION.get("Version", "packagedepends"),
                  ],
                  cmdclass={"sdist": Sdist},
                  data_files=(find_data_files("test_data") + ["version.ini"]),
                  entry_points={
                      "console_scripts": [
                          "grr_run_tests = grr.tools.run_tests:DistEntry",
                          "grr_run_tests_gui = grr.gui.runtests_test:DistEntry",
                      ]
                  })

setup(**setup_args)
