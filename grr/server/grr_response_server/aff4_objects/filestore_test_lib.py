#!/usr/bin/env python
"""Helper functions for filestore testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import events
from grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib


def AddFileToFileStore(pathspec=None, client_id=None, token=None):
  """Adds file with given pathspec to the hash file store."""
  if pathspec is None:
    raise ValueError("pathspec can't be None")

  if client_id is None:
    raise ValueError("client_id can't be None")

  client_mock = action_mocks.GetFileClientMock()
  flow_test_lib.TestFlowHelper(
      transfer.GetFile.__name__,
      client_mock,
      token=token,
      client_id=client_id,
      pathspec=pathspec)

  urn = pathspec.AFF4Path(client_id)
  events.Events.PublishEvent("LegacyFileStore.AddFileToStore", urn, token=token)

  return urn
