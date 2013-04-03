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
        "aff4:client_configuration", rdfvalue.RDFProtoDict,
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
                                 "A hex encoded MAC address.", "MAC")

    PING = aff4.Attribute("metadata:ping", rdfvalue.RDFDatetime,
                          "The last time the server heard from this client.",
                          versioned=False, default=0)

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
    # The client_id is the first element of the URN
    self.client_id = self.urn.Path().split("/")[1]

    # This object is invalid if the client_id does not conform to this scheme:
    if not self.CLIENT_ID_RE.match(self.client_id):
      raise IOError("Client id is invalid")

  def Update(self, attribute=None, priority=None):
    if attribute == self.Schema.CONTAINS:
      flow_id = flow.FACTORY.StartFlow(self.client_id, "Interrogate",
                                       token=self.token, priority=priority)

      return flow_id

  def OpenMember(self, path, mode="rw"):
    return aff4.AFF4Volume.OpenMember(self, path, mode=mode)

  # TODO(user): DEPRECATED - remove.
  def GetFlows(self, start=0, length=None, age_policy=aff4.ALL_TIMES):
    """A generator of all flows run on this client."""
    _ = age_policy

    flows = list(self.GetValuesForAttribute(self.Schema.FLOW))

    # Sort in descending order (more recent first)
    flows.sort(key=lambda x: x.age, reverse=True)

    if length is None:
      length = len(flows)

    return aff4.FACTORY.MultiOpen(flows[start:start+length],
                                  token=self.token)

  AFF4_PREFIXES = {rdfvalue.RDFPathSpec.Enum("OS"): "/fs/os",
                   rdfvalue.RDFPathSpec.Enum("TSK"): "/fs/tsk",
                   rdfvalue.RDFPathSpec.Enum("REGISTRY"): "/registry",
                   rdfvalue.RDFPathSpec.Enum("MEMORY"): "/devices/memory"}

  @staticmethod
  def PathspecToURN(pathspec, client_urn):
    """Returns a mapping between a pathspec and an AFF4 URN.

    Args:
      pathspec: The RDFPathSpec instance to convert.
      client_urn: A URN of any object within the client. We use it to find the
          client id.

    Returns:
      A urn that corresponds to this pathspec.

    Raises:
      ValueError: If pathspec is not of the correct type.
    """
    client_urn = rdfvalue.RDFURN(client_urn)
    client_id = client_urn.Path().split("/")[1]

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
    if pathspec[0].offset > 0:
      # We divide here just to get prettier numbers in the GUI
      dev += ":" + str(pathspec[0].offset / 512)

    if (len(pathspec) > 1 and
        pathspec[0].pathtype == rdfvalue.RDFPathSpec.Enum("OS") and
        pathspec[1].pathtype == rdfvalue.RDFPathSpec.Enum("TSK")):
      result = [VFSGRRClient.AFF4_PREFIXES[rdfvalue.RDFPathSpec.Enum("TSK")],
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

    result_urn = aff4.ROOT_URN.Add(client_id).Add("/".join(result))

    return result_urn


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
        "aff4:pathspec", rdfvalue.RDFPathSpec,
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
        if flow_obj.Get(flow_obj.Schema.FLOW_PB):
          rdf_flow = rdfvalue.Flow(flow_obj.Get(flow_obj.Schema.FLOW_PB).value)
        else:
          rdf_flow = flow_obj.Get(flow_obj.Schema.RDF_FLOW).payload
        if rdf_flow.state == rdf_flow.RUNNING:
          return

    # The client_id is the first element of the URN
    client_id = self.urn.Path().split("/", 2)[1]

    # Get the pathspec for this object
    pathspec = self.Get(self.Schema.STAT).pathspec
    flow_urn = flow.FACTORY.StartFlow(client_id, "GetFile", token=self.token,
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

  # Support both sets of attributes.
  class SchemaCls(VFSFile.SchemaCls, aff4.AFF4MemoryStream.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""


class VFSAnalysisFile(VFSFile):
  """A VFS file which has no Update method."""

  def Update(self, attribute=None):
    pass


class GRRFlow(aff4.AFF4Volume):
  """A container aff4 object to maintain a flow.

  Flow objects are executed and scheduled by the workers, and extend
  grr.flow.GRRFlow. This object contains the flows object within an AFF4
  container.

  Note: Usually this object can not be created by the regular
  aff4.FACTORY.Create() method since it required elevated permissions. This
  object can instead be created using the flow.FACTORY.StartFlow() method.

  After creation, read access to the flow object can still be obtained through
  the usual aff4.FACTORY.Open() method.
  """

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to VFSDirectory."""

    FLOW_PB = aff4.Attribute(
        "task:00000001", rdfvalue.Task,
        "DEPRECATED, use RDF_FLOW instead.",
        "Flow", versioned=False)

    RDF_FLOW = aff4.Attribute("task:flow", rdfvalue.GRRMessage,
                              "The GRRMessage object containing the Flow.",
                              "RDFFlow", versioned=False)

    LOG = aff4.Attribute("aff4:log", rdfvalue.RDFString,
                         "Log messages related to the progress of this flow.")

    NOTIFICATION = aff4.Attribute("aff4:notification", rdfvalue.Notification,
                                  "Notifications for the flow.")

    CLIENT_CRASH = aff4.Attribute("aff4:client_crash", rdfvalue.ClientCrash,
                                  "Client crash details in case of a crash.",
                                  default=None)

  create_time = 0
  rdf_flow = None

  def Initialize(self):
    """The initialization method."""
    if "r" in self.mode:
      try:
        self.flow_obj = self.GetFlowObj()
      except flow.FlowError as e:
        raise IOError(e)
      if self.flow_obj:
        self.rdf_flow = self.flow_obj.rdf_flow
        self.create_time = self.rdf_flow.create_time
    else:
      self.flow_obj = None

    self.session_id = self.urn

  def GetRDFFlow(self):
    task = self.Get(self.Schema.FLOW_PB)
    if task:
      result = rdfvalue.Flow(task.value)
      result.aff4_object = self
      return result
    else:
      msg = self.Get(self.Schema.RDF_FLOW)
      if msg:
        result = msg.payload
        result.aff4_object = self
        return result

  def GetFlowObj(self, forced_token=None):
    # This does not lock the flow - only read only.
    return flow.FACTORY.LoadFlow(self.GetRDFFlow(), forced_token=forced_token)

  def SetFlowObj(self, flow_obj):
    """Sets the flow state attribute."""
    self.flow_obj = flow_obj

  def Close(self, sync=True):
    """Flushes the flow and all its requests to the data_store."""
    flow_manager = None
    if self.flow_obj:
      self.urn = rdfvalue.RDFURN(self.flow_obj.session_id)
      # If its a parent flow manager, we skip flushing here.
      if self.flow_obj.context.parent_context is None:
        flow_manager = self.flow_obj.context.flow_manager

      task = self.Schema.RDF_FLOW(payload=rdfvalue.Flow(self.flow_obj.Dump()))
      self.Set(task)

    super(GRRFlow, self).Close(sync=sync)

    # Now that the flow is written we can also schedule all the requests.
    # If we have a parent flow manager though, we skip flushing here.
    if flow_manager:
      flow_manager.Flush()


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
    for rule in rules:
      if rule.expires > now:
        new_rules.Append(rule)
      else:
        for action in rule.actions:
          if action.hunt_id:
            # Notify the worker to mark this hunt as terminated.
            scheduler.SCHEDULER.NotifyQueue("W", action.hunt_id,
                                            token=self.token)

    self.Set(self.Schema.RULES, new_rules)

  def _CheckIfHuntTaskWasAssigned(self, client_id, hunt_id):
    """Will return True if hunt's task was assigned to this client before."""
    for _ in aff4.FACTORY.Stat(
        ["aff4:/%s/flows/%s:hunt" % (client_id,
                                     rdfvalue.RDFURN(hunt_id).Basename())],
        token=self.token):
      return True

    return False

  def _EvaluateRules(self, objects, rule, client_id):
    """Evaluates the rules."""
    try:
      # Do the attribute regex first.
      for regex_rule in rule.regex_rules:
        path = aff4.ROOT_URN.Add(client_id).Add(regex_rule.path)
        fd = objects[path]
        attribute = aff4.Attribute.NAMES[regex_rule.attribute_name]
        value = utils.SmartStr(fd.Get(attribute))
        if not re.search(regex_rule.attribute_regex, value, flags=re.S):
          return False

      # Now the integer rules.
      for integer_rule in rule.integer_rules:
        path = aff4.ROOT_URN.Add(client_id).Add(integer_rule.path)
        fd = objects[path]
        attribute = aff4.Attribute.NAMES[integer_rule.attribute_name]
        try:
          value = int(fd.Get(attribute))
        except (ValueError, TypeError):
          # Not an integer attribute.
          return False
        op = integer_rule.operator
        if op == rdfvalue.ForemanAttributeInteger.Enum("LESS_THAN"):
          if not value < integer_rule.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Enum("GREATER_THAN"):
          if not value > integer_rule.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Enum("EQUAL"):
          if not value == integer_rule.value:
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

        if action.hunt_id:
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
          flow.FACTORY.StartFlow(client_id, action.flow_name, token=token,
                                 **action.argv.ToDict())
          actions_count += 1
      # There could be all kinds of errors we don't know about when starting the
      # flow/hunt so we catch everything here.
      except Exception as e:  # pylint: disable=W0703
        logging.error("Failure running foreman action on client %s: %s",
                      action.hunt_id, e)

    return actions_count

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client.

    Args:
      client_id: Client id of the client for tasks to be assigned.

    Returns:
      Number of assigned tasks.
    """
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
        aff4_object = aff4.ROOT_URN.Add(client_id).Add(regex.path)
        object_urns[str(aff4_object)] = aff4_object
      for int_rule in rule.integer_rules:
        aff4_object = aff4.ROOT_URN.Add(client_id).Add(int_rule.path)
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


class GrepResultList(rdfvalue.RDFValueArray):
  """This wraps the BufferReadMessage pb."""
  rdf_type = rdfvalue.BufferReference


class GrepResults(aff4.AFF4Volume):
  """A collection of grep results."""

  _behaviours = frozenset(["Collection"])

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    HITS = aff4.Attribute(
        "aff4:grep_hits", GrepResultList,
        "A list of BufferReadMessages.", "hits",
        default="")


class VolatilityResponse(aff4.AFF4Volume):
  _behaviours = frozenset(["Collection"])

  class SchemaCls(standard.VFSDirectory.SchemaCls):

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    RESULT = aff4.Attribute("aff4:volatility_result",
                            rdfvalue.VolatilityResult,
                            "The result returned by the flow.")


class VFSHunt(GRRFlow):
  """The aff4 object for hunting."""

  STATE_STARTED = "started"
  STATE_STOPPED = "stopped"

  class SchemaCls(GRRFlow.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.  See lib/flow.py
    for the GRRHunt implementation which does the Hunt processing.
    """

    HUNT_NAME = aff4.Attribute("aff4:hunt_name", rdfvalue.RDFString,
                               "Name of this hunt.")

    EXPIRY_TIME = aff4.Attribute("aff4:hunt_expiry_time",
                                 rdfvalue.Duration,
                                 "Expiry time for the hunt.")

    CLIENT_LIMIT = aff4.Attribute("aff4:hunt_client_limit", rdfvalue.RDFInteger,
                                  "Client number limit for the hunt.")

    STATE = aff4.Attribute("aff4:hunt_state", rdfvalue.RDFString,
                           "State of this hunt.")

    DESCRIPTION = aff4.Attribute("aff4:hunt_description", rdfvalue.RDFString,
                                 "Description of this hunt.")

    CREATOR = aff4.Attribute("aff4:creator_name", rdfvalue.RDFString,
                             "Creator of this hunt.")

    CLIENTS = aff4.Attribute("aff4:clients", rdfvalue.RDFURN,
                             "The list of clients this hunt was run against.")

    FINISHED = aff4.Attribute("aff4:finished", rdfvalue.RDFURN,
                              "The list of clients the hunt has completed on.")

    BADNESS = aff4.Attribute("aff4:badness", rdfvalue.RDFURN,
                             ("A list of clients this hunt has found something "
                              "worth investigating on."))

    ERRORS = aff4.Attribute("aff4:errors", rdfvalue.HuntError,
                            "The list of clients that returned an error.")

    LOG = aff4.Attribute("aff4:result_log", rdfvalue.HuntLog,
                         "The log entries.")

    RESOURCES = aff4.Attribute("aff4:client_resources",
                               rdfvalue.ClientResources,
                               "The client resource usage for subflows.")

  def _Num(self, attribute):
    return len(set(self.GetValuesForAttribute(attribute)))

  def NumClients(self):
    return self._Num(self.Schema.CLIENTS)

  def NumCompleted(self):
    return self._Num(self.Schema.FINISHED)

  def NumOutstanding(self):
    return self.NumClients() - self.NumCompleted()

  def NumResults(self):
    return self._Num(self.Schema.BADNESS)

  def _List(self, attribute):
    items = self.GetValuesForAttribute(attribute)
    if items:
      print len(items), "items:"
      for item in items:
        print item
    else:
      print "Nothing found."

  def ListClients(self):
    self._List(self.Schema.CLIENTS)

  def GetBadClients(self):
    return sorted(self.GetValuesForAttribute(self.Schema.BADNESS))

  def GetCompletedClients(self):
    return sorted(self.GetValuesForAttribute(self.Schema.FINISHED))

  def ListCompletedClients(self):
    self._List(self.Schema.FINISHED)

  def GetOutstandingClients(self):
    started = self.GetValuesForAttribute(self.Schema.CLIENTS)
    done = self.GetValuesForAttribute(self.Schema.FINISHED)
    return sorted(list(set(started) - set(done)))

  def ListOutstandingClients(self):
    outstanding = self.GetOutstandingClients()
    if not outstanding:
      print "No outstanding clients."
      return

    print len(outstanding), "outstanding clients:"
    for client in outstanding:
      print client

  def GetClientsByStatus(self):
    """Get all the clients in a dict of {status: [client_list]}."""
    completed = set(self.GetCompletedClients())
    bad = set(self.GetBadClients())
    completed -= bad

    return {"COMPLETED": sorted(completed),
            "OUTSTANDING": self.GetOutstandingClients(),
            "BAD": sorted(bad)}

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in utils.Grouper(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(client_group, mode="r",
                                       required_type="VFSGRRClient",
                                       token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.PING)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def PrintLog(self, client_id=None):
    if not client_id:
      self._List(self.Schema.LOG)
      return

    for log in self.GetValuesForAttribute(self.Schema.LOG):
      if log.client_id == client_id:
        print log

  def PrintErrors(self, client_id=None):
    if not client_id:
      self._List(self.Schema.ERRORS)
      return

    for error in self.GetValuesForAttribute(self.Schema.ERRORS):
      if error.client_id == client_id:
        print error

  def GetResourceUsage(self, client_id=None, group_by_client=True):
    """Returns the cpu resource usage for subflows."""
    usages = {}
    for usage in self.GetValuesForAttribute(self.Schema.RESOURCES):
      if client_id and usage.client_id != client_id:
        continue

      if usage.client_id not in usages:
        usages[usage.client_id] = {
            usage.session_id: (usage.cpu_usage.user_cpu_time,
                               usage.cpu_usage.system_cpu_time)}
      else:
        client_usage = usages[usage.client_id]
        (user_cpu, sys_cpu) = client_usage.setdefault(usage.session_id,
                                                      (0.0, 0.0))
        client_usage[usage.session_id] = (
            user_cpu + usage.cpu_usage.user_cpu_time,
            sys_cpu + usage.cpu_usage.system_cpu_time)

    if group_by_client:
      grouped = {}
      for (client_id, usage) in usages.items():
        total_user, total_sys = 0.0, 0.0
        for (_, (user_cpu, sys_cpu)) in usage.items():
          total_user += user_cpu
          total_sys += sys_cpu
        grouped[client_id] = (total_user, total_sys)
      return grouped
    else:
      return usages


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

      event = rdfvalue.GRRMessage(
          name="AFF4RegexNotificationRuleMatch",
          args=aff4_object.urn.SerializeToString(),
          auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
          source=client_name)
      flow.PublishEvent(utils.SmartStr(self.event_name), event,
                        token=self.token)
