#!/usr/bin/env python
"""These are flows designed to discover information about the host."""

from grr import config
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact
from grr.server.grr_response_server import client_index
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import db
from grr.server.grr_response_server import events
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import notification
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import standard
from grr.server.grr_response_server.flows.general import collectors


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

    client_id = self.client_id.Basename()
    self.state.client = rdf_objects.ClientSnapshot(client_id=client_id)
    self.state.fqdn = None
    self.state.os = None

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

    # AFF4 client.
    with self._CreateClient() as client:
      client.Set(
          client.Schema.CLOUD_INSTANCE(
              cloud.ConvertCloudMetadataResponsesToCloudInstance(
                  metadata_responses)))

    # rdf_objects.ClientSnapshot.
    client = self.state.client
    client.cloud_instance = cloud.ConvertCloudMetadataResponsesToCloudInstance(
        metadata_responses)

  @flow.StateHandler()
  def StoreMemorySize(self, responses):
    if not responses.success:
      return

    # AFF4 client.
    with self._CreateClient() as client:
      client.Set(client.Schema.MEMORY_SIZE(responses.First()))

    # rdf_objects.ClientSnapshot.
    self.state.client.memory_size = responses.First()

  @flow.StateHandler()
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()
      # AFF4 client.

      # These need to be in separate attributes because they get searched on in
      # the GUI
      with self._OpenClient(mode="rw") as client:
        # For backwards compatibility.
        client.Set(client.Schema.HOSTNAME(response.fqdn))
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

      # rdf_objects.ClientSnapshot.
      client = self.state.client
      client.os_release = response.release
      client.os_version = response.version
      client.kernel = response.kernel
      client.arch = response.machine
      # Store these for later, there might be more accurate data
      # coming in from the artifact collector.
      self.state.fqdn = response.fqdn
      self.state.os = response.system

      if data_store.RelationalDBWriteEnabled():
        try:
          # Update the client index
          client_index.ClientIndex().AddClient(client)
        except db.UnknownClientError:
          pass

      if response.system == "Windows":
        with aff4.FACTORY.Create(
            self.client_id.Add("registry"),
            standard.VFSDirectory,
            token=self.token) as fd:
          fd.Set(
              fd.Schema.PATHSPEC,
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
      # We failed to get the Platform info, maybe there is a stored
      # system we can use to get at least some data.
      if data_store.RelationalDBReadEnabled():
        client = data_store.REL_DB.ReadClientSnapshot(self.client_id.Basename())
        known_system_type = client and client.knowledge_base.os
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
    if not responses.success:
      self.Log("Could not get InstallDate")
      return

    response = responses.First()

    if isinstance(response, rdfvalue.RDFDatetime):
      # New clients send the correct values already.
      install_date = response
    elif isinstance(response, rdf_protodict.DataBlob):
      # For backwards compatibility.
      install_date = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
          response.integer)
    else:
      self.Log("Unknown response type for InstallDate: %s" % type(response))
      return

    # AFF4 client.
    with self._CreateClient() as client:
      client.Set(client.Schema.INSTALL_DATE(install_date))

    # rdf_objects.ClientSnapshot.
    self.state.client.install_time = install_date

  def CopyOSReleaseFromKnowledgeBase(self, kb, client):
    """Copy os release and version from KB to client object."""
    if kb.os_release:
      client.Set(client.Schema.OS_RELEASE(kb.os_release))

      # Override OS version field too.
      # TODO(user): this actually results in incorrect versions for things
      #                like Ubuntu (14.4 instead of 14.04). I don't think zero-
      #                padding is always correct, however.
      os_version = "%d.%d" % (kb.os_major_version, kb.os_minor_version)
      client.Set(client.Schema.OS_VERSION(os_version))

  @flow.StateHandler()
  def ProcessKnowledgeBase(self, responses):
    """Collect and store any extra non-kb artifacts."""
    if not responses.success:
      raise flow.FlowError(
          "Error while collecting the knowledge base: %s" % responses.status)

    kb = responses.First()
    # AFF4 client.
    client = self._OpenClient(mode="rw")
    client.Set(client.Schema.KNOWLEDGE_BASE, kb)

    # Copy usernames.
    usernames = [user.username for user in kb.users if user.username]
    client.AddAttribute(client.Schema.USERNAMES(" ".join(usernames)))

    self.CopyOSReleaseFromKnowledgeBase(kb, client)
    client.Flush()

    # rdf_objects.ClientSnapshot.

    # Information already present in the knowledge base takes precedence.
    if not kb.os:
      kb.os = self.state.system

    if not kb.fqdn:
      kb.fqdn = self.state.fqdn
    self.state.client.knowledge_base = kb

    self.CallFlow(
        collectors.ArtifactCollectorFlow.__name__,
        artifact_list=config.CONFIG["Artifacts.non_kb_interrogate_artifacts"],
        next_state="ProcessArtifactResponses")

    # Update the client index for the AFF4 client.
    client_index.CreateClientIndex(token=self.token).AddClient(client)

    if data_store.RelationalDBWriteEnabled():
      try:
        # Update the client index for the rdf_objects.ClientSnapshot.
        client_index.ClientIndex().AddClient(self.state.client)
      except db.UnknownClientError:
        pass

  @flow.StateHandler()
  def ProcessArtifactResponses(self, responses):
    if not responses.success:
      self.Log("Error collecting artifacts: %s", responses.status)
    if not list(responses):
      return

    with self._OpenClient(mode="rw") as client:
      new_volumes = []
      for response in responses:
        if isinstance(response, rdf_client.Volume):
          # AFF4 client.
          new_volumes.append(response)

          # rdf_objects.ClientSnapshot.
          self.state.client.volumes.append(response)
        elif isinstance(response, rdf_client.HardwareInfo):
          # AFF4 client.
          client.Set(client.Schema.HARDWARE_INFO, response)

          # rdf_objects.ClientSnapshot.
          self.state.client.hardware_info = response
        else:
          raise ValueError("Unexpected response type: %s" % type(response))

      if new_volumes:
        volumes = client.Schema.VOLUMES()
        for v in new_volumes:
          volumes.Append(v)
        client.Set(client.Schema.VOLUMES, volumes)

  FILTERED_IPS = ["127.0.0.1", "::1", "fe80::1"]

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if not (responses.success and responses):
      self.Log("Could not enumerate interfaces: %s" % responses.status)
      return

    # AFF4 client.
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

    # rdf_objects.ClientSnapshot.
    self.state.client.interfaces = sorted(responses, key=lambda i: i.ifname)

  @flow.StateHandler()
  def EnumerateFilesystems(self, responses):
    """Store all the local filesystems in the client."""
    if not responses.success or not responses:
      self.Log("Could not enumerate file systems.")
      return

    # rdf_objects.ClientSnapshot.
    self.state.client.filesystems = responses

    # AFF4 client.
    filesystems = aff4_grr.VFSGRRClient.SchemaCls.FILESYSTEM()
    for response in responses:
      filesystems.Append(response)

    with self._CreateClient() as client:
      client.Set(client.Schema.FILESYSTEM, filesystems)

    # Create default pathspecs for all devices.
    for response in responses:
      if response.type == "partition":
        (device, offset) = response.device.rsplit(":", 1)

        offset = int(offset)

        pathspec = rdf_paths.PathSpec(
            path=device, pathtype=rdf_paths.PathSpec.PathType.OS, offset=offset)

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
            path=response.mount_point, pathtype=rdf_paths.PathSpec.PathType.OS)

        urn = pathspec.AFF4Path(self.client_id)
        with aff4.FACTORY.Create(
            urn, standard.VFSDirectory, token=self.token) as fd:
          fd.Set(fd.Schema.PATHSPEC(pathspec))

  @flow.StateHandler()
  def ClientInfo(self, responses):
    """Obtain some information about the GRR client running."""
    if not responses.success:
      self.Log("Could not get ClientInfo.")
      return
    response = responses.First()

    # AFF4 client.
    with self._OpenClient(mode="rw") as client:
      client.Set(client.Schema.CLIENT_INFO(response))
      client.AddLabels(response.labels, owner="GRR")

    # rdf_objects.ClientSnapshot.
    self.state.client.startup_info.client_info = response

  @flow.StateHandler()
  def ClientConfiguration(self, responses):
    """Process client config."""
    if not responses.success:
      return

    response = responses.First()

    # AFF4 client.
    with self._CreateClient() as client:
      client.Set(client.Schema.GRR_CONFIGURATION(response))

    # rdf_objects.ClientSnapshot.
    for k, v in response.items():
      self.state.client.grr_configuration.Append(key=k, value=utils.SmartStr(v))

  @flow.StateHandler()
  def ClientLibraries(self, responses):
    """Process client library information."""
    if not responses.success:
      return

    response = responses.First()
    # AFF4 client.
    with self._CreateClient() as client:
      client.Set(client.Schema.LIBRARY_VERSIONS(response))

    # rdf_objects.ClientSnapshot.
    for k, v in response.items():
      self.state.client.library_versions.Append(key=k, value=utils.SmartStr(v))

  def NotifyAboutEnd(self):
    notification.Notify(
        self.token.username,
        rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED, "",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CLIENT,
            client=rdf_objects.ClientReference(
                client_id=self.client_id.Basename())))

  @flow.StateHandler()
  def End(self):
    """Finalize client registration."""
    # Update summary and publish to the Discovery queue.

    if data_store.RelationalDBWriteEnabled():
      try:
        data_store.REL_DB.WriteClientSnapshot(self.state.client)
      except db.UnknownClientError:
        pass

    client = self._OpenClient()

    if data_store.RelationalDBReadEnabled():
      summary = self.state.client.GetSummary()
      summary.client_id = self.client_id
      summary.timestamp = rdfvalue.RDFDatetime.Now()
    else:
      summary = client.GetSummary()

    self.Publish("Discovery", summary)
    self.SendReply(summary)

    # Update the client index
    client_index.CreateClientIndex(token=self.token).AddClient(client)
    if data_store.RelationalDBWriteEnabled():
      try:
        index = client_index.ClientIndex()
        index.AddClient(self.state.client)
        labels = self.state.client.startup_info.client_info.labels
        if labels:
          data_store.REL_DB.AddClientLabels(self.state.client.client_id, "GRR",
                                            labels)
      except db.UnknownClientError:
        # TODO(amoser): Remove after data migration.
        pass


class EnrolmentInterrogateEvent(events.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]

  def ProcessMessages(self, msgs=None, token=None):
    for msg in msgs:
      flow.GRRFlow.StartFlow(
          client_id=msg,
          flow_name=Interrogate.__name__,
          queue=queues.ENROLLMENT,
          token=token)
