#!/usr/bin/env python
"""Stubs for the Chipsec component unit tests."""

__author__ = "tweksteen@gmail.com (Thiebaud Weksteen)"

from grr.client import actions
from grr.client.components.chipsec_support.actions import chipsec_types


class DumpFlashImage(actions.ActionPlugin):
  """A client action to collect the BIOS via SPI using Chipsec."""

  in_rdfvalue = chipsec_types.DumpFlashImageRequest
  out_rdfvalues = [chipsec_types.DumpFlashImageResponse]


class DumpACPITable(actions.ActionPlugin):
  """A client action to collect the ACPI table(s)."""

  in_rdfvalue = chipsec_types.DumpACPITableRequest
  out_rdfvalues = [chipsec_types.DumpACPITableResponse]
