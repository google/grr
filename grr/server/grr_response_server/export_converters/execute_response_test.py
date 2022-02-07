#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""

from absl import app

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_server.export_converters import execute_response
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class ExecuteResponseConverterTest(export_test_lib.ExportTestBase):
  """Tests for ExecuteResponseConverter."""

  def testExportsValueCorrectly(self):
    sample = rdf_client_action.ExecuteResponse(
        request=rdf_client_action.ExecuteRequest(
            cmd="some cmd",
            args=["-foo", "-bar"],
            time_limit=42,
        ),
        exit_status=-1,
        stdout=b"stdout",
        stderr=b"stderr",
        time_used=420,
    )

    converter = execute_response.ExecuteResponseConverter()
    converted = list(converter.Convert(self.metadata, sample))
    self.assertLen(converted, 1)
    c = converted[0]

    self.assertEqual(c.metadata, self.metadata)
    self.assertEqual(c.cmd, "some cmd")
    self.assertEqual(c.args, "-foo -bar")
    self.assertEqual(c.exit_status, -1)
    self.assertEqual(c.stdout, b"stdout")
    self.assertEqual(c.stderr, b"stderr")
    self.assertEqual(c.time_used_us, 420)

  def testExportsEmptyValueCorrectly(self):
    sample = rdf_client_action.ExecuteResponse()

    converter = execute_response.ExecuteResponseConverter()
    converted = list(converter.Convert(self.metadata, sample))
    self.assertLen(converted, 1)
    c = converted[0]

    self.assertEqual(c.metadata, self.metadata)
    self.assertEqual(c.cmd, "")
    self.assertEqual(c.args, "")
    self.assertEqual(c.exit_status, 0)
    self.assertEqual(c.stdout, b"")
    self.assertEqual(c.stderr, b"")
    self.assertEqual(c.time_used_us, 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
