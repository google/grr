#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for rdfvalues."""



from grr.client import conf

from grr.lib import test_lib
from grr.lib.rdfvalues import test_base
# pylint: disable=unused-import
from grr.lib.rdfvalues import tests
from grr.lib.flows.caenroll import ca_enroller
# pylint: enable=unused-import


class RDFValueTestLoader(test_lib.GRRTestLoader):
  base_class = test_base.RDFValueTestCase


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=RDFValueTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
