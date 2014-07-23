#!/usr/bin/env python
"""Tests for grr.parsers.volatility_artifact_parser."""




from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import volatility_artifact_parser


class VolatilityVADParserTest(test_lib.GRRBaseTest):
  """Test parsing of volatility "vad" plugin output."""

  @staticmethod
  def GenerateVADVolatilityResult(process_list):
    volatility_response = rdfvalue.VolatilityResult()

    section = rdfvalue.VolatilitySection()
    section.table.headers.Append(print_name="Protection", name="protection")
    section.table.headers.Append(print_name="start", name="start_pfn")
    section.table.headers.Append(print_name="Filename", name="filename")

    for proc in process_list:
      section.table.rows.Append(values=[
          rdfvalue.VolatilityValue(
              type="__MMVAD_FLAGS", name="VadFlags",
              offset=0, vm="None", value=7,
              svalue="EXECUTE_WRITECOPY"),

          rdfvalue.VolatilityValue(
              value=42),

          rdfvalue.VolatilityValue(
              type="_UNICODE_STRING", name="FileName",
              offset=275427702111096,
              vm="AMD64PagedMemory@0x00187000 (Kernel AS@0x187000)",
              value=275427702111096, svalue=proc)
          ])
    volatility_response.sections.Append(section)

    return volatility_response

  def testBasicParsing(self):
    knowledge_base = rdfvalue.KnowledgeBase()
    knowledge_base.environ_systemdrive = "C:"

    parser = volatility_artifact_parser.VolatilityVADParser()
    volatility_data = self.GenerateVADVolatilityResult(
        ["\\WINDOWS\\system.exe", "\\PROGRAM~1\\PROGRAM\\process.exe"])

    expected = [rdfvalue.PathSpec(path="C:\\WINDOWS\\system.exe",
                                  pathtype=rdfvalue.PathSpec.PathType.OS),
                rdfvalue.PathSpec(path="C:\\PROGRAM~1\\PROGRAM\\process.exe",
                                  pathtype=rdfvalue.PathSpec.PathType.OS)]

    results = list(parser.Parse(volatility_data, knowledge_base))
    self.assertListEqual(results, expected)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
