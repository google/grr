#!/usr/bin/env python
"""Functions and objects to access config-related GRR API methods."""

from grr_api_client import context as api_context
from grr_api_client import utils
from grr_response_proto import artifact_pb2
from grr_response_proto.api import artifact_pb2 as api_artifact_pb2


class Artifact(object):
  """GRR artifact object with fetched data."""

  def __init__(
      self,
      data: artifact_pb2.ArtifactDescriptor,
      context: api_context.GrrApiContext,
  ):
    self.data = data
    self._context = context


def ListArtifacts(
    context: api_context.GrrApiContext) -> utils.ItemsIterator[Artifact]:
  """Lists all registered Grr artifacts."""
  args = api_artifact_pb2.ApiListArtifactsArgs()

  items = context.SendIteratorRequest("ListArtifacts", args)
  return utils.MapItemsIterator(
      lambda data: Artifact(data=data, context=context), items)
