#!/usr/bin/env python
"""GRR specific AFF4 objects."""


import re
import time


import logging
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.server import foreman as rdf_foreman


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

    CERT = aff4.Attribute("metadata:cert", rdf_crypto.RDFX509Cert,
                          "The PEM encoded cert of the client.")

    FILESYSTEM = aff4.Attribute("aff4:filesystem", rdf_client.Filesystems,
                                "Filesystems on the client.")

    CLIENT_INFO = aff4.Attribute(
        "metadata:ClientInfo", rdf_client.ClientInformation,
        "GRR client information", "GRR client", default="")

    LAST_BOOT_TIME = aff4.Attribute("metadata:LastBootTime",
                                    rdfvalue.RDFDatetime,
                                    "When the machine was last booted",
                                    "BootTime")

    FIRST_SEEN = aff4.Attribute("metadata:FirstSeen", rdfvalue.RDFDatetime,
                                "First time the client registered with us",
                                "FirstSeen")

    # Information about the host.
    HOSTNAME = aff4.Attribute("metadata:hostname", rdfvalue.RDFString,
                              "Hostname of the host.", "Host",
                              index=client_index)
    FQDN = aff4.Attribute("metadata:fqdn", rdfvalue.RDFString,
                          "Fully qualified hostname of the host.", "FQDN",
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

    USERNAMES = aff4.Attribute("aff4:user_names", SpaceSeparatedStringArray,
                               "A space separated list of system users.",
                               "Usernames",
                               index=client_index)

    # This information is duplicated from the INTERFACES attribute but is done
    # to allow for fast searching by mac address.
    MAC_ADDRESS = aff4.Attribute("aff4:mac_addresses", rdfvalue.RDFString,
                                 "A hex encoded MAC address.", "MAC",
                                 index=client_index)

    KERNEL = aff4.Attribute("aff4:kernel_version", rdfvalue.RDFString,
                            "Kernel version string.", "KernelVersion")

    # Same for IP addresses.
    HOST_IPS = aff4.Attribute("aff4:host_ips", rdfvalue.RDFString,
                              "An IP address.", "Host_ip",
                              index=client_index)

    PING = aff4.Attribute("metadata:ping", rdfvalue.RDFDatetime,
                          "The last time the server heard from this client.",
                          "LastCheckin", versioned=False, default=0)

    CLOCK = aff4.Attribute("metadata:clock", rdfvalue.RDFDatetime,
                           "The last clock read on the client "
                           "(Can be used to estimate client clock skew).",
                           "Clock", versioned=False)

    CLIENT_IP = aff4.Attribute("metadata:client_ip", rdfvalue.RDFString,
                               "The ip address this client connected from.",
                               "Client_ip", versioned=False)

    # This is the last foreman rule that applied to us
    LAST_FOREMAN_TIME = aff4.Attribute(
        "aff4:last_foreman_time", rdfvalue.RDFDatetime,
        "The last time the foreman checked us.", versioned=False)

    LAST_INTERFACES = aff4.Attribute(
        "aff4:last_interfaces", rdf_client.Interfaces,
        "Last seen network interfaces. Full history is maintained in the "
        "clientid/network object. Separated for performance reasons.",
        versioned=False)

    LAST_CRASH = aff4.Attribute(
        "aff4:last_crash", rdf_client.ClientCrash,
        "Last client crash.", creates_new_object_version=False,
        versioned=False)

    VOLUMES = aff4.Attribute(
        "aff4:volumes", rdf_client.Volumes,
        "Client disk volumes.")

    HARDWARE_INFO = aff4.Attribute(
        "aff4:hardware_info", rdf_client.HardwareInfo,
        "Various hardware information.", default="")

    MEMORY_SIZE = aff4.Attribute(
        "aff4:memory_size", rdfvalue.ByteSize,
        "Amount of memory this client's machine has.")

  # Valid client ids
  CLIENT_ID_RE = re.compile(r"^C\.[0-9a-fA-F]{16}$")

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
      return rdfvalue.RDFDatetime().Now()

  def Initialize(self):
    # Our URN must be a valid client.id.
    self.client_id = rdf_client.ClientURN(self.urn)

  def Update(self, attribute=None, priority=None):
    if attribute == "CONTAINS":
      flow_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                       flow_name="Interrogate",
                                       token=self.token, priority=priority)

      return flow_id

  def OpenMember(self, path, mode="rw"):
    return aff4.AFF4Volume.OpenMember(self, path, mode=mode)

  AFF4_PREFIXES = {rdf_paths.PathSpec.PathType.OS: "/fs/os",
                   rdf_paths.PathSpec.PathType.TSK: "/fs/tsk",
                   rdf_paths.PathSpec.PathType.REGISTRY: "/registry",
                   rdf_paths.PathSpec.PathType.MEMORY: "/devices/memory",
                   rdf_paths.PathSpec.PathType.TMPFILE: "/temp"}

  @staticmethod
  def ClientURNFromURN(urn):
    return rdf_client.ClientURN(rdfvalue.RDFURN(urn).Split()[0])

  @staticmethod
  def PathspecToURN(pathspec, client_urn):
    """Returns a mapping between a pathspec and an AFF4 URN.

    Args:
      pathspec: The PathSpec instance to convert.
      client_urn: A URN of any object within the client. We use it to find the
          client id.

    Returns:
      A urn that corresponds to this pathspec.

    Raises:
      ValueError: If pathspec is not of the correct type.
    """
    client_urn = rdf_client.ClientURN(client_urn)

    if not isinstance(pathspec, rdfvalue.RDFValue):
      raise ValueError("Pathspec should be an rdfvalue.")

    # If the first level is OS and the second level is TSK its probably a mount
    # point resolution. We map it into the tsk branch. For example if we get:
    # path: \\\\.\\Volume{1234}\\
    # pathtype: OS
    # mount_point: /c:/
    # nested_path {
    #    path: /windows/
    #    pathtype: TSK
    # }
    # We map this to aff4://client_id/fs/tsk/\\\\.\\Volume{1234}\\/windows/
    dev = pathspec[0].path
    if pathspec[0].HasField("offset"):
      # We divide here just to get prettier numbers in the GUI
      dev += ":" + str(pathspec[0].offset / 512)

    if (len(pathspec) > 1 and
        pathspec[0].pathtype == rdf_paths.PathSpec.PathType.OS and
        pathspec[1].pathtype == rdf_paths.PathSpec.PathType.TSK):
      result = [VFSGRRClient.AFF4_PREFIXES[rdf_paths.PathSpec.PathType.TSK],
                dev]

      # Skip the top level pathspec.
      pathspec = pathspec[1]
    else:
      # For now just map the top level prefix based on the first pathtype
      result = [VFSGRRClient.AFF4_PREFIXES[pathspec[0].pathtype]]

    for p in pathspec:
      component = p.path

      # The following encode different pathspec properties into the AFF4 path in
      # such a way that unique files on the client are mapped to unique URNs in
      # the AFF4 space. Note that this transformation does not need to be
      # reversible since we always use the PathSpec when accessing files on the
      # client.
      if p.HasField("offset"):
        component += ":" + str(p.offset / 512)

      # Support ADS names.
      if p.HasField("stream_name"):
        component += ":" + p.stream_name

      result.append(component)

    return client_urn.Add("/".join(result))

  def GetSummary(self):
    """Gets a client summary object.

    Returns:
      rdf_client.ClientSummary
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
    summary.system_info.install_date = self.Get(
        self.Schema.INSTALL_DATE)
    kb = self.Get(self.Schema.KNOWLEDGE_BASE)
    if kb:
      summary.users = kb.users
    summary.interfaces = self.Get(self.Schema.LAST_INTERFACES)
    summary.client_info = self.Get(self.Schema.CLIENT_INFO)
    summary.serial_number = self.Get(self.Schema.HARDWARE_INFO).serial_number
    summary.timestamp = self.age
    summary.system_manufacturer = self.Get(
        self.Schema.HARDWARE_INFO).system_manufacturer

    return summary

  def AddLabels(self, *label_names, **kwargs):
    super(VFSGRRClient, self).AddLabels(*label_names, **kwargs)
    with aff4.FACTORY.Create(standard.LabelSet.CLIENT_LABELS_URN,
                             "LabelSet",
                             mode="w",
                             token=self.token) as client_labels_index:
      for label_name in label_names:
        client_labels_index.Add(label_name)

  @staticmethod
  def GetClientRequests(client_urns, token=None):
    """Returns all client requests for the given client urns."""
    task_urns = [urn.Add("tasks") for urn in client_urns]

    client_requests_raw = data_store.DB.MultiResolvePrefix(task_urns, "task:",
                                                           token=token)

    client_requests = {}
    for client_urn, requests in client_requests_raw:
      client_id = str(client_urn)[6:6 + 18]

      client_requests.setdefault(client_id, [])

      for _, serialized, _ in requests:
        client_requests[client_id].append(rdf_flows.GrrMessage(serialized))

    return client_requests


class UpdateVFSFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateVFSFileArgs


class UpdateVFSFile(flow.GRRFlow):
  """A flow to update VFS file."""
  args_type = UpdateVFSFileArgs

  ACL_ENFORCED = False

  def Init(self):
    self.state.Register("get_file_flow_urn")

  @flow.StateHandler()
  def Start(self):
    """Calls the Update() method of a given VFSFile/VFSDirectory object."""
    self.Init()

    client_id = rdf_client.ClientURN(self.args.vfs_file_urn.Split()[0])
    data_store.DB.security_manager.CheckClientAccess(self.token.RealUID(),
                                                     client_id)

    fd = aff4.FACTORY.Open(self.args.vfs_file_urn, mode="rw",
                           token=self.token)

    # Account for implicit directories.
    if fd.Get(fd.Schema.TYPE) is None:
      fd = fd.Upgrade("VFSDirectory")

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
    if attribute == self.Schema.CONTENT:
      # List the directory on the client
      currently_running = self.Get(self.Schema.CONTENT_LOCK)

      # Is this flow still active?
      if currently_running:
        flow_obj = aff4.FACTORY.Open(currently_running, token=self.token)
        if flow_obj.IsRunning():
          return

    # The client_id is the first element of the URN
    client_id = self.urn.Path().split("/", 2)[1]

    # Get the pathspec for this object
    pathspec = self.Get(self.Schema.STAT).pathspec
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_id, flow_name="MultiGetFile", token=self.token,
        pathspecs=[pathspec], priority=priority)
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
    RULES = aff4.Attribute("aff4:rules", rdf_foreman.ForemanRules,
                           "The rules the foreman uses.", versioned=False,
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
      # Notify the worker to mark this hunt as terminated.
      manager = queue_manager.QueueManager(token=self.token)
      manager.MultiNotifyQueue(
          [rdf_flows.GrrNotification(session_id=session_id)
           for session_id in expired_session_ids])

    if len(new_rules) < len(rules):
      self.Set(self.Schema.RULES, new_rules)
      self.Flush()

  def _CheckIfHuntTaskWasAssigned(self, client_id, hunt_id):
    """Will return True if hunt's task was assigned to this client before."""
    for _ in aff4.FACTORY.Stat(
        [client_id.Add("flows/%s:hunt" %
                       rdfvalue.RDFURN(hunt_id).Basename())],
        token=self.token):
      return True

    return False

  def _EvaluateRules(self, objects, rule, client_id):
    """Evaluates the rules."""
    if (rule.integer_rules or rule.regex_rules) and rule.client_rule_set.rules:
      raise RuntimeError("Both new and deprecated rules are set.")

    if rule.integer_rules or rule.regex_rules:
      return self._EvaluateDeprecatedRules(objects, rule, client_id)

    return rule.client_rule_set.Evaluate(objects, client_id)

  def _EvaluateDeprecatedRules(self, objects, rule, client_id):
    """[deprecated] Evaluates the rules."""
    try:
      # Do the attribute regex first.
      for regex_rule in rule.regex_rules:
        path = client_id.Add(regex_rule.path)
        fd = objects[path]
        attribute = aff4.Attribute.NAMES[regex_rule.attribute_name]
        value = utils.SmartStr(fd.Get(attribute))
        if not regex_rule.attribute_regex.Search(value):
          return False

      # Now the integer rules.
      for integer_rule in rule.integer_rules:
        path = client_id.Add(integer_rule.path)
        fd = objects[path]
        attribute = aff4.Attribute.NAMES[integer_rule.attribute_name]
        try:
          value = int(fd.Get(attribute))
        except (ValueError, TypeError):
          # Not an integer attribute.
          return False
        op = integer_rule.operator
        if op == rdf_foreman.ForemanAttributeInteger.Operator.LESS_THAN:
          if value >= integer_rule.value:
            return False
        elif op == rdf_foreman.ForemanAttributeInteger.Operator.GREATER_THAN:
          if value <= integer_rule.value:
            return False
        elif op == rdf_foreman.ForemanAttributeInteger.Operator.EQUAL:
          if value != integer_rule.value:
            return False
        else:
          # Unknown operator.
          return False

      return True

    except KeyError:
      # The requested attribute was not found.
      return False

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
              client_id=client_id, flow_name=action.flow_name, token=token,
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
    if not rules: return 0

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

      for regex in rule.regex_rules:
        aff4_object = client_id.Add(regex.path)
        object_urns[str(aff4_object)] = aff4_object
      for int_rule in rule.integer_rules:
        aff4_object = client_id.Add(int_rule.path)
        object_urns[str(aff4_object)] = aff4_object

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
  pre = ["AFF4InitHook"]

  def Run(self):
    try:
      # Make the foreman
      with aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                               token=aff4.FACTORY.root_token):
        pass
    except access_control.UnauthorizedAccess:
      pass


class MRUCollection(aff4.AFF4Object):
  """Stores all of the MRU files from the registry."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_USED_FOLDER = aff4.Attribute(
        "aff4:mru", rdf_client.MRUFolder, "The Most Recently Used files.",
        default="")


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
        self.delegate = aff4.FACTORY.Open(delegate, mode=self.mode,
                                          token=self.token, age=self.age_policy)

  def Read(self, length):
    if "r" not in self.mode:
      raise IOError("VFSFileSymlink was not opened for reading.")
    return self.delegate.Read(length)

  def Seek(self, offset, whence):
    return self.delegate.Seek(offset, whence)

  def Tell(self):
    return self.delegate.Tell()

  def Close(self, sync):
    super(VFSFileSymlink, self).Close(sync=sync)
    if self.delegate:
      return self.delegate.Close(sync)

  def Write(self):
    raise IOError("VFSFileSymlink not writeable.")


class VFSBlobImage(aff4.BlobImage, aff4.VFSFile):
  """BlobImage with VFS attributes for use in client namespace."""

  class SchemaCls(aff4.BlobImage.SchemaCls, aff4.VFSFile.SchemaCls):
    pass


class AFF4RekallProfile(aff4.AFF4Object):
  """A Rekall profile in the AFF4 namespace."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    PROFILE = aff4.Attribute("aff4:profile", rdf_rekall_types.RekallProfile,
                             "A Rekall profile.")


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
  labels_index = aff4.FACTORY.Create(standard.LabelSet.CLIENT_LABELS_URN,
                                     "LabelSet",
                                     mode="r",
                                     token=token)
  labels = set(labels_index.ListLabels())
  if include_catchall:
    labels.add(ALL_CLIENTS_LABEL)
  return labels
