#!/usr/bin/env python
"""Classes for hunt-related testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import sys
import time


from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import grr_collections
from grr_response_server import hunt
from grr_response_server import output_plugin
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import implementation
from grr_response_server.hunts import process_results
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import worker_test_lib


class SampleHuntMock(action_mocks.ActionMock):
  """Client mock for sample hunts."""

  def __init__(self,
               failrate=-1,
               data=b"Hello World!",
               user_cpu_time=None,
               system_cpu_time=None,
               network_bytes_sent=None):
    super(SampleHuntMock, self).__init__()
    self.responses = 0
    self.data = data
    self.failrate = failrate
    self.count = 0

    self.user_cpu_time = user_cpu_time
    self.system_cpu_time = system_cpu_time
    self.network_bytes_sent = network_bytes_sent

  def GetFileStat(self, args):
    return self.StatFile(args)

  # TODO(hanuszczak): Remove this once `StatFile` is deprecated.
  def StatFile(self, args):
    """StatFile action mock."""
    response = rdf_client_fs.StatEntry(
        pathspec=args.pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_dev=64512,
        st_nlink=1,
        st_uid=139592,
        st_gid=5000,
        st_size=len(self.data),
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    self.responses += 1
    self.count += 1

    # Every "failrate" client does not have this file.
    if self.count == self.failrate:
      self.count = 0
      return []

    return [response]

  def GenerateStatusMessage(self, message, response_id, status=None):
    status = rdf_flows.GrrStatus(
        status=status or rdf_flows.GrrStatus.ReturnedStatus.OK)

    if message.name in ["StatFile", "GetFileStat"]:
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

  def TransferBuffer(self, args):
    """TransferBuffer action mock."""
    response = rdf_client.BufferReference(args)

    offset = min(args.offset, len(self.data))
    sha256 = hashlib.sha256()
    sha256.update(self.data[offset:])
    response.data = sha256.digest()
    response.length = len(self.data[offset:])
    data_store.BLOBS.WriteBlobWithUnknownHash(self.data[offset:])

    return [response]


def TestHuntHelperWithMultipleMocks(client_mocks,
                                    check_flow_errors=False,
                                    token=None,
                                    iteration_limit=None,
                                    worker=None):
  """Runs a hunt with a given set of clients mocks.

  Args:
    client_mocks: Dictionary of (client_id->client_mock) pairs. Client mock
      objects are used to handle client actions. Methods names of a client mock
      object correspond to client actions names. For an example of a client mock
      object, see SampleHuntMock.
    check_flow_errors: If True, raises when one of hunt-initiated flows fails.
    token: An instance of access_control.ACLToken security token.
    iteration_limit: If None, hunt will run until it's finished. Otherwise,
      worker_mock.Next() will be called iteration_limit number of times. Every
      iteration processes worker's message queue. If new messages are sent to
      the queue during the iteration processing, they will be processed on next
      iteration.
    worker: flow_test_lib.TestWorker object to use.

  Returns:
    A number of iterations complete.
  """

  if token is None:
    token = access_control.ACLToken(username="test")

  total_flows = set()

  # Worker always runs with absolute privileges, therefore making the token
  # SetUID().
  token = token.SetUID()

  client_mocks = [
      flow_test_lib.MockClient(client_id, client_mock, token=token)
      for client_id, client_mock in iteritems(client_mocks)
  ]

  if worker is None:
    rel_db_worker = flow_test_lib.TestWorker(threadpool_size=0, token=True)
    data_store.REL_DB.RegisterFlowProcessingHandler(rel_db_worker.ProcessFlow)
  else:
    rel_db_worker = worker

  num_iterations = 0

  try:
    worker_mock = worker_test_lib.MockWorker(
        check_flow_errors=check_flow_errors, token=token)

    # Run the clients and worker until nothing changes any more.
    while iteration_limit is None or num_iterations < iteration_limit:
      client_processed = 0

      for client_mock in client_mocks:
        client_processed += client_mock.Next()

      flows_run = []

      for flow_run in worker_mock.Next():
        total_flows.add(flow_run)
        flows_run.append(flow_run)

      worker_processed = rel_db_worker.ResetProcessedFlows()
      flows_run.extend(worker_processed)

      num_iterations += 1

      if client_processed == 0 and not flows_run and not worker_processed:
        break

    if check_flow_errors:
      flow_test_lib.CheckFlowErrors(total_flows, token=token)
  finally:
    if worker is None:
      data_store.REL_DB.UnregisterFlowProcessingHandler(timeout=60)
      rel_db_worker.Shutdown()

  return num_iterations


def TestHuntHelper(client_mock,
                   client_ids,
                   check_flow_errors=False,
                   token=None,
                   iteration_limit=None,
                   worker=None):
  """Runs a hunt with a given client mock on given clients.

  Args:
    client_mock: Client mock objects are used to handle client actions. Methods
      names of a client mock object correspond to client actions names. For an
      example of a client mock object, see SampleHuntMock.
    client_ids: List of clients ids. Hunt will run on these clients. client_mock
      will be used for every client id.
    check_flow_errors: If True, raises when one of hunt-initiated flows fails.
    token: An instance of access_control.ACLToken security token.
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
      check_flow_errors=check_flow_errors,
      iteration_limit=iteration_limit,
      worker=worker,
      token=token)


class StandardHuntTestMixin(acl_test_lib.AclTestMixin):
  """Mixin with helper methods for hunt tests."""

  def _CreateForemanClientRuleSet(self):
    return foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="CLIENT_NAME", attribute_regex="GRR"))
    ])

  def CreateHunt(self,
                 flow_runner_args=None,
                 flow_args=None,
                 client_rule_set=None,
                 original_object=None,
                 client_rate=0,
                 token=None,
                 **kwargs):
    # Only initialize default flow_args value if default flow_runner_args value
    # is to be used.
    if not flow_runner_args:
      flow_args = (
          flow_args or transfer.GetFileArgs(
              pathspec=rdf_paths.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdf_paths.PathSpec.PathType.OS)))

    flow_runner_args = (
        flow_runner_args or
        rdf_flow_runner.FlowRunnerArgs(flow_name=transfer.GetFile.__name__))

    client_rule_set = (client_rule_set or self._CreateForemanClientRuleSet())

    if data_store.RelationalDBReadEnabled("hunts"):
      token = token or self.token

      hunt_args = rdf_hunt_objects.HuntArguments(
          hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
          standard=rdf_hunt_objects.HuntArgumentsStandard(
              flow_name=flow_runner_args.flow_name, flow_args=flow_args))

      hunt_obj = rdf_hunt_objects.Hunt(
          creator=token.username,
          client_rule_set=client_rule_set,
          original_object=original_object,
          client_rate=client_rate,
          args=hunt_args,
          **kwargs)
      data_store.REL_DB.WriteHuntObject(hunt_obj)

      return hunt_obj.hunt_id

    return implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner_args,
        flow_args=flow_args,
        client_rule_set=client_rule_set,
        client_rate=client_rate,
        original_object=original_object,
        token=token or self.token,
        **kwargs)

  def StartHunt(self, paused=False, **kwargs):
    if data_store.RelationalDBReadEnabled("hunts"):
      hunt_id = self.CreateHunt(**kwargs)
      if not paused:
        hunt.StartHunt(hunt_id)
      return rdfvalue.RDFURN("hunts").Add(hunt_id)
    else:
      with self.CreateHunt(**kwargs) as hunt_obj:
        if not paused:
          hunt_obj.Run()
      return hunt_obj.urn

  def FindForemanRules(self, hunt_obj, token=None):
    if data_store.RelationalDBReadEnabled(category="foreman"):
      rules = data_store.REL_DB.ReadAllForemanRules()
      return [
          rule for rule in rules
          if hunt_obj is None or rule.hunt_id == hunt_obj.urn.Basename()
      ]
    else:
      fman = aff4.FACTORY.Open(
          "aff4:/foreman", mode="r", aff4_type=aff4_grr.GRRForeman, token=token)
      rules = fman.Get(fman.Schema.RULES, [])
      return [
          rule for rule in rules
          if hunt_obj is None or rule.hunt_id == hunt_obj.urn
      ]

  def AssignTasksToClients(self, client_ids=None, worker=None):
    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    client_ids = client_ids or self.client_ids
    foreman_obj = foreman.GetForeman(token=self.token)

    def Assign():
      for client_id in client_ids:
        foreman_obj.AssignTasksToClient(
            rdf_client.ClientURN(client_id).Basename())

    if worker is None:
      with flow_test_lib.TestWorker(threadpool_size=0, token=True):
        Assign()
    else:
      Assign()

  def RunHunt(self,
              client_ids=None,
              iteration_limit=None,
              client_mock=None,
              **mock_kwargs):
    with flow_test_lib.TestWorker(threadpool_size=0, token=True) as test_worker:
      self.AssignTasksToClients(client_ids=client_ids, worker=test_worker)

      if client_mock is None:
        client_mock = SampleHuntMock(**mock_kwargs)
      return TestHuntHelper(
          client_mock,
          client_ids or self.client_ids,
          check_flow_errors=False,
          iteration_limit=iteration_limit,
          worker=test_worker,
          token=self.token)

  def RunHuntWithClientCrashes(self, client_ids):
    with flow_test_lib.TestWorker(threadpool_size=0, token=True) as test_worker:
      client_mocks = dict([(client_id,
                            flow_test_lib.CrashClientMock(
                                client_id, self.token))
                           for client_id in client_ids])
      self.AssignTasksToClients(client_ids=client_ids, worker=test_worker)
      return TestHuntHelperWithMultipleMocks(client_mocks, False, self.token)

  def AddResultsToHunt(self, hunt_id, client_id, values):
    if isinstance(client_id, rdfvalue.RDFURN):
      client_id = client_id.Basename()

    if isinstance(hunt_id, rdfvalue.RDFURN):
      hunt_id = hunt_id.Basename()

    if data_store.RelationalDBReadEnabled("hunts"):
      flow_id = flow_test_lib.StartFlow(
          transfer.GetFile, client_id=client_id, parent_hunt_id=hunt_id)

      for value in values:
        data_store.REL_DB.WriteFlowResults([
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                payload=value)
        ])
    else:
      collection = aff4.FACTORY.Open(
          rdfvalue.RDFURN("hunts").Add(hunt_id),
          token=self.token).ResultCollection()
      with data_store.DB.GetMutationPool() as pool:
        for value in values:
          collection.Add(
              rdf_flows.GrrMessage(payload=value, source=client_id),
              mutation_pool=pool)

  def AddLogToHunt(self, hunt_id, client_id, message):
    if isinstance(client_id, rdfvalue.RDFURN):
      client_id = client_id.Basename()

    if isinstance(hunt_id, rdfvalue.RDFURN):
      hunt_id = hunt_id.Basename()

    if data_store.RelationalDBReadEnabled("hunts"):
      flow_id = flow_test_lib.StartFlow(
          transfer.GetFile, client_id=client_id, parent_hunt_id=hunt_id)

      data_store.REL_DB.WriteFlowLogEntries([
          rdf_flow_objects.FlowLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              message=message)
      ])
    else:
      hunt_obj = aff4.FACTORY.Open(rdfvalue.RDFURN("hunts").Add(hunt_id))
      logs_collection_urn = hunt_obj.logs_collection_urn

      log_entry = rdf_flows.FlowLog(
          client_id=client_id,
          urn=rdf_client.ClientURN(client_id).Add(hunt_id),
          flow_name=hunt_obj.__class__.__name__,
          log_message=message)
      with data_store.DB.GetMutationPool() as pool:
        grr_collections.LogCollection.StaticAdd(
            logs_collection_urn, log_entry, mutation_pool=pool)

  def AddErrorToHunt(self, hunt_id, client_id, message, backtrace):
    if isinstance(client_id, rdfvalue.RDFURN):
      client_id = client_id.Basename()

    if isinstance(hunt_id, rdfvalue.RDFURN):
      hunt_id = hunt_id.Basename()

    if data_store.RelationalDBReadEnabled("hunts"):
      flow_id = flow_test_lib.StartFlow(
          transfer.GetFile, client_id=client_id, parent_hunt_id=hunt_id)
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      flow_obj.flow_state = flow_obj.FlowState.ERROR
      flow_obj.error_message = message
      flow_obj.backtrace = backtrace
      data_store.REL_DB.UpdateFlow(client_id, flow_id, flow_obj=flow_obj)
    else:
      hunt_obj = aff4.FACTORY.Open(rdfvalue.RDFURN("hunts").Add(hunt_id))
      hunt_obj.LogClientError(
          rdf_client.ClientURN(client_id), message, backtrace)

  def GetHuntResults(self, hunt_id):
    """Gets flow results for a given flow.

    Args:
      hunt_id: String with a hunt id or a RDFURN.

    Returns:
      List with hunt results payloads.
    """
    if isinstance(hunt_id, rdfvalue.RDFURN):
      hunt_id = hunt_id.Basename()

    if data_store.RelationalDBReadEnabled("hunts"):
      return data_store.REL_DB.ReadHuntResults(hunt_id, 0, sys.maxsize)
    else:
      hunt_obj = aff4.FACTORY.Open(rdfvalue.RDFURN("hunts").Add(hunt_id))
      return list(hunt_obj.ResultCollection())

  def StopHunt(self, hunt_urn):
    # Stop the hunt now.
    with aff4.FACTORY.Open(
        hunt_urn, age=aff4.ALL_TIMES, mode="rw", token=self.token) as hunt_obj:
      hunt_obj.Stop()

  def ProcessHuntOutputPlugins(self):
    if data_store.RelationalDBFlowsEnabled():
      job = rdf_cronjobs.CronJob(
          cron_job_id="some/id", lifetime=rdfvalue.Duration("1h"))
      run_state = rdf_cronjobs.CronJobRun(
          cron_job_id="some/id",
          status="RUNNING",
          started_at=rdfvalue.RDFDatetime.Now())
      process_results.ProcessHuntResultCollectionsCronJob(run_state, job).Run()
    else:
      flow_urn = flow.StartAFF4Flow(
          flow_name=process_results.ProcessHuntResultCollectionsCronFlow
          .__name__,
          token=self.token)
      flow_test_lib.TestFlowHelper(flow_urn, token=self.token)
      return flow_urn


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
    super(StatefulDummyHuntOutputPlugin, self).__init__(*args, **kwargs)
    self.delta = 0

  def InitializeState(self, state):
    super(StatefulDummyHuntOutputPlugin, self).InitializeState(state)
    state.index = 0

  def ProcessResponses(self, state, responses):
    StatefulDummyHuntOutputPlugin.data.append(state.index + self.delta)
    self.delta += 1

  def UpdateState(self, state):
    state.index += self.delta


class LongRunningDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0

  def ProcessResponses(self, state, responses):
    LongRunningDummyHuntOutputPlugin.num_calls += 1
    # TODO(hanuszczak): This is terrible. Figure out why it has been put here
    # delete it as soon as possible.
    time.time = lambda: 100
