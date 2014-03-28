#!/usr/bin/env python
"""End to end tests for lib.flows.general.file_finder."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.flows.console.client_tests import transfer


class TestFileFinderOSWindows(transfer.TestGetFileOSWindows):
  """Download a file with FileFinder.

  Exercise globbing, interpolation and filtering.
  """
  flow = "FileFinder"
  output_path = "/fs/os/.*/Windows/System32/notepad.exe"

  sizecondition = rdfvalue.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = rdfvalue.FileFinderCondition(
      condition_type=rdfvalue.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = rdfvalue.FileFinderDownloadActionOptions()
  action = rdfvalue.FileFinderAction(
      action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
          "conditions": filecondition, "action": action}


class TestFileFinderOSLinuxDarwin(transfer.TestGetFileOSLinux):
  """Download a file with FileFinder."""
  platforms = ["linux", "darwin"]
  flow = "FileFinder"
  output_path = "/fs/os/bin/ps"

  sizecondition = rdfvalue.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = rdfvalue.FileFinderCondition(
      condition_type=rdfvalue.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = rdfvalue.FileFinderDownloadActionOptions()
  action = rdfvalue.FileFinderAction(
      action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["/bin/ps"],
          "conditions": filecondition, "action": action}


class TestFileFinderOSHomedir(TestFileFinderOSLinuxDarwin):
  """List files in homedir with FileFinder.

  Exercise globbing and interpolation.
  """
  platforms = ["linux", "darwin", "windows"]
  download = rdfvalue.FileFinderDownloadActionOptions()
  action = rdfvalue.FileFinderAction(
      action_type=rdfvalue.FileFinderAction.Action.STAT)

  output_path = "/analysis/test/homedirs"
  args = {"paths": ["%%users.homedir%%/*"], "action": action,
          "runner_args": rdfvalue.FlowRunnerArgs(output=output_path)}

  def CheckFlow(self):
    results = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                                token=self.token)
    self.assertEqual(type(results), aff4.RDFValueCollection)
    self.assertTrue(len(results) > 1)
