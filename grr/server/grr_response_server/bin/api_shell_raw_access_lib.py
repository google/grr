#!/usr/bin/env python
"""Raw access server-side only API shell."""

from typing import Optional

from google.protobuf import message
from grr_api_client import connectors
from grr_api_client import errors
from grr_api_client import utils
from grr_response_server import access_control
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.root import api_root_router


class RawConnector(connectors.Connector):
  """API connector that uses API routers directly."""

  def __init__(self, page_size=None, context=None):
    super().__init__()

    if not page_size:
      raise ValueError("page_size has to be specified.")
    self._page_size = page_size

    if not context:
      raise ValueError("context has to be specified.")
    self._context = context

    self._router = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self._root_router = api_root_router.ApiRootRouter()

  def _MatchRouter(self, method_name, args):
    if hasattr(self._router, method_name) and hasattr(
        self._root_router, method_name
    ):
      mdata = self._router.__class__.GetAnnotatedMethods()[method_name]
      root_mdata = self._root_router.__class__.GetAnnotatedMethods()[
          method_name
      ]

      if args is None:
        if mdata.proto_args_type is None:
          return self._router
        elif root_mdata.proto_args_type is None:
          return self._root_router
      else:
        if mdata.proto_args_type and mdata.proto_args_type == args.__class__:
          return self._router
        elif (
            root_mdata.proto_args_type
            and root_mdata.proto_args_type == args.__class__
        ):
          return self._root_router

      raise RuntimeError(
          "Can't unambiguously select root/non-root router for %s" % method_name
      )
    elif hasattr(self._router, method_name):
      return self._router
    elif hasattr(self._root_router, method_name):
      return self._root_router

    raise RuntimeError("Can't find method for %s" % method_name)

  def _CallMethod(self, method_name, args):
    router = self._MatchRouter(method_name, args)

    method = getattr(router, method_name)
    try:
      handler = method(args, context=self._context)

      if handler.proto_args_type:
        result = handler.Handle(args, context=self._context)
      else:
        result = handler.Handle(None, context=self._context)

      # Results should be proto messages or binary streams.
      if result and (
          not isinstance(result, message.Message)
          and not isinstance(result, api_call_handler_base.ApiBinaryStream)
      ):
        raise RuntimeError(
            "Invalid result type returned from the API handler. Expected "
            "proto message or binary stream, got %s"
            % result.__class__.__name__
        )

      return result
    except access_control.UnauthorizedAccess as e:
      raise errors.AccessForbiddenError(e)
    except api_call_handler_base.ResourceNotFoundError as e:
      raise errors.ResourceNotFoundError(e)
    except NotImplementedError as e:
      raise errors.ApiNotImplementedError(
          "Method {} is not implemented in {}.".format(
              method_name, type(router).__name__
          )
      ) from e
    except Exception as e:  # pylint: disable=broad-except
      raise errors.UnknownError(e)

  @property
  def page_size(self) -> int:
    return self._page_size

  def SendRequest(  # pytype: disable=signature-mismatch  # overriding-parameter-type-checks
      self,
      handler_name: str,
      args: message.Message,
  ) -> Optional[message.Message]:
    return self._CallMethod(handler_name, args)

  def SendStreamingRequest(
      self,
      handler_name: str,
      args: message.Message,
  ) -> utils.BinaryChunkIterator:
    binary_stream = self._CallMethod(handler_name, args)
    return utils.BinaryChunkIterator(chunks=binary_stream.content_generator)
