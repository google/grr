#!/usr/bin/env python
"""API context definition. Context defines request/response behavior."""


class GrrApiContext(object):
  """API context object. Used to make every API request."""

  def __init__(self, connector=None):
    super(GrrApiContext, self).__init__()

    if not connector:
      raise ValueError("connector can't be None")

    self.connector = connector
    self.user = None

  def SendRequest(self, handler_name, args):
    return self.connector.SendRequest(handler_name, args)

  def SendIteratorRequest(self, handler_name, args):
    return self.connector.SendIteratorRequest(handler_name, args)

  def SendStreamingRequest(self, handler_name, args):
    return self.connector.SendStreamingRequest(handler_name, args)

  @property
  def username(self):
    if not self.user:
      self.user = self.SendRequest("GetGrrUser", None)

    return self.user.username
