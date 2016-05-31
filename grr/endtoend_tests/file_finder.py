#!/usr/bin/env python
"""End to end tests for lib.flows.general.file_finder."""


from grr.endtoend_tests import transfer
from grr.lib import aff4
from grr.lib import flow_runner
from grr.lib.aff4_objects import collects

from grr.lib.flows.general import file_finder


class TestFileFinderOSWindows(transfer.TestGetFileOSWindows):
  """Download a file with FileFinder.

  Exercise globbing, interpolation and filtering.
  """
  flow = "FileFinder"
  test_output_path = "/fs/os/.*/Windows/System32/notepad.exe"

  sizecondition = file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = file_finder.FileFinderCondition(
      condition_type=file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = file_finder.FileFinderDownloadActionOptions()
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
          "conditions": filecondition,
          "action": action}


class TestFileFinderTSKWindows(TestFileFinderOSWindows):

  download = file_finder.FileFinderDownloadActionOptions()
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)
  test_output_path = "/fs/tsk/.*/Windows/System32/notepad.exe"

  args = {"paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
          "action": action,
          "pathtype": "TSK"}


class TestFileFinderOSLinux(transfer.TestGetFileOSLinux):
  """Download a file with FileFinder."""
  platforms = ["Linux"]
  flow = "FileFinder"
  test_output_path = "/fs/os/bin/ps"

  sizecondition = file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = file_finder.FileFinderCondition(
      condition_type=file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = file_finder.FileFinderDownloadActionOptions()
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["/bin/ps"],
          "conditions": filecondition,
          "action": action}


class TestFileFinderOSLinuxProc(transfer.TestGetFileOSLinux):
  """Download a /proc/sys entry with FileFinder."""
  platforms = ["Linux"]
  flow = "FileFinder"
  test_output_path = "/fs/os/proc/sys/net/ipv4/ip_forward"
  client_min_version = 3007

  sizecondition = file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = file_finder.FileFinderCondition(
      condition_type=file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = file_finder.FileFinderDownloadActionOptions()
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["/proc/sys/net/ipv4/ip_forward"],
          "conditions": filecondition,
          "action": action}

  def CheckFile(self, fd):
    data = fd.Read(10)
    # Some value was read from the sysctl.
    self.assertTrue(data)


class TestFileFinderOSDarwin(TestFileFinderOSLinux):
  platforms = ["Darwin"]

  def CheckFile(self, fd):
    self.CheckMacMagic(fd)


class TestFileFinderOSHomedir(TestFileFinderOSLinux):
  """List files in homedir with FileFinder.

  Exercise globbing and interpolation.
  """
  platforms = ["Linux", "Darwin", "Windows"]
  test_output_path = "/analysis/test/homedirs"
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.STAT)
  args = {"paths": ["%%users.homedir%%/*"],
          "action": action,
          "runner_args": flow_runner.FlowRunnerArgs(output=test_output_path)}

  def CheckFlow(self):
    results = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    self.assertEqual(type(results), collects.RDFValueCollection)
    self.assertTrue(len(results) > 1)
