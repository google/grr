#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Some multiclient flows aka hunts."""



import re
import stat

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import cron
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.hunts import implementation
from grr.lib.hunts import output_plugins


class Error(Exception):
  pass


class HuntError(Error):
  pass


class CreateAndRunGenericHuntFlow(flow.GRRFlow):
  """Create and run GenericHunt with given name, args and rules.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  # TODO(user): describe proper types for hunt_flow_args and hunt_rules
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="Hunt id.",
          name="hunt_id"),

      type_info.String(
          description="Hunt flow name.",
          name="hunt_flow_name"),

      type_info.Any(
          description="A dictionary of hunt flow's arguments.",
          name="hunt_flow_args"),

      type_info.Any(
          description="Foreman rules for the hunt.",
          name="hunt_rules"),

      type_info.Duration(
          description="Expiration time for this hunt in seconds.",
          default=rdfvalue.Duration("31d"),
          name="expiry_time"),

      type_info.Integer(
          description="A client limit.",
          default=None,
          name="client_limit"),

      type_info.List(
          name="output_plugins",
          description="The output plugins to use for this hunt.",
          default=[("CollectionPlugin", {})],
          validator=type_info.List(validator=type_info.Any()),
          ),
      )

  @flow.StateHandler()
  def Start(self):
    """Create the hunt, perform permissions check and run it."""
    hunt = implementation.GRRHunt.StartHunt(
        "GenericHunt",
        flow_name=self.state.hunt_flow_name,
        args=self.state.hunt_flow_args,
        expiry_time=self.state.expiry_time,
        client_limit=self.state.client_limit,
        output_plugins=self.state.output_plugins,
        token=self.token)

    hunt.AddRule(rules=self.state.hunt_rules)
    hunt.WriteToDataStore()

    # We have to create special token here, because within the flow
    # token has supervisor access.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    data_store.DB.security_manager.CheckHuntAccess(check_token, hunt.urn)

    # General GUI workflow assumes that we're not gonna get here, as there are
    # not enough approvals for the newly created hunt.
    hunt.Run()


class ScheduleGenericHuntFlow(flow.GRRFlow):
  """Create a cron job that runs given hunt periodically."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = (
      CreateAndRunGenericHuntFlow.flow_typeinfo +
      type_info.TypeDescriptorSet(
          type_info.Integer(
              description="Hunt periodicity.",
              default=7,
              name="hunt_periodicity"
              )
          )
      )

  def CheckCronJobApproval(self, subject, token):
    """Find the approval for for this token and CheckAccess()."""
    logging.debug("Checking approval for cron job %s, %s", subject, token)

    if not token.username:
      raise access_control.UnauthorizedAccess(
          "Must specify a username for access.",
          subject=subject)

    if not token.reason:
      raise access_control.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=subject)

     # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(subject.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      approval_request = aff4.FACTORY.Open(
          approval_urn, aff4_type="Approval", mode="r",
          token=token, age=aff4.ALL_TIMES)
    except IOError:
      # No Approval found, reject this request.
      raise access_control.UnauthorizedAccess(
          "No approval found for hunt %s." % subject, subject=subject)

    if approval_request.CheckAccess(token):
      return True
    else:
      raise access_control.UnauthorizedAccess(
          "Approval %s was rejected." % approval_urn, subject=subject)

  @flow.StateHandler()
  def Start(self):
    """Start handler of a flow."""
    flow_args = dict(CreateAndRunGenericHuntFlow.flow_typeinfo.ParseArgs(
        self.state.AsDict()))

    uid = utils.PRNG.GetUShort()
    job_name = "Hunt_%s_%s" % (self.state.hunt_flow_name, uid)

    # No approval is needed to create a cron job, but approval is required
    # to enable it. Therefore first we create a disabled cron job and then
    # try to enable it.
    cron_job_urn = cron.CRON_MANAGER.ScheduleFlow(
        "CreateAndRunGenericHuntFlow", flow_args=flow_args,
        frequency=rdfvalue.Duration(str(self.state.hunt_periodicity) + "d"),
        token=self.token, disabled=True, job_name=job_name)

    # We have to create special token here, because within the flow
    # token has supervisor access. We use this token for a CheckCronJobApproval
    # check.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    self.CheckCronJobApproval(cron_job_urn, check_token)

    cron.CRON_MANAGER.EnableJob(cron_job_urn, token=self.token)


class RunHuntFlow(flow.GRRFlow):
  """Run already created hunt with given id.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="The URN of the hunt to execute.",
          name="hunt_urn"),
      )

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and run it."""
    hunt = aff4.FACTORY.Open(self.state.hunt_urn, aff4_type="GRRHunt",
                             age=aff4.ALL_TIMES, mode="rw", token=self.token)

    # We have to create special token here, because within the flow
    # token has supervisor access.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    data_store.DB.security_manager.CheckHuntAccess(check_token, hunt.urn)

    # Make the hunt token a supervisor so it can be started.
    hunt.token.supervisor = True
    hunt.Run()


class PauseHuntFlow(flow.GRRFlow):
  """Run already created hunt with given id."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="The URN of the hunt to pause.",
          name="hunt_urn"),
      )

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and pause it."""
    hunt = aff4.FACTORY.Open(self.state.hunt_urn, aff4_type="GRRHunt",
                             age=aff4.ALL_TIMES, mode="rw", token=self.token)

    # We have to create special token here, because within the flow
    # token has supervisor access.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    data_store.DB.security_manager.CheckHuntAccess(check_token, hunt.urn)

    # Make the hunt token a supervisor so it can be started.
    hunt.token.supervisor = True
    hunt.Pause()


class ModifyHuntFlow(flow.GRRFlow):
  """Modify already created hunt with given id.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="The URN of the hunt to pause.",
          name="hunt_urn"),
      ) + implementation.GRRHunt.hunt_typeinfo

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and modify it."""
    hunt = aff4.FACTORY.Open(self.state.hunt_urn, aff4_type="GRRHunt",
                             age=aff4.ALL_TIMES, mode="rw", token=self.token)
    # We have to create special token here, because within the flow
    # token has supervisor access.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    data_store.DB.security_manager.CheckHuntAccess(check_token, hunt.urn)

    # Make the hunt token a supervisor so it can be started.
    hunt.token.supervisor = True
    hunt.state.context.expiry_time = self.state.expiry_time
    hunt.state.context.client_limit = self.state.client_limit
    hunt.Close()


class CheckHuntAccessFlow(flow.GRRFlow):
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="Hunt urn.",
          name="hunt_urn"),
      )

  @flow.StateHandler()
  def Start(self):
    if not self.state.hunt_urn:
      raise RuntimeError("hunt_urn was not provided.")
    if self.state.hunt_urn.Split()[0] != "hunts":
      raise RuntimeError("invalid namespace in the hunt urn")

    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    data_store.DB.security_manager.CheckHuntAccess(check_token,
                                                   self.state.hunt_urn)


class SampleHunt(implementation.GRRHunt):
  """This hunt just looks for the presence of a evil.txt in /tmp.

  Scheduling the hunt works like this:

  > hunt = hunts.SampleHunt()

  # We want to schedule on clients that run windows and OS_RELEASE 7.
  > int_rule = rdfvalue.ForemanAttributeInteger(
                   attribute_name=client.Schema.OS_RELEASE.name,
                   operator=rdfvalue.ForemanAttributeInteger.Operator.EQUAL,
                   value=7)
  > regex_rule = hunts.GRRHunt.MATCH_WINDOWS

  # Run the hunt when both those rules match.
  > hunt.AddRule([int_rule, regex_rule])

  # Now we can test how many clients in the database match the rules.
  # Warning, this might take some time since it looks at all the stored clients.
  > hunt.TestRules()

  Out of 3171 checked clients, 2918 matched the given rule set.

  # This looks good, we exclude the few Linux / Mac clients in the datastore.

  # Now we can start the hunt. Note that this hunt is actually designed for
  # Linux / Mac clients so the example rules should not be used for this hunt.
  > hunt.Run()

  """

  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="evil filename to search for.",
          name="filename",
          default="/tmp/evil.txt")
      )

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self, responses):
    client_id = responses.request.client_id
    pathspec = rdfvalue.PathSpec(pathtype=rdfvalue.PathSpec.PathType.OS,
                                 path=self.state.filename)

    self.CallFlow("GetFile", pathspec=pathspec, next_state="StoreResults",
                  client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id

    if responses.success:
      logging.info("Client %s has a file %s.", client_id,
                   self.state.filename)
    else:
      logging.info("Client %s has no file %s.", client_id,
                   self.state.filename)

    self.MarkClientDone(client_id)


class RegistryFileHunt(implementation.GRRHunt):
  """A hunt that downloads registry files."""

  registry_files = ["DEFAULT", "SAM", "SECURITY", "SOFTWARE", "SYSTEM"]

  files = None

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self, responses):
    """Start."""
    client_id = responses.request.client_id

    if not self.state.files:
      self.state.files = {}

    self.state.files[client_id] = 0
    for filename in self.registry_files:
      pathspec = rdfvalue.PathSpec(
          pathtype=rdfvalue.PathSpec.PathType.TSK,
          path=r"C:\windows\system32\config\%s" % filename)

      self.state.files[client_id] += 1
      self.CallFlow("GetFile", pathspec=pathspec, next_state="StoreResults",
                    client_id=client_id)

    client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(client_id), mode="r",
                               token=self.token)
    users = client.Get(client.Schema.USER) or []
    for user in users:
      pathspec = rdfvalue.PathSpec(
          pathtype=rdfvalue.PathSpec.PathType.TSK,
          path=user.homedir + r"\NTUSER.DAT")
      self.state.files[client_id] += 1
      self.CallFlow("GetFile", pathspec=pathspec, next_state="StoreResults",
                    client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    if responses.success:
      pathspec = responses.First().pathspec
      self.LogResult(
          client_id, "Got file %s." % pathspec,
          aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id))
    else:
      self.LogClientError(client_id, log_message=responses.status)

    self.state.files[client_id] -= 1
    if self.state.files[client_id] == 0:
      self.MarkClientDone(client_id)


class ProcessesHunt(implementation.GRRHunt):
  """A hunt that downloads process lists."""

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self, responses):
    """Start."""
    client_id = responses.request.client_id

    self.CallFlow("ListProcesses", next_state="StoreResults",
                  client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    if responses.success:
      self.LogResult(client_id, "Got process listing.",
                     aff4.ROOT_URN.Add(client_id).Add("processes"))
    else:
      self.LogClientError(client_id, log_message=responses.status)

    self.MarkClientDone(client_id)

  def FindProcess(self, process_name):
    """This finds processes that contain process_name."""

    hunt = aff4.FACTORY.Open(self.state.urn,
                             age=aff4.ALL_TIMES, token=self.token)
    log = hunt.GetValuesForAttribute(hunt.Schema.LOG)

    for log_entry in log:
      proc_list = aff4.FACTORY.Open(log_entry.urn, "ProcessListing",
                                    token=self.token)
      procs = proc_list.Get(proc_list.Schema.PROCESSES)
      for process in procs:
        if process_name.lower() in process.name.lower():
          print "Found process for %s:" % log_entry.client_id
          print process

  def ProcessHistogram(self, full_path=True):
    """This generates a histogram of all the processes found."""

    hist = {}

    hunt = aff4.FACTORY.Open(self.state.urn,
                             age=aff4.ALL_TIMES, token=self.token)
    log = hunt.GetValuesForAttribute(hunt.Schema.LOG)

    for log_entry in log:
      proc_list = aff4.FACTORY.Open(log_entry.urn, "ProcessListing",
                                    token=self.token)
      procs = proc_list.Get(proc_list.Schema.PROCESSES)
      for process in procs:
        if full_path:
          cmd = " ".join(process.cmdline)
        else:
          cmd = process.name
        hist.setdefault(cmd, 0)
        hist[cmd] += 1

    proc_list = sorted(hist.iteritems(), reverse=True, key=lambda (k, v): v)
    for proc, freq in proc_list:
      print "%d  %s" % (freq, proc)

    return hist


class MBRHunt(implementation.GRRHunt):
  """A hunt that downloads MBRs."""

  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          name="length",
          default=4096,
          description="Number of bytes to retrieve."))

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self, responses):
    """Start."""
    client_id = responses.request.client_id

    self.CallFlow("GetMBR", length=self.state.length, next_state="StoreResults",
                  client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    if responses.success:
      self.LogResult(client_id, "Got MBR.", client_id.Add("mbr"))
    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.MarkClientDone(client_id)

  def MBRHistogram(self, length=512):
    """Prints a histogram of the MBRs found."""

    hist = {}

    hunt = aff4.FACTORY.Open(self.state.urn,
                             age=aff4.ALL_TIMES, token=self.token)

    log = hunt.GetValuesForAttribute(hunt.Schema.LOG)

    for log_entry in log:
      try:
        mbr = aff4.FACTORY.Open(log_entry.urn, token=self.token)
        mbr_data = mbr.Read(length)
        # Skip over the table of primary partitions.
        mbr_data = mbr_data[:440] + "\x00"*70 + mbr_data[440+70:]
        key = mbr_data.encode("hex")
        hist.setdefault(key, []).append(log_entry.client_id)
      except AttributeError:
        print "Error for urn %s" % log_entry.urn

    mbr_list = sorted(hist.iteritems(), reverse=True, key=lambda (k, v): len(v))
    for mbr, freq in mbr_list:
      print "%d  %s" % (len(freq), mbr)

    return mbr_list


class MatchRegistryHunt(implementation.GRRHunt):
  """A hunt to download registry keys containing a search string."""

  def __init__(self, paths, search_string=None, max_depth=None,
               match_case=False, **kw):
    """This hunt looks for registry keys matching a given string.

    Args:
      paths: A list of registry keys where this hunt should look for values.
      search_string: The string to look for. If none is given, this just
                     downloads all the values found and searches can be done
                     later using FindString().
      max_depth: If given, the hunt will be restricted to a maximal path depth.
      match_case: The match has to be case sensitive.
    """

    self.state.paths = paths
    self.state.max_depth = max_depth
    self.state.match_case = match_case
    self.state.search_string = search_string
    if not self.state.match_case:
      self.state.search_string = search_string.lower()

    super(MatchRegistryHunt, self).__init__(**kw)

  @flow.StateHandler()
  def Start(self, responses):
    """Start."""
    client_id = responses.request.client_id

    for path in self.state.paths:
      request = rdfvalue.RDFFindSpec()
      request.pathspec.path = path
      request.pathspec.pathtype = rdfvalue.PathSpec.PathType.REGISTRY

      if self.state.max_depth:
        request.max_depth = self.state.max_depth

      # Hard coded limit so this does not get too big.
      request.iterator.number = 10000
      self.CallClient("Find", request, client_id=client_id,
                      next_state="StoreResults")

  def Match(self, s):
    if not self.state.match_case:
      s = s.lower()
    return self.state.search_string in s

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    if responses.success:
      for response in responses:
        pathspec = response.hit.pathspec
        if stat.S_ISDIR(response.hit.st_mode):
          continue
        vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            pathspec, client_id)
        data = utils.SmartStr(response.hit.registry_data.GetValue())
        fd = aff4.FACTORY.Create(vfs_urn, "VFSFile", mode="w", token=self.token)
        fd.Set(fd.Schema.STAT(response.hit))
        fd.Set(fd.Schema.PATHSPEC(response.hit.pathspec))
        fd.Close(sync=False)
        if not self.state.search_string:
          self.LogResult(client_id, "Registry key downloaded.", vfs_urn)
        else:
          if self.Match(data):
            self.LogResult(client_id, "Matching registry key.", vfs_urn)
          else:
            self.LogResult(client_id, "Registry key not matched.", vfs_urn)
    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.MarkClientDone(client_id)

  def FindString(self, search_term, match_case=True):
    """Finds a string in the downloaded registry keys."""

    hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % self.session_id,
                             age=aff4.ALL_TIMES, token=self.token)

    log = hunt.GetValuesForAttribute(hunt.Schema.LOG)

    urns = []
    for log_entry in log:
      urns.append(log_entry.urn)

    if not match_case:
      search_term = search_term.lower()

    for key in aff4.FACTORY.MultiOpen(urns, token=self.token):
      value = utils.SmartStr(key.Get(key.Schema.STAT).registry_data.GetValue())
      if not match_case:
        value = value.lower()
      if search_term in value:
        print "Match: %s: %s" % (key, value)


class RunKeysHunt(implementation.GRRHunt):
  """A hunt for the RunKey collection."""

  @flow.StateHandler(next_state="StoreResults")
  def Start(self, responses):
    client_id = responses.request.client_id
    self.CallFlow("CollectRunKeys", next_state="StoreResults",
                  client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    if responses.success:
      self.LogResult(client_id, "Downloaded RunKeys",
                     aff4.ROOT_URN.Add(client_id).Add("analysis/RunKeys"))
    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.MarkClientDone(client_id)

  def Histogram(self):
    """Creates a histogram of all the filenames found in the RunKeys."""

    hist = {}

    hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % self.session_id,
                             age=aff4.ALL_TIMES, token=self.token)

    log = hunt.GetValuesForAttribute(hunt.Schema.LOG)

    client_ids = [l.client_id for l in log]

    to_read = []

    while client_ids:
      clients = aff4.FACTORY.MultiOpen(
          ["aff4:/%s" % client_id for client_id in client_ids[:1000]])
      client_ids = client_ids[1000:]

      for client in clients:
        for user in client.Get(client.Schema.USER):
          to_read.append("aff4:/%s/analysis/RunKeys/%s/RunOnce" %
                         (client.client_id, user.username))
          to_read.append("aff4:/%s/analysis/RunKeys/%s/Run" %
                         (client.client_id, user.username))
        to_read.append("aff4:/%s/analysis/RunKeys/System/RunOnce" %
                       client.client_id)
        to_read.append("aff4:/%s/analysis/RunKeys/System/Run" %
                       client.client_id)

    print "Processing %d collections." % len(to_read)
    collections_done = 0

    while to_read:
      # Only do 1000 at a time.
      collections_done += len(to_read[:1000])
      collections = aff4.FACTORY.MultiOpen(to_read[:1000], token=self.token)
      to_read = to_read[1000:]

      for collection in collections:
        try:
          for runkey in collection:
            key = runkey.filepath.replace("\"", "")
            key = re.sub(r"Users\\[^\\]+\\", r"Users\\USER\\", key)
            hist.setdefault(key, set()).add(str(collection.urn)[6:6+18])
        except AttributeError:
          pass

      print "%d collections done." % collections_done

    rk_list = sorted(hist.iteritems(), reverse=True, key=lambda (k, v): len(v))
    for rk, freq in rk_list:
      print "%d  %s" % (len(freq), rk)

    return rk_list


class FetchFilesHunt(implementation.GRRHunt):
  """This hunt launches the FetchAllFiles flow on a subset of hosts.

  Scheduling the hunt works like this:

  > hunt = hunts.FetchFilesHunt(client_limit=20)

  # We want to schedule on clients that run windows and OS_RELEASE 7.
  #
  # For now, we also want to limit ourselves to Windows *servers*.
  # TODO(user): This needs to be expressed here.

  > int_rule = rdfvalue.ForemanAttributeInteger(
                   attribute_name=client.Schema.OS_RELEASE.name,
                   operator=rdfvalue.ForemanAttributeInteger.Operator.EQUAL,
                   value=7)
  > regex_rule = hunts.GRRHunt.MATCH_WINDOWS

  # Run the hunt when both those rules match.
  > hunt.AddRule([int_rule, regex_rule])

  # Now we can test how many clients in the database match the rules.
  # Warning, this might take some time since it looks at all the stored clients.
  > hunt.TestRules()

  Out of 3171 checked clients, 2918 matched the given rule set.

  > hunt.Run()

  """

  @flow.StateHandler(next_state=["MarkDone"])
  def Start(self, responses):
    client_id = responses.request.client_id
    self.CallFlow("FetchAllFiles", next_state="MarkDone",
                  client_id=client_id)

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    self.MarkClientDone(client_id)


class MemoryHunt(implementation.GRRHunt):
  """This is a hunt to find signatures in memory."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.GrepspecType(
          description="Search memory for this expression.",
          name="request"),

      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/find/{u}-{t}"),
      )

  @flow.StateHandler(next_state=["SavePlatform"])
  def Start(self, responses):
    client_id = responses.request.client_id
    self.CallClient("GetPlatformInfo", client_id=client_id,
                    next_state="SavePlatform")

  @flow.StateHandler(next_state=["Grep"])
  def SavePlatform(self, responses):
    """Save the updated client information."""
    client_id = responses.request.client_id
    if responses.success:
      response = responses.First()
      client = aff4.FACTORY.Open("aff4:/%s" % client_id, mode="rw")
      client.Set(client.Schema.HOSTNAME(response.node))
      client.Set(client.Schema.SYSTEM(response.system))
      client.Set(client.Schema.OS_RELEASE(response.release))
      client.Set(client.Schema.OS_VERSION(response.version))
      client.Set(client.Schema.UNAME("%s-%s-%s" % (
          response.system, response.version,
          response.release)))
      client.Close()

    self.CallFlow("LoadMemoryDriver", next_state="Grep",
                  client_id=client_id)

  @flow.StateHandler(next_state=["Unload"])
  def Grep(self, responses):
    client_id = responses.request.client_id
    if not responses.success:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))
      return

    self.CallFlow("Grep", output=self.state.output,
                  request=self.state.request, client_id=client_id,
                  next_state="Unload")

  @flow.StateHandler(next_state=["MarkDone"])
  def Unload(self, responses):
    """Saves the log and unloads the driver."""
    client_id = responses.request.client_id
    if responses.success:
      self.LogResult(client_id, "Memory grep completed, found %d hits." %
                     len(responses),
                     aff4.ROOT_URN.Add(client_id).Add(self.state.output))
    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.CallFlow("UnloadMemoryDriver", next_state="MarkDone",
                  client_id=client_id)

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    self.MarkClientDone(client_id)


class GenericHunt(implementation.GRRHunt):
  """This is a hunt to start any flow on multiple clients.

  Args:
    flow_name: The flow to run.
    args: A dict containing the parameters for the flow.
  """

  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="Name of flow to run.",
          name="flow_name",
          default=""),
      type_info.GenericProtoDictType(
          name="args",
          description="Parameters passed to the child flow.",
          ),
      type_info.List(
          name="output_plugins",
          description="The output plugins to use for this hunt.",
          default=[("CollectionPlugin", {})],
          validator=type_info.List(validator=type_info.Any()),
          ),
      )

  def InitFromArguments(self, **kw):
    """Initializes this hunt from arguments."""
    super(GenericHunt, self).InitFromArguments(**kw)

    # Create all the output plugin objects.
    self.state.Register("output_objects", [])
    for plugin_name, args in self.state.output_plugins:
      if plugin_name not in output_plugins.HuntOutputPlugin.classes:
        raise HuntError("Invalid output plugin name: %s.", plugin_name)

      cls = output_plugins.HuntOutputPlugin.classes[plugin_name]
      self.state.output_objects.append(cls(self, **dict(args.items())))

    self.SetDescription()

  def SetDescription(self):
    desc = []
    for k, v in sorted(self.state.args.ToDict().items()):
      desc.append("%s=%s" % (utils.SmartStr(k), utils.SmartStr(v)))
    description = "%s { %s }." % (
        self.state.flow_name, ", ".join(desc))
    self.state.context.description = description

  @flow.StateHandler(next_state=["MarkDone"])
  def Start(self, responses):
    client_id = responses.request.client_id

    args = self.state.args.ToDict()
    if not self.state.output_plugins:
      args["send_replies"] = False

    self.CallFlow(self.state.flow_name, next_state="MarkDone",
                  client_id=client_id, **args)

  def Save(self):
    with self.lock:
      # Flush results frequently so users can monitor them as they come in.
      for plugin in self.state.output_objects:
        plugin.Flush()

    super(GenericHunt, self).Save()

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id

    # Open child flow and account its' reported resource usage
    flow_path = responses.status.child_session_id
    flow_obj = aff4.FACTORY.Open(flow_path, mode="r", token=self.token)
    client_res = flow_obj.state.context.client_resources

    resources = rdfvalue.ClientResources()
    resources.client_id = client_id
    resources.session_id = flow_path
    resources.cpu_usage.user_cpu_time = client_res.cpu_usage.user_cpu_time
    resources.cpu_usage.system_cpu_time = client_res.cpu_usage.system_cpu_time
    resources.network_bytes_sent = flow_obj.state.context.network_bytes_sent
    self.state.context.usage_stats.RegisterResources(resources)

    if responses.success:
      msg = "Flow %s completed." % responses.request.flow_name
      self.LogResult(client_id, msg)

      with self.lock:
        for plugin in self.state.output_objects:
          for response in responses:
            plugin.ProcessResponse(response, client_id)

    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.MarkClientDone(client_id)

  def GetOutputObjects(self, output_cls=None):
    result = []
    for obj in self.state.output_objects:
      if output_cls is None or isinstance(obj, output_cls):
        result.append(obj)
    return result


class VariableGenericHunt(GenericHunt):
  """A generic hunt using different flows for each client.

  Args:
    flows: A dictionary where the keys are the client_ids to start flows on and
           the values are lists of pairs (flow_name, dict of args) similar to
           the generic hunt above.
  """

  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.GenericProtoDictType(
          name="flows",
          description=("A dictionary where the keys are the client_ids to start"
                       " flows on and the values are lists of pairs (flow_name,"
                       " dict of args)"),
          ),
      type_info.List(
          name="output_plugins",
          description="The output plugins to use for this hunt.",
          default=[("CollectionPlugin", {})],
          validator=type_info.List(validator=type_info.Any()),
          ),
      )

  def InitFromArguments(self, **kw):
    """Initializes this hunt from arguments."""
    super(VariableGenericHunt, self).InitFromArguments(**kw)

    client_id_re = aff4_grr.VFSGRRClient.CLIENT_ID_RE
    for client_id in self.state.flows:
      if not client_id_re.match(client_id.Basename()):
        raise HuntError("%s is not a valid client_id." % client_id)

  def SetDescription(self):
    self.state.context.description = "Variable Generic Hunt"

  @flow.StateHandler(next_state=["MarkDone"])
  def Start(self, responses):
    client_id = responses.request.client_id

    try:
      flow_list = self.state.flows[client_id]
    except KeyError:
      self.LogClientError(client_id, "No flow found for client %s." % client_id)
      self.MarkClientDone(client_id)
      return
    for flow_name, args in flow_list:
      self.CallFlow(flow_name, next_state="MarkDone", client_id=client_id,
                    **args.ToDict())

  def ManuallyScheduleClients(self):
    """Schedule all flows without using the Foreman.

    Since we know all the client ids to run on we might as well just schedule
    all the flows and wait for the results.
    """

    for client_id in self.state.flows:
      self.StartClient(self.session_id, client_id,
                       self.state.context.client_limit)


class CollectFilesHunt(implementation.GRRHunt):
  """A hunt to collect files from various clients.

  Args:
    files_by_client:
      A dictionary where the keys are the client_ids to collect files from and
      the values are lists of Pathspecs to get from this client.
  """

  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.Any(
          name="files_by_client",
          default={}))

  def InitFromArguments(self, **kw):
    super(CollectFilesHunt, self).InitFromArguments(**kw)

    for client_id in self.state.files_by_client:
      rdfvalue.ClientURN.Validate(client_id)

  @flow.StateHandler(next_state=["MarkDone"])
  def Start(self, responses):
    """Start."""
    client_id = responses.request.client_id
    try:
      file_list = self.state.files_by_client[client_id]
    except KeyError:
      self.LogClientError(client_id,
                          "No files found for client %s." % client_id)
      self.MarkClientDone(client_id)
      return
    for pathspec in file_list:
      self.CallFlow("GetFile", next_state="MarkDone", client_id=client_id,
                    pathspec=pathspec)

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    if not responses.success:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))
    else:
      for response in responses:
        msg = "Got file %s (%s)." % (response.aff4path, client_id)
        self.LogResult(client_id, msg, urn=response.aff4path)

    # This is not entirely accurate since it will mark the client as done as
    # soon as the first flow is done.
    self.MarkClientDone(client_id)

  def ManuallyScheduleClients(self):
    """Schedule all flows without using the Foreman.

    Since we know all the client ids to run on we might as well just schedule
    all the flows and wait for the results.
    """

    for client_id in self.state.files_by_client:
      self.StartClient(self.session_id, client_id,
                       self.state.context.client_limit)
