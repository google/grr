#!/usr/bin/env python
"""End to end tests for lib.flows.general.file_finder."""


from grr.endtoend_tests import base
from grr.lib import flow_runner

from grr.lib.flows.general import file_finder


class TestFileFinderOSWindows(base.VFSPathContentIsPE):
  """Download a file with FileFinder.

  Exercise globbing, interpolation and filtering.
  """
  platforms = ["Windows"]
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


class TestFileFinderTSKWindows(base.VFSPathContentIsPE):
  """Download notepad with TSK on windows."""
  platforms = ["Windows"]
  flow = "FileFinder"
  test_output_path = "/fs/os/.*/Windows/System32/notepad.exe"

  download = file_finder.FileFinderDownloadActionOptions()
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
          "action": action,
          "pathtype": "TSK"}


class TestFileFinderOSLinux(base.VFSPathContentIsELF):
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


class TestFileFinderOSLinuxProc(base.VFSPathContentExists):
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


class TestFileFinderOSDarwin(base.VFSPathContentIsMachO):
  platforms = ["Darwin"]
  flow = "FileFinder"
  test_output_path = "/fs/os/bin/ps"


class TestFileFinderOSHomedir(base.AutomatedTest):
  """List files in homedir with FileFinder.

  Exercise globbing and interpolation.
  """
  platforms = ["Linux", "Darwin", "Windows"]
  flow = "FileFinder"
  action = file_finder.FileFinderAction(
      action_type=file_finder.FileFinderAction.Action.STAT)
  args = {"paths": ["%%users.homedir%%/*"],
          "action": action,
          "runner_args": flow_runner.FlowRunnerArgs()}

  def CheckFlow(self):
    self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
