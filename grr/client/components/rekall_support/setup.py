#!/usr/bin/env python
"""Rekall GRR integration."""
__author__ = "Michael Cohen <scudette@gmail.com>"

from setuptools import setup

setup_args = dict(name="grr-rekall",
                  version="0.4",
                  description="Rekall GRR Integration module.",
                  license="GPL",
                  url="https://www.rekall-forensic.com/",
                  author="The Rekall team",
                  author_email="rekall-discuss@googlegroups.com",
                  classifiers=[
                      "Development Status :: 4 - Beta",
                      "Environment :: Console",
                      "Operating System :: OS Independent",
                      "Programming Language :: Python",
                  ],
                  py_modules=[
                      "grr_rekall",
                      "memory",
                      "rekall_types",
                      "rekall_pb2",
                  ],
                  install_requires=[
                      "rekall-core == 1.5.2rc1",
                  ],
                  zip_safe=False,)

if __name__ == "__main__":
  setup(**setup_args)
