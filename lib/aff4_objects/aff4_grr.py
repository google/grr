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


from M2Crypto import X509

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import scheduler
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


# These are objects we store as attributes of the client.
class FileSystem(aff4.RDFProtoArray):
  """An RDFValue class representing one of the filesystems."""
  _proto = sysinfo_pb2.Filesystem


class Interface(aff4.RDFProtoArray):
  """An RDFValue class representing an list of interfaces on the host."""
  _proto = jobs_pb2.Interface


class User(aff4.RDFProtoArray):
  """An RDFValue class representing a list of users account."""
  _proto = jobs_pb2.UserAccount


class Processes(aff4.RDFProtoArray):
  """A list of processes on the system."""
  _proto = sysinfo_pb2.Process


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


class Flow(aff4.RDFProto):
  """A Flow protobuf."""
  _proto = jobs_pb2.Task

  rdf_map = dict(create_time=aff4.RDFDatetime)

  def ParseFromString(self, string):
    task = flow.SCHEDULER.Task(decoder=jobs_pb2.FlowPB)
    task.ParseFromString(string)
    self.data = task.value

  def SerializeToString(self):
    # We do not allow flows to be manipulated through the AFF4 subsystem.
    raise RuntimeError("Flow attributes are read only.")


class VFSGRRClient(standard.VFSDirectory):
  """A Remote client."""
  default_container = "VFSDirectory"

  class Schema(standard.VFSDirectory.Schema):
    """The schema for the client."""
    CERT = aff4.Attribute("metadata:cert", RDFX509Cert,
                          "The PEM encoded cert of the client.")

    FILESYSTEM = aff4.Attribute("aff4:filesystem", FileSystem,
                                "Filesystems on the client.")

    # Information about the host.
    HOSTNAME = aff4.Attribute("metadata:hostname", aff4.RDFString,
                              "Hostname of the host.", "Host")
    SYSTEM = aff4.Attribute("metadata:system", aff4.RDFString,
                            "Operating System class.", "System")
    UNAME = aff4.Attribute("metadata:uname", aff4.RDFString,
                           "Uname string.", "Uname")
    OS_RELEASE = aff4.Attribute("metadata:os_release", aff4.RDFString,
                                "OS Major release number.", "Release")
    OS_VERSION = aff4.Attribute("metadata:os_version", aff4.RDFString,
                                "OS Version number.", "Version")
    ARCH = aff4.Attribute("metadata:architecture", aff4.RDFString,
                          "Architecture.", "Architecture")
    INSTALL_DATE = aff4.Attribute("metadata:install_date", aff4.RDFDatetime,
                                  "Install Date.", "Install")

    USER = aff4.Attribute("aff4:users", User,
                          "A user of the system.", "Users")
    INTERFACE = aff4.Attribute("aff4:interfaces", Interface,
                               "A Network interface.")

    PROCESSES = aff4.Attribute("aff4:processes", Processes,
                               "Process Listing.")

    # This information is duplicated from the INTERFACES attribute but is done
    # to allow for fast searching by mac address.
    MAC_ADDRESS = aff4.Attribute("aff4:mac_addresses", aff4.RDFString,
                                 "A hex encoded MAC address.", "MAC")

    PING = aff4.Attribute("metadata:ping", aff4.RDFDatetime,
                          "The last ping time from this client.")

    CLOCK = aff4.Attribute("metadata:clock", aff4.RDFDatetime,
                           "The last clock read on the client "
                           "(Can be used to estimate client clock skew).",
                           "Clock")

    # This is the last foreman rule that applied to us
    LAST_FOREMAN_TIME = aff4.Attribute(
        "aff4:last_foreman_time", aff4.RDFDatetime,
        "The last time the foreman checked us.")

  def __init__(self, urn, mode="r", **kwargs):
    super(VFSGRRClient, self).__init__(urn, mode=mode, **kwargs)

    # The client_id is the first element of the URN
    self.client_id = self.urn.Path().split("/")[1]

  def Update(self, attribute=None, user=None):
    if attribute == self.Schema.DIRECTORY:
      flow_id = flow.FACTORY.StartFlow(
          self.client_id, "Interrogate", user=user)

      return flow_id

  def GetFlows(self, start=0, length=None):
    """A generator of all flows run on this client."""
    flows = self.GetValuesForAttribute(self.Schema.FLOW)
    if length is None:
      length = len(flows)

    flow_root = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN)
    return flow_root.OpenChildren(flows[start:start+length])


class VFSFile(aff4.AFF4Image):
  """A VFSFile object."""

  class Schema(aff4.AFF4Image.Schema):
    STAT = standard.VFSDirectory.Schema.STAT

    CONTENT_LOCK = aff4.Attribute(
        "aff4:content_lock", aff4.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this flow.")

  def Update(self, attribute=None, user=None):
    """Update an attribute from the client."""
    if attribute == self.Schema.CONTENT:
      # List the directory on the client
      currently_running = self.Get(self.Schema.CONTENT_LOCK)

      # Is this flow still active?
      if currently_running:
        flow_obj = aff4.FACTORY.Open(currently_running)
        flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB)
        if flow_pb.data.state == jobs_pb2.FlowPB.RUNNING:
          return

    # The client_id is the first element of the URN
    client_id = self.urn.Path().split("/")[1]

    client_urn = aff4.ROOT_URN.Add(client_id)

    ps = utils.Aff4ToPathspec("/" + self.urn.RelativeName(client_urn))

    session_id = flow.FACTORY.StartFlow(client_id, "GetFile", path=ps.path,
                                        pathtype=ps.pathtype, user=user)
    flow_urn = aff4.FLOW_SWITCH_URN.Add(session_id)
    self.Set(self.Schema.CONTENT_LOCK, flow_urn)
    self.Finish()

    return flow_urn


class VFSMemoryFile(VFSFile, aff4.AFF4MemoryStream):
  """A VFS file under a VFSDirectory node which does not have storage."""


class VFSAnalysisFile(VFSFile):
  """A VFS file which has no Update method."""

  def Update(self, attribute=None, user=None):
    pass


class GRRFlow(aff4.AFF4Object):
  """An object virtualizing flow to a client."""

  class Schema(aff4.AFF4Object.Schema):
    """Attributes specific to VFSDirectory."""
    FLOW_PB = aff4.Attribute("task:00000001", Flow,
                             "The Flow protobuf.", "Flow")

    TASK_COUNTER = aff4.Attribute("metadata:task_counter", aff4.RDFInteger,
                                  "Number of tasks scheduled.")

  def Initialize(self):
    # Our session_id is the last path element
    self.session_id = str(self.urn).split("/")[-1]

  def GetFlowObj(self):
    # This does not lock the flow - only read only.
    flow_pb = self.Get(self.Schema.FLOW_PB)
    if flow_pb:
      return flow.FACTORY.LoadFlow(flow_pb.data)


class GRRFlowSwitch(standard.VFSDirectory):
  """A VFS Container for flows.

  The idea here is to present a virtual view of flows so they can be dealt with
  using the AFF4 subsystem. This way we can place references to flows at various
  places.
  """

  def _OpenDirectChild(self, direct_child, stem, mode="r"):
    """Open the direct_child as a flow."""
    if stem:
      raise IOError("No objects contained within a flow.")

    return GRRFlow(scheduler.TaskScheduler.QueueToSubject(direct_child),
                   mode=mode)

  def ListChildren(self):
    """There are usually too many flows to make sense listing."""
    return {}, 0

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
    for child, attributes in data_store.DB.MultiResolveRegex(
        flow_names, ["aff4:.*", "metadata:.*", "fs:.*", "task:.*"],
        timestamp=data_store.ALL_TIMESTAMPS).iteritems():
      result = GRRFlow(aff4.RDFURN(child), mode, clone={}, parent=self)
      # Decode the attributes for the new object from existing data
      for attribute, value, ts in attributes:
        result.DecodeValueFromAttribute(attribute, value, ts)

      result.Initialize()
      results[child] = result

    # Order the results in the same order they were requested.
    for f in flow_names:
      if f in results:
        yield results[f]


class ForemanRules(aff4.RDFProtoArray):
  """A list of rules that the foreman will apply."""
  _proto = jobs_pb2.ForemanRule


class GRRForeman(aff4.AFF4Object):
  """The foreman starts flows for clients depending on rules."""

  class Schema(aff4.AFF4Object.Schema):
    """Attributes specific to VFSDirectory."""
    RULES = aff4.Attribute("aff4:rules", ForemanRules,
                           "The rules the foreman uses.")

  def _EvaluateRegexRules(self, objects, rule, client_id):
    """Evaluate the rule."""
    # Do the attribute regex first.
    for regex_rule in rule.regex_rules:
      path = aff4.ROOT_URN.Add(client_id).Add(regex_rule.path)
      fd = objects[path]
      attribute = aff4.Attribute.NAMES[regex_rule.attribute_name]
      value = utils.SmartStr(fd.Get(attribute))
      if not re.search(regex_rule.attribute_regex, value):
        return False

    return True

  def _RunActions(self, rule, client_id):
    """Run all the actions specified in the rule."""
    for action in rule.actions:
      flow.FACTORY.StartFlow(client_id, action.flow_name, user="Foreman",
                             **utils.ProtoDict(action.argv).ToDict())

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client."""
    rules = self.Get(self.Schema.RULES)
    if not rules: return

    client = aff4.FACTORY.Open(client_id)
    try:
      last_foreman_run = client.Get(client.Schema.LAST_FOREMAN_TIME).age
    except AttributeError:
      last_foreman_run = 0

    # For efficiency we collect all the objects we want to open first and then
    # open them all in one round trip.
    object_urns = {}
    relevant_rules = []
    latest_rule = 0

    for rule in rules:
      if rule.created <= last_foreman_run: continue

      # What is the latest created rule?
      latest_rule = max(latest_rule, rule.created)

      relevant_rules.append(rule)
      for regex in rule.regex_rules:
        aff4_object = aff4.ROOT_URN.Add(client_id).Add(regex.path)
        object_urns[str(aff4_object)] = aff4_object

    # Retrieve all aff4 objects we need
    objects = {}
    for fd in aff4.FACTORY.MultiOpen(object_urns):
      objects[fd.urn] = fd

    for rule in relevant_rules:
      if self._EvaluateRegexRules(objects, rule, client_id):
        self._RunActions(rule, client_id)

    # Update the latest checked rule on the client
    if latest_rule > last_foreman_run:
      client.Set(client.Schema.LAST_FOREMAN_TIME, aff4.RDFDatetime(latest_rule))
      client.Flush()


class GRRAFF4Init(aff4.AFF4InitHook):
  """Ensure critical AFF4 objects exist for GRR."""

  def __init__(self, **unused_kwargs):
    fd = aff4.FACTORY.Create(aff4.FLOW_SWITCH_URN).Upgrade("GRRFlowSwitch")
    fd.Close()

    # Make the foreman
    fd = aff4.FACTORY.Create("aff4:/foreman").Upgrade("GRRForeman")
    fd.Close()


# We add these attributes to all objects. This means that every object we create
# has a URN link back to the flow that created it.
aff4.AFF4Object.Schema.FLOW = aff4.Attribute(
    "aff4:flow", aff4.RDFURN, "A currently scheduled flow.")


class BlobArray(aff4.RDFProtoArray):
  """An array of blobs."""
  _proto = jobs_pb2.DataBlob

  def Add(self, **kwargs):
    """Add another member to this array."""
    self.Append(jobs_pb2.DataBlob(**kwargs))


class View(BlobArray):
  """A view specifies how a collection is seen."""


class AFF4Collection(standard.VFSDirectory):
  """A collection of objects."""

  _behaviours = frozenset(["Collection"])

  def CreateView(self, attributes):
    """Given a list of attributes, update our view."""
    result = BlobArray()

    for attribute in attributes:
      result.Append(jobs_pb2.DataBlob(string=str(attribute)))

    self.Set(self.Schema.VIEW, result)

  def OpenChildren(self, children=None, mode="r"):
    return aff4.AFF4Volume.OpenChildren(self, children=children, mode=mode)

  def Query(self, filter_string="", filter_obj=None):
    """Filter the objects contained within this collection."""
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = aff4.AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.Filter)

    subjects = [aff4.RDFURN(x.path) for x in self.Get(self.Schema.DIRECTORY)]
    result = []
    for match in data_store.DB.Query([], filter_obj, subjects=subjects):
      result.append(match["subject"][0])

    return self.OpenChildren(result)

  class Schema(standard.VFSDirectory.Schema):
    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")

    VIEW = aff4.Attribute("aff4:view", View,
                          "The list of attributes which will show up in "
                          "the table.")
