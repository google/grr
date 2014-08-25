#!/usr/bin/env python
"""These are flows designed to discover information about the host."""


from grr.lib import aff4
from grr.lib import artifact
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import worker
from grr.proto import flows_pb2


class EnrolmentInterrogateEvent(flow.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]
  well_known_session_id = rdfvalue.SessionID("aff4:/flows/CA:Interrogate")

  # We only accept messages that came from the CA flows.
  sourcecheck = lambda source: source.Basename().startswith("CA:")

  @flow.EventHandler(source_restriction=sourcecheck)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    flow.GRRFlow.StartFlow(client_id=event, flow_name="Interrogate",
                           queue=worker.DEFAULT_ENROLLER_QUEUE,
                           token=self.token)


class InterrogateArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.InterrogateArgs


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Administrative/"
  client = None
  args_type = InterrogateArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["Hostname",
                                 "Platform",
                                 "InstallDate",
                                 "EnumerateInterfaces",
                                 "EnumerateFilesystems",
                                 "ClientInfo",
                                 "ClientConfig",
                                 "ClientConfiguration"])
  def Start(self):
    """Start off all the tests."""
    self.state.Register("summary", rdfvalue.ClientSummary(
        client_id=self.client_id))

    # Create the objects we need to exist.
    self.Load()
    fd = aff4.FACTORY.Create(self.client.urn.Add("network"), "Network",
                             token=self.token)
    fd.Close()

    self.CallClient("GetPlatformInfo", next_state="Platform")
    self.CallClient("GetInstallDate", next_state="InstallDate")
    self.CallClient("GetClientInfo", next_state="ClientInfo")
    self.CallClient("GetConfiguration", next_state="ClientConfiguration")
    self.CallClient("EnumerateInterfaces", next_state="EnumerateInterfaces")
    self.CallClient("EnumerateFilesystems", next_state="EnumerateFilesystems")

  def Load(self):
    # Ensure there is a client object
    self.client = aff4.FACTORY.Open(self.client_id,
                                    mode="rw", token=self.token)

  def Save(self):
    # Make sure the client object is removed and closed
    if self.client:
      self.client.Close()
      self.client = None

  @flow.StateHandler(next_state=["ProcessKnowledgeBase"])
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      self.state.summary.system_info = response

      # These need to be in separate attributes because they get searched on in
      # the GUI
      self.client.Set(self.client.Schema.HOSTNAME(response.node))
      self.client.Set(self.client.Schema.SYSTEM(response.system))
      self.client.Set(self.client.Schema.OS_RELEASE(response.release))
      self.client.Set(self.client.Schema.OS_VERSION(response.version))
      self.client.Set(self.client.Schema.FQDN(response.fqdn))

      # response.machine is the machine value of platform.uname()
      # On Windows this is the value of:
      # HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session
      # Manager\Environment\PROCESSOR_ARCHITECTURE
      # "AMD64", "IA64" or "x86"
      self.client.Set(self.client.Schema.ARCH(response.machine))
      self.client.Set(self.client.Schema.UNAME("%s-%s-%s" % (
          response.system, response.release, response.version)))
      self.client.Flush(sync=True)

      if response.system == "Windows":
        with aff4.FACTORY.Create(self.client.urn.Add("registry"),
                                 "VFSDirectory", token=self.token) as fd:
          fd.Set(fd.Schema.PATHSPEC, fd.Schema.PATHSPEC(
              path="/", pathtype=rdfvalue.PathSpec.PathType.REGISTRY))

    else:
      self.Log("Could not retrieve Platform info.")

    if self.client.Get(self.client.Schema.SYSTEM):
      # We will accept a partial KBInit rather than raise, so pass
      # require_complete=False.
      self.CallFlow("KnowledgeBaseInitializationFlow",
                    require_complete=False,
                    lightweight=self.args.lightweight,
                    next_state="ProcessKnowledgeBase")
    else:
      self.Log("Unknown system type, skipping KnowledgeBaseInitializationFlow")

  @flow.StateHandler()
  def InstallDate(self, responses):
    if responses.success:
      response = responses.First()
      install_date = self.client.Schema.INSTALL_DATE(
          response.integer * 1000000)
      self.client.Set(install_date)
      self.state.summary.install_date = install_date
    else:
      self.Log("Could not get InstallDate")

  def _GetExtraArtifactsForCollection(self):
    original_set = set(config_lib.CONFIG["Artifacts.interrogate_store_in_aff4"])
    add_set = set(
        config_lib.CONFIG["Artifacts.interrogate_store_in_aff4_additions"])
    skip_set = set(
        config_lib.CONFIG["Artifacts.interrogate_store_in_aff4_skip"])
    return original_set.union(add_set) - skip_set

  @flow.StateHandler(next_state=["ProcessArtifactResponses"])
  def ProcessKnowledgeBase(self, responses):
    """Update the SUMMARY from the knowledgebase data."""
    if not responses.success:
      raise flow.FlowError("Error collecting artifacts: %s" % responses.status)

    knowledge_base = artifact.GetArtifactKnowledgeBase(self.client)
    for kbuser in knowledge_base.users:
      self.state.summary.users.Append(
          rdfvalue.User().FromKnowledgeBaseUser(kbuser))

    # Collect any non-knowledgebase artifacts that will be stored in aff4.
    artifact_list = self._GetExtraArtifactsForCollection()
    if artifact_list:
      self.CallFlow("ArtifactCollectorFlow", artifact_list=artifact_list,
                    next_state="ProcessArtifactResponses",
                    store_results_in_aff4=True)

  @flow.StateHandler()
  def ProcessArtifactResponses(self, responses):
    if not responses.success:
      self.Log("Error collecting artifacts: %s", responses.status)

  FILTERED_IPS = ["127.0.0.1", "::1", "fe80::1"]

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if responses.success and responses:
      net_fd = aff4.FACTORY.Create(self.client.urn.Add("network"), "Network",
                                   token=self.token)
      interface_list = net_fd.Schema.INTERFACES()
      mac_addresses = []
      ip_addresses = []
      for response in responses:
        interface_list.Append(response)

        # Add a hex encoded string for searching
        if (response.mac_address and
            response.mac_address != "\x00" * len(response.mac_address)):
          mac_addresses.append(response.mac_address.human_readable_address)

        for address in response.addresses:
          if address.human_readable_address not in self.FILTERED_IPS:
            ip_addresses.append(address.human_readable_address)

      self.client.Set(self.client.Schema.MAC_ADDRESS(
          "\n".join(mac_addresses)))
      self.client.Set(self.client.Schema.HOST_IPS(
          "\n".join(ip_addresses)))

      net_fd.Set(net_fd.Schema.INTERFACES, interface_list)
      net_fd.Close()

      self.state.summary.interfaces = interface_list
    else:
      self.Log("Could not enumerate interfaces.")

  @flow.StateHandler()
  def EnumerateFilesystems(self, responses):
    """Store all the local filesystems in the client."""
    if responses.success and len(responses):
      filesystems = self.client.Schema.FILESYSTEM()
      for response in responses:
        filesystems.Append(response)

        if response.type == "partition":
          (device, offset) = response.device.rsplit(":", 1)

          offset = int(offset)

          pathspec = rdfvalue.PathSpec(
              path=device, pathtype=rdfvalue.PathSpec.PathType.OS,
              offset=offset)

          pathspec.Append(path="/",
                          pathtype=rdfvalue.PathSpec.PathType.TSK)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()
          continue

        if response.device:
          # Create the raw device
          urn = "devices/%s" % response.device

          pathspec = rdfvalue.PathSpec(
              path=response.device,
              pathtype=rdfvalue.PathSpec.PathType.OS)

          pathspec.Append(path="/",
                          pathtype=rdfvalue.PathSpec.PathType.TSK)

          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

          # Create the TSK device
          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

        if response.mount_point:
          # Create the OS device
          pathspec = rdfvalue.PathSpec(
              path=response.mount_point,
              pathtype=rdfvalue.PathSpec.PathType.OS)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

      self.client.Set(self.client.Schema.FILESYSTEM, filesystems)
    else:
      self.Log("Could not enumerate file systems.")

  @flow.StateHandler()
  def ClientInfo(self, responses):
    """Obtain some information about the GRR client running."""
    if responses.success:
      response = responses.First()
      self.state.summary.client_info = response
      self.client.Set(self.client.Schema.CLIENT_INFO(response))
      self.client.AddLabels(*response.labels, owner="GRR")
      self.state.summary.client_info = response
    else:
      self.Log("Could not get ClientInfo.")

  @flow.StateHandler()
  def ClientConfig(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIG(response))

  @flow.StateHandler()
  def ClientConfiguration(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIGURATION(response))

  @flow.StateHandler()
  def End(self):
    """Finalize client registration."""
    self.Notify("Discovery", self.client.urn, "Client Discovery Complete")

    # Publish this client to the Discovery queue.
    self.state.summary.timestamp = rdfvalue.RDFDatetime().Now()
    self.Publish("Discovery", self.state.summary)
    self.SendReply(self.state.summary)
    self.client.Set(self.client.Schema.SUMMARY, self.state.summary)

    # Flush the data to the data store.
    self.client.Close()
