#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
full grr server.
"""
from __future__ import absolute_import
from __future__ import division

import ConfigParser
import itertools
import os
import shutil
import subprocess

from setuptools import find_packages
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist


def find_data_files(source, ignore_dirs=None):
  ignore_dirs = ignore_dirs or []
  result = []
  for directory, dirnames, files in os.walk(source):
    dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

    files = [os.path.join(directory, x) for x in files]
    result.append((directory, files))

  return result


def make_ui_files():
  """Builds necessary assets from sources."""

  # Install node_modules, but keep package(-lock).json frozen.
  subprocess.check_call(["npm", "ci"], cwd="grr_response_server/gui/static")
  subprocess.check_call(["npm", "run", "gulp", "compile"],
                        cwd="grr_response_server/gui/static")


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = ConfigParser.SafeConfigParser()
  config.read(ini_path)
  return config


IGNORE_GUI_DIRS = ["node_modules", "tmp"]

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# If you run setup.py from the root GRR dir you get very different results since
# setuptools uses the MANIFEST.in from the root dir.  Make sure we are in the
# package dir.
os.chdir(THIS_DIRECTORY)

VERSION = get_config()


class Develop(develop):

  def run(self):
    make_ui_files()

    develop.run(self)


class Sdist(sdist):
  """Build sdist."""

  user_options = sdist.user_options + [
      ("no-make-ui-files", None, "Don't build UI JS/CSS bundles (AdminUI "
       "won't work without them)."),
  ]

  def initialize_options(self):
    self.no_make_ui_files = None
    sdist.initialize_options(self)

  def run(self):
    if not self.no_make_ui_files:
      make_ui_files()

    sdist.run(self)

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)
    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


data_files = list(
    itertools.chain(
        find_data_files("grr_response_server/checks"),
        find_data_files("grr_response_server/gui/templates"),
        find_data_files(
            "grr_response_server/gui/static", ignore_dirs=IGNORE_GUI_DIRS),
        find_data_files(
            "grr_response_server/gui/local/static",
            ignore_dirs=IGNORE_GUI_DIRS),
        ["version.ini"],
    ))

setup_args = dict(
    name="grr-response-server",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response Server.",
    license="Apache License, Version 2.0",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    url="https://github.com/google/grr",
    cmdclass={
        "sdist": Sdist,
        "develop": Develop
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "grr_console = "
            "grr_response_server.distro_entry:Console",
            "grr_api_shell_raw_access = "
            "grr_response_server.distro_entry:ApiShellRawAccess",
            "grr_config_updater = "
            "grr_response_server.distro_entry:ConfigUpdater",
            "grr_frontend = "
            "grr_response_server.distro_entry:GrrFrontend",
            "grr_server = "
            "grr_response_server.distro_entry:GrrServer",
            "grr_worker = "
            "grr_response_server.distro_entry:Worker",
            "grr_admin_ui = "
            "grr_response_server.distro_entry:AdminUI",
            "grr_fuse = "
            "grr_response_server.distro_entry:GRRFuse",
        ]
    },
    install_requires=[
        "google-api-python-client==1.6.2",
        "google-auth==1.2.1",
        "google-cloud-bigquery==0.22.1",
        "grr-api-client==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "Jinja2==2.9.5",
        "pexpect==4.0.1",
        "portpicker==1.1.1",
        "python-crontab==2.0.1",
        "python-debian==0.1.31",
        "Werkzeug==0.11.3",
        "wsgiref==0.1.2",
    ],
    extras_require={
        # This is an optional component. Install to get MySQL data
        # store support:
        # pip install grr-response[mysqldatastore]
        "mysqldatastore": ["mysqlclient==1.3.12"],
    },
    data_files=data_files)

setup(**setup_args)
