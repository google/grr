#!/usr/bin/env python
"""Helper functions for filestore testing."""

from grr.lib.rdfvalues import flows as rdf_flows
from grr.server import events
from grr.server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import worker_test_lib


def AddFileToFileStore(pathspec=None, client_id=None, token=None):
  """Adds file with given pathspec to the hash file store."""
  if pathspec is None:
    raise ValueError("pathspec can't be None")

  if client_id is None:
    raise ValueError("client_id can't be None")

  urn = pathspec.AFF4Path(client_id)

  client_mock = action_mocks.GetFileClientMock()
  for _ in flow_test_lib.TestFlowHelper(
      transfer.GetFile.__name__,
      client_mock,
      token=token,
      client_id=client_id,
      pathspec=pathspec):
    pass

  auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
  events.Events.PublishEvent(
      "FileStore.AddFileToStore",
      rdf_flows.GrrMessage(payload=urn, auth_state=auth_state),
      token=token)
  worker = worker_test_lib.MockWorker(token=token)
  worker.Simulate()

  return urn
