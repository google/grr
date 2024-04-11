#!/usr/bin/env python
"""Tests for grr.parsers.windows_registry_parser."""

from absl import app

from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class WindowsRegistryParserTest(flow_test_lib.FlowTestsBaseclass):

  def _MakeRegStat(self, path, value, registry_type):
    options = rdf_paths.PathSpec.Options.CASE_LITERAL
    pathspec = rdf_paths.PathSpec(
        path=path,
        path_options=options,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
    )

    if registry_type == rdf_client_fs.StatEntry.RegistryType.REG_MULTI_SZ:
      reg_data = rdf_protodict.DataBlob(
          list=rdf_protodict.BlobArray(
              content=[rdf_protodict.DataBlob(string=value)]
          )
      )
    else:
      reg_data = rdf_protodict.DataBlob().SetValue(value)

    return rdf_client_fs.StatEntry(
        pathspec=pathspec, registry_data=reg_data, registry_type=registry_type
    )

  def testWinSystemDriveParser(self):
    sysroot = (
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT"
        r"\CurrentVersion\SystemRoot"
    )
    stat = self._MakeRegStat(sysroot, r"C:\Windows", None)
    parser = windows_registry_parser.WinSystemDriveParser()
    self.assertEqual(r"C:", next(parser.Parse(stat, None)))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
