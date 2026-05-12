#!/usr/bin/env python
"""Classes for hunt-related testing."""

from typing import Optional, Sequence

from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman
from grr_response_server import hunt
from grr_response_server.databases import db
from grr_response_server.flows.general import file_finder
from grr_response_server.models import hunts as models_hunts
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
    # TODO - Stop relying on these constants.
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

    # TODO - Stop relying on these constants.
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

  def _CreateForemanClientRuleSet(self) -> jobs_pb2.ForemanClientRuleSet:
    return jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field="CLIENT_NAME", attribute_regex="GRR"
                ),
            )
        ]
    )

  def CreateHunt(
      self,
      flow_runner_args: Optional[flows_pb2.FlowRunnerArgs] = None,
      flow_args: Optional[pb_message.Message] = None,
      client_rule_set: Optional[jobs_pb2.ForemanClientRuleSet] = None,
      original_object: Optional[flows_pb2.FlowLikeObjectReference] = None,
      client_rate: int = 0,
      client_limit: int = 100,
      duration_seconds: Optional[int] = None,
      creator: str = "test_creator",
      description: Optional[str] = None,
      output_plugins: Optional[
          Sequence[output_plugin_pb2.OutputPluginDescriptor]
      ] = None,
  ) -> str:
    # Only initialize default flow_args value if default flow_runner_args value
    # is to be used.
    if flow_runner_args is None:
      flow_name = file_finder.ClientFileFinder.__name__
      if flow_args is None:
        flow_args = flows_pb2.FileFinderArgs(
            paths=["/tmp/evil.txt"],
            pathtype=jobs_pb2.PathSpec.PathType.OS,
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
                download=flows_pb2.FileFinderDownloadActionOptions(
                    collect_ext_attrs=False
                ),
            ),
        )
    else:
      flow_name = flow_runner_args.flow_name
      if flow_args is None:
        raise ValueError("flow_args must be specified if flow_runner_args is.")

    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=flow_name,
        flow_args=flow_args,
        creator=creator,
    )
    hunt_obj.client_rate = client_rate
    hunt_obj.client_limit = client_limit

    if description is not None:
      hunt_obj.description = description

    client_rule_set = client_rule_set or self._CreateForemanClientRuleSet()
    hunt_obj.client_rule_set.CopyFrom(client_rule_set)

    if original_object is not None:
      hunt_obj.original_object.CopyFrom(original_object)
    if duration_seconds is not None:
      hunt_obj.duration = duration_seconds
    if output_plugins is not None:
      del hunt_obj.output_plugins[:]
      hunt_obj.output_plugins.extend(output_plugins)

    hunt.CreateHunt(hunt_obj)
    return hunt_obj.hunt_id

  def StartHunt(
      self,
      paused: bool = False,
      flow_runner_args: Optional[flows_pb2.FlowRunnerArgs] = None,
      flow_args: Optional[pb_message.Message] = None,
      client_rule_set: Optional[jobs_pb2.ForemanClientRuleSet] = None,
      original_object: Optional[flows_pb2.FlowLikeObjectReference] = None,
      client_rate: int = 0,
      client_limit: int = 100,
      creator: str = "test_creator",
      description: Optional[str] = None,
      output_plugins: Optional[
          Sequence[output_plugin_pb2.OutputPluginDescriptor]
      ] = None,
  ) -> str:
    hunt_id = self.CreateHunt(
        flow_runner_args=flow_runner_args,
        flow_args=flow_args,
        client_rule_set=client_rule_set,
        original_object=original_object,
        client_rate=client_rate,
        client_limit=client_limit,
        creator=creator,
        description=description,
        output_plugins=output_plugins,
    )
    if not paused:
      hunt.StartHunt(hunt_id)
    return hunt_id

  def FindForemanRules(self, hunt_obj) -> list[jobs_pb2.ForemanCondition]:
    rules = data_store.REL_DB.ReadAllForemanRules()
    return [
        rule
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
      result = flows_pb2.FlowResult(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
      )
      result.payload.Pack(value)
      data_store.REL_DB.WriteFlowResults([result])

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
