#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
full grr server.
"""
from setuptools import setup

setup(
    name="grr-response-server",
    version="3.1.0",
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
        "grr-response-core[Server,test]",
        "grr-response-client",
    ],

    extras_require={
        # This is an optional component. Install to get MySQL data
        # store support:
        # pip install grr-response[MySQLDataStore]
        "MySQLDataStore": [
            "MySQL-python==1.2.5"
        ],
    }
)
