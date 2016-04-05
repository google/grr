#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for rdfvalues."""



from grr.lib import flags
from grr.lib import test_lib

# pylint: disable=unused-import
from grr.lib.rdfvalues import test_base
from grr.lib.rdfvalues import tests
# pylint: enable=unused-import


class RDFValueTestLoader(test_lib.GRRTestLoader):
  base_class = test_base.RDFValueBaseTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=RDFValueTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
