#!/usr/bin/env python
"""GRR specific AFF4 objects."""


import re
import StringIO
import time


import logging
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import scheduler
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import standard


class SpaceSeparatedStringArray(rdfvalue.RDFString):
  """A special string which stores strings as space separated."""

  def __iter__(self):
    for value in self._value.split():
      yield value


class VersionString(rdfvalue.RDFString):

  @property
  def versions(self):
    version = str(self)
    result = []
    for x in version.split("."):
      try:
        result.append(int(x))
      except ValueError:
        break

    return result


class VFSGRRClient(standard.VFSDirectory):
  """A Remote client."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    """The schema for the client."""
    client_index = rdfvalue.RDFURN("aff4:/index/client")

    CERT = aff4.Attribute("metadata:cert", rdfvalue.RDFX509Cert,
                          "The PEM encoded cert of the client.")

    FILESYSTEM = aff4.Attribute("aff4:filesystem", rdfvalue.Filesystems,
                                "Filesystems on the client.")

    CLIENT_INFO = aff4.Attribute(
        "metadata:ClientInfo", rdfvalue.ClientInformation,
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
    OS_VERSION = aff4.Attribute("metadata:os_version", VersionString,
                                "OS Version number.", "Version")

    # ARCH values come from platform.uname machine value, e.g. x86_64, AMD64.
    ARCH = aff4.Attribute("metadata:architecture", rdfvalue.RDFString,
                          "Architecture.", "Architecture")
    INSTALL_DATE = aff4.Attribute("metadata:install_date", rdfvalue.RDFDatetime,
                                  "Install Date.", "Install")

    # Deprecated for new clients - DO NOT USE.
    GRR_CONFIG = aff4.Attribute("aff4:client_config", rdfvalue.GRRConfig,
                                "Running configuration for the GRR client.")

    GRR_CONFIGURATION = aff4.Attribute(
        "aff4:client_configuration", rdfvalue.Dict,
        "Running configuration for the GRR client.", "Config")

    USER = aff4.Attribute("aff4:users", rdfvalue.Users,
                          "A user of the system.", "Users")

    USERNAMES = aff4.Attribute("aff4:user_names", SpaceSeparatedStringArray,
                               "A space separated list of system users.",
                               "Usernames",
                               index=client_index)

    # This information is duplicated from the INTERFACES attribute but is done
    # to allow for fast searching by mac address.
    MAC_ADDRESS = aff4.Attribute("aff4:mac_addresses", rdfvalue.RDFString,
                                 "A hex encoded MAC address.", "MAC",
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

  # Valid client ids
  CLIENT_ID_RE = re.compile(r"^C\.[0-9a-fA-F]{16}$")

  def Initialize(self):
    # Our URN must be a valid client.id.
    self.client_id = rdfvalue.ClientURN(self.urn)

  def Update(self, attribute=None, priority=None):
    if attribute == self.Schema.CONTAINS:
      flow_id = flow.GRRFlow.StartFlow(self.client_id, "Interrogate",
                                       token=self.token, priority=priority)

      return flow_id

  def OpenMember(self, path, mode="rw"):
    return aff4.AFF4Volume.OpenMember(self, path, mode=mode)

  AFF4_PREFIXES = {rdfvalue.PathSpec.PathType.OS: "/fs/os",
                   rdfvalue.PathSpec.PathType.TSK: "/fs/tsk",
                   rdfvalue.PathSpec.PathType.REGISTRY: "/registry",
                   rdfvalue.PathSpec.PathType.MEMORY: "/devices/memory"}

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
    client_urn = rdfvalue.ClientURN(client_urn)

    if not isinstance(pathspec, rdfvalue.RDFValue):
      raise ValueError("Pathspec should be an rdfvalue.")

    # Do not change the argument pathspec.
    pathspec = pathspec.Copy()

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
        pathspec[0].pathtype == rdfvalue.PathSpec.PathType.OS and
        pathspec[1].pathtype == rdfvalue.PathSpec.PathType.TSK):
      result = [VFSGRRClient.AFF4_PREFIXES[rdfvalue.PathSpec.PathType.TSK],
                dev]

      # Skip the top level pathspec.
      pathspec.Pop()
    else:
      # For now just map the top level prefix based on the first pathtype
      result = [VFSGRRClient.AFF4_PREFIXES[pathspec[0].pathtype]]

    for p in pathspec:
      if p.HasField("offset"):
        result.append(p.path + ":" + str(p.offset / 512))
      else:
        result.append(p.path)

    return client_urn.Add("/".join(result))


class UpdateVFSFile(flow.GRRFlow):
  """A flow to update VFS file."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="VFSFile urn",
          name="vfs_file_urn"),
      type_info.String(
          description="Attribute to update",
          name="attribute",
          default=str(aff4.AFF4Volume.SchemaCls.CONTAINS)),
      )

  def Init(self):
    self.state.Register("get_file_flow_urn")

  @flow.StateHandler()
  def Start(self):
    """Calls Update() method of a given VFSFile/VFSDirectory object.

    This method uses token with supervisor=True, because we assume that
    if the user is allowed to run flows on the client, he is priviledged
    enough to call Update on VFSFiles/VFSDirectories below this client.
    """
    self.Init()

    super_token = self.token.Copy()
    super_token.supervisor = True

    fd = aff4.FACTORY.Open(self.state.vfs_file_urn, mode="rw",
                           token=super_token)

    # Account for implicit directories.
    if fd.Get(fd.Schema.TYPE) is None:
      fd = fd.Upgrade("VFSDirectory")

    self.state.get_file_flow_urn = fd.Update(
        attribute=self.state.attribute,
        priority=rdfvalue.GrrMessage.Priority.HIGH_PRIORITY)


class VFSFile(aff4.AFF4Image):
  """A VFSFile object."""

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""
    STAT = standard.VFSDirectory.SchemaCls.STAT

    CONTENT_LOCK = aff4.Attribute(
        "aff4:content_lock", rdfvalue.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this flow.")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdfvalue.PathSpec,
        "The pathspec used to retrieve this object from the client.")

    HASH = aff4.Attribute("aff4:sha256", rdfvalue.RDFSHAValue,
                          "SHA256 hash.")

    FINGERPRINT = aff4.Attribute("aff4:fingerprint",
                                 rdfvalue.FingerprintResponse,
                                 "Protodict containing arrays of hashes.")

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
    flow_urn = flow.GRRFlow.StartFlow(client_id, "GetFile", token=self.token,
                                      pathspec=pathspec, priority=priority)
    self.Set(self.Schema.CONTENT_LOCK(flow_urn))
    self.Close()

    return flow_urn


class MemoryImage(VFSFile):
  """The server representation of the client's memory device."""

  _behaviours = frozenset(["Container"])

  class SchemaCls(VFSFile.SchemaCls):
    LAYOUT = aff4.Attribute("aff4:memory/geometry", rdfvalue.MemoryInformation,
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
    FINGERPRINT = VFSFile.SchemaCls.FINGERPRINT


class VFSAnalysisFile(VFSFile):
  """A VFS file which has no Update method."""

  def Update(self, attribute=None):
    pass


class GRRSignedBlob(aff4.AFF4MemoryStream):
  """A container for storing a signed binary blob such as a driver."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Signed blob attributes."""

    BINARY = aff4.Attribute("aff4:signed_blob", rdfvalue.SignedBlob,
                            "Signed blob proto for deployment to clients."
                            "This is used for signing drivers, binaries "
                            "and python code.")

  def Initialize(self):
    contents = ""
    if "r" in self.mode:
      contents = self.Get(self.Schema.BINARY)
      if contents:
        contents = contents.data
    self.fd = StringIO.StringIO(contents)
    self.size = rdfvalue.RDFInteger(self.fd.len)


class GRRMemoryDriver(GRRSignedBlob):
  """A driver for acquiring memory."""

  class SchemaCls(GRRSignedBlob.SchemaCls):
    INSTALLATION = aff4.Attribute(
        "aff4:driver/installation", rdfvalue.DriverInstallTemplate,
        "The driver installation control protobuf.", "installation",
        default=rdfvalue.DriverInstallTemplate(
            driver_name="pmem", device_path=r"\\.\pmem"))


class GRRForeman(aff4.AFF4Object):
  """The foreman starts flows for clients depending on rules."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Attributes specific to VFSDirectory."""
    RULES = aff4.Attribute("aff4:rules", rdfvalue.ForemanRules,
                           "The rules the foreman uses.",
                           default=rdfvalue.ForemanRules())

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
      priorities = dict()
      for session_id in expired_session_ids:
        priorities[session_id] = rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY

      scheduler.SCHEDULER.MultiNotifyQueue(list(expired_session_ids),
                                           priorities, token=self.token)

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
        if op == rdfvalue.ForemanAttributeInteger.Operator.LESS_THAN:
          if value >= integer_rule.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN:
          if value <= integer_rule.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Operator.EQUAL:
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
            flow_cls.StartClient(action.hunt_id, client_id, action.client_limit)
            actions_count += 1
        else:
          flow.GRRFlow.StartFlow(client_id, action.flow_name, token=token,
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
    client_id = rdfvalue.ClientURN(client_id)

    rules = self.Get(self.Schema.RULES)
    if not rules: return 0

    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    try:
      last_foreman_run = client.Get(client.Schema.LAST_FOREMAN_TIME) or 0
    except AttributeError:
      last_foreman_run = 0

    latest_rule = max([rule.created for rule in rules])

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
  pre = ["AFF4InitHook", "ACLInit"]

  def Run(self):
    try:
      # Make the foreman
      fd = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                               token=aff4.FACTORY.root_token)
      fd.Close()
    except access_control.UnauthorizedAccess:
      pass

# We add these attributes to all objects. This means that every object we create
# has a URN link back to the flow that created it.
aff4.AFF4Object.SchemaCls.FLOW = aff4.Attribute(
    "aff4:flow", rdfvalue.RDFURN, "A currently scheduled flow.")


class AFF4CollectionView(rdfvalue.RDFValueArray):
  """A view specifies how an AFF4Collection is seen."""


class RDFValueCollectionView(rdfvalue.RDFValueArray):
  """A view specifies how an RDFValueCollection is seen."""


class VolatilityResponse(aff4.AFF4Volume):
  _behaviours = frozenset(["Collection"])

  class SchemaCls(standard.VFSDirectory.SchemaCls):

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    RESULT = aff4.Attribute("aff4:volatility_result",
                            rdfvalue.VolatilityResult,
                            "The result returned by the flow.")


class MRUCollection(aff4.AFF4Object):
  """Stores all of the MRU files from the registry."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_USED_FOLDER = aff4.Attribute(
        "aff4:mru", rdfvalue.MRUFolder, "The Most Recently Used files.",
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


class AFF4RegexNotificationRule(aff4.AFF4NotificationRule):
  """AFF4 rule that matches path to a regex and publishes an event."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for AFF4RegexNotificationRule."""
    CLIENT_PATH_REGEX = aff4.Attribute("aff4:change_rule/client_path_regex",
                                       rdfvalue.RDFString,
                                       "Regex to match the urn.")
    EVENT_NAME = aff4.Attribute("aff4:change_rule/event_name",
                                rdfvalue.RDFString,
                                "Event to trigger on match.")
    NOTIFY_ONLY_IF_NEW = aff4.Attribute("aff4:change_rule/notify_only_if_new",
                                        rdfvalue.RDFInteger,
                                        "If True (1), then notify only when "
                                        "the file is created for the first "
                                        "time")

  def _UpdateState(self):
    regex_str = self.Get(self.Schema.CLIENT_PATH_REGEX)
    if not regex_str:
      raise IOError("Regular expression not specified for the rule.")
    self.regex = re.compile(utils.SmartStr(regex_str))

    self.event_name = self.Get(self.Schema.EVENT_NAME)
    if not self.event_name:
      raise IOError("Event name not specified for the rule.")

  def Initialize(self):
    if "r" in self.mode:
      self._UpdateState()

  def OnWriteObject(self, aff4_object):
    if not self.event_name:
      self._UpdateState()

    client_name, path = aff4_object.urn.Split(2)
    if not aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(client_name):
      return

    if self.regex.match(path):
      # TODO(user): maybe add a timestamp attribute to the rule so
      # that we get notified only for the new writes after a certain
      # timestamp?
      if (self.IsAttributeSet(self.Schema.NOTIFY_ONLY_IF_NEW) and
          self.Get(self.Schema.NOTIFY_ONLY_IF_NEW)):
        fd = aff4.FACTORY.Open(aff4_object.urn, age=aff4.ALL_TIMES,
                               token=self.token)
        stored_vals = list(fd.GetValuesForAttribute(fd.Schema.TYPE))
        if len(stored_vals) > 1:
          return

      event = rdfvalue.GrrMessage(
          name="AFF4RegexNotificationRuleMatch",
          args=aff4_object.urn.SerializeToString(),
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
          source=client_name)
      flow.PublishEvent(utils.SmartStr(self.event_name), event,
                        token=self.token)
