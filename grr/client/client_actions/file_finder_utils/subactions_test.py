#!/usr/bin/env python
import unittest
from grr.lib import flags
from grr.test_lib import test_lib

# TODO(hanuszczak): Implement basic unit tests for subactions.


class StatActionTest(unittest.TestCase):
  pass


class HashActionTest(unittest.TestCase):
  pass


class DownloadActionTest(unittest.TestCase):
  pass


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
