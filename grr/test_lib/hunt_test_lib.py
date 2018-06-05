#!/usr/bin/env python
"""Classes for hunt-related testing."""

import time

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import foreman
from grr.server.grr_response_server import foreman_rules
from grr.server.grr_response_server import output_plugin
from grr.server.grr_response_server.flows.general import transfer
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import process_results
from grr.server.grr_response_server.hunts import standard
from grr.test_lib import acl_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import worker_test_lib


class SampleHuntMock(object):
  """Client mock for sample hunts."""

  def __init__(self,
               failrate=2,
               data="Hello World!",
               user_cpu_time=None,
               system_cpu_time=None,
               network_bytes_sent=None):
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
    response = rdf_client.StatEntry(
        pathspec=args.pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_dev=64512L,
        st_nlink=1,
        st_uid=139592,
        st_gid=5000,
        st_size=len(self.data),
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    self.responses += 1
    self.count += 1

    # Create status message to report sample resource usage
    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
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

    # Every "failrate" client does not have this file.
    if self.count == self.failrate:
      self.count = 0
      return [status]

    return [response, status]

  def TransferBuffer(self, args):
    """TransferBuffer action mock."""
    response = rdf_client.BufferReference(args)

    offset = min(args.offset, len(self.data))
    response.data = self.data[offset:]
    response.length = len(self.data[offset:])
    return [response]


def TestHuntHelperWithMultipleMocks(client_mocks,
                                    check_flow_errors=False,
                                    token=None,
                                    iteration_limit=None):
  """Runs a hunt with a given set of clients mocks.

  Args:
    client_mocks: Dictionary of (client_id->client_mock) pairs. Client mock
        objects are used to handle client actions. Methods names of a client
        mock object correspond to client actions names. For an example of a
        client mock object, see SampleHuntMock.
    check_flow_errors: If True, raises when one of hunt-initiated flows fails.
    token: An instance of access_control.ACLToken security token.
    iteration_limit: If None, hunt will run until it's finished. Otherwise,
        worker_mock.Next() will be called iteration_limit number of times.
        Every iteration processes worker's message queue. If new messages
        are sent to the queue during the iteration processing, they will
        be processed on next iteration,
  """

  total_flows = set()

  # Worker always runs with absolute privileges, therefore making the token
  # SetUID().
  token = token.SetUID()

  client_mocks = [
      flow_test_lib.MockClient(client_id, client_mock, token=token)
      for client_id, client_mock in client_mocks.iteritems()
  ]
  worker_mock = worker_test_lib.MockWorker(
      check_flow_errors=check_flow_errors, token=token)

  # Run the clients and worker until nothing changes any more.
  while iteration_limit is None or iteration_limit > 0:
    client_processed = 0

    for client_mock in client_mocks:
      client_processed += client_mock.Next()

    flows_run = []

    for flow_run in worker_mock.Next():
      total_flows.add(flow_run)
      flows_run.append(flow_run)

    if client_processed == 0 and not flows_run:
      break

    if iteration_limit:
      iteration_limit -= 1

  if check_flow_errors:
    flow_test_lib.CheckFlowErrors(total_flows, token=token)


def TestHuntHelper(client_mock,
                   client_ids,
                   check_flow_errors=False,
                   token=None,
                   iteration_limit=None):
  """Runs a hunt with a given client mock on given clients.

  Args:
    client_mock: Client mock objects are used to handle client actions.
        Methods names of a client mock object correspond to client actions
        names. For an example of a client mock object, see SampleHuntMock.
    client_ids: List of clients ids. Hunt will run on these clients.
        client_mock will be used for every client id.
    check_flow_errors: If True, raises when one of hunt-initiated flows fails.
    token: An instance of access_control.ACLToken security token.
    iteration_limit: If None, hunt will run until it's finished. Otherwise,
        worker_mock.Next() will be called iteration_limit number of tiems.
        Every iteration processes worker's message queue. If new messages
        are sent to the queue during the iteration processing, they will
        be processed on next iteration.
  """
  TestHuntHelperWithMultipleMocks(
      dict([(client_id, client_mock) for client_id in client_ids]),
      check_flow_errors=check_flow_errors,
      iteration_limit=iteration_limit,
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
        rdf_flows.FlowRunnerArgs(flow_name=transfer.GetFile.__name__))

    client_rule_set = (client_rule_set or self._CreateForemanClientRuleSet())
    return implementation.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner_args,
        flow_args=flow_args,
        client_rule_set=client_rule_set,
        client_rate=0,
        original_object=original_object,
        token=token or self.token,
        **kwargs)

  def StartHunt(self, **kwargs):
    with self.CreateHunt(**kwargs) as hunt:
      hunt.Run()

    return hunt.urn

  def AssignTasksToClients(self, client_ids=None):
    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    client_ids = client_ids or self.client_ids
    foreman_obj = foreman.GetForeman(token=self.token)
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(
          rdf_client.ClientURN(client_id).Basename())

  def RunHunt(self, client_ids=None, iteration_limit=None, **mock_kwargs):
    client_mock = SampleHuntMock(**mock_kwargs)
    TestHuntHelper(
        client_mock,
        client_ids or self.client_ids,
        check_flow_errors=False,
        iteration_limit=iteration_limit,
        token=self.token)

  def StopHunt(self, hunt_urn):
    # Stop the hunt now.
    with aff4.FACTORY.Open(
        hunt_urn, age=aff4.ALL_TIMES, mode="rw", token=self.token) as hunt_obj:
      hunt_obj.Stop()

  def ProcessHuntOutputPlugins(self, **flow_args):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=process_results.ProcessHuntResultCollectionsCronFlow.__name__,
        token=self.token,
        **flow_args)
    flow_test_lib.TestFlowHelper(flow_urn, token=self.token)
    return flow_urn


class DummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, responses):
    DummyHuntOutputPlugin.num_calls += 1
    DummyHuntOutputPlugin.num_responses += len(list(responses))


class FailingDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    raise RuntimeError("Oh no!")


class FailingInFlushDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass

  def Flush(self):
    raise RuntimeError("Flush, oh no!")


class StatefulDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  data = []

  def InitializeState(self):
    super(StatefulDummyHuntOutputPlugin, self).InitializeState()
    self.state.index = 0

  def ProcessResponses(self, unused_responses):
    StatefulDummyHuntOutputPlugin.data.append(self.state.index)
    self.state.index += 1


class LongRunningDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0

  def ProcessResponses(self, unused_responses):
    LongRunningDummyHuntOutputPlugin.num_calls += 1
    # TODO(hanuszczak): This is terrible. Figure out why it has been put here
    # delete it as soon as possible.
    time.time = lambda: 100


class VerifiableDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass


class VerifiableDummyHuntOutputPluginVerfier(
    output_plugin.OutputPluginVerifier):
  """One of the dummy hunt output plugins."""
  plugin_name = VerifiableDummyHuntOutputPlugin.__name__

  num_calls = 0

  def VerifyHuntOutput(self, plugin, hunt):
    # Check that we get the plugin object we expected to get.
    # Actual verifiers implementations don't have to do this check.
    if not isinstance(plugin, VerifiableDummyHuntOutputPlugin):
      raise ValueError(
          "Passed plugin must be an "
          "VerifiableDummyHuntOutputPlugin, got: " % plugin.__class__.__name__)

    VerifiableDummyHuntOutputPluginVerfier.num_calls += 1
    return output_plugin.OutputPluginVerificationResult(
        status="SUCCESS", status_message="yo")

  def VerifyFlowOutput(self, plugin, hunt):
    pass


class DummyHuntOutputPluginWithRaisingVerifier(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass


class DummyHuntOutputPluginWithRaisingVerifierVerifier(
    output_plugin.OutputPluginVerifier):
  """One of the dummy hunt output plugins."""
  plugin_name = DummyHuntOutputPluginWithRaisingVerifier.__name__

  def VerifyHuntOutput(self, plugin, hunt):
    # Check that we get the plugin object we expected to get.
    # Actual verifiers implementations don't have to do this check.
    if not isinstance(plugin, DummyHuntOutputPluginWithRaisingVerifier):
      raise ValueError(
          "Passed plugin must be an "
          "VerifiableDummyHuntOutputPlugin, got: " % plugin.__class__.__name__)

    raise RuntimeError("foobar")

  def VerifyFlowOutput(self, plugin, hunt):
    pass
