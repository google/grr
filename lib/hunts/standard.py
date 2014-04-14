#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Some multiclient flows aka hunts."""



import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import cronjobs
from grr.lib.hunts import implementation
from grr.proto import flows_pb2


class Error(Exception):
  pass


class HuntError(Error):
  pass


class CreateGenericHuntFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CreateGenericHuntFlowArgs


class CreateGenericHuntFlow(flow.GRRFlow):
  """Create and run GenericHunt with given name, args and rules.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  args_type = CreateGenericHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Create the hunt, in the paused state."""
    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.GRRHunt.StartHunt(
        runner_args=self.args.hunt_runner_args,
        args=self.args.hunt_args,
        token=self.token) as hunt:

      # Nothing really to do here - hunts are always created in the paused
      # state.
      self.Log("User %s created a new %s hunt",
               self.token.username, hunt.state.args.flow_runner_args.flow_name)


class StartHuntFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.StartHuntFlowArgs


class StartHuntFlow(flow.GRRFlow):
  """Start already created hunt with given id.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False
  args_type = StartHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and run it."""
    # Check permissions first, and if ok, just proceed.
    data_store.DB.security_manager.CheckHuntAccess(
        self.token.RealUID(), self.args.hunt_urn)

    with aff4.FACTORY.Open(
        self.args.hunt_urn, aff4_type="GRRHunt",
        mode="rw", token=self.token) as hunt:

      hunt.Run()


class PauseHuntFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.PauseHuntFlowArgs


class PauseHuntFlow(flow.GRRFlow):
  """Run already created hunt with given id."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False
  args_type = PauseHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and pause it."""
    # Check permissions first, and if ok, just proceed.
    data_store.DB.security_manager.CheckHuntAccess(
        self.token.RealUID(), self.args.hunt_urn)

    with aff4.FACTORY.Open(
        self.args.hunt_urn, aff4_type="GRRHunt", mode="rw",
        token=self.token) as hunt:

      with hunt.GetRunner() as runner:
        runner.Pause()


class ModifyHuntFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ModifyHuntFlowArgs


class ModifyHuntFlow(flow.GRRFlow):
  """Modify already created hunt with given id.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  args_type = ModifyHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and modify it."""
    with aff4.FACTORY.Open(
        self.args.hunt_urn, aff4_type="GRRHunt",
        mode="rw", token=self.token) as hunt:

      with hunt.GetRunner() as runner:
        data_store.DB.security_manager.CheckHuntAccess(
            self.token.RealUID(), hunt.urn)

        # Make sure the hunt is not running:
        if runner.IsHuntStarted():
          raise RuntimeError("Unable to modify a running hunt. Pause it first.")

        # Record changes in the audit event
        changes = []
        if runner.context.expires != self.args.expiry_time:
          changes.append("Expires: Old=%s, New=%s" % (runner.context.expires,
                                                      self.args.expiry_time))

        if runner.args.client_limit != self.args.client_limit:
          changes.append("Client Limit: Old=%s, New=%s" % (
              runner.args.client_limit, self.args.client_limit))

        description = ", ".join(changes)
        event = rdfvalue.AuditEvent(user=self.token.username,
                                    action="HUNT_MODIFIED",
                                    urn=self.args.hunt_urn,
                                    description=description)
        flow.Events.PublishEvent("Audit", event, token=self.token)

        # Just go ahead and change the hunt now.
        runner.context.expires = self.args.expiry_time
        runner.args.client_limit = self.args.client_limit


class CheckHuntAccessFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CheckHuntAccessFlowArgs


class CheckHuntAccessFlow(flow.GRRFlow):
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False
  args_type = CheckHuntAccessFlowArgs

  @flow.StateHandler()
  def Start(self):
    if not self.args.hunt_urn:
      raise RuntimeError("hunt_urn was not provided.")
    if self.args.hunt_urn.Split()[0] != "hunts":
      raise RuntimeError("invalid namespace in the hunt urn")

    data_store.DB.security_manager.CheckHuntAccess(
        self.token.RealUID(), self.args.hunt_urn)


class SampleHuntArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.SampleHuntArgs


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
  args_type = SampleHuntArgs

  @flow.StateHandler()
  def RunClient(self, responses):
    pathspec = rdfvalue.PathSpec(pathtype=rdfvalue.PathSpec.PathType.OS,
                                 path=self.args.filename)

    for client_id in responses:
      self.CallFlow("GetFile", pathspec=pathspec, next_state="StoreResults",
                    client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id

    if responses.success:
      logging.info("Client %s has a file %s.", client_id,
                   self.args.filename)
    else:
      logging.info("Client %s has no file %s.", client_id,
                   self.args.filename)

    self.MarkClientDone(client_id)


class HuntResultsMetadata(aff4.AFF4Object):
  """Metadata AFF4 object used by CronHuntOutputFlow."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """AFF4 schema for CronHuntOutputMetadata."""

    NUM_PROCESSED_RESULTS = aff4.Attribute(
        "aff4:num_processed_results", rdfvalue.RDFInteger,
        "Number of hunt results already processed by the cron job.",
        versioned=False, default=0)

    COLLECTION_RAW_OFFSET = aff4.Attribute(
        "aff4:collection_raw_position", rdfvalue.RDFInteger,
        "Effectively, number of bytes occuppied by NUM_PROCESSED_RESULTS "
        "processed results in the results collection. Used to optimize "
        "results collection access and not to iterate over all previously "
        "processes results all the time.",
        versioned=False, default=0)

    OUTPUT_PLUGINS = aff4.Attribute(
        "aff4:output_plugins_state", rdfvalue.FlowState,
        "Pickled output plugins.", versioned=False)


class ProcessHuntResultsCronFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ProcessHuntResultsCronFlowArgs


class ProcessHuntResultsCronFlow(cronjobs.SystemCronFlow):
  """Periodic cron flow that processes hunts results with output plugins."""
  frequency = rdfvalue.Duration("5m")
  lifetime = rdfvalue.Duration("40m")

  args_type = ProcessHuntResultsCronFlowArgs

  DEFAULT_BATCH_SIZE = 1000

  def ProcessHunt(self, session_id):
    metadata_urn = session_id.Add("ResultsMetadata")
    last_exception = None

    with aff4.FACTORY.Open(
        metadata_urn, mode="rw", token=self.token) as metadata_obj:

      output_plugins = metadata_obj.Get(metadata_obj.Schema.OUTPUT_PLUGINS)
      num_processed = int(metadata_obj.Get(
          metadata_obj.Schema.NUM_PROCESSED_RESULTS))
      raw_offset = int(metadata_obj.Get(
          metadata_obj.Schema.COLLECTION_RAW_OFFSET))
      results = aff4.FACTORY.Open(session_id.Add("Results"), mode="r",
                                  token=self.token)

      batch_size = self.state.args.batch_size or self.DEFAULT_BATCH_SIZE
      batches = utils.Grouper(results.GenerateItems(offset=raw_offset),
                              batch_size)

      used_plugins = {}
      for batch_index, batch in enumerate(batches):
        if not used_plugins:
          for plugin_name, (plugin_def,
                            state) in output_plugins.data.iteritems():
            used_plugins[plugin_name] = plugin_def.GetPluginForState(state)

        # If this flow is working for more than max_running_time - stop
        # processing.
        if self.state.args.max_running_time:
          elapsed = (rdfvalue.RDFDatetime().Now().AsSecondsFromEpoch() -
                     self.start_time.AsSecondsFromEpoch())
          if elapsed > self.state.args.max_running_time:
            self.Log("Running for too long, skipping rest of batches for %s.",
                     session_id)
            break

        batch = list(batch)
        num_processed += len(batch)

        for plugin_name, plugin in used_plugins.iteritems():
          logging.debug("Processing hunt %s with %s, batch %d", session_id,
                        plugin_name, batch_index)

          try:
            plugin.ProcessResponses(batch)
          except Exception as e:  # pylint: disable=broad-except
            logging.exception("Error processing hunt results: hunt %s, "
                              "plugin %s, batch %d", session_id, plugin_name,
                              batch_index)
            self.Log("Error processing hunt results (hunt %s, "
                     "plugin %s, batch %d): %s" %
                     (session_id, plugin_name, batch_index, e))
            last_exception = e
        self.HeartBeat()

      for plugin in used_plugins.itervalues():
        try:
          plugin.Flush()
        except Exception as e:  # pylint: disable=broad-except
          logging.exception("Error flushing hunt results: hunt %s, "
                            "plugin %s", session_id, str(plugin))
          self.Log("Error processing hunt results (hunt %s, "
                   "plugin %s): %s" % (session_id, str(plugin), e))
          last_exception = e

      metadata_obj.Set(metadata_obj.Schema.OUTPUT_PLUGINS(output_plugins))
      metadata_obj.Set(metadata_obj.Schema.NUM_PROCESSED_RESULTS(num_processed))
      metadata_obj.Set(metadata_obj.Schema.COLLECTION_RAW_OFFSET(
          results.current_offset))

      # TODO(user): throw proper exception which will contain all the
      # exceptions that were raised while processing this hunt.
      if last_exception:
        raise last_exception  # pylint: disable=raising-bad-type

  @flow.StateHandler()
  def Start(self):
    """Start state of the flow."""
    # If max_running_time is not specified, set it to 60% of this job's
    # lifetime.
    if not self.state.args.max_running_time:
      self.state.args.max_running_time = rdfvalue.Duration(
          "%ds" % int(ProcessHuntResultsCronFlow.lifetime.seconds * 0.6))

    last_exception = None
    self.start_time = rdfvalue.RDFDatetime().Now()
    for session_id, timestamp, _ in data_store.DB.ResolveRegex(
        GenericHunt.RESULTS_QUEUE, ".*", token=self.token):

      logging.info("Found new results for hunt %s.", session_id)
      try:
        self.ProcessHunt(rdfvalue.RDFURN(session_id))
        self.HeartBeat()

      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Error processing hunt %s.", session_id)
        self.Log("Error processing hunt %s: %s", session_id, e)
        last_exception = e

      # We will delete hunt's results notification even if ProcessHunt has
      # failed
      finally:
        results = data_store.DB.ResolveRegex(
            GenericHunt.RESULTS_QUEUE, session_id, token=self.token)
        if results and len(results) == 1:
          _, latest_timestamp, _ = results[0]
        else:
          logging.warning("Inconsistent state in hunt results queue for "
                          "hunt %s", session_id)
          latest_timestamp = None

        # We don't want to delete notification that was written after we
        # started processing.
        if latest_timestamp and latest_timestamp > timestamp:
          logging.debug("Not deleting results notification: it was written "
                        "after processing has started.")
        else:
          data_store.DB.DeleteAttributes(GenericHunt.RESULTS_QUEUE,
                                         [session_id], sync=True,
                                         token=self.token)

    # TODO(user): throw proper exception which will contain all the
    # exceptions that were raised while processing the hunts.
    if last_exception:
      raise last_exception  # pylint: disable=raising-bad-type


class GenericHuntArgs(rdfvalue.RDFProtoStruct):
  """Arguments to the generic hunt."""
  protobuf = flows_pb2.GenericHuntArgs

  def Validate(self):
    self.flow_runner_args.Validate()
    self.flow_args.Validate()

  def GetFlowArgsClass(self):
    if self.flow_runner_args.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.flow_runner_args.flow_name)
      if flow_cls is None:
        raise ValueError("Flow '%s' not known by this implementation." %
                         self.flow_runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class GenericHunt(implementation.GRRHunt):
  """This is a hunt to start any flow on multiple clients."""

  args_type = GenericHuntArgs

  RESULTS_QUEUE = rdfvalue.RDFURN("HR")

  def Initialize(self):
    super(GenericHunt, self).Initialize()
    self.processed_responses = False

  @flow.StateHandler()
  def Start(self):
    """Initializes this hunt from arguments."""
    self.state.context.Register("results_metadata_urn",
                                self.urn.Add("ResultsMetadata"))
    self.state.context.Register("results_collection_urn",
                                self.urn.Add("Results"))

    with aff4.FACTORY.Create(
        self.state.context.results_metadata_urn, "HuntResultsMetadata",
        mode="rw", token=self.token) as results_metadata:

      state = rdfvalue.FlowState()
      plugins = self.state.args.output_plugins or []
      for index, plugin in enumerate(plugins):
        plugin_obj = plugin.GetPluginForHunt(self)
        state.Register("%s_%d" % (plugin.plugin_name, index),
                       (plugin, plugin_obj.state))

      results_metadata.Set(results_metadata.Schema.OUTPUT_PLUGINS(state))

    with aff4.FACTORY.Create(
        self.state.context.results_collection_urn, "RDFValueCollection",
        mode="rw", token=self.token) as results_collection:
      results_collection.SetChunksize(1024 * 1024)
      self.state.context.Register("results_collection", results_collection)

    self.SetDescription()

  def SetDescription(self, description=None):
    if description:
      self.state.context.args.description = description
    else:
      flow_name = self.state.args.flow_runner_args.flow_name
      self.state.context.args.description = flow_name

  @flow.StateHandler(next_state=["MarkDone"])
  def RunClient(self, responses):
    # Just run the flow on this client.
    for client_id in responses:
      self.CallFlow(args=self.state.args.flow_args, client_id=client_id,
                    next_state="MarkDone", sync=False,
                    runner_args=self.state.args.flow_runner_args)

  def GetLaunchedFlows(self, flow_type="outstanding"):
    """Returns the session IDs of all the flows we launched.

    Args:
      flow_type: The type of flows to fetch. Can be "all", "outstanding" or
      "finished".

    Returns:
      A list of flow URNs.
    """
    result = None
    all_clients = set(self.GetValuesForAttribute(self.Schema.CLIENTS))
    finished_clients = set(self.GetValuesForAttribute(self.Schema.FINISHED))
    outstanding_clients = all_clients - finished_clients

    if flow_type == "all":
      result = all_clients
    elif flow_type == "finished":
      result = finished_clients
    elif flow_type == "outstanding":
      result = outstanding_clients

    # Now get the flows for all these clients.
    flows = aff4.FACTORY.MultiListChildren(
        [self.urn.Add(x.Basename()) for x in result])

    return [x[0] for _, x in flows]

  def Save(self):
    if self.state and self.processed_responses:
      with self.lock:
        self.state.context.results_collection.Flush(sync=True)
        data_store.DB.Set(self.RESULTS_QUEUE, self.urn,
                          rdfvalue.RDFDatetime().Now(),
                          replace=True, token=self.token)

    super(GenericHunt, self).Save()

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id

    # Open child flow and account its' reported resource usage
    flow_path = responses.status.child_session_id
    status = responses.status

    resources = rdfvalue.ClientResources()
    resources.client_id = client_id
    resources.session_id = flow_path
    resources.cpu_usage.user_cpu_time = status.cpu_time_used.user_cpu_time
    resources.cpu_usage.system_cpu_time = status.cpu_time_used.system_cpu_time
    resources.network_bytes_sent = status.network_bytes_sent
    self.state.context.usage_stats.RegisterResources(resources)

    if responses.success:
      with self.lock:
        self.processed_responses = True
        msgs = [rdfvalue.GrrMessage(payload=response, source=client_id)
                for response in responses]
        self.state.context.results_collection.AddAll(msgs)

    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

    self.MarkClientDone(client_id)


class FlowRequest(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FlowRequest

  def GetFlowArgsClass(self):
    if self.runner_args.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.runner_args.flow_name)
      if flow_cls is None:
        raise ValueError("Flow %s not known by this implementation." %
                         self.runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class VariableGenericHuntArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.VariableGenericHuntArgs


class VariableGenericHunt(GenericHunt):
  """A generic hunt using different flows for each client."""

  args_type = VariableGenericHuntArgs

  def SetDescription(self, description=None):
    self.state.context.args.description = description or "Variable Generic Hunt"

  @flow.StateHandler(next_state=["MarkDone"])
  def RunClient(self, responses):
    for client_id in responses:
      for flow_request in self.state.args.flows:
        for requested_client_id in flow_request.client_ids:
          if requested_client_id == client_id:
            self.CallFlow(
                args=flow_request.args,
                runner_args=flow_request.runner_args,
                next_state="MarkDone", client_id=client_id)

  def ManuallyScheduleClients(self, token=None):
    """Schedule all flows without using the Foreman.

    Since we know all the client ids to run on we might as well just schedule
    all the flows and wait for the results.

    Args:
      token: A datastore access token.
    """
    client_ids = set()
    for flow_request in self.state.args.flows:
      for client_id in flow_request.client_ids:
        client_ids.add(client_id)

    self.StartClients(self.session_id, client_ids, token=token)
