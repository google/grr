#!/usr/bin/env python
"""Tests for Windows Volume Shadow Copy flow."""
import stat

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
# needed for ListVolumeShadowCopies pylint: disable=unused-import
from grr.lib.flows.general import windows_vsc
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class TestClient(object):
  """A test client mock."""

  _RESPONSES = {
      "Caption": "None",
      "ClientAccessible": "True",
      "Count": "1",
      "Description": "None",
      "DeviceObject": r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy3",
      "Differential": "True",
      "ExposedLocally": "False",
      "ExposedName": "None",
      "ExposedPath": "None",
      "ExposedRemotely": "False",
      "HardwareAssisted": "False",
      "ID": "{4F1D1E03-C7C1-4023-8CE9-5FF4D16E133D}",
      "Imported": "False",
      "InstallDate": "20130430022911.144000-420",
      "Name": "None",
      "NoAutoRelease": "True",
      "NotSurfaced": "False",
      "NoWriters": "False",
      "OriginatingMachine": "mic-PC",
      "Persistent": "True",
      "Plex": "False",
      "ProviderID": "{B5946137-7B9F-4925-AF80-51ABD60B20D5}",
      "ServiceMachine": "mic-PC",
      "SetID": "{9419738B-113C-4ACC-BD64-DADDD3B88381}",
      "State": "12",
      "Status": "None",
      "Transportable": "False",
      "VolumeName": r"\\?\Volume{f2180d84-7eb0-11e1-bed0-806e6f6e6963}",
  }

  def WmiQuery(self, query):
    expected_query = "SELECT * FROM Win32_ShadowCopy"
    if query.query != expected_query:
      raise RuntimeError("Received unexpected query.")

    return [rdf_protodict.Dict(**self._RESPONSES)]

  def ListDirectory(self, list_directory_request):
    """A mock list directory."""
    pathspec = list_directory_request.pathspec
    if not pathspec:
      raise RuntimeError("Missing pathspec.")

    if (pathspec.path != r"\\.\HarddiskVolumeShadowCopy3" or
        pathspec.pathtype != rdf_paths.PathSpec.PathType.OS):
      raise RuntimeError("Invalid pathspec.")

    if not pathspec.nested_path:
      raise RuntimeError("Missing nested pathspec.")

    if (pathspec.nested_path.path != "/" or
        pathspec.nested_path.pathtype != rdf_paths.PathSpec.PathType.TSK):
      raise RuntimeError("Invalid nested pathspec.")

    result = []
    for i in range(10):
      mock_pathspec = pathspec.Copy()
      mock_pathspec.last.path = "/file %s" % i
      result.append(rdf_client.StatEntry(pathspec=mock_pathspec,
                                         st_mode=stat.S_IFDIR))

    return result


class TestListVolumeShadowCopies(test_lib.FlowTestsBaseclass):
  """Test the list Volume Shadow Copies flow."""

  def testListVolumeShadowCopies(self):
    """Test the list Volume Shadow Copies flow."""
    flow_name = "ListVolumeShadowCopies"

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(flow_name,
                                     TestClient(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    fd = aff4.FACTORY.Open(
        self.client_id.Add("fs/tsk/\\\\.\\HarddiskVolumeShadowCopy3"),
        token=self.token)

    children = list(fd.ListChildren())

    self.assertEqual(len(children), 10)
    self.assertEqual([x.Basename() for x in sorted(children)],
                     ["file %s" % i for i in range(10)])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
