#!/usr/bin/env python
"""A Test component."""

from setuptools import setup

setup_args = dict(name="grr-test-component",
                  version="1.0",
                  description="GRR Test component",
                  py_modules=[
                      "grr_test_component"
                  ],)

if __name__ == "__main__":
  setup(**setup_args)
