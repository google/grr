#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Automation flows to do the the normal case initialization work in one go."""




from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import type_info
from grr.proto import jobs_pb2


class WinUserActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a user investigation."""

  category = "/Automation/"
  flow_typeinfo = {"username": type_info.String(),
                   "artifact_list": type_info.ArtifactList()}

  artifact_list = ()

  def __init__(self, username="", get_browser_history=True,
               recursive_list_homedir=5, recursive_list_user_registry=5,
               artifact_list=None,
               timeline_collected_data=True,
               use_tsk=True, **kwargs):
    """Constructor.

    Args:
      username: The user to target the actions to.
      get_browser_history: Call each of the browser history flows.
      recursive_list_homedir: Recursively list the users homedir to this depth.
      recursive_list_user_registry: Recursively list the users registry hive.
      artifact_list: A list of Artifact names. If None use self.artifact_list.
      timeline_collected_data: Once complete create a timeline for the host.
      use_tsk: Use raw filesystem access where possible.

    Raises:
      RuntimeError: On bad parameters.

    """
    super(WinUserActivityInvestigation, self).__init__(**kwargs)

    if not username:
      raise RuntimeError("Please supply a valid user name.")
    self.username = username
    self.timeline_collected_data = timeline_collected_data
    self.recursive_list_homedir = recursive_list_homedir
    self.recursive_list_user_registry = recursive_list_user_registry
    if artifact_list is not None:
      self.artifact_list = artifact_list
    self.get_browser_history = get_browser_history
    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.user_pb = flow_utils.GetUserInfo(client, username)
    if not self.user_pb:
      self.Error("Could not find homedir for user %s" % username)
      raise RuntimeError("No homedir found for user %s" % username)

    self.use_tsk = use_tsk
    if use_tsk:
      self.path_type = jobs_pb2.Path.TSK
    else:
      self.path_type = jobs_pb2.Path.OS

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Do the actual work."""
    if self.get_browser_history:
      self.CallFlow("FirefoxHistory", pathtype=self.path_type,
                    username=self.user, next_state="FinishFlow")
      self.CallFlow("ChromeHistory", pathtype=self.path_type,
                    username=self.user, next_state="FinishFlow")

    if self.recursive_list_homedir:
      homedir = self.user_pb.homedir
      self.CallFlow("RecursiveListDirectory", pathtype=self.path_type,
                    path=homedir, max_depth=int(self.recursive_list_homedir),
                    next_state="FinishFlow")

    if self.recursive_list_user_registry:
      regdir = "HKEY_USERS/%s" % self.user_pb.sid
      max_depth = int(self.recursive_list_user_registry)
      self.CallFlow("RecursiveListDirectory", pathtype=jobs_pb2.Path.REGISTRY,
                    path=regdir, max_depth=max_depth, next_state="FinishFlow")

    if self.artifact_list:
      self.CallFlow("ArtifactCollectorFlow", artifact_list=self.artifact_list,
                    use_tsk=self.use_tsk, next_state="FinishFlow")

  @flow.StateHandler()
  def FinishFlow(self, responses):
    """Complete anything we need to do for each flow finishing."""

    flow_name = self.__class__.__name__
    if responses.success:
      self.Log("Flow %s completed successfully", flow_name)
    else:
      self.Log("Flow %s failed to complete", flow_name)

    # If no more flows, we're done and we can run the timeline.
    if self.OutstandingRequests() == 1:  # We're processing last request now.
      if self.timeline_collected_data:
        self.CallFlow("MACTimes", path="/", next_state="End")


class WinSystemActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a system investigation.

  This encapsulates the different platform specific modules.
  """
  category = "/Automation/"
  flow_typeinfo = {"artifact_list": type_info.ArtifactList()}

  artifact_list = ("ApplicationEventLog", "SystemEventLog", "SecurityEventLog",
                   "TerminalServicesEventLogEvtx", "ApplicationEventLogEvtx",
                   "SystemEventLogEvtx", "SecurityEventLogEvtx")

  common_dirs = ["c:\\",
                 "c:\\users",
                 "c:\\windows",
                 "c:\\windows\\system32\\drivers",
                 "c:\\windows\\logs",
                 "c:\\program files"]

  def __init__(self, list_processes=True, list_network_connections=True,
               artifact_list=artifact_list, collect_av_data=True,
               collect_prefetch=True, list_common_dirs=True, use_tsk=True,
               timeline_collected_data=True,
               **kwargs):
    """Constructor.

    Args:
      list_processes: Call the ListProcesses flow.
      list_network_connections: Call the Netstat flow.
      artifact_list: List of artifacts to collect. If None use
          self.artifact_list.
      collect_av_data: Call the Antivirus flows to collect quarantine/logs.
      collect_prefetch: List the prefetch directory.
      list_common_dirs: List common system directories.
      use_tsk: Use raw filesystem access where possible.
      timeline_collected_data: Once complete create a timeline for the host.
    """
    super(WinSystemActivityInvestigation, self).__init__(**kwargs)

    self.client = aff4.FACTORY.Open(self.client_id)
    self.system = str(self.client.Get(self.client.Schema.SYSTEM))
    self.os_version = str(self.client.Get(self.client.Schema.OS_VERSION))
    self.os_major_version = self.os_version.split(".")[0]

    self.list_processes = list_processes
    self.list_network_connections = list_network_connections
    self.collect_av_data = collect_av_data
    self.timeline_collected_data = timeline_collected_data
    self.artifact_list = artifact_list
    self.collect_prefetch = collect_prefetch
    self.list_common_dirs = list_common_dirs

    self.use_tsk = use_tsk
    if use_tsk:
      self.path_type = jobs_pb2.Path.TSK
    else:
      self.path_type = jobs_pb2.Path.OS

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Start."""
    if self.collect_av_data:
      self.CallFlow("SophosCollector", pathtype=self.path_type,
                    next_state="FinishFlow")
    if self.list_processes:
      self.CallFlow("ListProcesses", next_state="FinishFlow")
    if self.list_network_connections:
      self.CallFlow("Netstat", next_state="FinishFlow")

    # Execution events.
    if self.collect_prefetch:
      self.CallFlow("ListDirectory", path=r"C:\Windows\Prefetch",
                    pathtype=self.path_type, next_state="FinishFlow")

    if self.list_common_dirs:
      for common_dir in self.common_dirs:
        self.CallFlow("ListDirectory", path=common_dir,
                      pathtype=self.path_type, next_state="FinishFlow")

    if self.artifact_list:
      self.CallFlow("ArtifactCollectorFlow", artifact_list=self.artifact_list,
                    use_tsk=self.use_tsk, next_state="FinishFlow")

  @flow.StateHandler()
  def FinishFlow(self, responses):
    """Complete anything we need to do for each flow finishing."""
    flow_name = self.__class__.__name__
    if responses.success:
      self.Log("Flow %s completed successfully", flow_name)
    else:
      self.Log("Flow %s failed to complete", flow_name)

    # If no more flows, we're done and we can run the timeline.
    if self.OutstandingRequests() == 1:  # We're processing last request now.
      if self.timeline_collected_data:
        self.CallFlow("MACTimes", path="/", next_state="End")


class LinSystemActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a Linux system investigation.

  This encapsulates the different platform specific modules.
  """
  category = "/Automation/"
  flow_typeinfo = {"artifact_list": type_info.ArtifactList()}

  artifact_list = ("AuthLog", "Wtmp")

  def __init__(self, list_processes=True, list_network_connections=True,
               artifact_list=artifact_list, use_tsk=False,
               timeline_collected_data=True,
               **kwargs):
    """Constructor.

    Args:
      list_processes: Call the ListProcesses flow.
      list_network_connections: Call the Netstat flow.
      artifact_list: List of artifacts to collect. If None use
          self.artifact_list.
      use_tsk: Use raw filesystem access where possible.
      timeline_collected_data: Once complete create a timeline for the host.
    """
    super(LinSystemActivityInvestigation, self).__init__(**kwargs)

    self.client = aff4.FACTORY.Open(self.client_id)
    self.system = str(self.client.Get(self.client.Schema.SYSTEM))
    self.os_version = str(self.client.Get(self.client.Schema.OS_VERSION))
    self.os_major_version = self.os_version.split(".")[0]

    self.list_processes = list_processes
    self.list_network_connections = list_network_connections
    self.timeline_collected_data = timeline_collected_data
    self.artifact_list = artifact_list

    self.use_tsk = use_tsk
    if use_tsk:
      self.path_type = jobs_pb2.Path.TSK
    else:
      self.path_type = jobs_pb2.Path.OS

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Start."""
    if self.list_processes:
      self.CallFlow("ListProcesses", next_state="FinishFlow")
    if self.list_network_connections:
      self.CallFlow("Netstat", next_state="FinishFlow")

    if self.artifact_list:
      self.CallFlow("ArtifactCollectorFlow", artifact_list=self.artifact_list,
                    use_tsk=self.use_tsk, next_state="FinishFlow")

  @flow.StateHandler()
  def FinishFlow(self, responses):
    """Complete anything we need to do for each flow finishing."""
    flow_name = self.__class__.__name__
    if responses.success:
      self.Log("Flow %s completed successfully", flow_name)
    else:
      self.Log("Flow %s failed to complete", flow_name)

    # If no more flows, we're done and we can run the timeline.
    if self.OutstandingRequests() == 1:  # We're processing last request now.
      if self.timeline_collected_data:
        self.CallFlow("MACTimes", path="/", next_state="End")


### Placeholder classes below to attempt to define how we break down our
### automation tasks and maintain a list of things to be implemented.


class WindowsExecutionActivity(flow.GRRFlow):
  """Extract and timeline artifacts that indicate binary execution on Windows.

  TODO:
    Add Windows prefetch.
    Add Windows process logs from event log.
    Add Windows Run command MRU.
    Add process information from running processes.
  """


class OsxExecutionActivity(flow.GRRFlow):
  """Extract and timeline artifacts that indicate binary execution on OSX.

  TODO:
    Add QuarantineEvents.
    Add logged .app executions.

  """


class WindowsAntiForensicActivity(flow.GRRFlow):
  """Automatically use heuristics to detect anti forensic activity.

  Adding this class to act as a todo list of things we should add.

  TODO:
    Add Eraser artifacts.
    Add Chrome Incognito mode execution detection.
    Add Firefox anonymous browsing execution detection.
    Add Evidence eliminator detection.
    Add timestomp detection through MFT parsing.
    Add unmounted partition detection.
    Add sampled slackfile statistical analysis (avg entropy in slack space).
  """
