#!/usr/bin/env python
"""Functions and objects to access config-related GRR API methods."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import utils
from grr_response_proto.api import artifact_pb2


class Artifact(object):
  """GRR artifact object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    if not context:
      raise ValueError("context can't be empty")

    self.data = data
    self._context = context


def ListArtifacts(context=None):
  """Lists all registered Grr artifacts."""
  args = artifact_pb2.ApiListArtifactsArgs()

  items = context.SendIteratorRequest("ListArtifacts", args)
  return utils.MapItemsIterator(
      lambda data: Artifact(data=data, context=context), items)
