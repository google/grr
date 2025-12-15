#!/usr/bin/env python
"""GRR Colab API errors."""
from typing import Optional

from grr_colab import flags
from grr_response_proto import jobs_pb2

FLAGS = flags.FLAGS


class UnknownClientError(Exception):

  def __init__(self, client_id: str, cause: Exception) -> None:
    self.client_id = client_id
    self.cause = cause
    msg = 'Client with id {} does not exist: {}'.format(client_id, cause)
    super().__init__(msg)


class AmbiguousHostnameError(Exception):

  def __init__(self, hostname: str, clients: list[str]) -> None:
    self.hostname = hostname
    self.clients = clients
    msg = 'Too many clients ({}) found for hostname: {}'.format(
        clients, hostname)
    super().__init__(msg)


class UnknownHostnameError(Exception):

  def __init__(self, hostname: str) -> None:
    self.hostname = hostname
    msg = 'No clients found for hostname: {}'.format(hostname)
    super().__init__(msg)


class ApprovalMissingError(Exception):

  def __init__(self, client_id: str, cause: Exception) -> None:
    self.client_id = client_id
    self.cause = cause
    msg = 'No approval to the client {} found: {}'.format(client_id, cause)
    super().__init__(msg)


class FlowTimeoutError(Exception):
  """Raised if a flow is timed out.

  Attributes:
    client_id: Id of the client.
    flow_id: Id of the flow.
    cause: Exception raised.
  """

  def __init__(
      self,
      client_id: str,
      flow_id: str,
      cause: Optional[Exception] = None,
  ) -> None:
    self.client_id = client_id
    self.flow_id = flow_id
    self.cause = cause

    msg = 'Flow with id {} is timed out'.format(flow_id)
    url = self._build_path_to_ui()
    if url is not None:
      msg = '{}. Results will be available at {} when the flow finishes'.format(
          msg, url)
    super().__init__(msg)

  def _build_path_to_ui(self) -> Optional[str]:
    if not FLAGS.grr_admin_ui_url:
      return None
    url = '{}/v2/clients/{}/flows/{}'
    return url.format(FLAGS.grr_admin_ui_url, self.client_id, self.flow_id)


class NotDirectoryError(Exception):

  def __init__(self, client_id: str, path: str) -> None:
    self.client_id = client_id
    self.path = path
    msg = 'Path `{}` for client {} is not a directory'.format(client_id, path)
    super().__init__(msg)


class UnsupportedPathTypeError(Exception):

  def __init__(self, path_type: jobs_pb2.PathSpec.PathType) -> None:
    self.path_type = path_type
    msg = 'Unsupported path type {}'.format(path_type)
    super().__init__(msg)
