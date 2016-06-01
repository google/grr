#!/usr/bin/env python
"""These are flows designed to discover information about the host."""


from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib.aff4_objects import network
from grr.lib.aff4_objects import standard
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class EnrolmentInterrogateEvent(flow.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]
  well_known_session_id = rdfvalue.SessionID(queue=queues.ENROLLMENT,
                                             flow_name="Interrogate")

  def CheckSource(self, source):
    if not isinstance(source, rdfvalue.SessionID):
      try:
        source = rdfvalue.SessionID(source)
      except rdfvalue.InitializeError:
        return False
    return source.Queue() == queues.ENROLLMENT

  @flow.EventHandler(source_restriction=True)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    flow.GRRFlow.StartFlow(client_id=event,
                           flow_name="Interrogate",
                           queue=queues.ENROLLMENT,
                           token=self.token)


class InterrogateArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.InterrogateArgs


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Administrative/"
  client = None
  args_type = InterrogateArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["Platform", "InstallDate",
                                 "EnumerateInterfaces", "EnumerateFilesystems",
                                 "ClientInfo", "ClientConfiguration"])
  def Start(self):
    """Start off all the tests."""

    # Create the objects we need to exist.
    self.Load()
    fd = aff4.FACTORY.Create(
        self.client.urn.Add("network"),
        network.Network,
        token=self.token)
    fd.Close()

    # Make sure we always have a VFSDirectory with a pathspec at fs/os
    pathspec = rdf_paths.PathSpec(path="/",
                                  pathtype=rdf_paths.PathSpec.PathType.OS)
    urn = self.client.PathspecToURN(pathspec, self.client.urn)
    with aff4.FACTORY.Create(urn,
                             standard.VFSDirectory,
                             mode="w",
                             token=self.token) as fd:
      fd.Set(fd.Schema.PATHSPEC, pathspec)

    self.CallClient("GetPlatformInfo", next_state="Platform")
    self.CallClient("GetMemorySize", next_state="StoreMemorySize")
    self.CallClient("GetInstallDate", next_state="InstallDate")
    self.CallClient("GetClientInfo", next_state="ClientInfo")
    self.CallClient("GetConfiguration", next_state="ClientConfiguration")
    self.CallClient("GetLibraryVersions", next_state="ClientLibraries")
    self.CallClient("EnumerateInterfaces", next_state="EnumerateInterfaces")
    self.CallClient("EnumerateFilesystems", next_state="EnumerateFilesystems")

  def Load(self):
    # Ensure there is a client object
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)

  def Save(self):
    # Make sure the client object is removed and closed
    if self.client:
      self.client.Close()
      self.client = None

  @flow.StateHandler()
  def StoreMemorySize(self, responses):
    if not responses.success:
      return
    self.client.Set(self.client.Schema.MEMORY_SIZE(responses.First()))

  @flow.StateHandler(next_state=["ProcessKnowledgeBase"])
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      # These need to be in separate attributes because they get searched on in
      # the GUI
      self.client.Set(self.client.Schema.HOSTNAME(response.node))
      self.client.Set(self.client.Schema.SYSTEM(response.system))
      self.client.Set(self.client.Schema.OS_RELEASE(response.release))
      self.client.Set(self.client.Schema.OS_VERSION(response.version))
      self.client.Set(self.client.Schema.KERNEL(response.kernel))
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
        with aff4.FACTORY.Create(
            self.client.urn.Add("registry"),
            standard.VFSDirectory,
            token=self.token) as fd:
          fd.Set(fd.Schema.PATHSPEC,
                 fd.Schema.PATHSPEC(
                     path="/",
                     pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

      # Update the client index
      aff4.FACTORY.Create(client_index.MAIN_INDEX,
                          aff4_type=client_index.ClientIndex,
                          mode="rw",
                          object_exists=True,
                          token=self.token).AddClient(self.client)

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
      install_date = self.client.Schema.INSTALL_DATE(response.integer * 1000000)
      self.client.Set(install_date)
    else:
      self.Log("Could not get InstallDate")

  def _GetExtraArtifactsForCollection(self):
    original_set = set(config_lib.CONFIG["Artifacts.interrogate_store_in_aff4"])
    add_set = set(config_lib.CONFIG[
        "Artifacts.interrogate_store_in_aff4_additions"])
    skip_set = set(config_lib.CONFIG[
        "Artifacts.interrogate_store_in_aff4_skip"])
    return original_set.union(add_set) - skip_set

  @flow.StateHandler(next_state=["ProcessArtifactResponses"])
  def ProcessKnowledgeBase(self, responses):
    """Collect and store any extra non-kb artifacts."""
    if not responses.success:
      raise flow.FlowError("Error collecting artifacts: %s" % responses.status)

    # Collect any non-knowledgebase artifacts that will be stored in aff4.
    artifact_list = self._GetExtraArtifactsForCollection()
    if artifact_list:
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=artifact_list,
                    next_state="ProcessArtifactResponses",
                    store_results_in_aff4=True)

    # Update the client index
    aff4.FACTORY.Create(client_index.MAIN_INDEX,
                        aff4_type=client_index.ClientIndex,
                        mode="rw",
                        object_exists=True,
                        token=self.token).AddClient(self.client)

  @flow.StateHandler()
  def ProcessArtifactResponses(self, responses):
    if not responses.success:
      self.Log("Error collecting artifacts: %s", responses.status)

  FILTERED_IPS = ["127.0.0.1", "::1", "fe80::1"]

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if responses.success and responses:
      net_fd = aff4.FACTORY.Create(
          self.client.urn.Add("network"),
          network.Network,
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

      self.client.Set(self.client.Schema.MAC_ADDRESS("\n".join(mac_addresses)))
      self.client.Set(self.client.Schema.HOST_IPS("\n".join(ip_addresses)))

      net_fd.Set(net_fd.Schema.INTERFACES(interface_list))
      net_fd.Close()
      self.client.Set(self.client.Schema.LAST_INTERFACES(interface_list))

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

          pathspec = rdf_paths.PathSpec(path=device,
                                        pathtype=rdf_paths.PathSpec.PathType.OS,
                                        offset=offset)

          pathspec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()
          continue

        if response.device:
          pathspec = rdf_paths.PathSpec(path=response.device,
                                        pathtype=rdf_paths.PathSpec.PathType.OS)

          pathspec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

        if response.mount_point:
          # Create the OS device
          pathspec = rdf_paths.PathSpec(path=response.mount_point,
                                        pathtype=rdf_paths.PathSpec.PathType.OS)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
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
      self.client.Set(self.client.Schema.CLIENT_INFO(response))
      self.client.AddLabels(*response.labels, owner="GRR")
    else:
      self.Log("Could not get ClientInfo.")

  @flow.StateHandler()
  def ClientConfiguration(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIGURATION(response))

  @flow.StateHandler()
  def ClientLibraries(self, responses):
    """Process client library information."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.LIBRARY_VERSIONS(response))

  @flow.StateHandler()
  def End(self):
    """Finalize client registration."""
    self.Notify("Discovery", self.client.urn, "Client Discovery Complete")

    # Update summary and publish to the Discovery queue.
    summary = self.client.GetSummary()
    self.Publish("Discovery", summary)
    self.SendReply(summary)

    # Update the client index
    aff4.FACTORY.Create(client_index.MAIN_INDEX,
                        aff4_type=client_index.ClientIndex,
                        mode="rw",
                        object_exists=True,
                        token=self.token).AddClient(self.client)
