#!/usr/bin/env python
"""Main file of GRR API client library."""

from grr.gui.api_client import client
from grr.gui.api_client import context
from grr.gui.api_client.connectors import http_connector


class GrrApi(object):
  """Root GRR API object."""

  def __init__(self, connector=None):
    super(GrrApi, self).__init__()

    self.context = context.GrrApiContext(connector=connector)

  def Client(self, client_id):
    return client.ClientRef(client_id=client_id, context=self.context)

  def SearchClients(self, query=None):
    for c in client.SearchClients(query, context=self.context):
      yield c


def InitHttp(api_endpoint=None, page_size=None, auth=None):
  """Inits an GRR API object with a HTTP connector."""

  connector = http_connector.HttpConnector(api_endpoint=api_endpoint,
                                           page_size=page_size,
                                           auth=auth)

  return GrrApi(connector=connector)
