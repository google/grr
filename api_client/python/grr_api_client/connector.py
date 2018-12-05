#!/usr/bin/env python
"""API connector base class definition."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class Connector(object):

  @property
  def page_size(self):
    raise NotImplementedError()

  def SendRequest(self, handler_name, args):
    raise NotImplementedError()

  def SendStreamingRequest(self, handler_name, args):
    raise NotImplementedError()
