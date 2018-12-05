#!/usr/bin/env python
"""API context definition. Context defines request/response behavior."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools


from builtins import map  # pylint: disable=redefined-builtin

from grr_api_client import utils


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

  def _GeneratePages(self, handler_name, args):
    offset = args.offset

    while True:
      args_copy = utils.CopyProto(args)
      args_copy.offset = offset
      args_copy.count = self.connector.page_size
      result = self.connector.SendRequest(handler_name, args_copy)

      yield result

      if not result.items:
        break

      offset += self.connector.page_size

  def SendIteratorRequest(self, handler_name, args):
    if not args or not hasattr(args, "count"):
      result = self.connector.SendRequest(handler_name, args)
      total_count = getattr(result, "total_count", None)
      return utils.ItemsIterator(items=result.items, total_count=total_count)
    else:
      pages = self._GeneratePages(handler_name, args)

      first_page = pages.next()
      total_count = getattr(first_page, "total_count", None)

      page_items = lambda page: page.items
      next_pages_items = itertools.chain.from_iterable(map(page_items, pages))
      all_items = itertools.chain(first_page.items, next_pages_items)

      if args.count:
        all_items = itertools.islice(all_items, args.count)

      return utils.ItemsIterator(items=all_items, total_count=total_count)

  def SendStreamingRequest(self, handler_name, args):
    return self.connector.SendStreamingRequest(handler_name, args)

  @property
  def username(self):
    if not self.user:
      self.user = self.SendRequest("GetGrrUser", None)

    return self.user.username
