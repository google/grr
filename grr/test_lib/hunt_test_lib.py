#!/usr/bin/env python
"""Classes for hunt-related testing."""

import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import mig_foreman_rules
from grr_response_server import output_plugin
from grr_response_server.databases import db
from grr_response_server.flows.general import file_finder
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_hunt_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib


class SampleHuntMock(action_mocks.ActionMock):
  """Client mock for sample hunts."""

  def __init__(self,
               failrate=-1,
               data=b"Hello World!",
               user_cpu_time=None,
               system_cpu_time=None,
               network_bytes_sent=None):
    super().__init__()
    self.responses = 0
    self.data = data
    self.failrate = failrate
    self.count = 0

    self.user_cpu_time = user_cpu_time
    self.system_cpu_time = system_cpu_time
    self.network_bytes_sent = network_bytes_sent

  def FileFinderOS(self, args):
    # TODO: Stop relying on these constants.
    response = rdf_file_finder.FileFinderResult(
        stat_entry=rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path=args.paths[0], pathtype=rdf_paths.PathSpec.PathType.OS
            ),
            st_mode=33184,
            st_ino=1063090,
            st_dev=64512,
            st_nlink=1,
            st_uid=139592,
            st_gid=5000,
            st_size=len(self.data),
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
        )
    )

    self.responses += 1
    self.count += 1

    # Every "failrate" client does not have this file.
    if self.count == self.failrate:
      self.count = 0
      raise ValueError(
          f"FileFinderOS failed as planned, failrate = {self.failrate}"
      )

    return [response]

  def GenerateStatusMessage(self, message, response_id, status=None):
    status = rdf_flows.GrrStatus(
        status=status or rdf_flows.GrrStatus.ReturnedStatus.OK
    )

    # TODO: Stop relying on these constants.
    if message.name == "FileFinderOS":
      # Create status message to report sample resource usage
      if self.user_cpu_time is None:
        status.cpu_time_used.user_cpu_time = self.responses
      else:
        status.cpu_time_used.user_cpu_time = self.user_cpu_time

      if self.system_cpu_time is None:
        status.cpu_time_used.system_cpu_time = self.responses * 2
      else:
        status.cpu_time_used.system_cpu_time = self.system_cpu_time

      if self.network_bytes_sent is None:
        status.network_bytes_sent = self.responses * 3
      else:
        status.network_bytes_sent = self.network_bytes_sent

    return rdf_flows.GrrMessage(
        session_id=message.session_id,
        name=message.name,
        response_id=response_id,
        request_id=message.request_id,
        payload=status,
        type=rdf_flows.GrrMessage.Type.STATUS)


def TestHuntHelperWithMultipleMocks(client_mocks,
                                    iteration_limit=None,
                                    worker=None):
  """Runs a hunt with a given set of clients mocks.

  Args:
    client_mocks: Dictionary of (client_id->client_mock) pairs. Client mock
      objects are used to handle client actions. Methods names of a client mock
      object correspond to client actions names. For an example of a client mock
      object, see SampleHuntMock.
    iteration_limit: If None, hunt will run until it's finished. Otherwise,
      worker_mock.Next() will be called iteration_limit number of times. Every
      iteration processes worker's message queue. If new messages are sent to
      the queue during the iteration processing, they will be processed on next
      iteration.
    worker: flow_test_lib.TestWorker object to use.

  Returns:
    A number of iterations complete.
  """

  client_mocks = [
      flow_test_lib.MockClient(client_id, client_mock)
      for client_id, client_mock in client_mocks.items()
  ]

  if worker is None:
    rel_db_worker = flow_test_lib.TestWorker()
    data_store.REL_DB.RegisterFlowProcessingHandler(rel_db_worker.ProcessFlow)
  else:
    rel_db_worker = worker

  num_iterations = 0

  try:
    # Run the clients and worker until nothing changes any more.
    while iteration_limit is None or num_iterations < iteration_limit:
      data_store.REL_DB.delegate.WaitUntilNoFlowsToProcess(
          timeout=rdfvalue.DurationSeconds(10)
      )
      worker_processed = rel_db_worker.ResetProcessedFlows()

      client_processed = 0

      for client_mock in client_mocks:
        client_processed += int(client_mock.Next())

      num_iterations += 1

      if client_processed == 0 and not worker_processed:
        break

  finally:
    if worker is None:
      data_store.REL_DB.UnregisterFlowProcessingHandler(timeout=60)
      rel_db_worker.Shutdown()

  return num_iterations


def TestHuntHelper(client_mock,
                   client_ids,
                   iteration_limit=None,
                   worker=None):
  """Runs a hunt with a given client mock on given clients.

  Args:
    client_mock: Client mock objects are used to handle client actions. Methods
      names of a client mock object correspond to client actions names. For an
      example of a client mock object, see SampleHuntMock.
    client_ids: List of clients ids. Hunt will run on these clients. client_mock
      will be used for every client id.
    iteration_limit: If None, hunt will run until it's finished. Otherwise,
      worker_mock.Next() will be called iteration_limit number of tiems. Every
      iteration processes worker's message queue. If new messages are sent to
      the queue during the iteration processing, they will be processed on next
      iteration.
    worker: flow_test_lib.TestWorker object to use.

  Returns:
    A number of iterations complete.
  """
  return TestHuntHelperWithMultipleMocks(
      dict([(client_id, client_mock) for client_id in client_ids]),
      iteration_limit=iteration_limit,
      worker=worker)


class StandardHuntTestMixin(acl_test_lib.AclTestMixin):
  """Mixin with helper methods for hunt tests."""

  def _CreateForemanClientRuleSet(self):
    return foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="CLIENT_NAME", attribute_regex="GRR"))
    ])

  def CreateHunt(
      self,
      flow_runner_args=None,
      flow_args=None,
      client_rule_set=None,
      original_object=None,
      client_rate=0,
      client_limit=100,
      duration=None,
      creator="test_creator",
      **kwargs,
  ):
    # Only initialize default flow_args value if default flow_runner_args value
    # is to be used.
    if not flow_runner_args:
      flow_args = rdf_file_finder.FileFinderArgs(
          paths=["/tmp/evil.txt"],
          pathtype=rdf_paths.PathSpec.PathType.OS,
          action=rdf_file_finder.FileFinderAction.Download(),
      )

    flow_runner_args = flow_runner_args or rdf_flow_runner.FlowRunnerArgs(
        flow_name=file_finder.ClientFileFinder.__name__
    )

    client_rule_set = (client_rule_set or self._CreateForemanClientRuleSet())

    hunt_args = rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=flow_runner_args.flow_name,
            flow_args=rdf_structs.AnyValue.Pack(flow_args),
        ),
    )

    hunt_obj = rdf_hunt_objects.Hunt(
        creator=creator,
        client_rule_set=client_rule_set,
        original_object=original_object,
        client_rate=client_rate,
        client_limit=client_limit,
        duration=duration,
        args=hunt_args,
        **kwargs,
    )
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    hunt.CreateHunt(hunt_obj)

    return hunt_obj.hunt_id

  def StartHunt(self, paused=False, **kwargs):
    hunt_id = self.CreateHunt(**kwargs)
    if not paused:
      hunt.StartHunt(hunt_id)
    return hunt_id

  def FindForemanRules(self, hunt_obj):
    rules = data_store.REL_DB.ReadAllForemanRules()
    return [
        mig_foreman_rules.ToRDFForemanCondition(rule)
        for rule in rules
        if hunt_obj is None or rule.hunt_id == hunt_obj.urn.Basename()
    ]

  def AssignTasksToClients(self, client_ids=None, worker=None):
    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    client_ids = client_ids or self.client_ids
    foreman_obj = foreman.Foreman()

    def Assign():
      for client_id in client_ids:
        foreman_obj.AssignTasksToClient(client_id)

    if worker is None:
      with flow_test_lib.TestWorker():
        Assign()
    else:
      Assign()

  def RunHunt(self,
              client_ids=None,
              iteration_limit=None,
              client_mock=None,
              **mock_kwargs):
    with flow_test_lib.TestWorker() as test_worker:
      self.AssignTasksToClients(client_ids=client_ids, worker=test_worker)

      if client_mock is None:
        client_mock = SampleHuntMock(**mock_kwargs)
      return TestHuntHelper(
          client_mock,
          client_ids or self.client_ids,
          iteration_limit=iteration_limit,
          worker=test_worker)

  def RunHuntWithClientCrashes(self, client_ids):
    with flow_test_lib.TestWorker() as test_worker:
      client_mocks = dict([(client_id, flow_test_lib.CrashClientMock(client_id))
                           for client_id in client_ids])
      self.AssignTasksToClients(client_ids=client_ids, worker=test_worker)
      return TestHuntHelperWithMultipleMocks(client_mocks)

  def _EnsureClientHasHunt(self, client_id, hunt_id):
    try:
      data_store.REL_DB.ReadFlowObject(client_id, hunt_id)
    except db.UnknownFlowError:
      flow_test_lib.StartFlow(
          file_finder.ClientFileFinder,
          client_id=client_id,
          parent=flow.FlowParent.FromHuntID(hunt_id),
      )

    return hunt_id

  def AddResultsToHunt(self, hunt_id, client_id, values):
    flow_id = self._EnsureClientHasHunt(client_id, hunt_id)

    for value in values:
      data_store.REL_DB.WriteFlowResults(
          [
              mig_flow_objects.ToProtoFlowResult(
                  rdf_flow_objects.FlowResult(
                      client_id=client_id,
                      flow_id=flow_id,
                      hunt_id=hunt_id,
                      payload=value,
                  )
              )
          ]
      )

  def FinishHuntFlow(self, hunt_id, client_id):
    flow_id = self._EnsureClientHasHunt(client_id, hunt_id)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_obj.flow_state = flows_pb2.Flow.FlowState.FINISHED
    data_store.REL_DB.UpdateFlow(client_id, flow_id, flow_obj=flow_obj)

  def AddLogToHunt(self, hunt_id, client_id, message):
    flow_id = self._EnsureClientHasHunt(client_id, hunt_id)

    data_store.REL_DB.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            message=message,
        )
    )

  def AddErrorToHunt(self, hunt_id, client_id, message, backtrace):
    flow_id = self._EnsureClientHasHunt(client_id, hunt_id)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj.error_message = message
    flow_obj.backtrace = backtrace
    data_store.REL_DB.UpdateFlow(client_id, flow_id, flow_obj=flow_obj)

  def GetHuntResults(self, hunt_id):
    """Gets flow results for a given flow.

    Args:
      hunt_id: String with a hunt id or a RDFURN.

    Returns:
      List with hunt results payloads.
    """
    return [
        mig_flow_objects.ToRDFFlowResult(r)
        for r in data_store.REL_DB.ReadHuntResults(hunt_id, 0, sys.maxsize)
    ]


class DummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, state, responses):
    DummyHuntOutputPlugin.num_calls += 1
    DummyHuntOutputPlugin.num_responses += len(list(responses))


class FailingDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, state, responses):
    raise RuntimeError("Oh no!")


class FailingInFlushDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, state, responses):
    pass

  def Flush(self, state):
    raise RuntimeError("Flush, oh no!")


class StatefulDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  """Stateful dummy hunt output plugin."""
  data = []

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.delta = 0

  def InitializeState(self, state):
    super().InitializeState(state)
    state.index = 0

  def ProcessResponses(self, state, responses):
    StatefulDummyHuntOutputPlugin.data.append(state.index + self.delta)
    self.delta += 1

  def UpdateState(self, state):
    state.index += self.delta


class LongRunningDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0
  faketime = None

  def ProcessResponses(self, state, responses):
    LongRunningDummyHuntOutputPlugin.num_calls += 1
    LongRunningDummyHuntOutputPlugin.faketime.time += 100
