#!/usr/bin/env python
"""API connector base class definition."""


class Connector(object):

  def SendRequest(self, handler_name, args):
    raise NotImplementedError()

  def SendIteratorRequest(self, handler_name, args):
    raise NotImplementedError()
