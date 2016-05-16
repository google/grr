#!/usr/bin/env python
"""This is the setup.py file for the GRR client.

This is just a meta-package which pulls in the minimal requirements to create a
client.

This package needs to stay simple so that it can be installed on windows and
ancient versions of linux to build clients.
"""
import platform
from setuptools import setup

setup(
    name="grr-response-client",
    version="3.1.0post1",
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
        "grr-response-core==3.1.*",
    ] + (["pyinstaller==3.2"] if (
        platform.linux_distribution()[0] == "CentOS") else [
            "pyinstaller==3.1.1"]),
)
