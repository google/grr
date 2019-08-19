#!/usr/bin/env python
"""Clients-related part of GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_api_client import utils
from grr_response_proto.api import user_pb2


class Notification(object):
  """GRR user notification object with fetched data."""

  def __init__(self, data=None, context=None):
    if data is None:
      raise ValueError("data can't be None")

    if not context:
      raise ValueError("context can't be empty")

    self.data = data
    self._context = context


class GrrUser(object):
  """GRR user object describing the current API user."""

  def __init__(self, context=None):
    if not context:
      raise ValueError("context can't be empty")

    self._context = context

  @property
  def username(self):
    return self._context.username

  def GetPendingNotificationsCount(self):
    return self._context.SendRequest("GetPendingUserNotificationsCount",
                                     None).count

  def ListPendingNotifications(self, timestamp=None):
    args = user_pb2.ApiListPendingUserNotificationsArgs()
    if timestamp is not None:
      args.timestamp = timestamp

    items = self._context.SendIteratorRequest("ListPendingUserNotifications",
                                              args)
    return utils.MapItemsIterator(
        lambda data: Notification(data=data, context=self._context), items)
