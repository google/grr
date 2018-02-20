#!/usr/bin/env python
"""Classes for hunt-related testing."""

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows

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

  def StatFile(self, args):
    """StatFile action mock."""
    req = rdf_client.ListDirRequest(args)

    response = rdf_client.StatEntry(
        pathspec=req.pathspec,
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
