#!/usr/bin/env python
"""End to end tests for lib.flows.general.memory."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import rdfvalue


class TestAnalyzeClientMemoryVolatility(base.AutomatedTest):
  """Test AnalyzeClientMemoryVolatility."""
  platforms = ["Windows"]
  flow = "AnalyzeClientMemoryVolatility"
  test_output_path = "analysis/pslist/testing"
  args = {"request": rdfvalue.VolatilityRequest(
      plugins=["pslist"], args={"pslist": {}}),
          "output": test_output_path}

  def CheckFlow(self):
    response = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                 token=self.token)
    self.assertIsInstance(response, aff4.RDFValueCollection)
    self.assertEqual(len(response), 1)
    result = response[0]
    self.assertEqual(result.error, "")
    self.assertGreater(len(result.sections), 0)

    rows = result.sections[0].table.rows
    self.assertGreater(len(rows), 0)

    expected_name = self.GetGRRBinaryName()
    for values in rows:
      for value in values.values:
        if value.name == "ImageFileName":
          if expected_name == value.svalue:
            return

    self.fail("Process listing does not contain %s." % expected_name)


class TestGrepMemory(base.AutomatedTest):
  """Test ScanMemory."""
  platforms = ["Windows", "Darwin"]
  flow = "ScanMemory"
  test_output_path = "analysis/grep/testing"
  args = {"also_download": False,
          "grep": rdfvalue.BareGrepSpec(
              literal="grr", length=4*1024*1024*1024,
              mode=rdfvalue.GrepSpec.Mode.FIRST_HIT,
              bytes_before=10, bytes_after=10),
          "output": test_output_path,}

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                   token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)
    self.assertEqual(len(list(collection)), 1)
    reference = collection[0]

    self.assertEqual(reference.length, 23)
    self.assertEqual(reference.data[10:10+3], "grr")


