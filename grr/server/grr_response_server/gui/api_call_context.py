#!/usr/bin/env python
"""Api call context used during the request/response handling."""

from typing import Optional

from grr_response_proto import objects_pb2


class ApiCallContext:
  """Context used throughout an API call handling."""

  def __init__(
      self,
      username: str,
      approval: Optional[objects_pb2.ApprovalRequest] = None,
  ):
    self._username = username
    self._approval = approval

  @property
  def username(self) -> str:
    return self._username

  @property
  def approval(self) -> Optional[objects_pb2.ApprovalRequest]:
    return self._approval

  @approval.setter
  def approval(self, value: Optional[objects_pb2.ApprovalRequest]):
    self._approval = value

  def __repr__(self) -> str:
    return (
        f"<ApiCallContext(username={self._username}, "
        f"approval={repr(self._approval)})>"
    )
