#!/usr/bin/env python
"""Chipsec GRR integration."""
__author__ = "Thiebaud Weksteen <tweksteen@gmail.com>"

import platform

from setuptools import setup

setup_args = dict(
    name="grr-chipsec",
    version="0.1",
    description="Chipsec GRR Integration module.",
    license="GPL",
    url="https://github.com/chipsec/chipsec/",
    author="Thiebaud Weksteen",
    author_email="tweksteen@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    py_modules=[
        "grr_chipsec",
        "chipsec_types",
        "chipsec_pb2"
    ],
    install_requires=[
        "chipsec"
    ],
    dependency_links=[
        # Chipsec tarball
        # branch userland_linux_with_cleanup
        # comment out is_frozen in get_main_dir
        # then: python setup.py sdist
        ("http://www.googledrive.com/host/"
         "0B1syiKu7qItDYU13X25qQ2U4LU0/chipsec-1.2.2.tar.gz"),
    ],
    zip_safe=False,
)


# Currently this is only enabled in Linux.
if platform.system() != "Linux":
  setup_args["install_requires"] = []
  setup_args["py_modules"] = []


if __name__ == "__main__":
  setup(**setup_args)
