#!/usr/bin/env python
"""GRR specific AFF4 objects."""


import logging
import re
import time


from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.server import access_control
from grr.server import aff4
from grr.server import data_store
from grr.server import flow
from grr.server import foreman as rdf_foreman
from grr.server import grr_collections
from grr.server import queue_manager
from grr.server.aff4_objects import standard


class SpaceSeparatedStringArray(rdfvalue.RDFString):
  """A special string which stores strings as space separated."""

  def __iter__(self):
    for value in self._value.split():
      yield value


class VFSGRRClient(standard.VFSDirectory):
  """A Remote client."""

  # URN of the index for client labels.
  labels_index_urn = rdfvalue.RDFURN("aff4:/index/labels/clients")

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    """The schema for the client."""
    client_index = rdfvalue.RDFURN("aff4:/index/client")

    FLEETSPEAK_ENABLED = aff4.Attribute(
        "metadata:IsFleetspeak", rdfvalue.RDFBool,
        "Whether this client uses Fleetspeak for comms.")

    CERT = aff4.Attribute("metadata:cert", rdf_crypto.RDFX509Cert,
                          "The PEM encoded cert of the client.")

    FILESYSTEM = aff4.Attribute("aff4:filesystem", rdf_client.Filesystems,
                                "Filesystems on the client.")

    CLIENT_INFO = aff4.Attribute(
        "metadata:ClientInfo",
        rdf_client.ClientInformation,
        "GRR client information",
        "GRR client",
        default=rdf_client.ClientInformation())

    LAST_BOOT_TIME = aff4.Attribute(
        "metadata:LastBootTime", rdfvalue.RDFDatetime,
        "When the machine was last booted", "BootTime")

    FIRST_SEEN = aff4.Attribute("metadata:FirstSeen", rdfvalue.RDFDatetime,
                                "First time the client registered with us",
                                "FirstSeen")

    # Information about the host.
    HOSTNAME = aff4.Attribute(
        "metadata:hostname",
        rdfvalue.RDFString,
        "Hostname of the host.",
        "Host",
        index=client_index)
    FQDN = aff4.Attribute(
        "metadata:fqdn",
        rdfvalue.RDFString,
        "Fully qualified hostname of the host.",
        "FQDN",
        index=client_index)

    SYSTEM = aff4.Attribute("metadata:system", rdfvalue.RDFString,
                            "Operating System class.", "System")
    UNAME = aff4.Attribute("metadata:uname", rdfvalue.RDFString,
                           "Uname string.", "Uname")
    OS_RELEASE = aff4.Attribute("metadata:os_release", rdfvalue.RDFString,
                                "OS Major release number.", "Release")
    OS_VERSION = aff4.Attribute("metadata:os_version", rdf_client.VersionString,
                                "OS Version number.", "Version")

    # ARCH values come from platform.uname machine value, e.g. x86_64, AMD64.
    ARCH = aff4.Attribute("metadata:architecture", rdfvalue.RDFString,
                          "Architecture.", "Architecture")
    INSTALL_DATE = aff4.Attribute("metadata:install_date", rdfvalue.RDFDatetime,
                                  "Install Date.", "Install")

    # The knowledge base is used for storing data about the host and users.
    # This is currently a slightly odd object as we only use some of the fields.
    # The proto itself is used in Artifact handling outside of GRR (e.g. Plaso).
    # Over time we will migrate fields into this proto, but for now it is a mix.
    KNOWLEDGE_BASE = aff4.Attribute("metadata:knowledge_base",
                                    rdf_client.KnowledgeBase,
                                    "Artifact Knowledge Base", "KnowledgeBase")

    GRR_CONFIGURATION = aff4.Attribute(
        "aff4:client_configuration", rdf_protodict.Dict,
        "Running configuration for the GRR client.", "Config")

    LIBRARY_VERSIONS = aff4.Attribute(
        "aff4:library_versions", rdf_protodict.Dict,
        "Running library versions for the client.", "Libraries")

    USERNAMES = aff4.Attribute(
        "aff4:user_names",
        SpaceSeparatedStringArray,
        "A space separated list of system users.",
        "Usernames",
        index=client_index)

    # This information is duplicated from the INTERFACES attribute but is done
    # to allow for fast searching by mac address.
    MAC_ADDRESS = aff4.Attribute(
        "aff4:mac_addresses",
        rdfvalue.RDFString,
        "A hex encoded MAC address.",
        "MAC",
        index=client_index)

    KERNEL = aff4.Attribute("aff4:kernel_version", rdfvalue.RDFString,
                            "Kernel version string.", "KernelVersion")

    # Same for IP addresses.
    HOST_IPS = aff4.Attribute(
        "aff4:host_ips",
        rdfvalue.RDFString,
        "An IP address.",
        "Host_ip",
        index=client_index)

    PING = aff4.Attribute(
        "metadata:ping",
        rdfvalue.RDFDatetime,
        "The last time the server heard from this client.",
        "LastCheckin",
        versioned=False,
        default=0)

    CLOCK = aff4.Attribute(
        "metadata:clock",
        rdfvalue.RDFDatetime,
        "The last clock read on the client "
        "(Can be used to estimate client clock skew).",
        "Clock",
        versioned=False)

    CLIENT_IP = aff4.Attribute(
        "metadata:client_ip",
        rdfvalue.RDFString,
        "The ip address this client connected from.",
        "Client_ip",
        versioned=False)

    # This is the last foreman rule that applied to us
    LAST_FOREMAN_TIME = aff4.Attribute(
        "aff4:last_foreman_time",
        rdfvalue.RDFDatetime,
        "The last time the foreman checked us.",
        versioned=False)

    LAST_CRASH = aff4.Attribute(
        "aff4:last_crash",
        rdf_client.ClientCrash,
        "Last client crash.",
        creates_new_object_version=False,
        versioned=False)

    VOLUMES = aff4.Attribute("aff4:volumes", rdf_client.Volumes,
                             "Client disk volumes.")

    INTERFACES = aff4.Attribute("aff4:interfaces", rdf_client.Interfaces,
                                "Network interfaces.", "Interfaces")

    HARDWARE_INFO = aff4.Attribute(
        "aff4:hardware_info",
        rdf_client.HardwareInfo,
        "Various hardware information.",
        default=rdf_client.HardwareInfo())

    MEMORY_SIZE = aff4.Attribute("aff4:memory_size", rdfvalue.ByteSize,
                                 "Amount of memory this client's machine has.")

    # Cloud VM information.
    CLOUD_INSTANCE = aff4.Attribute("metadata:cloud_instance",
                                    cloud.CloudInstance,
                                    "Information about cloud machines.")

  # Valid client ids
  CLIENT_ID_RE = re.compile(r"^C\.[0-9a-fA-F]{16}$")

  # A collection of crashes for this client.
  @classmethod
  def CrashCollectionURNForCID(cls, client_id):
    return client_id.Add("crashes")

  @classmethod
  def CrashCollectionForCID(cls, client_id, token=None):
    """Returns the collection storing crash information for the given client.

    Args:
      client_id: The id of the client, a rdfvalue.ClientURN.
      token: A data store token.
    Returns:
      The collection containing the crash information objects for the client.
    """
    return grr_collections.CrashCollection(
        cls.CrashCollectionURNForCID(client_id), token=token)

  def CrashCollection(self):
    return self.CrashCollectionForCID(self.client_id, token=self.token)

  # A collection of Anomalies found on this client.
  @classmethod
  def AnomalyCollectionURNForCID(cls, client_id):
    return client_id.Add("anomalies")

  @classmethod
  def AnomalyCollectionForCID(cls, client_id, token=None):
    return grr_collections.AnomalyCollection(
        cls.AnomalyCollectionURNForCID(client_id), token=token)

  def AnomalyCollection(self):
    return self.AnomalyCollectionForCID(self.client_id, token=self.token)

  @property
  def age(self):
    """RDFDatetime at which the object was created."""
    # TODO(user) move up to AFF4Object after some analysis of how .age is
    # used in the codebase.
    aff4_type = self.Get(self.Schema.TYPE)

    if aff4_type:
      return aff4_type.age
    else:
      # If there is no type attribute yet, we have only just been created and
      # not flushed yet, so just set timestamp to now.
      return rdfvalue.RDFDatetime.Now()

  def Initialize(self):
    # Our URN must be a valid client.id.
    self.client_id = rdf_client.ClientURN(self.urn)

  def Update(self, attribute=None, priority=None):
    if attribute == "CONTAINS":
      flow_id = flow.GRRFlow.StartFlow(
          client_id=self.client_id,
          # TODO(user): dependency loop with flows/general/discover.py
          # flow_name=discovery.Interrogate.__name__,
          flow_name="Interrogate",
          token=self.token,
          priority=priority)

      return flow_id

  @staticmethod
  def ClientURNFromURN(urn):
    return rdf_client.ClientURN(rdfvalue.RDFURN(urn).Split()[0])

  def GetSummary(self):
    """Gets a client summary object.

    Returns:
      rdf_client.ClientSummary
    Raises:
      ValueError: on bad cloud type
    """
    self.max_age = 0
    summary = rdf_client.ClientSummary(client_id=self.urn)
    summary.system_info.node = self.Get(self.Schema.HOSTNAME)
    summary.system_info.system = self.Get(self.Schema.SYSTEM)
    summary.system_info.release = self.Get(self.Schema.OS_RELEASE)
    summary.system_info.version = str(self.Get(self.Schema.OS_VERSION, ""))
    summary.system_info.kernel = self.Get(self.Schema.KERNEL)
    summary.system_info.fqdn = self.Get(self.Schema.FQDN)
    summary.system_info.machine = self.Get(self.Schema.ARCH)
    summary.system_info.install_date = self.Get(self.Schema.INSTALL_DATE)
    kb = self.Get(self.Schema.KNOWLEDGE_BASE)
    if kb:
      summary.users = kb.users
    summary.interfaces = self.Get(self.Schema.INTERFACES)
    summary.client_info = self.Get(self.Schema.CLIENT_INFO)
    hwi = self.Get(self.Schema.HARDWARE_INFO)
    if hwi:
      summary.serial_number = hwi.serial_number
      summary.system_manufacturer = hwi.system_manufacturer
    summary.timestamp = self.age
    cloud_instance = self.Get(self.Schema.CLOUD_INSTANCE)
    if cloud_instance:
      summary.cloud_type = cloud_instance.cloud_type
      if cloud_instance.cloud_type == "GOOGLE":
        summary.cloud_instance_id = cloud_instance.google.unique_id
      elif cloud_instance.cloud_type == "AMAZON":
        summary.cloud_instance_id = cloud_instance.amazon.instance_id
      else:
        raise ValueError("Bad cloud type: %s" % cloud_instance.cloud_type)

    return summary

  def AddLabels(self, label_names, owner=None):
    super(VFSGRRClient, self).AddLabels(label_names, owner=owner)
    with aff4.FACTORY.Create(
        standard.LabelSet.CLIENT_LABELS_URN,
        standard.LabelSet,
        mode="w",
        token=self.token) as client_labels_index:
      for label_name in label_names:
        client_labels_index.Add(label_name)

  @staticmethod
  def GetClientRequests(client_urns, token=None):
    """Returns all client requests for the given client urns."""
    task_urns = [urn.Add("tasks") for urn in client_urns]

    client_requests_raw = data_store.DB.MultiResolvePrefix(
        task_urns, "task:", token=token)

    client_requests = {}
    for client_urn, requests in client_requests_raw:
      client_id = str(client_urn)[6:6 + 18]

      client_requests.setdefault(client_id, [])

      for _, serialized, _ in requests:
        msg = rdf_flows.GrrMessage.FromSerializedString(serialized)
        client_requests[client_id].append(msg)

    return client_requests


class UpdateVFSFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateVFSFileArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class UpdateVFSFile(flow.GRRFlow):
  """A flow to update VFS file."""
  args_type = UpdateVFSFileArgs

  def Init(self):
    self.state.get_file_flow_urn = None

  @flow.StateHandler()
  def Start(self):
    """Calls the Update() method of a given VFSFile/VFSDirectory object."""
    self.Init()
    fd = aff4.FACTORY.Open(self.args.vfs_file_urn, mode="rw", token=self.token)

    # Account for implicit directories.
    if fd.Get(fd.Schema.TYPE) is None:
      fd = fd.Upgrade(standard.VFSDirectory)

    self.state.get_file_flow_urn = fd.Update(
        attribute=self.args.attribute,
        priority=rdf_flows.GrrMessage.Priority.HIGH_PRIORITY)


class VFSAnalysisFile(aff4.AFF4Image):
  """A file object in the VFS space."""

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""
    STAT = standard.VFSDirectory.SchemaCls.STAT

    CONTENT_LOCK = aff4.Attribute(
        "aff4:content_lock", rdfvalue.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this flow.")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdf_paths.PathSpec,
        "The pathspec used to retrieve this object from the client.")


class VFSFile(VFSAnalysisFile):
  """A file object that can be updated under lock."""

  class SchemaCls(VFSAnalysisFile.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""

    CONTENT_LOCK = aff4.Attribute(
        "aff4:content_lock", rdfvalue.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this flow.")

  def Update(self, attribute=None, priority=None):
    """Update an attribute from the client."""
    # List the directory on the client
    currently_running = self.Get(self.Schema.CONTENT_LOCK)

    # Is this flow still active?
    if currently_running:
      flow_obj = aff4.FACTORY.Open(currently_running, token=self.token)
      if flow_obj and flow_obj.GetRunner().IsRunning():
        return

    # The client_id is the first element of the URN
    client_id = self.urn.Path().split("/", 2)[1]

    # Get the pathspec for this object
    pathspec = self.Get(self.Schema.STAT).pathspec
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_id,
        # TODO(user): dependency loop between aff4_grr.py and transfer.py
        # flow_name=transfer.MultiGetFile.__name__,
        flow_name="MultiGetFile",
        token=self.token,
        pathspecs=[pathspec],
        priority=priority)
    self.Set(self.Schema.CONTENT_LOCK(flow_urn))
    self.Close()

    return flow_urn


class MemoryImage(standard.VFSDirectory):
  """The server representation of the client's memory device."""

  class SchemaCls(VFSFile.SchemaCls):
    LAYOUT = aff4.Attribute("aff4:memory/geometry",
                            rdf_rekall_types.MemoryInformation,
                            "The memory layout of this image.")


class VFSMemoryFile(aff4.AFF4MemoryStream):
  """A VFS file under a VFSDirectory node which does not have storage."""

  class SchemaCls(aff4.AFF4MemoryStream.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""
    # Support also VFSFile attributes.
    STAT = VFSFile.SchemaCls.STAT
    HASH = VFSFile.SchemaCls.HASH
    PATHSPEC = VFSFile.SchemaCls.PATHSPEC
    CONTENT_LOCK = VFSFile.SchemaCls.CONTENT_LOCK


class GRRForeman(aff4.AFF4Object):
  """The foreman starts flows for clients depending on rules."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Attributes specific to VFSDirectory."""
    RULES = aff4.Attribute(
        "aff4:rules",
        rdf_foreman.ForemanRules,
        "The rules the foreman uses.",
        versioned=False,
        creates_new_object_version=False,
        default=rdf_foreman.ForemanRules())

  def ExpireRules(self):
    """Removes any rules with an expiration date in the past."""
    rules = self.Get(self.Schema.RULES)
    new_rules = self.Schema.RULES()
    now = time.time() * 1e6
    expired_session_ids = set()

    for rule in rules:
      if rule.expires > now:
        new_rules.Append(rule)
      else:
        for action in rule.actions:
          if action.hunt_id:
            expired_session_ids.add(action.hunt_id)

    if expired_session_ids:
      with data_store.DB.GetMutationPool(token=self.token) as pool:
        # Notify the worker to mark this hunt as terminated.
        manager = queue_manager.QueueManager(token=self.token)
        manager.MultiNotifyQueue(
            [
                rdf_flows.GrrNotification(session_id=session_id)
                for session_id in expired_session_ids
            ],
            mutation_pool=pool)

    if len(new_rules) < len(rules):
      self.Set(self.Schema.RULES, new_rules)
      self.Flush()

  def _CheckIfHuntTaskWasAssigned(self, client_id, hunt_id):
    """Will return True if hunt's task was assigned to this client before."""
    for _ in aff4.FACTORY.Stat(
        [client_id.Add("flows/%s:hunt" % rdfvalue.RDFURN(hunt_id).Basename())],
        token=self.token):
      return True

    return False

  def _EvaluateRules(self, objects, rule, client_id):
    """Evaluates the rules."""
    return rule.client_rule_set.Evaluate(objects, client_id)

  def _RunActions(self, rule, client_id):
    """Run all the actions specified in the rule.

    Args:
      rule: Rule which actions are to be executed.
      client_id: Id of a client where rule's actions are to be executed.

    Returns:
      Number of actions started.
    """
    actions_count = 0

    for action in rule.actions:
      try:
        # Say this flow came from the foreman.
        token = self.token.Copy()
        token.username = "Foreman"

        if action.HasField("hunt_id"):
          if self._CheckIfHuntTaskWasAssigned(client_id, action.hunt_id):
            logging.info("Foreman: ignoring hunt %s on client %s: was started "
                         "here before", client_id, action.hunt_id)
          else:
            logging.info("Foreman: Starting hunt %s on client %s.",
                         action.hunt_id, client_id)

            flow_cls = flow.GRRFlow.classes[action.hunt_name]
            flow_cls.StartClients(action.hunt_id, [client_id])
            actions_count += 1
        else:
          flow.GRRFlow.StartFlow(
              client_id=client_id,
              flow_name=action.flow_name,
              token=token,
              **action.argv.ToDict())
          actions_count += 1
      # There could be all kinds of errors we don't know about when starting the
      # flow/hunt so we catch everything here.
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Failure running foreman action on client %s: %s",
                          action.hunt_id, e)

    return actions_count

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client.

    Args:
      client_id: Client id of the client for tasks to be assigned.

    Returns:
      Number of assigned tasks.
    """
    client_id = rdf_client.ClientURN(client_id)

    rules = self.Get(self.Schema.RULES)
    if not rules:
      return 0

    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    try:
      last_foreman_run = client.Get(client.Schema.LAST_FOREMAN_TIME) or 0
    except AttributeError:
      last_foreman_run = 0

    latest_rule = max(rule.created for rule in rules)

    if latest_rule <= int(last_foreman_run):
      return 0

    # Update the latest checked rule on the client.
    client.Set(client.Schema.LAST_FOREMAN_TIME(latest_rule))
    client.Close()

    # For efficiency we collect all the objects we want to open first and then
    # open them all in one round trip.
    object_urns = {}
    relevant_rules = []
    expired_rules = False

    now = time.time() * 1e6

    for rule in rules:
      if rule.expires < now:
        expired_rules = True
        continue
      if rule.created <= int(last_foreman_run):
        continue

      relevant_rules.append(rule)

      for path in rule.client_rule_set.GetPathsToCheck():
        aff4_object = client_id.Add(path)
        object_urns[str(aff4_object)] = aff4_object

    # Retrieve all aff4 objects we need.
    objects = {}
    for fd in aff4.FACTORY.MultiOpen(object_urns, token=self.token):
      objects[fd.urn] = fd

    actions_count = 0
    for rule in relevant_rules:
      if self._EvaluateRules(objects, rule, client_id):
        actions_count += self._RunActions(rule, client_id)

    if expired_rules:
      self.ExpireRules()

    return actions_count


class GRRAFF4Init(registry.InitHook):
  """Ensure critical AFF4 objects exist for GRR."""

  # Must run after the AFF4 subsystem is ready.
  pre = [aff4.AFF4InitHook]

  def Run(self):
    try:
      # Make the foreman
      with aff4.FACTORY.Create(
          "aff4:/foreman", GRRForeman, token=aff4.FACTORY.root_token):
        pass
    except access_control.UnauthorizedAccess:
      pass


class VFSFileSymlink(aff4.AFF4Stream):
  """A Delegate object for another URN."""

  delegate = None

  class SchemaCls(VFSFile.SchemaCls):
    DELEGATE = aff4.Attribute("aff4:delegate", rdfvalue.RDFURN,
                              "The URN of the delegate of this object.")

  def Initialize(self):
    """Open the delegate object."""
    if "r" in self.mode:
      delegate = self.Get(self.Schema.DELEGATE)
      if delegate:
        self.delegate = aff4.FACTORY.Open(
            delegate, mode=self.mode, token=self.token, age=self.age_policy)

  def Read(self, length):
    if "r" not in self.mode:
      raise IOError("VFSFileSymlink was not opened for reading.")
    return self.delegate.Read(length)

  def Seek(self, offset, whence):
    return self.delegate.Seek(offset, whence)

  def Tell(self):
    return self.delegate.Tell()

  def Close(self, sync):
    super(VFSFileSymlink, self).Close()
    if self.delegate:
      return self.delegate.Close()

  def Write(self):
    raise IOError("VFSFileSymlink not writeable.")


class VFSBlobImage(standard.BlobImage, VFSFile):
  """BlobImage with VFS attributes for use in client namespace."""

  class SchemaCls(standard.BlobImage.SchemaCls, VFSFile.SchemaCls):
    pass


class AFF4RekallProfile(aff4.AFF4Object):
  """A Rekall profile in the AFF4 namespace."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    PROFILE = aff4.Attribute("aff4:profile", rdf_rekall_types.RekallProfile,
                             "A Rekall profile.")


class TempKnowledgeBase(standard.VFSDirectory):
  """This is only used in end to end tests."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    KNOWLEDGE_BASE = aff4.Attribute("metadata:temp_knowledge_base",
                                    rdf_client.KnowledgeBase,
                                    "Artifact Knowledge Base", "KnowledgeBase")


# The catchall client label used when compiling server-side stats about clients
# by label.
ALL_CLIENTS_LABEL = "All"


def GetAllClientLabels(token, include_catchall=False):
  """Get the set of all label names applied to all clients.

  Args:
    token: token to use when opening the index.
    include_catchall: If true, we include ALL_CLIENTS_LABEL in the results.

  Returns:
    set of label name strings, including the catchall "All"
  """
  labels_index = aff4.FACTORY.Create(
      standard.LabelSet.CLIENT_LABELS_URN,
      standard.LabelSet,
      mode="r",
      token=token)
  labels = set(labels_index.ListLabels())
  if include_catchall:
    labels.add(ALL_CLIENTS_LABEL)
  return labels
