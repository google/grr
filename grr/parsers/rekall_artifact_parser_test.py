#!/usr/bin/env python
"""Tests for grr.parsers.rekall_artifact_parser."""



import gzip
import os
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.parsers import rekall_artifact_parser


class RekallVADParserTest(test_lib.GRRBaseTest):
  """Test parsing of the Rekall "vad" plugin output."""

  def testBasicParsing(self):
    ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat.gz")

    result = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file).read(10000000),
        plugin="pslist")

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
