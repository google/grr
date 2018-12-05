#!/usr/bin/env python
"""Tests for grr.parsers.rekall_artifact_parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import os
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import rekall_artifact_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr.test_lib import test_lib


class RekallVADParserTest(test_lib.GRRBaseTest):
  """Test parsing of the Rekall "vad" plugin output."""

  def testBasicParsing(self):
    ps_list_file = os.path.join(config.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat.gz")

    result = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file, "rb").read(), plugin="pslist")

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.environ_systemdrive = "C:"

    parser = rekall_artifact_parser.RekallVADParser()
    parsed_pathspecs = list(parser.Parse(result, knowledge_base))

    paths = [p.path for p in parsed_pathspecs]
    self.assertIn(u"C:\\Windows\\System32\\spoolsv.exe", paths)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
