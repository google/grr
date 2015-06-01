#!/usr/bin/env python
"""Tests for grr.parsers.windows_persistence."""

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.parsers import windows_persistence


class WindowsPersistenceMechanismsParserTest(test_lib.FlowTestsBaseclass):

  def testParse(self):
    parser = windows_persistence.WindowsPersistenceMechanismsParser()
    path = (r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion"
            r"\Run\test")
    pathspec = rdf_paths.PathSpec(path=path,
                                  pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
    reg_data = "C:\\blah\\some.exe /v"
    reg_type = rdf_client.StatEntry.RegistryType.REG_SZ
    stat = rdf_client.StatEntry(
        aff4path="aff4:/asdfasdf/",
        pathspec=pathspec,
        registry_type=reg_type,
        registry_data=rdf_protodict.DataBlob(string=reg_data))

    persistence = [stat]
    image_paths = ["system32\\drivers\\ACPI.sys",
                   "%systemroot%\\system32\\svchost.exe -k netsvcs",
                   "\\SystemRoot\\system32\\drivers\\acpipmi.sys"]
    reg_key = rdfvalue.RDFURN("aff4:/C.1000000000000000/registry"
                              "/HKEY_LOCAL_MACHINE/SYSTEM/ControlSet001"
                              "/services/AcpiPmi")
    for path in image_paths:
      serv_info = rdf_client.WindowsServiceInformation(
          name="blah",
          display_name="GRRservice",
          image_path=path,
          registry_key=reg_key)
      persistence.append(serv_info)

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.environ_systemroot = "C:\\Windows"

    expected = ["C:\\blah\\some.exe",
                "C:\\Windows\\system32\\drivers\\ACPI.sys",
                "C:\\Windows\\system32\\svchost.exe",
                "C:\\Windows\\system32\\drivers\\acpipmi.sys"]

    for index, item in enumerate(persistence):
      results = list(parser.Parse(item, knowledge_base,
                                  rdf_paths.PathSpec.PathType.OS))
      self.assertEqual(results[0].pathspec.path, expected[index])
      self.assertEqual(len(results), 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
