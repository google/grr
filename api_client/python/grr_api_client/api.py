#!/usr/bin/env python
"""Main file of GRR API client library."""

from typing import Any, Optional

from google.protobuf import message
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
from grr_api_client import utils
from grr_api_client import yara
from grr_response_proto import flows_pb2
from grr_response_proto.api import config_pb2
# TODO: Remove this import once the SignedCommands API is
# implemented. Currently required to be able to parse responses from the server.
from grr_response_proto.api import signed_commands_pb2  # pylint: disable=unused-import


class GrrApi(object):
  """Root GRR API object."""

  def __init__(self, connector: connectors.Connector):
    super().__init__()

    self._context = context.GrrApiContext(connector=connector)
    self.types: types.Types = types.Types(context=self._context)
    self.root: root.RootGrrApi = root.RootGrrApi(context=self._context)

  def Client(self, client_id: str) -> client.ClientRef:
    return client.ClientRef(client_id=client_id, context=self._context)

  def SearchClients(
      self,
      query: Optional[str] = None,
  ) -> utils.ItemsIterator[client.Client]:
    return client.SearchClients(query, context=self._context)

  def Hunt(
      self,
      hunt_id: str,
  ) -> hunt.HuntRef:
    return hunt.HuntRef(hunt_id=hunt_id, context=self._context)

  def CreateHunt(
      self,
      flow_name: Optional[str] = None,
      flow_args: Optional[message.Message] = None,
      hunt_runner_args: Optional[flows_pb2.HuntRunnerArgs] = None,
  ) -> hunt.Hunt:
    return hunt.CreateHunt(
        flow_name=flow_name,
        flow_args=flow_args,
        hunt_runner_args=hunt_runner_args,
        context=self._context,
    )

  def ListHunts(self) -> utils.ItemsIterator[hunt.Hunt]:
    return hunt.ListHunts(context=self._context)

  def ListHuntApprovals(self) -> utils.ItemsIterator[hunt.HuntApproval]:
    return hunt.ListHuntApprovals(context=self._context)

  def ListGrrBinaries(self) -> utils.ItemsIterator[config.GrrBinary]:
    return config.ListGrrBinaries(context=self._context)

  def ListArtifacts(self) -> utils.ItemsIterator[artifact.Artifact]:
    return artifact.ListArtifacts(context=self._context)

  def UploadArtifact(self, yaml: str) -> None:
    # pylint: disable=line-too-long
    # fmt: off
    """Uploads the given [YAML artifact definition][1] to the GRR server.

    [1]: https://artifacts.readthedocs.io/en/latest/sources/Format-specification.html

    Args:
      yaml: YAML with the artifact definition.

    Returns:
      Nothing.
    """
    # pylint: enable=line-too-long
    # fmt: on
    return artifact.UploadArtifact(context=self._context, yaml=yaml)

  def GrrBinary(
      self,
      binary_type: config_pb2.ApiGrrBinary.Type,
      path: str,
  ) -> config.GrrBinaryRef:
    return config.GrrBinaryRef(
        binary_type=binary_type, path=path, context=self._context
    )

  def GrrUser(self) -> user.GrrUser:
    return user.GrrUser(context=self._context)

  def UploadYaraSignature(self, signature: str) -> bytes:
    """Uploads the specified YARA signature.

    Args:
      signature: A YARA signature to upload.

    Returns:
      A reference to the uploaded blob.
    """
    return yara.UploadYaraSignature(signature, context=self._context)

  @property
  def username(self) -> str:
    return self._context.username

  def GetOpenApiDescription(self) -> dict[str, Any]:
    """Returns the OpenAPI description of the GRR API as a dictionary."""
    return metadata.GetOpenApiDescription(context=self._context)


def InitHttp(
    api_endpoint: str,
    page_size: Optional[int] = None,
    auth: Optional[tuple[str, str]] = None,
    proxies: Optional[dict[str, str]] = None,
    verify: Optional[bool] = None,
    cert: Optional[bytes] = None,
    trust_env: Optional[bool] = None,
    validate_version: Optional[bool] = None,
) -> GrrApi:
  """Inits an GRR API object with a HTTP connector."""

  connector = connectors.HttpConnector(
      api_endpoint=api_endpoint,
      page_size=page_size,
      auth=auth,
      proxies=proxies,
      verify=verify,
      cert=cert,
      trust_env=trust_env,
      validate_version=validate_version,
  )

  return GrrApi(connector=connector)
