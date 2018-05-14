#!/usr/bin/env python
"""Some multiclient flows aka hunts."""

import logging
import operator

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import events as rdf_events
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import hunts as rdf_hunts
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import events
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import grr_collections
from grr.server.grr_response_server import output_plugin
from grr.server.grr_response_server import queue_manager
from grr.server.grr_response_server.aff4_objects import cronjobs
from grr.server.grr_response_server.flows.general import transfer
from grr.server.grr_response_server.hunts import implementation


class Error(Exception):
  pass


class GenericHuntArgs(rdf_structs.RDFProtoStruct):
  """Arguments to the generic hunt."""
  protobuf = flows_pb2.GenericHuntArgs
  rdf_deps = [
      rdf_flows.FlowRunnerArgs,
      output_plugin.OutputPluginDescriptor,
  ]

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


class CreateGenericHuntFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CreateGenericHuntFlowArgs
  rdf_deps = [
      GenericHuntArgs,
      rdf_hunts.HuntRunnerArgs,
  ]


class CreateGenericHuntFlow(flow.GRRFlow):
  """Create but don't run a GenericHunt with the given name, args and rules.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """

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
      self.Log("User %s created a new %s hunt (%s)", self.token.username,
               hunt.args.flow_runner_args.flow_name, hunt.urn)


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

      self.Log("User %s created a new %s hunt (%s)", self.token.username,
               hunt.args.flow_runner_args.flow_name, hunt.urn)


class SampleHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.SampleHuntArgs


class SampleHunt(implementation.GRRHunt):
  """This hunt just looks for the presence of a evil.txt in /tmp.

  Scheduling the hunt works like this:

  > hunt = standard.SampleHunt()

  # We want to schedule on clients that run windows and OS_RELEASE 7.
  > release_rule = rdf_foreman.ForemanAttributeRegex(
                   field="OS_RELEASE",
                   attribute_regex="7")
  > regex_rule = implementation.GRRHunt.MATCH_WINDOWS

  # Run the hunt when both those rules match.
  > hunt.AddRule([release_rule, regex_rule])

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
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=self.args.filename)

    for client_id in responses:
      self.CallFlow(
          transfer.GetFile.__name__,
          pathspec=pathspec,
          next_state="StoreResults",
          client_id=client_id)

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id

    if responses.success:
      logging.info("Client %s has a file %s.", client_id, self.args.filename)
    else:
      logging.info("Client %s has no file %s.", client_id, self.args.filename)

    self.MarkClientDone(client_id)


class HuntVerificationError(Error):
  """Used when something goes wrong during the verification."""


class MultiHuntVerificationSummaryError(HuntVerificationError):
  """Used when problem is detected in at least one verified hunt."""

  def __init__(self, errors):
    super(MultiHuntVerificationSummaryError, self).__init__()
    self.errors = errors

  def __str__(self):
    return "\n".join(str(error) for error in self.errors)


class VerifyHuntOutputPluginsCronFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.VerifyHuntOutputPluginsCronFlowArgs
  rdf_deps = [
      rdfvalue.Duration,
  ]


class VerifyHuntOutputPluginsCronFlow(cronjobs.SystemCronFlow):
  """Runs Verify() method of output plugins of active hunts."""

  frequency = rdfvalue.Duration("4h")
  lifetime = rdfvalue.Duration("4h")

  args_type = VerifyHuntOutputPluginsCronFlowArgs

  NON_VERIFIABLE = "NON_VERIFIABLE"

  def _GroupHuntsAndPluginsByVerifiers(self, hunts):
    """Opens hunts results metadata in bulk and groups the by verifier type.

    We've traded simplicity for performance here. Initial implementations of
    VerifyHuntOutputPluginsCronFlow checked the hunts one-by-one, but that
    turned out to be too slow and inefficient when many hunts had to be
    checked. To make the checks more effective, MultiVerifyHuntOutput()
    method was introduced in the verifiers API.

    It's this cron flow's responsibility to group the plugin objects by
    verifier type, so that we can feed them to MultiVerifyHuntOutput.

    Args:
      hunts: A list of GRRHunt objects.

    Returns:
      A dictionary where keys are verifier classes and values are lists of
      tuples (plugin id, plugin descriptor, plugin object, hunt object).
      Special constant NON_VERIFIABLE is used as a key for plugins that
      have no corresponding verifier.
    """
    hunts_by_urns = {}
    for hunt in hunts:
      hunts_by_urns[hunt.urn] = hunt

    results_metadata_urns = [hunt.results_metadata_urn for hunt in hunts]
    results_metadata_objects = aff4.FACTORY.MultiOpen(
        results_metadata_urns,
        aff4_type=implementation.HuntResultsMetadata,
        token=self.token)

    results = {}
    for mdata in results_metadata_objects:
      hunt_urn = rdfvalue.RDFURN(mdata.urn.Dirname())
      hunt = hunts_by_urns[hunt_urn]

      for plugin_id, (plugin_descriptor, plugin_state) in mdata.Get(
          mdata.Schema.OUTPUT_PLUGINS, {}).items():

        plugin_obj = plugin_descriptor.GetPluginForState(plugin_state)
        plugin_verifiers_classes = plugin_descriptor.GetPluginVerifiersClasses()

        if not plugin_verifiers_classes:
          results.setdefault(self.NON_VERIFIABLE, []).append(
              (plugin_id, plugin_descriptor, plugin_obj, hunt))
        else:
          for cls in plugin_verifiers_classes:
            results.setdefault(cls, []).append((plugin_id, plugin_descriptor,
                                                plugin_obj, hunt))

    return results

  def _FillResult(self, result, plugin_id, plugin_descriptor):
    result.timestamp = rdfvalue.RDFDatetime.Now()
    result.plugin_id = plugin_id
    result.plugin_descriptor = plugin_descriptor
    return result

  def _VerifyHunts(self, hunts_plugins_by_verifier):
    results_by_hunt = {}

    errors = []
    for verifier_cls, hunts_plugins in hunts_plugins_by_verifier.items():

      if verifier_cls == self.NON_VERIFIABLE:
        for plugin_id, plugin_descriptor, plugin_obj, hunt in hunts_plugins:
          result = output_plugin.OutputPluginVerificationResult(
              status=output_plugin.OutputPluginVerificationResult.Status.N_A,
              status_message=("Plugin %s is not verifiable." %
                              plugin_obj.__class__.__name__))
          self._FillResult(result, plugin_id, plugin_descriptor)

          results_by_hunt.setdefault(hunt.urn, []).append(result)
          stats.STATS.IncrementCounter(
              "hunt_output_plugin_verifications",
              fields=[utils.SmartStr(result.status)])
        continue

      verifier = verifier_cls()

      plugins_hunts_pairs = []
      for plugin_id, plugin_descriptor, plugin_obj, hunt in hunts_plugins:
        plugins_hunts_pairs.append((plugin_obj, hunt))

      try:
        for hunt_urn, result in verifier.MultiVerifyHuntOutput(
            plugins_hunts_pairs):
          self._FillResult(result, plugin_id, plugin_descriptor)

          results_by_hunt.setdefault(hunt.urn, []).append(result)
          stats.STATS.IncrementCounter(
              "hunt_output_plugin_verifications",
              fields=[utils.SmartStr(result.status)])

      except output_plugin.MultiVerifyHuntOutputError as e:
        logging.exception(e)

        errors.extend(e.errors)
        stats.STATS.IncrementCounter(
            "hunt_output_plugin_verification_errors", delta=len(e.errors))

    for hunt_urn, results in results_by_hunt.items():
      yield hunt_urn, results

    if errors:
      raise MultiHuntVerificationSummaryError(errors)

  def _WriteVerificationResults(self, hunt_urn, results):
    with aff4.FACTORY.Create(
        hunt_urn.Add("ResultsMetadata"),
        aff4_type=implementation.HuntResultsMetadata,
        mode="w",
        token=self.token) as results_metadata:
      results_metadata.Set(
          results_metadata.Schema.OUTPUT_PLUGINS_VERIFICATION_RESULTS,
          output_plugin.OutputPluginVerificationResultsList(results=results))

  @flow.StateHandler()
  def Start(self):
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)

    if not self.args.check_range:
      self.args.check_range = rdfvalue.Duration(
          "%ds" % int(self.__class__.frequency.seconds * 2))

    range_end = rdfvalue.RDFDatetime.Now()
    range_start = rdfvalue.RDFDatetime.Now() - self.args.check_range

    children_urns = list(hunts_root.ListChildren(age=(range_start, range_end)))
    children_urns.sort(key=operator.attrgetter("age"), reverse=True)

    self.Log("Will verify %d hunts." % len(children_urns))

    hunts_to_process = []
    for hunt in hunts_root.OpenChildren(children_urns):
      # Skip non-GenericHunts.
      if not isinstance(hunt, GenericHunt):
        self.Log("Skipping: %s." % utils.SmartStr(hunt.urn))
        continue

      hunts_to_process.append(hunt)

    hunts_by_verifier = self._GroupHuntsAndPluginsByVerifiers(hunts_to_process)
    for hunt_urn, results in self._VerifyHunts(hunts_by_verifier):
      self._WriteVerificationResults(hunt_urn, results)


class GenericHunt(implementation.GRRHunt):
  """This is a hunt to start any flow on multiple clients."""

  args_type = GenericHuntArgs

  def _CreateAuditEvent(self, event_action):
    flow_name = self.hunt_obj.args.flow_runner_args.flow_name

    event = rdf_events.AuditEvent(
        user=self.hunt_obj.token.username,
        action=event_action,
        urn=self.hunt_obj.urn,
        flow_name=flow_name,
        description=self.runner_args.description)
    events.Events.PublishEvent("Audit", event, token=self.hunt_obj.token)

  def SetDescription(self, description=None):
    if description:
      self.runner_args.description = description
    else:
      flow_name = self.args.flow_runner_args.flow_name
      self.runner_args.description = flow_name

  @property
  def started_flows_collection_urn(self):
    return self.urn.Add("StartedFlows")

  @flow.StateHandler()
  def RunClient(self, responses):
    # Just run the flow on this client.
    for client_id in responses:
      flow_urn = self.CallFlow(
          args=self.args.flow_args,
          client_id=client_id,
          next_state="MarkDone",
          sync=False,
          runner_args=self.args.flow_runner_args)
      with data_store.DB.GetMutationPool() as pool:
        grr_collections.RDFUrnCollection.StaticAdd(
            self.started_flows_collection_urn, flow_urn, mutation_pool=pool)

  STOP_BATCH_SIZE = 10000

  def Stop(self, reason=None):
    super(GenericHunt, self).Stop(reason=reason)

    started_flows = grr_collections.RDFUrnCollection(
        self.started_flows_collection_urn)

    num_terminated_flows = 0
    self.Log("Hunt stop. Terminating all the started flows.")

    # Delete hunt flows states.
    for flows_batch in utils.Grouper(started_flows,
                                     self.__class__.STOP_BATCH_SIZE):
      with queue_manager.QueueManager(token=self.token) as manager:
        manager.MultiDestroyFlowStates(flows_batch)

      with data_store.DB.GetMutationPool() as mutation_pool:
        for f in flows_batch:
          flow.GRRFlow.MarkForTermination(
              f, reason="Parent hunt stopped.", mutation_pool=mutation_pool)

      num_terminated_flows += len(flows_batch)

    # Delete hunt's requests and responses to ensure no more
    # processing is going to occur.
    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DestroyFlowStates(self.session_id)

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

  @flow.StateHandler()
  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    self.AddResultsToCollection(responses, client_id)
    self.MarkClientDone(client_id)


class FlowRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowRequest
  rdf_deps = [
      rdf_client.ClientURN,
      rdf_flows.FlowRunnerArgs,
  ]

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
  rdf_deps = [
      FlowRequest,
      output_plugin.OutputPluginDescriptor,
  ]


class VariableGenericHunt(GenericHunt):
  """A generic hunt using different flows for each client."""

  args_type = VariableGenericHuntArgs

  def SetDescription(self, description=None):
    self.runner_args.description = description or "Variable Generic Hunt"

  @flow.StateHandler()
  def RunClient(self, responses):
    client_ids_to_schedule = set(responses)
    with data_store.DB.GetMutationPool() as pool:
      for flow_request in self.args.flows:
        for requested_client_id in flow_request.client_ids:
          if requested_client_id in client_ids_to_schedule:
            flow_urn = self.CallFlow(
                args=flow_request.args,
                runner_args=flow_request.runner_args,
                next_state="MarkDone",
                client_id=requested_client_id)

            grr_collections.RDFUrnCollection.StaticAdd(
                self.started_flows_collection_urn, flow_urn, mutation_pool=pool)

  def ManuallyScheduleClients(self, token=None):
    """Schedule all flows without using the Foreman.

    Since we know all the client ids to run on we might as well just schedule
    all the flows and wait for the results.

    Args:
      token: A datastore access token.
    """

    client_ids = set()
    for flow_request in self.args.flows:
      for client_id in flow_request.client_ids:
        client_ids.add(client_id)

    self.StartClients(self.session_id, client_ids, token=token)


class StandardHuntInitHook(registry.InitHook):

  def RunOnce(self):
    """Register standard hunt-related stats."""
    stats.STATS.RegisterCounterMetric(
        "hunt_output_plugin_verifications", fields=[("status", str)])
    stats.STATS.RegisterCounterMetric("hunt_output_plugin_verification_errors")
    stats.STATS.RegisterCounterMetric(
        "hunt_output_plugin_errors", fields=[("plugin", str)])
    stats.STATS.RegisterCounterMetric(
        "hunt_results_ran_through_plugin", fields=[("plugin", str)])
    stats.STATS.RegisterCounterMetric("hunt_results_compacted")
    stats.STATS.RegisterCounterMetric("hunt_results_compaction_locking_errors")
