#!/usr/bin/env python
"""Tests for grr.parsers.windows_persistence."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import windows_persistence
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class WindowsPersistenceMechanismsParserTest(flow_test_lib.FlowTestsBaseclass):

  def testParse(self):
    parser = windows_persistence.WindowsPersistenceMechanismsParser()
    path = (r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion"
            r"\Run\test")
    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
    reg_data = "C:\\blah\\some.exe /v"
    reg_type = rdf_client_fs.StatEntry.RegistryType.REG_SZ
    stat = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        registry_type=reg_type,
        registry_data=rdf_protodict.DataBlob(string=reg_data))

    persistence = [stat]
    image_paths = [
        "system32\\drivers\\ACPI.sys",
        "%systemroot%\\system32\\svchost.exe -k netsvcs",
        "\\SystemRoot\\system32\\drivers\\acpipmi.sys"
    ]
    reg_key = "HKEY_LOCAL_MACHINE/SYSTEM/CurrentControlSet/services/AcpiPmi"
    for path in image_paths:
      serv_info = rdf_client.WindowsServiceInformation(
          name="blah",
          display_name="GRRservice",
          image_path=path,
          registry_key=reg_key)
      persistence.append(serv_info)

    knowledge_base = rdf_client.KnowledgeBase()
    knowledge_base.environ_systemroot = "C:\\Windows"

    expected = [
        "C:\\blah\\some.exe", "C:\\Windows\\system32\\drivers\\ACPI.sys",
        "C:\\Windows\\system32\\svchost.exe",
        "C:\\Windows\\system32\\drivers\\acpipmi.sys"
    ]

    for index, item in enumerate(persistence):
      results = list(
          parser.Parse(item, knowledge_base, rdf_paths.PathSpec.PathType.OS))
      self.assertEqual(results[0].pathspec.path, expected[index])
      self.assertLen(results, 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
