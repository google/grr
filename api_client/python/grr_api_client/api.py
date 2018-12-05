#!/usr/bin/env python
"""Main file of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import client
from grr_api_client import config
from grr_api_client import context
from grr_api_client import hunt
from grr_api_client import root
from grr_api_client import types
from grr_api_client.connectors import http_connector


class GrrApi(object):
  """Root GRR API object."""

  def __init__(self, connector=None):
    super(GrrApi, self).__init__()

    self._context = context.GrrApiContext(connector=connector)
    self.types = types.Types(context=self._context)
    self.root = root.RootGrrApi(context=self._context)

  def Client(self, client_id):
    return client.ClientRef(client_id=client_id, context=self._context)

  def SearchClients(self, query=None):
    return client.SearchClients(query, context=self._context)

  def Hunt(self, hunt_id):
    return hunt.HuntRef(hunt_id=hunt_id, context=self._context)

  def CreateHunt(self, flow_name=None, flow_args=None, hunt_runner_args=None):
    return hunt.CreateHunt(
        flow_name=flow_name,
        flow_args=flow_args,
        hunt_runner_args=hunt_runner_args,
        context=self._context)

  def ListHunts(self):
    return hunt.ListHunts(context=self._context)

  def ListHuntApprovals(self):
    return hunt.ListHuntApprovals(context=self._context)

  def ListGrrBinaries(self):
    return config.ListGrrBinaries(context=self._context)

  def GrrBinary(self, binary_type, path):
    return config.GrrBinaryRef(
        binary_type=binary_type, path=path, context=self._context)

  @property
  def username(self):
    return self._context.username


def InitHttp(api_endpoint=None,
             page_size=None,
             auth=None,
             proxies=None,
             verify=None,
             cert=None,
             trust_env=True):
  """Inits an GRR API object with a HTTP connector."""

  connector = http_connector.HttpConnector(
      api_endpoint=api_endpoint,
      page_size=page_size,
      auth=auth,
      proxies=proxies,
      verify=verify,
      cert=cert,
      trust_env=trust_env)

  return GrrApi(connector=connector)
