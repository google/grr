#!/usr/bin/env python
"""These are flows designed to discover information about the host."""


from grr import config
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.server import aff4
from grr.server import artifact
from grr.server import client_index
from grr.server import flow
from grr.server import server_stubs
from grr.server.aff4_objects import aff4_grr
from grr.server.aff4_objects import standard
from grr.server.flows.general import collectors


class InterrogateArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.InterrogateArgs


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Administrative/"
  client = None
  args_type = InterrogateArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def _OpenClient(self, mode="r"):
    return aff4.FACTORY.Open(
        self.client_id,
        aff4_type=aff4_grr.VFSGRRClient,
        mode=mode,
        token=self.token)

  def _CreateClient(self, mode="w"):
    return aff4.FACTORY.Create(
        self.client_id,
        aff4_type=aff4_grr.VFSGRRClient,
        mode=mode,
        token=self.token)

  @flow.StateHandler()
  def Start(self):
    """Start off all the tests."""

    # Create the objects we need to exist.
    self.Load()

    # Make sure we always have a VFSDirectory with a pathspec at fs/os
    pathspec = rdf_paths.PathSpec(
        path="/", pathtype=rdf_paths.PathSpec.PathType.OS)
    urn = pathspec.AFF4Path(self.client_id)
    with aff4.FACTORY.Create(
        urn, standard.VFSDirectory, mode="w", token=self.token) as fd:
      fd.Set(fd.Schema.PATHSPEC, pathspec)

    self.CallClient(server_stubs.GetPlatformInfo, next_state="Platform")
    self.CallClient(server_stubs.GetMemorySize, next_state="StoreMemorySize")
    self.CallClient(server_stubs.GetInstallDate, next_state="InstallDate")
    self.CallClient(server_stubs.GetClientInfo, next_state="ClientInfo")
    self.CallClient(
        server_stubs.GetConfiguration, next_state="ClientConfiguration")
    self.CallClient(
        server_stubs.GetLibraryVersions, next_state="ClientLibraries")
    self.CallClient(
        server_stubs.EnumerateInterfaces, next_state="EnumerateInterfaces")
    self.CallClient(
        server_stubs.EnumerateFilesystems, next_state="EnumerateFilesystems")

  @flow.StateHandler()
  def CloudMetadata(self, responses):
    """Process cloud metadata and store in the client."""
    if not responses.success:
      # We want to log this but it's not serious enough to kill the whole flow.
      self.Log("Failed to collect cloud metadata: %s" % responses.status)
      return
    metadata_responses = responses.First()

    # Expected for non-cloud machines.
    if not metadata_responses:
      return

    with self._CreateClient() as client:
      client.Set(
          client.Schema.CLOUD_INSTANCE(
              cloud.ConvertCloudMetadataResponsesToCloudInstance(
                  metadata_responses)))

  @flow.StateHandler()
  def StoreMemorySize(self, responses):
    if not responses.success:
      return

    with self._CreateClient() as client:
      client.Set(client.Schema.MEMORY_SIZE(responses.First()))

  @flow.StateHandler()
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      # These need to be in separate attributes because they get searched on in
      # the GUI
      with self._OpenClient(mode="rw") as client:
        client.Set(client.Schema.HOSTNAME(response.node))
        client.Set(client.Schema.SYSTEM(response.system))
        client.Set(client.Schema.OS_RELEASE(response.release))
        client.Set(client.Schema.OS_VERSION(response.version))
        client.Set(client.Schema.KERNEL(response.kernel))
        client.Set(client.Schema.FQDN(response.fqdn))

        # response.machine is the machine value of platform.uname()
        # On Windows this is the value of:
        # HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session
        # Manager\Environment\PROCESSOR_ARCHITECTURE
        # "AMD64", "IA64" or "x86"
        client.Set(client.Schema.ARCH(response.machine))
        client.Set(
            client.Schema.UNAME("%s-%s-%s" % (response.system, response.release,
                                              response.version)))

        # Update the client index
        client_index.CreateClientIndex(token=self.token).AddClient(client)

      if response.system == "Windows":
        with aff4.FACTORY.Create(
            self.client_id.Add("registry"),
            standard.VFSDirectory,
            token=self.token) as fd:
          fd.Set(fd.Schema.PATHSPEC,
                 fd.Schema.PATHSPEC(
                     path="/", pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

      # No support for OS X cloud machines as yet.
      if response.system in ["Linux", "Windows"]:
        self.CallClient(
            server_stubs.GetCloudVMMetadata,
            cloud.BuildCloudMetadataRequests(),
            next_state="CloudMetadata")

      known_system_type = True
    else:
      client = self._OpenClient()
      known_system_type = client.Get(client.Schema.SYSTEM)
      self.Log("Could not retrieve Platform info.")

    if known_system_type:
      # We will accept a partial KBInit rather than raise, so pass
      # require_complete=False.
      self.CallFlow(
          artifact.KnowledgeBaseInitializationFlow.__name__,
          require_complete=False,
          lightweight=self.args.lightweight,
          next_state="ProcessKnowledgeBase")
    else:
      self.Log("Unknown system type, skipping KnowledgeBaseInitializationFlow")

  @flow.StateHandler()
  def InstallDate(self, responses):
    if responses.success:
      response = responses.First()
      with self._CreateClient() as client:
        install_date = client.Schema.INSTALL_DATE(response.integer * 1000000)
        client.Set(install_date)
    else:
      self.Log("Could not get InstallDate")

  def _GetExtraArtifactsForCollection(self):
    original_set = set(config.CONFIG["Artifacts.interrogate_store_in_aff4"])
    add_set = set(
        config.CONFIG["Artifacts.interrogate_store_in_aff4_additions"])
    skip_set = set(config.CONFIG["Artifacts.interrogate_store_in_aff4_skip"])
    return original_set.union(add_set) - skip_set

  @flow.StateHandler()
  def ProcessKnowledgeBase(self, responses):
    """Collect and store any extra non-kb artifacts."""
    if not responses.success:
      raise flow.FlowError("Error collecting artifacts: %s" % responses.status)

    # Collect any non-knowledgebase artifacts that will be stored in aff4.
    artifact_list = self._GetExtraArtifactsForCollection()
    if artifact_list:
      self.CallFlow(
          collectors.ArtifactCollectorFlow.__name__,
          artifact_list=artifact_list,
          next_state="ProcessArtifactResponses",
          store_results_in_aff4=True)

    # Update the client index
    client = self._OpenClient()
    client_index.CreateClientIndex(token=self.token).AddClient(client)

  @flow.StateHandler()
  def ProcessArtifactResponses(self, responses):
    if not responses.success:
      self.Log("Error collecting artifacts: %s", responses.status)

  FILTERED_IPS = ["127.0.0.1", "::1", "fe80::1"]

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if not (responses.success and responses):
      self.Log("Could not enumerate interfaces: %s" % responses.status)
      return

    with self._CreateClient() as client:
      interface_list = client.Schema.INTERFACES()
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

      client.Set(client.Schema.MAC_ADDRESS("\n".join(mac_addresses)))
      client.Set(client.Schema.HOST_IPS("\n".join(ip_addresses)))
      client.Set(client.Schema.INTERFACES(interface_list))

  @flow.StateHandler()
  def EnumerateFilesystems(self, responses):
    """Store all the local filesystems in the client."""
    if responses.success and len(responses):
      filesystems = aff4_grr.VFSGRRClient.SchemaCls.FILESYSTEM()
      for response in responses:
        filesystems.Append(response)

        if response.type == "partition":
          (device, offset) = response.device.rsplit(":", 1)

          offset = int(offset)

          pathspec = rdf_paths.PathSpec(
              path=device,
              pathtype=rdf_paths.PathSpec.PathType.OS,
              offset=offset)

          pathspec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

          urn = pathspec.AFF4Path(self.client_id)
          fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()
          continue

        if response.device:
          pathspec = rdf_paths.PathSpec(
              path=response.device, pathtype=rdf_paths.PathSpec.PathType.OS)

          pathspec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

          urn = pathspec.AFF4Path(self.client_id)
          fd = aff4.FACTORY.Create(urn, standard.VFSDirectory, token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

        if response.mount_point:
          # Create the OS device
          pathspec = rdf_paths.PathSpec(
              path=response.mount_point,
              pathtype=rdf_paths.PathSpec.PathType.OS)

          urn = pathspec.AFF4Path(self.client_id)
          with aff4.FACTORY.Create(
              urn, standard.VFSDirectory, token=self.token) as fd:
            fd.Set(fd.Schema.PATHSPEC(pathspec))

      with self._CreateClient() as client:
        client.Set(client.Schema.FILESYSTEM, filesystems)
    else:
      self.Log("Could not enumerate file systems.")

  @flow.StateHandler()
  def ClientInfo(self, responses):
    """Obtain some information about the GRR client running."""
    if responses.success:
      response = responses.First()
      with self._OpenClient(mode="rw") as client:
        client.Set(client.Schema.CLIENT_INFO(response))
        client.AddLabels(response.labels, owner="GRR")
    else:
      self.Log("Could not get ClientInfo.")

  @flow.StateHandler()
  def ClientConfiguration(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      with self._CreateClient() as client:
        client.Set(client.Schema.GRR_CONFIGURATION(response))

  @flow.StateHandler()
  def ClientLibraries(self, responses):
    """Process client library information."""
    if responses.success:
      response = responses.First()
      with self._CreateClient() as client:
        client.Set(client.Schema.LIBRARY_VERSIONS(response))

  def NotifyAboutEnd(self):
    self.Notify("Discovery", self.client_id, "Client Discovery Complete")

  @flow.StateHandler()
  def End(self):
    """Finalize client registration."""
    # Update summary and publish to the Discovery queue.
    client = self._OpenClient()
    summary = client.GetSummary()
    self.Publish("Discovery", summary)
    self.SendReply(summary)

    # Update the client index
    client_index.CreateClientIndex(token=self.token).AddClient(client)


class EnrolmentInterrogateEvent(flow.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]
  well_known_session_id = rdfvalue.SessionID(
      queue=queues.ENROLLMENT, flow_name=Interrogate.__name__)

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
    flow.GRRFlow.StartFlow(
        client_id=event,
        flow_name=Interrogate.__name__,
        queue=queues.ENROLLMENT,
        token=self.token)
