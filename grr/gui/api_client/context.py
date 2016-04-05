#!/usr/bin/env python
"""API context definition. COntext defines request/response behavior."""


class GrrApiContext(object):
  """API context object. Used to make every API request."""

  def __init__(self, connector=None):
    super(GrrApiContext, self).__init__()

    if not connector:
      raise ValueError("connector can't be None")

    self.connector = connector

  def SendRequest(self, handler_name, args):
    return self.connector.SendRequest(handler_name, args)

  def SendIteratorRequest(self, handler_name, args):
    return self.connector.SendIteratorRequest(handler_name, args)

  def GetDataAttribute(self, data, attribute_name):
    return self.connector.GetDataAttribute(data, attribute_name)
