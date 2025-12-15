#!/usr/bin/env python
"""API context definition. Context defines request/response behavior."""

from collections.abc import Iterator
import itertools
from typing import Any, Optional

from google.protobuf import message
from grr_api_client import connectors
from grr_api_client import utils
from grr_response_proto.api import user_pb2


class GrrApiContext(object):
  """API context object. Used to make every API request."""

  def __init__(self, connector: connectors.Connector):
    super().__init__()

    self.connector: connectors.Connector = connector
    self.user: Optional[user_pb2.ApiGrrUser] = None

  def SendRequest(
      self,
      handler_name: str,
      args: Optional[message.Message],
  ) -> Optional[message.Message]:
    return self.connector.SendRequest(handler_name, args)

  # TODO(hanuszczak): Once only Python 3.8 is supported, these `Any` calls can
  # be refactored with protocols (or better yet: completely removed and replaced
  # with properly typed methods).

  def _GeneratePages(
      self,
      handler_name: str,
      args: Any,
  ) -> Iterator[message.Message]:
    """Generates iterator pages."""
    offset = args.offset

    while True:
      args_copy = utils.CopyProto(args)
      args_copy.offset = offset
      args_copy.count = self.connector.page_size
      result = self.connector.SendRequest(handler_name, args_copy)

      if result is None:
        detail = f"No response returned for '{handler_name}'"
        raise TypeError(detail)
      if not hasattr(result, "items"):
        detail = f"Incorrect result type for '{handler_name}': {type(result)}"
        raise TypeError(detail)

      yield result

      if not result.items:
        break

      offset += self.connector.page_size

  def SendIteratorRequest(
      self,
      handler_name: str,
      args: Any,
  ) -> utils.ItemsIterator:
    """Sends an iterator request."""
    if not args or not hasattr(args, "count"):
      result = self.connector.SendRequest(handler_name, args)

      if not hasattr(result, "items"):
        detail = f"Incorrect result type for '{handler_name}': {type(result)}"
        raise TypeError(detail)

      total_count = getattr(result, "total_count", None)
      return utils.ItemsIterator(items=result.items, total_count=total_count)
    else:
      pages = self._GeneratePages(handler_name, args)
      first_page = next(pages)
      total_count = getattr(first_page, "total_count", None)

      def PageItems(page: message.Message) -> Iterator[message.Message]:
        if not hasattr(page, "items"):
          detail = f"Incorrect page type for '{handler_name}': {type(page)}"
          raise TypeError(detail)

        return page.items

      next_pages_items = itertools.chain.from_iterable(map(PageItems, pages))
      all_items = itertools.chain(PageItems(first_page), next_pages_items)

      if args.count:
        all_items = itertools.islice(all_items, args.count)

      return utils.ItemsIterator(items=all_items, total_count=total_count)

  def SendStreamingRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> utils.BinaryChunkIterator:
    return self.connector.SendStreamingRequest(handler_name, args)

  @property
  def username(self) -> str:
    if self.user is None:
      self.user = self.SendRequest("GetGrrUser", None)  # pytype: disable=annotation-type-mismatch  # bind-properties

    return self.user.username  # pytype: disable=attribute-error  # bind-properties
