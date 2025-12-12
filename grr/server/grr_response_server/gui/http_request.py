#!/usr/bin/env python
"""HTTP request wrapper."""

from werkzeug import wrappers as werkzeug_wrappers

from grr_response_core.lib import rdfvalue


class RequestHasNoUserError(AttributeError):
  """Error raised when accessing a user of an unautenticated request."""


class HttpRequest(werkzeug_wrappers.Request):
  """HTTP request object to be used in GRR."""

  charset = "utf-8"
  encoding_errors = "strict"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self._user = None
    self.email = None

    self.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    self.parsed_args = None

  @property
  def user(self):
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
  def user(self, value):
    if not isinstance(value, str):
      message = "Expected instance of '%s' but got value '%s' of type '%s'"
      message %= (str, value, type(value))
      raise TypeError(message)

    self._user = value
