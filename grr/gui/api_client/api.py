#!/usr/bin/env python
"""Main file of GRR API client library."""

from grr.gui.api_client import client
from grr.gui.api_client import context
from grr.gui.api_client import hunt
from grr.gui.api_client.connectors import http_connector
from grr.proto import flows_pb2


class GrrApi(object):
  """Root GRR API object."""

  class Types(object):
    # pylint: disable=invalid-name
    FlowRunnerArgs = flows_pb2.FlowRunnerArgs
    HuntRunnerArgs = flows_pb2.HuntRunnerArgs
    # pylint: enable=invalid-name

  def __init__(self, connector=None):
    super(GrrApi, self).__init__()

    self.context = context.GrrApiContext(connector=connector)

  def Client(self, client_id):
    return client.ClientRef(client_id=client_id, context=self.context)

  def SearchClients(self, query=None):
    return client.SearchClients(query, context=self.context)

  def Hunt(self, hunt_id):
    return hunt.HuntRef(hunt_id=hunt_id, context=self.context)

  def CreateHunt(self, flow_name=None, flow_args=None, hunt_runner_args=None):
    return hunt.CreateHunt(
        flow_name=flow_name,
        flow_args=flow_args,
        hunt_runner_args=hunt_runner_args,
        context=self.context)

  def ListHunts(self):
    return hunt.ListHunts(context=self.context)

  def ListHuntApprovals(self):
    return hunt.ListHuntApprovals(context=self.context)


def InitHttp(api_endpoint=None, page_size=None, auth=None):
  """Inits an GRR API object with a HTTP connector."""

  connector = http_connector.HttpConnector(
      api_endpoint=api_endpoint, page_size=page_size, auth=auth)

  return GrrApi(connector=connector)
