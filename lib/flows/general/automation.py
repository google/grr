#!/usr/bin/env python
"""Automation flows to do the the normal case initialization work in one go.

This file is disabled since it has no tests and is broken.
"""



from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import flows_pb2


class WinUserActivityInvestigationArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.WinUserActivityInvestigationArgs


# This file is disabled since it has no tests and is broken.
class WinUserActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a user investigation."""

  category = "/Automation/"
  args_type = WinUserActivityInvestigation

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Validate parameters and do the actual work."""
    if not self.username:
      raise RuntimeError("Please supply a valid user name.")

    if self.use_tsk:
      self.path_type = rdfvalue.PathSpec.PathType.TSK
    else:
      self.path_type = rdfvalue.PathSpec.PathType.OS

    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.user_pb = flow_utils.GetUserInfo(client, self.username)
    if not self.user_pb:
      self.Error("Could not find homedir for user %s" % self.username)
      raise RuntimeError("No homedir found for user %s" % self.username)

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
      self.CallFlow("RecursiveListDirectory",
                    pathtype=rdfvalue.PathSpec.PathType.REGISTRY,
                    path=regdir, max_depth=max_depth, next_state="FinishFlow")

    if self.artifact_list:
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=list(self.artifact_list),
                    use_tsk=self.use_tsk,
                    next_state="FinishFlow")

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


# This file is disabled since it has no tests and is broken.
class WinSystemActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a system investigation.

  This encapsulates the different platform specific modules.
  """
  category = "/Automation/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Bool(
          name="list_processes",
          description="Call the ListProcesses flow.",
          default=True,
          ),
      type_info.Bool(
          name="list_network_connections",
          description="Call the Netstat flow.",
          default=True,
          ),
      type_info.MultiSelectList(
          name="artifact_list",
          description="A list of Artifact names.",
          default=["ApplicationEventLog", "SystemEventLog", "SecurityEventLog",
                   "TerminalServicesEventLogEvtx", "ApplicationEventLogEvtx",
                   "SystemEventLogEvtx", "SecurityEventLogEvtx"],
          ),
      type_info.Bool(
          name="collect_av_data",
          description="Call the Antivirus flows to collect quarantine/logs.",
          default=True,
          ),
      type_info.Bool(
          name="collect_prefetch",
          description="List the prefetch directory.",
          default=True,
          ),
      type_info.Bool(
          name="list_common_dirs",
          description="List common system directories.",
          default=True,
          ),
      type_info.Bool(
          name="use_tsk",
          description="Use raw filesystem access where possible.",
          default=True
          ),
      type_info.Bool(
          name="timeline_collected_data",
          description="Once complete create a timeline for the host.",
          default=True
          ),
      )

  common_dirs = ["c:\\",
                 "c:\\users",
                 "c:\\windows",
                 "c:\\windows\\system32\\drivers",
                 "c:\\windows\\logs",
                 "c:\\program files"]

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Start."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = str(self.client.Get(self.client.Schema.SYSTEM))
    self.os_version = str(self.client.Get(self.client.Schema.OS_VERSION))
    self.os_major_version = self.os_version.split(".")[0]

    if self.use_tsk:
      self.path_type = rdfvalue.PathSpec.PathType.TSK
    else:
      self.path_type = rdfvalue.PathSpec.PathType.OS

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
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=list(self.artifact_list),
                    use_tsk=self.use_tsk,
                    next_state="FinishFlow")

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


# This file is disabled since it has no tests and is broken.
class LinSystemActivityInvestigation(flow.GRRFlow):
  """Do the initial work for a Linux system investigation.

  This encapsulates the different platform specific modules.
  """
  category = "/Automation/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Bool(
          name="list_processes",
          description="Call the ListProcesses flow.",
          default=True,
          ),
      type_info.Bool(
          name="list_network_connections",
          description="Call the Netstat flow.",
          default=True,
          ),
      type_info.MultiSelectList(
          name="artifact_list",
          description="A list of Artifact names.",
          default=["AuthLog", "LinuxWtmp"],
          ),
      type_info.Bool(
          name="use_tsk",
          description="Use raw filesystem access where possible.",
          default=True
          ),
      type_info.Bool(
          name="timeline_collected_data",
          description="Once complete create a timeline for the host.",
          default=True
          ),
      )

  @flow.StateHandler(next_state="FinishFlow")
  def Start(self):
    """Start."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = str(self.client.Get(self.client.Schema.SYSTEM))
    self.os_version = str(self.client.Get(self.client.Schema.OS_VERSION))
    self.os_major_version = self.os_version.split(".")[0]

    if self.use_tsk:
      self.path_type = rdfvalue.PathSpec.PathType.TSK
    else:
      self.path_type = rdfvalue.PathSpec.PathType.OS

    if self.list_processes:
      self.CallFlow("ListProcesses", next_state="FinishFlow")
    if self.list_network_connections:
      self.CallFlow("Netstat", next_state="FinishFlow")

    if self.artifact_list:
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=self.artifact_list,
                    use_tsk=self.use_tsk,
                    next_state="FinishFlow")

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
