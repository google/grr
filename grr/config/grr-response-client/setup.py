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
from setuptools import setup


def get_config():
  config = ConfigParser.SafeConfigParser()
  config.read(os.path.join(
      os.path.dirname(os.path.realpath(__file__)), "../../../version.ini"))
  return config


VERSION = get_config()


setup_args = dict(
    name="grr-response-client",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response client.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    entry_points={
        "console_scripts": [
            "grr_client = grr.lib.distro_entry:Client",
            "grr_client_build = grr.lib.distro_entry:ClientBuild",
        ]
    },
    # We need pyinstaller 3.2 for centos but it's broken on windows.
    # https://github.com/google/grr/issues/367
    install_requires=[
        "grr-response-core==%s" % VERSION.get("Version", "packagedepends"),
    ] + (["pyinstaller==3.2"] if (
        platform.linux_distribution()[0] == "CentOS") else [
            "pyinstaller==3.1.1"]),
)

setup(**setup_args)
