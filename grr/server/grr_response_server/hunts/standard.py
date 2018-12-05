#!/usr/bin/env python
"""Some multiclient flows aka hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_proto import flows_pb2
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import flow
from grr_response_server import grr_collections
from grr_response_server import queue_manager
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import implementation
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class Error(Exception):
  pass


class RunHunt(cronjobs.CronJobBase):
  """A cron job that starts a hunt."""

  def Run(self):
    action = self.job.args.hunt_cron_action
    token = access_control.ACLToken(username="Cron")

    hunt_args = rdf_hunts.GenericHuntArgs(
        flow_args=action.flow_args,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=action.flow_name))
    with implementation.StartHunt(
        hunt_name=GenericHunt.__name__,
        args=hunt_args,
        runner_args=action.hunt_runner_args,
        token=token) as hunt:

      hunt.Run()


class CreateGenericHuntFlow(flow.GRRFlow):
  """Create but don't run a GenericHunt with the given name, args and rules.

  As direct write access to the data store is forbidden, we have to use flows to
  perform any kind of modifications. This flow delegates ACL checks to
  access control manager.
  """

  args_type = rdf_hunts.CreateGenericHuntFlowArgs

  def Start(self):
    """Create the hunt, in the paused state."""
    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.StartHunt(
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
  immediately runs the hunt it created.
  """

  args_type = rdf_hunts.CreateGenericHuntFlowArgs

  def Start(self):
    """Create the hunt and run it."""
    with implementation.StartHunt(
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

  def RunClient(self, responses):
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=self.args.filename)

    for client_id in responses:
      self.CallFlow(
          transfer.GetFile.__name__,
          pathspec=pathspec,
          next_state="StoreResults",
          client_id=client_id)

  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id

    if responses.success:
      logging.info("Client %s has a file %s.", client_id, self.args.filename)
    else:
      logging.info("Client %s has no file %s.", client_id, self.args.filename)

    self.MarkClientDone(client_id)


class GenericHunt(implementation.GRRHunt):
  """This is a hunt to start any flow on multiple clients."""

  args_type = rdf_hunts.GenericHuntArgs

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

  def RunClient(self, responses):
    # Just run the flow on this client.
    for client_id in responses:
      flow_urn = self.CallFlow(
          args=self.args.flow_args,
          client_id=client_id,
          next_state="MarkDone",
          runner_args=self.args.flow_runner_args)
      with data_store.DB.GetMutationPool() as pool:
        grr_collections.RDFUrnCollection.StaticAdd(
            self.started_flows_collection_urn, flow_urn, mutation_pool=pool)

  STOP_BATCH_SIZE = 10000

  def _StopLegacy(self, reason=None):
    super(GenericHunt, self).Stop(reason=reason)

    started_flows = grr_collections.RDFUrnCollection(
        self.started_flows_collection_urn)

    num_terminated_flows = 0
    self.Log("Hunt stop. Terminating all the started flows.")

    # Delete hunt flows states.
    for flows_batch in collection.Batch(started_flows,
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

  def _StopRelational(self, reason=None):
    super(GenericHunt, self).Stop(reason=reason)
    started_flows = grr_collections.RDFUrnCollection(
        self.started_flows_collection_urn)

    client_id_flow_id_pairs = []
    for flow_urn in started_flows:
      components = flow_urn.Split()
      client_id_flow_id_pairs.append((components[0], components[2]))

    data_store.REL_DB.UpdateFlows(
        client_id_flow_id_pairs,
        pending_termination=rdf_flow_objects.PendingFlowTermination(
            reason="Parent hunt stopped."))

  def Stop(self, reason=None):
    if data_store.RelationalDBFlowsEnabled():
      self._StopRelational(reason=reason)
    else:
      self._StopLegacy(reason=reason)

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

  def MarkDone(self, responses):
    """Mark a client as done."""
    client_id = responses.request.client_id
    self.AddResultsToCollection(responses, client_id)
    self.MarkClientDone(client_id)


class FlowStartRequest(rdf_structs.RDFProtoStruct):
  """Defines a flow to start on a number of clients."""
  protobuf = flows_pb2.FlowStartRequest
  rdf_deps = [
      rdf_client.ClientURN,
      rdf_flow_runner.FlowRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.runner_args.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(
          self.runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class VariableGenericHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.VariableGenericHuntArgs
  rdf_deps = [
      FlowStartRequest,
      rdf_output_plugin.OutputPluginDescriptor,
  ]


class VariableGenericHunt(GenericHunt):
  """A generic hunt using different flows for each client."""

  args_type = VariableGenericHuntArgs

  def SetDescription(self, description=None):
    self.runner_args.description = description or "Variable Generic Hunt"

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
