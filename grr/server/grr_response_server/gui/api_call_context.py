#!/usr/bin/env python
# Lint as: python3
"""Api call context used during the request/response handling."""

from typing import Optional

from grr_response_server.rdfvalues import objects as rdf_objects


class ApiCallContext:
  """Context used throughout an API call handling."""

  def __init__(self,
               username: str,
               approval: Optional[rdf_objects.ApprovalRequest] = None):
    self._username = username
    self._approval = approval

  @property
  def username(self) -> str:
    return self._username

  @property
  def approval(self) -> Optional[rdf_objects.ApprovalRequest]:
    return self._approval

  @approval.setter
  def approval(self, value: Optional[rdf_objects.ApprovalRequest]):
    self._approval = value

  def __repr__(self) -> str:
    return (f"<ApiCallContext(username={self._username}, "
            f"approval={repr(self._approval)})>")
