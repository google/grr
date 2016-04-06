#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.
"""
from setuptools import setup

setup(
    name="grr-response-client",
    version="3.1.0",
    description="The GRR Rapid Response client.",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr",
    entry_points={
        "console_scripts": [
            "grr_client = grr.lib.distro_entry:Client",
            "grr_client_build = grr.lib.distro_entry:ClientBuild",
        ]
    },
    install_requires=[
        "grr-response-core",
    ],
)
