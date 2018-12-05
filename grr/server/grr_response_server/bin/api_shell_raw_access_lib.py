#!/usr/bin/env python
"""Raw access server-side only API shell."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_api_client import connector
from grr_api_client import errors
from grr_api_client import utils
from grr_response_server import access_control
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.root import api_root_router


class RawConnector(connector.Connector):
  """API connector that uses API routers directly."""

  def __init__(self, page_size=None, token=None):
    super(RawConnector, self).__init__()

    if not page_size:
      raise ValueError("page_size has to be specified.")
    self._page_size = page_size

    if not token:
      raise ValueError("token has to be specified.")
    self._token = token

    self._router = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self._root_router = api_root_router.ApiRootRouter()

  def _MatchRouter(self, method_name, args):
    if (hasattr(self._router, method_name) and
        hasattr(self._root_router, method_name)):
      mdata = self._router.__class__.GetAnnotatedMethods()[method_name]
      root_mdata = self._root_router.__class__.GetAnnotatedMethods()[
          method_name]

      if args is None:
        if mdata.args_type is None:
          return self._router
        elif root_mdata.args_type is None:
          return self._root_router
      else:
        if mdata.args_type and mdata.args_type.protobuf == args.__class__:
          return self._router
        elif (root_mdata.args_type and
              root_mdata.args_type.protobuf == args.__class__):
          return self._root_router

      raise RuntimeError(
          "Can't unambiguously select root/non-root router for %s" %
          method_name)
    elif hasattr(self._router, method_name):
      return self._router
    elif hasattr(self._root_router, method_name):
      return self._root_router

    raise RuntimeError("Can't find method for %s" % method_name)

  def _CallMethod(self, method_name, args):
    router = self._MatchRouter(method_name, args)

    rdf_args = None
    if args is not None:
      mdata = router.__class__.GetAnnotatedMethods()[method_name]
      rdf_args = mdata.args_type()
      rdf_args.ParseFromString(args.SerializeToString())

    method = getattr(router, method_name)
    try:
      handler = method(rdf_args, token=self._token)
      return handler.Handle(rdf_args, token=self._token)
    except access_control.UnauthorizedAccess as e:
      raise errors.AccessForbiddenError(e.message)
    except api_call_handler_base.ResourceNotFoundError as e:
      raise errors.ResourceNotFoundError(e.message)
    except NotImplementedError as e:
      raise errors.ApiNotImplementedError(e.message)
    except Exception as e:  # pylint: disable=broad-except
      raise errors.UnknownError(e.message)

  @property
  def page_size(self):
    return self._page_size

  def SendRequest(self, method_name, args):
    rdf_result = self._CallMethod(method_name, args)

    if rdf_result is not None:
      return rdf_result.AsPrimitiveProto()
    else:
      return None

  def SendStreamingRequest(self, method_name, args):
    binary_stream = self._CallMethod(method_name, args)
    return utils.BinaryChunkIterator(chunks=binary_stream.content_generator)
