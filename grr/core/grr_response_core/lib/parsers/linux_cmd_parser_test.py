#!/usr/bin/env python
"""Unit test for the linux cmd parser."""

from absl import app

from grr.test_lib import test_lib


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
