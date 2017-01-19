#!/usr/bin/env python
"""Helper functions for filestore testing."""

from grr.lib import action_mocks
from grr.lib import events
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import flows as rdf_flows


def AddFileToFileStore(pathspec=None, client_id=None, token=None):
  """Adds file with given pathspec to the hash file store."""
  if pathspec is None:
    raise ValueError("pathspec can't be None")

  if client_id is None:
    raise ValueError("client_id can't be None")

  urn = aff4_grr.VFSGRRClient.PathspecToURN(pathspec, client_id)

  client_mock = action_mocks.GetFileClientMock()
  for _ in test_lib.TestFlowHelper(
      transfer.GetFile.__name__,
      client_mock,
      token=token,
      client_id=client_id,
      pathspec=pathspec):
    pass

  auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
  events.Events.PublishEvent(
      "FileStore.AddFileToStore",
      rdf_flows.GrrMessage(
          payload=urn, auth_state=auth_state),
      token=token)
  worker = test_lib.MockWorker(token=token)
  worker.Simulate()

  return urn
