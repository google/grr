#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""End to end tests for lib.flows.general.file_finder."""


from grr.client.client_actions import standard
from grr.endtoend_tests import base
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import flows as rdf_flows

from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import flow
from grr.server.flows.general import file_finder


class TestFileFinderOSWindows(base.VFSPathContentIsPE):
  """Download a file with FileFinder.

  Exercise globbing, interpolation and filtering.
  """
  platforms = ["Windows"]
  flow = file_finder.FileFinder.__name__
  test_output_path = "/fs/os/C:/Windows/System32/notepad.exe"

  sizecondition = rdf_file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = rdf_file_finder.FileFinderCondition(
      condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = rdf_file_finder.FileFinderDownloadActionOptions()
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {
      "paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
      "conditions": filecondition,
      "action": action
  }


class TestFileFinderTSKWindows(base.VFSPathContentIsPE):
  """Download notepad with TSK on windows."""
  platforms = ["Windows"]
  flow = file_finder.FileFinder.__name__
  test_output_path = "/fs/tsk/.*/Windows/System32/notepad.exe"

  download = rdf_file_finder.FileFinderDownloadActionOptions()
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {
      "paths": ["%%environ_systemroot%%\\System32\\notepad.*"],
      "action": action,
      "pathtype": "TSK"
  }


class TestFileFinderOSLinux(base.VFSPathContentIsELF):
  """Download a file with FileFinder."""
  platforms = ["Linux"]
  flow = file_finder.FileFinder.__name__
  test_output_path = "/fs/os/bin/ps"

  sizecondition = rdf_file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = rdf_file_finder.FileFinderCondition(
      condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = rdf_file_finder.FileFinderDownloadActionOptions()
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {"paths": ["/bin/ps"], "conditions": filecondition, "action": action}


class TestFileFinderOSLinuxProc(base.VFSPathContentExists):
  """Download a /proc/sys entry with FileFinder."""
  platforms = ["Linux"]
  flow = file_finder.FileFinder.__name__
  test_output_path = "/fs/os/proc/sys/net/ipv4/ip_forward"
  client_min_version = 3007

  sizecondition = rdf_file_finder.FileFinderSizeCondition(max_file_size=1000000)
  filecondition = rdf_file_finder.FileFinderCondition(
      condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
      size=sizecondition)

  download = rdf_file_finder.FileFinderDownloadActionOptions()
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)

  args = {
      "paths": ["/proc/sys/net/ipv4/ip_forward"],
      "conditions": filecondition,
      "action": action
  }


class TestFileFinderOSDarwin(base.VFSPathContentIsMachO):
  platforms = ["Darwin"]
  flow = file_finder.FileFinder.__name__
  download = rdf_file_finder.FileFinderDownloadActionOptions()
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      download=download)
  args = {"paths": ["/bin/ps"], "action": action}
  test_output_path = "/fs/os/bin/ps"


class TestFileFinderOSHomedir(base.AutomatedTest):
  """List files in homedir with FileFinder.

  Exercise globbing and interpolation.
  """
  platforms = ["Linux", "Darwin", "Windows"]
  flow = file_finder.FileFinder.__name__
  action = rdf_file_finder.FileFinderAction(
      action_type=rdf_file_finder.FileFinderAction.Action.STAT)
  args = {
      "paths": ["%%users.homedir%%/*"],
      "action": action,
      "runner_args": rdf_flows.FlowRunnerArgs()
  }

  def CheckFlow(self):
    self.CheckResultCollectionNotEmptyWithRetry(self.session_id)


class UnicodeTestFlow(flow.GRRFlow):
  """A flow that tests unicode file name handling."""

  @flow.StateHandler()
  def Start(self):
    urandom = rdf_paths.PathSpec(
        path="/dev/urandom", pathtype=rdf_paths.PathSpec.PathType.OS)

    test_path = u"/tmp/uñîcödé"

    self.CallClient(
        standard.CopyPathToFile,
        offset=0,
        length=1024,
        src_path=urandom,
        dest_dir=test_path,
        gzip_output=False,
        lifetime=600,
        next_state="StartDownload")

  @flow.StateHandler()
  def StartDownload(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD)

    paths = [response.dest_path.path for response in responses]
    args = {"paths": paths, "action": action}
    self.CallFlow(file_finder.FileFinder.__name__, next_state="Done", **args)

  @flow.StateHandler()
  def Done(self, responses):
    for response in responses:
      self.SendReply(response)


class TestUnicode(base.LocalClientTest):
  """Tests we handle unicode filenames properly."""

  platforms = ["Linux"]
  flow = UnicodeTestFlow.__name__

  def CheckFlow(self):
    self.CheckResultCollectionNotEmptyWithRetry(self.session_id)
