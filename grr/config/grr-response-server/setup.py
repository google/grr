#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
full grr server.
"""
import ConfigParser
import os
from setuptools import setup


def get_config():
  config = ConfigParser.SafeConfigParser()
  config.read(os.path.join(
      os.path.dirname(os.path.realpath(__file__)), "../../version.ini"))
  return config


VERSION = get_config()


setup_args = dict(
    name="grr-response-server",
    version=VERSION.get("Version", "packageversion"),
    description="The GRR Rapid Response Server.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
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
        "rekall-core>=1.5.0.post4",
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
    }
)

setup(**setup_args)
