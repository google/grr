#!/usr/bin/env python
"""Chipsec GRR integration."""
__author__ = "Thiebaud Weksteen <tweksteen@gmail.com>"

import platform

from setuptools import setup

# Note this component was renamed from grr-chipsec so as not to conflict with
# the grr-chipsec module published on pypi.
setup_args = dict(name="grr-chipsec-component",
                  version="1.2.2",
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
                      "grr_chipsec", "chipsec_types", "chipsec_pb2"
                  ],
                  install_requires=[
                      "grr-chipsec == 1.2.2",
                  ],
                  zip_safe=False)

# Currently this is only enabled in Linux.
if platform.system() != "Linux":
  setup_args["install_requires"] = []
  setup_args["py_modules"] = []

if __name__ == "__main__":
  setup(**setup_args)
