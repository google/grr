#!/usr/bin/env python
"""Tests for grr.parsers.rekall_artifact_parser."""




import os
import pickle

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import rekall_artifact_parser


class RekallVADParserTest(test_lib.GRRBaseTest):
  """Test parsing of the Rekall "vad" plugin output."""

  def testBasicParsing(self):
    ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat")
    serialized_responses = pickle.loads(open(ps_list_file, "rb").read())
    responses = [rdfvalue.GrrMessage(x).payload for x in serialized_responses]

    knowledge_base = rdfvalue.KnowledgeBase()
    knowledge_base.environ_systemdrive = "C:"

    parser = rekall_artifact_parser.RekallVADParser()
    parsed_pathspecs = list(parser.ParseMultiple(responses, knowledge_base))

    paths = [p.path for p in parsed_pathspecs]
    for reference_path in [
        u"C:\\Windows\\System32\\spoolsv.exe",
        (u"C:\\Users\\testing\\AppData\\Local\\"
         u"Temp\\Temp1_DumpIt.zip\\DumpIt.exe")]:
      self.assertIn(reference_path, paths)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
