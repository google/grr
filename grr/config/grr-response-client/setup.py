#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.

This package needs to stay simple so that it can be installed on windows and
ancient versions of linux to build clients.
"""
import ConfigParser
import os
import platform
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
    name="grr-response-client",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response client.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    entry_points={
        "console_scripts": [
            "grr_client = grr.client.distro_entry:Client",
            "grr_client_build = grr.client.distro_entry:ClientBuild",
            "grr_pool_client = grr.client.distro_entry:PoolClient"
        ]
    },
    cmdclass={"sdist": Sdist},
    data_files=["version.ini"],
    install_requires=[
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
        "rekall-core==1.6.0", "pyinstaller==3.2.1"
    ] + (["chipsec==1.2.4"] if platform.system() == "Linux" else []),)

setup(**setup_args)
