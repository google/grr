#!/usr/bin/env python
"""Main file of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any
from typing import Dict
from typing import Text

from grr_api_client import artifact
from grr_api_client import client
from grr_api_client import config
from grr_api_client import connectors
from grr_api_client import context
from grr_api_client import hunt
from grr_api_client import metadata
from grr_api_client import root
from grr_api_client import types
from grr_api_client import user
from grr_api_client import yara
from grr_response_proto.api import hunt_pb2


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

  def CreatePerClientFileCollectionHunt(
      self, hunt_args: hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs
  ) -> hunt.Hunt:
    return hunt.CreatePerClientFileCollectionHunt(
        hunt_args, context=self._context)

  def ListHunts(self):
    return hunt.ListHunts(context=self._context)

  def ListHuntApprovals(self):
    return hunt.ListHuntApprovals(context=self._context)

  def ListGrrBinaries(self):
    return config.ListGrrBinaries(context=self._context)

  def ListArtifacts(self):
    return artifact.ListArtifacts(context=self._context)

  def GrrBinary(self, binary_type, path):
    return config.GrrBinaryRef(
        binary_type=binary_type, path=path, context=self._context)

  def GrrUser(self):
    return user.GrrUser(context=self._context)

  def UploadYaraSignature(self, signature: Text) -> bytes:
    """Uploads the specified YARA signature.

    Args:
      signature: A YARA signature to upload.

    Returns:
      A reference to the uploaded blob.
    """
    return yara.UploadYaraSignature(signature, context=self._context)

  @property
  def username(self):
    return self._context.username

  def GetOpenApiDescription(self) -> Dict[str, Any]:
    """Returns the OpenAPI description of the GRR API as a dictionary."""
    return metadata.GetOpenApiDescription(context=self._context)


def InitHttp(api_endpoint=None,
             page_size=None,
             auth=None,
             proxies=None,
             verify=None,
             cert=None,
             trust_env=True,
             validate_version=True):
  """Inits an GRR API object with a HTTP connector."""

  connector = connectors.HttpConnector(
      api_endpoint=api_endpoint,
      page_size=page_size,
      auth=auth,
      proxies=proxies,
      verify=verify,
      cert=cert,
      trust_env=trust_env,
      validate_version=validate_version)

  return GrrApi(connector=connector)
