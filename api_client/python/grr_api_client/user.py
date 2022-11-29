#!/usr/bin/env python
"""Clients-related part of GRR API client library."""

from typing import Optional

from grr_api_client import context as api_context
from grr_api_client import utils
from grr_response_proto.api import user_pb2


class Notification(object):
  """GRR user notification object with fetched data."""

  def __init__(
      self,
      data: user_pb2.ApiNotification,
      context: api_context.GrrApiContext,
  ):
    self.data: user_pb2.ApiNotification = data
    self._context: api_context.GrrApiContext = context


class GrrUser(object):
  """GRR user object describing the current API user."""

  def __init__(
      self,
      context: api_context.GrrApiContext,
  ):
    self._context: api_context.GrrApiContext = context

  @property
  def username(self) -> str:
    return self._context.username

  def GetPendingNotificationsCount(self) -> int:
    response = self._context.SendRequest("GetPendingUserNotificationsCount",
                                         None)
    if not isinstance(response,
                      user_pb2.ApiGetPendingUserNotificationsCountResult):
      raise TypeError(f"Unexpected response type: {type(response)}")

    return response.count

  def ListPendingNotifications(
      self,
      timestamp: Optional[int] = None,
  ) -> utils.ItemsIterator[Notification]:
    """Lists pending notifications for the user."""
    args = user_pb2.ApiListPendingUserNotificationsArgs()
    if timestamp is not None:
      args.timestamp = timestamp

    items = self._context.SendIteratorRequest("ListPendingUserNotifications",
                                              args)
    return utils.MapItemsIterator(
        lambda data: Notification(data=data, context=self._context), items)
