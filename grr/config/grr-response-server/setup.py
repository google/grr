#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
full grr server.
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


if "VIRTUAL_ENV" not in os.environ:
  print "*****************************************************"
  print "  WARNING: You are not installing in a virtual"
  print "  environment. This configuration is not supported!!!"
  print "  Expect breakage."
  print "*****************************************************"

setup_args = dict(
    name="grr-response-server",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response Server.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    cmdclass={"sdist": Sdist},
    entry_points={
        "console_scripts": [
            "grr_console = grr.lib.distro_entry:Console",
            "grr_config_updater = grr.lib.distro_entry:ConfigUpdater",
            "grr_front_end = grr.lib.distro_entry:GrrFrontEnd",
            "grr_server = grr.lib.distro_entry:GrrServer",
            "grr_end_to_end_tests = grr.lib.distro_entry:EndToEndTests",
            "grr_export = grr.lib.distro_entry:Export",
            "grr_worker = grr.lib.distro_entry:Worker",
            "grr_admin_ui = grr.lib.distro_entry:AdminUI",
            "grr_fuse = grr.lib.distro_entry:GRRFuse",
            "grr_dataserver = grr.lib.distro_entry:DataServer",
        ]
    },
    install_requires=[
        "Django==1.8.3",
        "google-api-python-client==1.4.2",
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "grr-response-client==%s" % VERSION.get("Version", "packagedepends"),
        "oauth2client==1.5.2",
        "pexpect==4.0.1",
        "portpicker==1.1.1",
        "python-crontab==2.0.1",
        "rekall-core~=1.5.1",
        "Werkzeug==0.11.3",
        "wsgiref==0.1.2",
    ],
    extras_require={
        # This is an optional component. Install to get MySQL data
        # store support:
        # pip install grr-response[mysqldatastore]
        "mysqldatastore": [
            "MySQL-python==1.2.5"
        ],
    },
    data_files=["version.ini"])

setup(**setup_args)
