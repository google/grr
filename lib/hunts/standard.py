#!/usr/bin/env python
"""Some multiclient flows aka hunts."""



import threading

import logging

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.aff4_objects import collections
from grr.lib.aff4_objects import cronjobs
from grr.lib.hunts import implementation
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.parsers import wmi_parser
from grr.proto import flows_pb2
from grr.proto import output_plugin_pb2


class OutputPluginBatchProcessingStatus(rdf_structs.RDFProtoStruct):
  """Describes processing status of a single batch by a hunt output plugin."""
  protobuf = output_plugin_pb2.OutputPluginBatchProcessingStatus


class Error(Exception):
  pass


class HuntError(Error):
  pass


class ResultsProcessingError(Error):
  """This exception is raised when errors happen during results processing."""

  def __init__(self):
    self.exceptions_by_hunt = {}
    super(ResultsProcessingError, self).__init__()

  def RegisterSubException(self, hunt_urn, plugin_name, exception):
    self.exceptions_by_hunt.setdefault(hunt_urn, {}).setdefault(
        plugin_name, []).append(exception)

  def __repr__(self):
    messages = []
    for hunt_urn, exceptions_by_plugin in self.exceptions_by_hunt.items():
      for plugin_name, exception in exceptions_by_plugin.items():
        messages.append("Exception for hunt %s (plugin %s): %s" %
                        (hunt_urn, plugin_name, exception))

    return "\n".join(messages)


class CreateGenericHuntFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CreateGenericHuntFlowArgs


class CreateGenericHuntFlow(flow.GRRFlow):
  """Create but don't run a GenericHunt with the given name, args and rules.

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


class CreateAndRunGenericHuntFlow(flow.GRRFlow):
  """Create and run a GenericHunt with the given name, args and rules.

  This flow is different to the CreateGenericHuntFlow in that it
  immediately runs the hunt it created. This functionality cannot be
  offered in a SUID flow or every user could run any flow on any
  client without approval by just running a hunt on just that single
  client. Thus, this flow must *not* be SUID.
  """

  args_type = CreateGenericHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Create the hunt and run it."""
    with implementation.GRRHunt.StartHunt(
        runner_args=self.args.hunt_runner_args,
        args=self.args.hunt_args,
        token=self.token) as hunt:

      hunt.Run()

      self.Log("User %s created a new %s hunt",
               self.token.username, hunt.state.args.flow_runner_args.flow_name)


class StartHuntFlowArgs(rdf_structs.RDFProtoStruct):
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


class DeleteHuntFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DeleteHuntFlowArgs


class DeleteHuntFlow(flow.GRRFlow):
  """Delete an existing hunt, if it hasn't done anything yet."""
  ACL_ENFORCED = False
  args_type = DeleteHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Open(
        self.args.hunt_urn, aff4_type="GRRHunt", mode="rw",
        token=self.token) as hunt:
      # Check for approval if the hunt was created by somebody else.
      if self.token.username != hunt.creator:
        data_store.DB.security_manager.CheckHuntAccess(
            self.token.RealUID(), self.args.hunt_urn)
      if hunt.GetRunner().IsHuntStarted():
        raise RuntimeError("Unable to delete a running hunt.")
      if (not config_lib.CONFIG["AdminUI.allow_hunt_results_delete"] and
          hunt.client_count):
        raise RuntimeError("Unable to delete a hunt with results while "
                           "AdminUI.allow_hunt_results_delete is disabled.")
    aff4.FACTORY.Delete(self.args.hunt_urn, token=self.token)


class StopHuntFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.StopHuntFlowArgs


class StopHuntFlow(flow.GRRFlow):
  """Run already created hunt with given id."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False
  args_type = StopHuntFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Find a hunt, perform a permissions check and pause it."""
    # Check permissions first, and if ok, just proceed.
    data_store.DB.security_manager.CheckHuntAccess(
        self.token.RealUID(), self.args.hunt_urn)

    with aff4.FACTORY.Open(
        self.args.hunt_urn, aff4_type="GRRHunt", mode="rw",
        token=self.token) as hunt:

      hunt.Stop()


class ModifyHuntFlowArgs(rdf_structs.RDFProtoStruct):
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

      runner = hunt.GetRunner()
      data_store.DB.security_manager.CheckHuntAccess(
          self.token.RealUID(), hunt.urn)

      # Make sure the hunt is not running:
      if runner.IsHuntStarted():
        raise RuntimeError("Unable to modify a running hunt.")

      # Record changes in the audit event
      changes = []
      if runner.context.expires != self.args.expiry_time:
        changes.append("Expires: Old=%s, New=%s" % (runner.context.expires,
                                                    self.args.expiry_time))

      if runner.args.client_limit != self.args.client_limit:
        changes.append("Client Limit: Old=%s, New=%s" % (
            runner.args.client_limit, self.args.client_limit))

      description = ", ".join(changes)
      event = flow.AuditEvent(user=self.token.username,
                              action="HUNT_MODIFIED",
                              urn=self.args.hunt_urn,
                              description=description)
      flow.Events.PublishEvent("Audit", event, token=self.token)

      # Just go ahead and change the hunt now.
      runner.context.expires = self.args.expiry_time
      runner.args.client_limit = self.args.client_limit


class CheckHuntAccessFlowArgs(rdf_structs.RDFProtoStruct):
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


class SampleHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.SampleHuntArgs


class SampleHunt(implementation.GRRHunt):
  """This hunt just looks for the presence of a evil.txt in /tmp.

  Scheduling the hunt works like this:

  > hunt = hunts.SampleHunt()

  # We want to schedule on clients that run windows and OS_RELEASE 7.
  > int_rule = rdf_foreman.ForemanAttributeInteger(
                   attribute_name=client.Schema.OS_RELEASE.name,
                   operator=rdf_foreman.ForemanAttributeInteger.Operator.EQUAL,
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
    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS,
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

    OUTPUT_PLUGINS = aff4.Attribute(
        "aff4:output_plugins_state", rdf_flows.FlowState,
        "Pickled output plugins.", versioned=False)


class ProcessHuntResultsCronFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ProcessHuntResultsCronFlowArgs


class ProcessHuntResultsCronFlow(cronjobs.SystemCronFlow):
  """Periodic cron flow that processes hunts results with output plugins."""
  frequency = rdfvalue.Duration("5m")
  lifetime = rdfvalue.Duration("40m")

  args_type = ProcessHuntResultsCronFlowArgs

  DEFAULT_BATCH_SIZE = 1000
  MAX_REVERSED_RESULTS = 500000

  def CheckIfRunningTooLong(self):
    if self.state.args.max_running_time:
      elapsed = (rdfvalue.RDFDatetime().Now().AsSecondsFromEpoch() -
                 self.start_time.AsSecondsFromEpoch())
      if elapsed > self.state.args.max_running_time:
        return True

    return False

  def StatusCollectionUrn(self, hunt_urn):
    return hunt_urn.Add("OutputPluginsStatus")

  def ErrorsCollectionUrn(self, hunt_urn):
    return hunt_urn.Add("OutputPluginsErrors")

  def ApplyPluginsToBatch(self, hunt_urn, plugins, batch, batch_index):
    exceptions_by_plugin = {}
    for plugin_def, plugin in plugins:
      logging.debug("Processing hunt %s with %s, batch %d", hunt_urn,
                    plugin_def.plugin_name, batch_index)

      try:
        plugin.ProcessResponses(batch)

        stats.STATS.IncrementCounter("hunt_results_ran_through_plugin",
                                     delta=len(batch),
                                     fields=[plugin_def.plugin_name])

        plugin_status = OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_def,
            status="SUCCESS",
            batch_index=batch_index,
            batch_size=len(batch))
      except Exception as e:  # pylint: disable=broad-except
        stats.STATS.IncrementCounter("hunt_output_plugin_errors",
                                     fields=[plugin_def.plugin_name])

        plugin_status = OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_def,
            status="ERROR",
            summary=utils.SmartStr(e),
            batch_index=batch_index,
            batch_size=len(batch))

        logging.exception("Error processing hunt results: hunt %s, "
                          "plugin %s, batch %d", hunt_urn,
                          plugin_def.plugin_name, batch_index)
        self.Log("Error processing hunt results (hunt %s, "
                 "plugin %s, batch %d): %s" %
                 (hunt_urn, plugin_def.plugin_name, batch_index, e))
        exceptions_by_plugin[plugin_def] = e

      collections.PackedVersionedCollection.AddToCollection(
          self.StatusCollectionUrn(hunt_urn),
          [plugin_status], sync=False, token=self.token)
      if plugin_status.status == plugin_status.Status.ERROR:
        collections.PackedVersionedCollection.AddToCollection(
            self.ErrorsCollectionUrn(hunt_urn),
            [plugin_status], sync=False, token=self.token)

    return exceptions_by_plugin

  def FlushPlugins(self, hunt_urn, plugins):
    flush_exceptions = {}
    for plugin_def, plugin in plugins:
      try:
        plugin.Flush()
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Error flushing hunt results: hunt %s, "
                          "plugin %s", hunt_urn, str(plugin))
        self.Log("Error processing hunt results (hunt %s, "
                 "plugin %s): %s" % (hunt_urn, str(plugin), e))
        flush_exceptions[plugin_def] = e

    return flush_exceptions

  def ProcessHuntResults(self, results, freeze_timestamp):
    plugins_exceptions = {}

    hunt_urn = results.Get(results.Schema.RESULTS_SOURCE)
    metadata_urn = hunt_urn.Add("ResultsMetadata")

    batch_size = self.state.args.batch_size or self.DEFAULT_BATCH_SIZE
    batches = utils.Grouper(results.GenerateUncompactedItems(
        max_reversed_results=self.MAX_REVERSED_RESULTS,
        timestamp=freeze_timestamp), batch_size)

    with aff4.FACTORY.Open(
        metadata_urn, mode="rw", token=self.token) as metadata_obj:

      output_plugins = metadata_obj.Get(metadata_obj.Schema.OUTPUT_PLUGINS)
      num_processed = int(metadata_obj.Get(
          metadata_obj.Schema.NUM_PROCESSED_RESULTS))

      used_plugins = []
      for batch_index, batch in enumerate(batches):
        batch = list(batch)
        num_processed += len(batch)

        if not used_plugins:
          for _, (plugin_def, state) in output_plugins.data.iteritems():
            # TODO(user): Remove as soon as migration to new-style
            # output plugins is completed.
            if not hasattr(plugin_def, "GetPluginForState"):
              logging.error("Invalid plugin_def: %s", plugin_def)
              continue

            used_plugins.append((plugin_def,
                                 plugin_def.GetPluginForState(state)))

        batch_exceptions = self.ApplyPluginsToBatch(hunt_urn, used_plugins,
                                                    batch, batch_index)
        if batch_exceptions:
          for key, value in batch_exceptions.items():
            plugins_exceptions.setdefault(key, []).append(value)

        self.HeartBeat()

        # If this flow is working for more than max_running_time - stop
        # processing.
        if self.CheckIfRunningTooLong():
          self.Log("Running for too long, skipping rest of batches for %s",
                   hunt_urn)
          break

      if not used_plugins:
        logging.debug("Got notification, but no results were processed for %s.",
                      hunt_urn)

      flush_exceptions = self.FlushPlugins(hunt_urn, used_plugins)
      plugins_exceptions.update(flush_exceptions)

      metadata_obj.Set(metadata_obj.Schema.OUTPUT_PLUGINS(output_plugins))
      metadata_obj.Set(metadata_obj.Schema.NUM_PROCESSED_RESULTS(num_processed))

      return plugins_exceptions

  @flow.StateHandler()
  def Start(self):
    """Start state of the flow."""
    # If max_running_time is not specified, set it to 60% of this job's
    # lifetime.
    if not self.state.args.max_running_time:
      self.state.args.max_running_time = rdfvalue.Duration(
          "%ds" % int(ProcessHuntResultsCronFlow.lifetime.seconds * 0.6))

    self.start_time = rdfvalue.RDFDatetime().Now()

    exceptions_by_hunt = {}
    freeze_timestamp = rdfvalue.RDFDatetime().Now()
    for results_urn in aff4.ResultsOutputCollection.QueryNotifications(
        timestamp=freeze_timestamp, token=self.token):

      aff4.ResultsOutputCollection.DeleteNotifications(
          [results_urn], end=freeze_timestamp, token=self.token)

      # Feed the results to output plugins
      try:
        results = aff4.FACTORY.Open(
            results_urn, aff4_type="ResultsOutputCollection", token=self.token)
      except aff4.InstantiationError:  # Collection does not exist.
        continue

      exceptions_by_plugin = self.ProcessHuntResults(results, freeze_timestamp)
      if exceptions_by_plugin:
        hunt_urn = results.Get(results.Schema.RESULTS_SOURCE)
        exceptions_by_hunt[hunt_urn] = exceptions_by_plugin

      lease_time = config_lib.CONFIG["Worker.compaction_lease_time"]
      try:
        with aff4.FACTORY.OpenWithLock(results_urn, blocking=False,
                                       aff4_type="ResultsOutputCollection",
                                       lease_time=lease_time,
                                       token=self.token) as results:
          num_compacted = results.Compact(callback=self.HeartBeat,
                                          timestamp=freeze_timestamp)
          stats.STATS.IncrementCounter("hunt_results_compacted",
                                       delta=num_compacted)
          logging.debug("Compacted %d results in %s.", num_compacted,
                        results_urn)
      except aff4.LockError:
        logging.error("Trying to compact a collection that's already "
                      "locked: %s", results_urn)
        stats.STATS.IncrementCounter("hunt_results_compaction_locking_errors")

      if self.CheckIfRunningTooLong():
        self.Log("Running for too long, skipping rest of hunts.")
        break

    if exceptions_by_hunt:
      e = ResultsProcessingError()
      for hunt_urn, exceptions_by_plugin in exceptions_by_hunt.items():
        for plugin_name, exceptions in exceptions_by_plugin.items():
          for exception in exceptions:
            e.RegisterSubException(hunt_urn, plugin_name, exception)
      raise e


class GenericHuntArgs(rdf_structs.RDFProtoStruct):
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

  @property
  def started_flows_collection_urn(self):
    return self.urn.Add("StartedFlows")

  @flow.StateHandler()
  def Start(self):
    super(GenericHunt, self).Start()

    with aff4.FACTORY.Create(self.started_flows_collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token):
      pass

  @flow.StateHandler(next_state=["MarkDone"])
  def RunClient(self, responses):
    started_flows = []
    # Just run the flow on this client.
    for client_id in responses:
      flow_urn = self.CallFlow(
          args=self.state.args.flow_args, client_id=client_id,
          next_state="MarkDone", sync=False,
          runner_args=self.state.args.flow_runner_args)
      started_flows.append(flow_urn)

    collections.PackedVersionedCollection.AddToCollection(
        self.started_flows_collection_urn, started_flows, sync=False,
        token=self.token)

  def Stop(self):
    super(GenericHunt, self).Stop()

    started_flows = aff4.FACTORY.Create(self.started_flows_collection_urn,
                                        "PackedVersionedCollection",
                                        mode="r", token=self.token)

    self.Log("Hunt stop. Terminating all the started flows.")
    num_terminated_flows = 0
    for started_flow in started_flows:
      flow.GRRFlow.MarkForTermination(started_flow,
                                      reason="Parent hunt stopped.",
                                      token=self.token)
      num_terminated_flows += 1

    self.Log("%d flows terminated.", num_terminated_flows)

  def GetLaunchedFlows(self, flow_type="outstanding"):
    """Returns the session IDs of all the flows we launched.

    Args:
      flow_type: The type of flows to fetch. Can be "all", "outstanding" or
      "finished".

    Returns:
      A list of flow URNs.
    """
    result = None
    all_clients = set(self.ListAllClients())
    finished_clients = set(self.ListFinishedClients())
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

  def StoreResourceUsage(self, responses, client_id):
    """Open child flow and account its' reported resource usage."""
    flow_path = responses.status.child_session_id
    status = responses.status

    resources = rdf_client.ClientResources()
    resources.client_id = client_id
    resources.session_id = flow_path
    resources.cpu_usage.user_cpu_time = status.cpu_time_used.user_cpu_time
    resources.cpu_usage.system_cpu_time = status.cpu_time_used.system_cpu_time
    resources.network_bytes_sent = status.network_bytes_sent
    self.state.context.usage_stats.RegisterResources(resources)

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    self.StoreResourceUsage(responses, client_id)
    self.AddResultsToCollection(responses, client_id)
    self.MarkClientDone(client_id)


class FlowRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowRequest

  def GetFlowArgsClass(self):
    if self.runner_args.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.runner_args.flow_name)
      if flow_cls is None:
        raise ValueError("Flow %s not known by this implementation." %
                         self.runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class VariableGenericHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.VariableGenericHuntArgs


class VariableGenericHunt(GenericHunt):
  """A generic hunt using different flows for each client."""

  args_type = VariableGenericHuntArgs

  def SetDescription(self, description=None):
    self.state.context.args.description = description or "Variable Generic Hunt"

  @flow.StateHandler(next_state=["MarkDone"])
  def RunClient(self, responses):
    started_flows = []

    for client_id in responses:
      for flow_request in self.state.args.flows:
        for requested_client_id in flow_request.client_ids:
          if requested_client_id == client_id:
            flow_urn = self.CallFlow(
                args=flow_request.args,
                runner_args=flow_request.runner_args,
                next_state="MarkDone", client_id=client_id)
            started_flows.append(flow_urn)

    collections.PackedVersionedCollection.AddToCollection(
        self.started_flows_collection_urn, started_flows, sync=False,
        token=self.token)

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


class StatsHunt(implementation.GRRHunt):
  """A Hunt to continuously collect stats from all clients.

  This hunt is very unusual, it doesn't call any flows, instead using CallClient
  directly.  This is done to minimise the message handling and server load
  caused by collecting this information with a short time period.

  TODO(user): implement a aff4 object cleanup cron that we can use to
  automatically delete the collections generated by this hunt.
  """

  args_type = GenericHuntArgs
  client_list = None
  client_list_lock = None

  def Start(self, **kwargs):
    super(StatsHunt, self).Start(**kwargs)

    # Force all client communication to be LOW_PRIORITY. This ensures that
    # clients do not switch to fast poll mode when returning stats messages.
    self.runner.args.priority = "LOW_PRIORITY"
    self.runner.args.require_fastpoll = False

    # The first time we're loaded we create these variables here.  After we are
    # sent to storage we recreate them in the Load method.
    self._MakeLock()

  def _MakeLock(self):
    if self.client_list is None:
      self.client_list = []
    if self.client_list_lock is None:
      self.client_list_lock = threading.RLock()

  def Load(self):
    super(StatsHunt, self).Load()
    self._MakeLock()

  def Save(self):
    # Make sure we call any remaining clients before we are saved
    with self.client_list_lock:
      call_list, self.client_list = self.client_list, None

    self._CallClients(call_list)

    super(StatsHunt, self).Save()

  @flow.StateHandler()
  def RunClient(self, responses):
    client_call_list = self._GetCallClientList(responses)
    self._CallClients(client_call_list)

  def _GetCallClientList(self, client_ids):
    """Use self.client_list to determine clients that need calling.

    Batch calls into StatsHunt.ClientBatchSize (or larger) chunks.

    Args:
      client_ids: list of client ids
    Returns:
      list of client IDs that should be called with callclient.
    """
    call_list = []
    with self.client_list_lock:
      self.client_list.extend(client_ids)

      if len(self.client_list) >= config_lib.CONFIG[
          "StatsHunt.ClientBatchSize"]:
        # We have enough clients ready to process, take a copy of the list so we
        # can release the lock.
        call_list, self.client_list = self.client_list, []
    return call_list

  def _CallClients(self, client_id_list):
    now = rdfvalue.RDFDatetime().Now()
    due = now + rdfvalue.Duration(
        config_lib.CONFIG["StatsHunt.CollectionInterval"])

    for client in aff4.FACTORY.MultiOpen(client_id_list,
                                         token=self.token):

      if client.Get(client.SchemaCls.SYSTEM) == "Windows":
        wmi_query = ("Select * from Win32_NetworkAdapterConfiguration where"
                     " IPEnabled=1")
        self.CallClient("WmiQuery", query=wmi_query,
                        next_state="StoreResults", client_id=client.urn,
                        start_time=due)
      else:
        self.CallClient("EnumerateInterfaces", next_state="StoreResults",
                        client_id=client.urn, start_time=due)

  def ProcessInterface(self, response):
    """Filter out localhost interfaces."""
    if response.mac_address != "000000000000" and response.ifname != "lo":
      return response

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id
    # TODO(user): Should we record client usage stats?
    processed_responses = []
    wmi_interface_parser = wmi_parser.WMIInterfacesParser()

    for response in responses:
      if isinstance(response, rdf_client.Interface):
        processed_responses.extend(
            filter(None, [self.ProcessInterface(response)]))
      elif isinstance(response, rdf_protodict.Dict):
        # This is a result from the WMIQuery call
        processed_responses.extend(list(
            wmi_interface_parser.Parse(None, response, None)))

    new_responses = flow.FakeResponses(processed_responses,
                                       responses.request_data)
    new_responses.success = responses.success
    new_responses.status = responses.status
    self.AddResultsToCollection(new_responses, client_id)

    # Respect both the expiry and pause controls, since this will otherwise run
    # forever. Pausing will effectively stop this hunt, and a new one will need
    # to be created.
    if self.runner.IsHuntStarted():
      # Re-issue the request to the client for the next collection.
      client_call_list = self._GetCallClientList([client_id])
      if client_call_list:
        self._CallClients(client_call_list)
    else:
      self.MarkClientDone(client_id)


class StandardHuntInitHook(registry.InitHook):

  pre = ["StatsInit"]

  def RunOnce(self):
    """Register standard hunt-related stats."""
    stats.STATS.RegisterCounterMetric("hunt_output_plugin_errors",
                                      fields=[("plugin", str)])
    stats.STATS.RegisterCounterMetric("hunt_results_ran_through_plugin",
                                      fields=[("plugin", str)])
    stats.STATS.RegisterCounterMetric("hunt_results_compacted")
    stats.STATS.RegisterCounterMetric("hunt_results_compaction_locking_errors")
