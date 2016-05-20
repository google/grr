#!/usr/bin/env python
"""This is the setup.py file for the GRR response test code.

This package contains all the test data and test runners required to be able to
run GRR tests.

If you want to do any development, you probably want this.

"""
import ConfigParser
import os
from setuptools import setup


def get_config():
  config = ConfigParser.SafeConfigParser()
  config.read(os.path.join(
      os.path.dirname(os.path.realpath(__file__)), "../../../version.ini"))
  return config


VERSION = get_config()


def find_data_files(source):
  result = []
  for directory, _, files in os.walk(source):
    files = [os.path.join(directory, x) for x in files]
    result.append((directory, files))

  return result


setup_args = dict(
    name="grr-response-test",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response test suite.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    install_requires=[
        "mock==1.3.0",
        "mox==0.5.3",
        "selenium==2.50.1",
        "grr-response-server==%s" % VERSION.get("Version", "packagedepends"),
    ],
    data_files=find_data_files("test_data"),
    entry_points={
        "console_scripts": [
            "grr_run_tests = grr.tools.run_tests:DistEntry",
            "grr_run_tests_gui = grr.gui.runtests_test:DistEntry",
        ]
    }
)

setup(**setup_args)
