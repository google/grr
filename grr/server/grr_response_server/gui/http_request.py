#!/usr/bin/env python
"""HTTP request wrapper."""

from __future__ import annotations

from typing import Any

from werkzeug import wrappers as werkzeug_wrappers

from grr_response_core.lib import rdfvalue


class RequestHasNoUserError(AttributeError):
  """Error raised when accessing a user of an unautenticated request."""


class HttpRequest(werkzeug_wrappers.Request):
  """HTTP request object to be used in GRR."""

  charset = "utf-8"
  encoding_errors = "strict"

  def __init__(self, *args: Any, **kwargs: Any):
    super().__init__(*args, **kwargs)

    self._user: str | None = None
    self.email: str | None = None

    self.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    self.parsed_args: Any = None

  @property
  def user(self) -> str:
    if self._user is None:
      raise RequestHasNoUserError(
          "Trying to access Request.user while user is unset."
      )

    if not self._user:
      raise RequestHasNoUserError(
          "Trying to access Request.user while user is empty."
      )

    return self._user

  @user.setter
  def user(self, value: str) -> None:
    if not isinstance(value, str):
      message = "Expected instance of '%s' but got value '%s' of type '%s'"
      message %= (str, value, type(value))
      raise TypeError(message)

    self._user = value
