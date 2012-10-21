#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""GRR specific AFF4 objects."""


import re
import StringIO
import time


from M2Crypto import X509

import logging
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import registry
from grr.lib import scheduler
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


# These are objects we store as attributes of the client.
class FileSystem(aff4.RDFProtoArray):
  """An RDFValue class representing one of the filesystems."""
  _proto = sysinfo_pb2.Filesystem


class User(aff4.RDFProtoArray):
  """An RDFValue class representing a list of users account."""
  _proto = jobs_pb2.UserAccount


class GRRConfig(aff4.RDFProto):
  """An RDFValue class representing the configuration of a GRR Client."""
  _proto = jobs_pb2.GRRConfig


class RDFX509Cert(aff4.RDFString):
  """An RDFValue for X509 certificates."""

  def _GetCN(self, x509cert):
    subject = x509cert.get_subject()
    try:
      cn_id = subject.nid["CN"]
      cn = subject.get_entries_by_nid(cn_id)[0]
    except IndexError:
      raise IOError("Cert has no CN")

    self.common_name = cn.get_data().as_text()

  def GetX509Cert(self):
    return X509.load_cert_string(str(self))

  def GetPubKey(self):
    return self.GetX509Cert().get_pubkey().get_rsa()

  def ParseFromString(self, string):
    super(RDFX509Cert, self).ParseFromString(string)
    try:
      self._GetCN(self.GetX509Cert())
    except X509.X509Error:
      raise IOError("Cert invalid")

  def AsProto(self):
    """Return the certificate encoded as a Certificate protobuf."""
    return jobs_pb2.Certificate(pem=str(self),
                                cn=self.common_name,
                                type=jobs_pb2.Certificate.CRT)


class Flow(aff4.RDFProto):
  """A Flow protobuf."""
  _proto = jobs_pb2.Task

  rdf_map = dict(create_time=aff4.RDFDatetime,
                 args=aff4.RDFProtoDict)

  def ParseFromString(self, string):
    task = scheduler.TaskScheduler.Task(decoder=jobs_pb2.FlowPB)
    task.ParseFromString(string)
    self.data = task.value

  def SerializeToString(self):
    # We do not allow flows to be manipulated through the AFF4 subsystem.
    raise RuntimeError("Flow attributes are read only.")


class ClientInfo(aff4.RDFProto):
  """The GRR client info pb."""
  _proto = jobs_pb2.ClientInformation


class VersionString(aff4.RDFString):

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


class GRRMessage(aff4.RDFProto):
  """An RDFValue for GRR messages."""
  _proto = jobs_pb2.GrrMessage


class TaskSchedulerTask(aff4.RDFProto):
  """An RDFValue for Task scheduler tasks."""
  _proto = jobs_pb2.Task


class VFSGRRClient(standard.VFSDirectory):
  """A Remote client."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    """The schema for the client."""
    client_index = aff4.RDFURN("aff4:/index/client")

    CERT = aff4.Attribute("metadata:cert", RDFX509Cert,
                          "The PEM encoded cert of the client.")

    FILESYSTEM = aff4.Attribute("aff4:filesystem", FileSystem,
                                "Filesystems on the client.")

    CLIENT_INFO = aff4.Attribute("metadata:ClientInfo", ClientInfo,
                                 "GRR client information", "GRR client")

    # Information about the host.
    HOSTNAME = aff4.Attribute("metadata:hostname", aff4.RDFString,
                              "Hostname of the host.", "Host",
                              index=client_index)
    SYSTEM = aff4.Attribute("metadata:system", aff4.RDFString,
                            "Operating System class.", "System")
    UNAME = aff4.Attribute("metadata:uname", aff4.RDFString,
                           "Uname string.", "Uname")
    OS_RELEASE = aff4.Attribute("metadata:os_release", aff4.RDFString,
                                "OS Major release number.", "Release")
    OS_VERSION = aff4.Attribute("metadata:os_version", VersionString,
                                "OS Version number.", "Version")
    ARCH = aff4.Attribute("metadata:architecture", aff4.RDFString,
                          "Architecture.", "Architecture")
    INSTALL_DATE = aff4.Attribute("metadata:install_date", aff4.RDFDatetime,
                                  "Install Date.", "Install")
    GRR_CONFIG = aff4.Attribute("aff4:client_config", GRRConfig,
                                "Running configuration for the GRR client.",
                                "Config")

    USER = aff4.Attribute("aff4:users", User,
                          "A user of the system.", "Users")

    USERNAMES = aff4.Attribute("aff4:user_names", aff4.RDFString,
                               "A space separated list of system users.",
                               "Usernames",
                               index=client_index)

    # This information is duplicated from the INTERFACES attribute but is done
    # to allow for fast searching by mac address.
    MAC_ADDRESS = aff4.Attribute("aff4:mac_addresses", aff4.RDFString,
                                 "A hex encoded MAC address.", "MAC")

    PING = aff4.Attribute("metadata:ping", aff4.RDFDatetime,
                          "The last time the server heard from this client.",
                          versioned=False, default=0)

    CLOCK = aff4.Attribute("metadata:clock", aff4.RDFDatetime,
                           "The last clock read on the client "
                           "(Can be used to estimate client clock skew).",
                           "Clock", versioned=False)

    CLIENT_IP = aff4.Attribute("metadata:client_ip", aff4.RDFString,
                               "The ip address this client connected from.",
                               "Client_ip", versioned=False)

    # This is the last foreman rule that applied to us
    LAST_FOREMAN_TIME = aff4.Attribute(
        "aff4:last_foreman_time", aff4.RDFDatetime,
        "The last time the foreman checked us.", versioned=False)

  # Valid client ids
  CLIENT_ID_RE = re.compile(r"^C\.[0-9a-fA-F]{16}$")

  def Initialize(self):
    # The client_id is the first element of the URN
    self.client_id = self.urn.Path().split("/")[1]

    # This object is invalid if the client_id does not conform to this scheme:
    if not self.CLIENT_ID_RE.match(self.client_id):
      raise IOError("Client id is invalid")

  def Update(self, attribute=None):
    if attribute == self.Schema.CONTAINS:
      flow_id = flow.FACTORY.StartFlow(self.client_id, "Interrogate",
                                       token=self.token)

      return flow_id

  def OpenMember(self, path, mode="rw"):
    return aff4.AFF4Volume.OpenMember(self, path, mode=mode)

  def GetFlows(self, start=0, length=None, age_policy=aff4.ALL_TIMES):
    """A generator of all flows run on this client."""
    flows = list(self.GetValuesForAttribute(self.Schema.FLOW))

    # Sort in descending order (more recent first)
    flows.sort(key=lambda x: x.age, reverse=True)

    if length is None:
      length = len(flows)

    flow_root = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN, age=age_policy,
                                  token=self.token)
    return flow_root.OpenChildren(flows[start:start+length])

  AFF4_PREFIXES = {jobs_pb2.Path.OS: "/fs/os",
                   jobs_pb2.Path.TSK: "/fs/tsk",
                   jobs_pb2.Path.REGISTRY: "/registry",
                   jobs_pb2.Path.MEMORY: "/devices/memory"}

  @staticmethod
  def PathspecToURN(pathspec, client_urn):
    """Returns a mapping between a pathspec and an AFF4 URN.

    Args:
      pathspec: The pathspec to convert.
      client_urn: A URN of any object within the client. We use it to find the
          client id.

    Returns:
      A urn that corresponds to this pathspec.
    """
    client_urn = aff4.RDFURN(client_urn)
    client_id = client_urn.Path().split("/")[1]

    pathspec = utils.Pathspec(pathspec)

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

    if (len(pathspec) > 1 and pathspec[0].pathtype == jobs_pb2.Path.OS and
        pathspec[1].pathtype == jobs_pb2.Path.TSK):
      result = [VFSGRRClient.AFF4_PREFIXES[jobs_pb2.Path.TSK], dev]
      pathspec.Pop(0)
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
        "aff4:content_lock", aff4.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this flow.")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", standard.RDFPathSpec,
        "The pathspec used to retrieve this object from the client.")

    HASH = aff4.Attribute("aff4:sha256", aff4.RDFSHAValue,
                          "SHA256 hash.")

    FINGERPRINT = aff4.Attribute("aff4:fingerprint", aff4.RDFFingerprintValue,
                                 "Protodict containing arrays of hashes.")

  def Update(self, attribute=None):
    """Update an attribute from the client."""
    if attribute == self.Schema.CONTENT:
      # List the directory on the client
      currently_running = self.Get(self.Schema.CONTENT_LOCK)

      # Is this flow still active?
      if currently_running:
        flow_obj = aff4.FACTORY.Open(currently_running, token=self.token)
        flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB)
        if flow_pb.data.state == jobs_pb2.FlowPB.RUNNING:
          return

    # The client_id is the first element of the URN
    client_id = self.urn.Path().split("/", 2)[1]

    # Get the pathspec for this object
    pathspec = self.Get(self.Schema.STAT).data.pathspec
    session_id = flow.FACTORY.StartFlow(client_id, "GetFile", token=self.token,
                                        pathspec=pathspec)

    flow_urn = aff4.FLOW_SWITCH_URN.Add(session_id)
    self.Set(self.Schema.CONTENT_LOCK, flow_urn)
    self.Flush()

    return flow_urn


class MemoryGeometry(aff4.RDFProto):
  """The GRR client info pb."""
  _proto = jobs_pb2.MemoryInfomation


class MemoryImage(VFSFile):
  """The server representation of the client's memory device."""

  _behaviours = frozenset(["Container"])

  class SchemaCls(VFSFile.SchemaCls):
    LAYOUT = aff4.Attribute("aff4:memory/geometry", MemoryGeometry,
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


class Notification(aff4.RDFProto):

  _proto = jobs_pb2.Notification

  rdf_map = dict(timestamp=aff4.RDFDatetime,
                 subject=aff4.RDFURN)


class GRRFlow(aff4.AFF4Object):
  """An object virtualizing flow to a client."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Attributes specific to VFSDirectory."""

    FLOW_PB = aff4.Attribute("task:00000001", Flow,
                             "The Flow protobuf.", "Flow")

    LOG = aff4.Attribute("aff4:log", aff4.RDFString,
                         "Log messages related to the progress of this flow.")

    NOTIFICATION = aff4.Attribute("aff4:notification", Notification,
                                  "Notifications for the flow.")

  def Initialize(self):
    # Our session_id is the last path element.
    self.session_id = str(self.urn).split("/")[-1]
    self.urn = self.parent.urn.Add(self.session_id)
    self.flow_pb = self.Get(self.Schema.FLOW_PB)
    if self.flow_pb is None:
      raise IOError("Flow %s not found" % self.session_id)

  def GetFlowObj(self):
    # This does not lock the flow - only read only.
    flow_pb = self.flow_pb
    if flow_pb:
      return flow.FACTORY.LoadFlow(flow_pb.data)


class SignedBlob(aff4.RDFProto):
  """RDFValue representing a signed blob (e.g. driver binary)."""
  _proto = jobs_pb2.SignedBlob


class GRRSignedBlob(aff4.AFF4MemoryStream):
  """A container for storing a signed binary blob such as a driver."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Signed blob attributes."""

    BINARY = aff4.Attribute("aff4:signed_blob", SignedBlob,
                            "Signed blob proto for deployment to clients."
                            "This is used for signing drivers, binaries "
                            "and python code.")

  def Initialize(self):
    contents = ""
    if "r" in self.mode:
      contents = self.Get(self.Schema.BINARY)
      if contents:
        contents = contents.data.SerializeToString()
    self.fd = StringIO.StringIO(contents)
    self.size = aff4.RDFInteger(self.fd.len)


class DriverInstallTemplate(aff4.RDFProto):
  """A driver specific protobuf to control default installation."""
  _proto = jobs_pb2.InstallDriverRequest


class GRRMemoryDriver(GRRSignedBlob):
  """A driver for acquiring memory."""

  class SchemaCls(GRRSignedBlob.SchemaCls):
    INSTALLATION = aff4.Attribute(
        "aff4:driver/installation", DriverInstallTemplate,
        "The driver installation control protobuf.", "installation",
        default=jobs_pb2.InstallDriverRequest(
            driver_name="pmem", device_path=r"\\.\pmem"))


class GRRFlowSwitch(aff4.AFF4Volume):
  """A VFS Container for flows.

  The idea here is to present a virtual view of flows so they can be dealt with
  using the AFF4 subsystem. This way we can place references to flows at various
  places.
  """

  def ListChildren(self):
    """There are usually too many flows to make sense listing."""
    return {}, 0

  def OpenMember(self, child, mode="r"):
    # Allow the child to be specified as a full URN relative to us.
    child = aff4.RDFURN(child).RelativeName(self.urn) or child
    for result in self.OpenChildren([child], mode=mode):
      return result

    raise IOError("Flow %s not found" % child)

  def OpenChildren(self, children=None, mode="r"):
    """Efficiently return a bunch of flows at once."""
    if not children: return

    flow_names = []
    for child in children:
      session_id = child
      if isinstance(child, aff4.RDFURN):
        session_id = child.RelativeName(self.urn)

      if session_id and "/" not in session_id:
        flow_names.append(scheduler.TaskScheduler.QueueToSubject(session_id))

    results = {}
    for child, attributes in aff4.FACTORY.GetAttributes(
        flow_names, token=self.token, age=self.age_policy):
      try:
        result = GRRFlow(aff4.RDFURN(child), mode, clone={}, parent=self,
                         token=self.token, age=self.age_policy)
        # Decode the attributes for the new object from existing data
        for attribute, value, ts in attributes:
          result.DecodeValueFromAttribute(attribute, value, ts)

        result.Initialize()
        results[child] = result
      except IOError:
        pass

    # Order the results in the same order they were requested.
    for f in flow_names:
      if f in results:
        yield results[f]


class GRRHuntSwitch(GRRFlowSwitch):

  def OpenChildren(self, children=None, mode="r"):
    for child in super(GRRHuntSwitch, self).OpenChildren(children=children,
                                                         mode=mode):
      if isinstance(child.GetFlowObj(), flow.GRRHunt):
        yield child


class ForemanRules(aff4.RDFProtoArray):
  """A list of rules that the foreman will apply."""
  _proto = jobs_pb2.ForemanRule


class GRRForeman(aff4.AFF4Object):
  """The foreman starts flows for clients depending on rules."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Attributes specific to VFSDirectory."""
    RULES = aff4.Attribute("aff4:rules", ForemanRules,
                           "The rules the foreman uses.")

  def ExpireRules(self):
    rules = self.Get(self.Schema.RULES)
    new_rules = self.Schema.RULES()
    now = time.time() * 1e6
    for rule in rules:
      if rule.expires > now:
        new_rules.Append(rule)

    self.Set(self.Schema.RULES, new_rules)

  def _EvaluateRules(self, objects, rule, client_id):
    """Evaluates the rules."""
    try:
      # Do the attribute regex first.
      for regex_rule in rule.regex_rules:
        path = aff4.ROOT_URN.Add(client_id).Add(regex_rule.path)
        fd = objects[path]
        attribute = aff4.Attribute.NAMES[regex_rule.attribute_name]
        value = utils.SmartStr(fd.Get(attribute))
        if not re.search(regex_rule.attribute_regex, value, re.S):
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
        if op == jobs_pb2.ForemanAttributeInteger.LESS_THAN:
          if not value < integer_rule.value:
            return False
        elif op == jobs_pb2.ForemanAttributeInteger.GREATER_THAN:
          if not value > integer_rule.value:
            return False
        elif op == jobs_pb2.ForemanAttributeInteger.EQUAL:
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
    """Run all the actions specified in the rule."""
    for action in rule.actions:
      try:
        # Say this flow came from the foreman.
        token = self.token.Copy()
        token.username = "Foreman"

        if action.hunt_id:
          logging.info("Foreman: Starting hunt %s on client %s.",
                       action.hunt_id, client_id)
          flow_cls = flow.GRRFlow.classes[action.hunt_name]
          flow_cls.StartClient(action.hunt_id, client_id, action.client_limit)
        else:
          flow.FACTORY.StartFlow(client_id, action.flow_name, token=token,
                                 **utils.ProtoDict(action.argv).ToDict())
      # There could be all kinds of errors we don't know about when starting the
      # flow/hunt so we catch everything here.
      except Exception:  # pylint: disable=W0703
        pass

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client."""
    rules = self.Get(self.Schema.RULES)
    if not rules: return

    client = aff4.FACTORY.Open(client_id, mode="rw", token=self.token)
    try:
      last_foreman_run = client.Get(client.Schema.LAST_FOREMAN_TIME) or 0
    except AttributeError:
      last_foreman_run = 0

    # For efficiency we collect all the objects we want to open first and then
    # open them all in one round trip.
    object_urns = {}
    relevant_rules = []
    latest_rule = 0
    expired_rules = False

    now = time.time() * 1e6
    for rule in rules:
      # What is the latest created rule?
      latest_rule = max(latest_rule, rule.created)

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

    for rule in relevant_rules:
      if self._EvaluateRules(objects, rule, client_id):
        self._RunActions(rule, client_id)

    # Update the latest checked rule on the client.
    if latest_rule > int(last_foreman_run):
      client.Set(client.Schema.LAST_FOREMAN_TIME(latest_rule))
      client.Flush()

    if expired_rules:
      self.ExpireRules()


class GRRAFF4Init(registry.InitHook):
  """Ensure critical AFF4 objects exist for GRR."""

  # Must run after the AFF4 subsystem is ready.
  pre = ["AFF4InitHook"]

  def Run(self):
    fd = aff4.FACTORY.Create(aff4.FLOW_SWITCH_URN, "GRRFlowSwitch",
                             token=aff4.FACTORY.root_token)
    fd.Close()

    try:
      # Make the foreman
      fd = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                               token=aff4.FACTORY.root_token)
      fd.Close()
    except data_store.UnauthorizedAccess:
      pass

# We add these attributes to all objects. This means that every object we create
# has a URN link back to the flow that created it.
aff4.AFF4Object.SchemaCls.FLOW = aff4.Attribute(
    "aff4:flow", aff4.RDFURN, "A currently scheduled flow.")


class BlobArray(aff4.RDFProtoArray):
  """An array of blobs."""
  _proto = jobs_pb2.DataBlob

  def Add(self, **kwargs):
    """Add another member to this array."""
    self.Append(jobs_pb2.DataBlob(**kwargs))


class View(BlobArray):
  """A view specifies how a collection is seen."""


class CollectionList(aff4.RDFProtoArray):
  """This wraps the Collection pb."""
  _proto = jobs_pb2.StatResponse


class AFF4Collection(aff4.AFF4Volume):
  """A collection of objects."""

  _behaviours = frozenset(["Collection"])

  def CreateView(self, attributes):
    """Given a list of attributes, update our view."""
    result = View()

    for attribute in attributes:
      result.Append(jobs_pb2.DataBlob(string=str(attribute)))

    self.Set(self.Schema.VIEW, result)

  def Query(self, filter_string="", filter_obj=None, subjects=None, limit=100):
    """Filter the objects contained within this collection."""
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = aff4.AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.filter)

    subjects = set([
        aff4.RDFURN(x.aff4path) for x in self.Get(self.Schema.COLLECTION)])
    if not subjects:
      return []
    result = []
    for match in data_store.DB.Query([], filter_obj, subjects=subjects,
                                     limit=limit, token=self.token):
      result.append(match["subject"][0])

    return self.OpenChildren(result)

  def OpenChildren(self, children=None, mode="r"):
    if children is None:
      children = set([
          aff4.RDFURN(x.aff4path) for x in self.Get(self.Schema.COLLECTION)])

    return super(AFF4Collection, self).OpenChildren(children, mode=mode)

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")

    COLLECTION = aff4.Attribute(
        "aff4:directory_listing", CollectionList,
        "A list of StatResponses.", "collection_list",
        default="")

    VIEW = aff4.Attribute("aff4:view", View,
                          "The list of attributes which will show up in "
                          "the table.", default="")


class GrepResultList(aff4.RDFProtoArray):
  """This wraps the BufferReadMessage pb."""
  _proto = jobs_pb2.BufferReadMessage


class GrepResults(aff4.AFF4Volume):
  """A collection of grep results."""

  _behaviours = frozenset(["Collection"])

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")

    HITS = aff4.Attribute(
        "aff4:grep_hits", GrepResultList,
        "A list of BufferReadMessages.", "hits",
        default="")


class VolatilityResult(aff4.RDFProto):
  _proto = jobs_pb2.VolatilityResponse


class VolatilityResponse(aff4.AFF4Volume):
  _behaviours = frozenset(["Collection"])

  class SchemaCls(standard.VFSDirectory.SchemaCls):

    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")
    RESULT = aff4.Attribute("aff4:volatility_result",
                            VolatilityResult,
                            "The result returned by the flow.")


class HuntError(aff4.RDFProto):
  """An RDFValue class representing a hunt error."""
  _proto = jobs_pb2.HuntError


class HuntLog(aff4.RDFProto):
  """An RDFValue class representing the hunt log entries."""
  _proto = jobs_pb2.HuntLog


class ClientResources(aff4.RDFProto):
  """An RDFValue class representing the client resource usage."""
  _proto = jobs_pb2.ClientResources


class VFSHunt(aff4.AFF4Object):
  """The aff4 object for hunting."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.  See lib/flow.py
    for the GRRHunt implementation which does the Hunt processing.
    """

    HUNT_NAME = aff4.Attribute("aff4:hunt_name", aff4.RDFString,
                               "Name of this hunt.")

    CREATOR = aff4.Attribute("aff4:creator_name", aff4.RDFString,
                             "Creator of this hunt.")

    CLIENTS = aff4.Attribute("aff4:clients", aff4.RDFURN,
                             "The list of clients this hunt was run against.")

    FINISHED = aff4.Attribute("aff4:finished", aff4.RDFURN,
                              "The list of clients the hunt has completed on.")

    BADNESS = aff4.Attribute("aff4:badness", aff4.RDFURN,
                             ("A list of clients this hunt has found something "
                              "worth investigating on."))

    ERRORS = aff4.Attribute("aff4:errors", HuntError,
                            "The list of clients that returned an error.")

    LOG = aff4.Attribute("aff4:result_log", HuntLog,
                         "The log entries.")

    RESOURCES = aff4.Attribute("aff4:client_resources", ClientResources,
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

  def GetFlowObj(self):
    """Get the object representing the flow."""
    return flow.FACTORY.GetFlowObj(self.urn.Basename(), token=self.token)

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
    outstanding = self.GetOutstanding()
    if not outstanding:
      print "No outstanding clients."
      return

    print len(outstanding), "outstanding clients:"
    for client in outstanding:
      print client

  def GetClientsByStatus(self):
    """Get all the clients in a dict of {status: [client_list]}."""
    return {"COMPLETED": self.GetCompletedClients(),
            "OUTSTANDING": self.GetOutstandingClients(),
            "BAD": self.GetBadClients()}

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in utils.Grouper(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(client_group, mode="r",
                                       required_type="VFSGRRClient",
                                       token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.CLOCK)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def PrintLog(self, client_id=None):
    if not client_id:
      self._List(self.Schema.LOG)
      return

    for log in self.GetValuesForAttribute(self.Schema.LOG):
      if log.data.client_id == client_id:
        print log

  def PrintErrors(self, client_id=None):
    if not client_id:
      self._List(self.Schema.ERRORS)
      return

    for error in self.GetValuesForAttribute(self.Schema.ERRORS):
      if error.data.client_id == client_id:
        print error

  def GetResourceUsage(self, client_id=None, group_by_client=True):
    """Returns the cpu resource usage for subflows."""
    usages = {}
    for usage_ in self.GetValuesForAttribute(self.Schema.RESOURCES):
      usage = usage_.data
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


# Start of the Registry Specific Data types
class RunKeyEntry(aff4.RDFProtoArray):
  """Structure of a Run Key entry with keyname, filepath, and last written."""
  _proto = sysinfo_pb2.RunKey


class RunKeyCollection(AFF4Collection):
  """Collection of RunKeys."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    RUNKEYS = aff4.Attribute("aff4:runkey", RunKeyEntry, "Run Keys", default="")


class MRUFolder(aff4.RDFProtoArray):
  """Structure describing Most Recently Used (MRU) files."""
  _proto = sysinfo_pb2.MRUFile


class MRUCollection(aff4.AFF4Object):
  """Stores all of the MRU files from the registry."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_USED_FOLDER = aff4.Attribute(
        "aff4:mru", MRUFolder, "The Most Recently Used files.",
        default="")


class VFSFileSymlink(aff4.AFF4Stream):
  """A Delegate object for another URN."""

  delegate = None

  class SchemaCls(VFSFile.SchemaCls):
    DELEGATE = aff4.Attribute("aff4:delegate", aff4.RDFURN,
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
    self.Flush(sync=sync)
    if self.delegate:
      return self.delegate.Close(sync)

  def Write(self):
    raise IOError("VFSFileSymlink not writeable.")


class Service(aff4.RDFProtoArray):
  """Structure of a running service."""
  _proto = sysinfo_pb2.Service


class ServiceCollection(AFF4Collection):
  """Collection of services."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SERVICES = aff4.Attribute("aff4:service", Service,
                              "Services", default="")
