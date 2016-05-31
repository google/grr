#!/usr/bin/env python
"""Clients-related part of GRR API client library."""

from grr.gui.api_client import flow
from grr.gui.api_client import utils
from grr.proto import api_pb2


class ClientBase(object):
  """Base class for Client and ClientRef."""

  def __init__(self, client_id=None, context=None):
    super(ClientBase, self).__init__()

    if not client_id:
      raise ValueError("client_id can't be empty.")

    if not context:
      raise ValueError("context can't be empty.")

    self.client_id = client_id
    self._context = context

  def Flow(self, flow_id):
    """Return a reference to a flow with a given id on this client."""

    return flow.FlowRef(client_id=self.client_id,
                        flow_id=flow_id,
                        context=self._context)

  def CreateFlow(self, name=None, args=None, runner_args=None):
    """Create new flow on this client."""

    if not name:
      raise ValueError("name can't be empty")

    request = api_pb2.ApiCreateFlowArgs(client_id=self.client_id)

    request.flow.name = name
    if runner_args:
      request.flow.runner_args = runner_args

    if args:
      request.flow.args.value = args.SerializeToString()
      request.flow.args.type_url = utils.GetTypeUrl(args)

    data = self._context.SendRequest("CreateFlow", request)
    return flow.Flow(data=data, context=self._context)

  def ListFlows(self, offset=0, count=0):
    """List flows that ran on this client."""

    args = api_pb2.ApiListFlowsArgs(client_id=self.client_id,
                                    offset=offset,
                                    count=count)

    items = self._context.SendIteratorRequest("ListFlows", args)
    return utils.MapItemsIterator(
        lambda data: flow.Flow(data=data, context=self._context),
        items)


class ClientRef(ClientBase):
  """Ref to the client."""

  def Get(self):
    """Fetch client's data and return a proper Client object."""

    args = api_pb2.ApiGetClientArgs(client_id=self.client_id)
    result = self._context.SendRequest("GetClient", args)
    return Client(data=result["client"], context=self._context)


class Client(ClientBase):
  """Client object with fetched data."""

  def __init__(self, data=None, context=None):

    if data is None:
      raise ValueError("data can't be None")
    client_id = utils.UrnToClientId(context.GetDataAttribute(data, "urn"))

    super(Client, self).__init__(client_id=client_id, context=context)

    self.data = data


def SearchClients(query=None, context=None):
  """List clients conforming to a givent query."""

  args = api_pb2.ApiSearchClientsArgs(query=query)

  items = context.SendIteratorRequest("SearchClients", args)
  return utils.MapItemsIterator(
      lambda data: Client(data=data, context=context),
      items)
