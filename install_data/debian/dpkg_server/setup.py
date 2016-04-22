#!/usr/bin/env python
"""This setup.py is used to install into the virtualenv.

NOTE: This is specifically written to work together with dh-virtualenv. Do not
install this by itself.
"""

import os
import subprocess
import sys

import pkg_resources

from setuptools import setup
from setuptools.command.install import install


class Install(install):
  """This installs into the deb package's virtual env."""

  def run(self):
    working_directory = os.path.abspath(os.getcwd() + "/../")
    virtualenv_bin = os.path.dirname(sys.executable)
    pip = "%s/pip" % virtualenv_bin

    # Install the GRR server component to satisfy the dependency below.
    subprocess.check_call(
        [sys.executable, pip, "install", "."],
        cwd=working_directory)

    # Install the grr-response-server metapackage to get the remaining
    # dependencies and the entry points.
    subprocess.check_call(
        [sys.executable, pip, "install", "."],
        cwd=working_directory + "/grr/config/grr-response-server/")

    major_minor_version = ".".join(
        pkg_resources.get_distribution(
            "grr-response-core").version.split(".")[0:2])
    subprocess.check_call(
        [sys.executable, pip, "install", "-f",
         "https://storage.googleapis.com/releases.grr-response.com/index.html",
         "grr-response-templates==%s.*" % major_minor_version],
        cwd=working_directory)


setup_args = dict(
    cmdclass={
        "install": Install,
    },
)

setup(**setup_args)
