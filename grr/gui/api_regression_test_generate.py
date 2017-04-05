#!/usr/bin/env python
"""Program that generates golden regression data."""


from grr.gui import api_regression_test_lib

# pylint: disable=unused-import
from grr.gui.api_plugins import tests
# pylint: enable=unused-import

from grr.lib import flags


def main(argv):
  """Entry function."""
  api_regression_test_lib.main(argv)


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  flags.StartMain(main)
