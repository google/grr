#!/usr/bin/env python
"""Raw access server-side only API shell."""

import os
import sys
import traceback


# pylint: disable=unused-import,g-bad-import-order
from grr.server.grr_response_server import server_plugins
# pylint: enable=g-bad-import-order


from grr import config
from grr_api_client import api
from grr_api_client import api_shell_lib
from grr_api_client import connector
from grr_api_client import errors
from grr_api_client import utils
from grr.config import contexts
from grr.config import server as config_server
from grr.lib import flags
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import fleetspeak_connector
from grr.server.grr_response_server import server_startup
from grr.server.grr_response_server.gui import api_call_handler_base
from grr.server.grr_response_server.gui import api_call_router_without_checks
from grr.server.grr_response_server.gui.root import api_root_router

flags.DEFINE_integer(
    "page_size", 1000,
    "Page size used when paging through collections of items. Default is 1000.")

flags.DEFINE_string(
    "username", None, "Username to use when making raw API calls. If not "
    "specified, USER environment variable value will be used.")

flags.DEFINE_string(
    "exec_code", None,
    "If present, no IPython shell is started but the code given in "
    "the flag is run instead (comparable to the -c option of "
    "IPython). The code will be able to use a predefined "
    "global 'grrapi' object.")

flags.DEFINE_string(
    "exec_file", None,
    "If present, no IPython shell is started but the code given in "
    "command file is supplied as input instead. The code "
    "will be able to use a predefined global 'grrapi' "
    "object.")

flags.DEFINE_version(config_server.VERSION["packageversion"])


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
      traceback.print_exc()
      raise errors.AccessForbiddenError(e.message)
    except api_call_handler_base.ResourceNotFoundError as e:
      traceback.print_exc()
      raise errors.ResourceNotFoundError(e.message)
    except NotImplementedError as e:
      traceback.print_exc()
      raise errors.ApiNotImplementedError(e.message)
    except Exception as e:  # pylint: disable=broad-except
      traceback.print_exc()
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


def main(argv=None):
  del argv  # Unused.

  config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  config.CONFIG.AddContext(contexts.CONSOLE_CONTEXT,
                           "Context applied when running the console binary.")
  server_startup.Init()
  fleetspeak_connector.Init()

  username = flags.FLAGS.username
  if not username:
    username = os.environ["USER"]

  if not username:
    print("Username has to be specified with either --username flag or "
          "USER environment variable.")
    sys.exit(1)

  grrapi = api.GrrApi(
      connector=RawConnector(
          token=access_control.ACLToken(username=username),
          page_size=flags.FLAGS.page_size))

  if flags.FLAGS.exec_code and flags.FLAGS.exec_file:
    print "--exec_code --exec_file flags can't be supplied together."
    sys.exit(1)
  elif flags.FLAGS.exec_code:
    # pylint: disable=exec-used
    exec (flags.FLAGS.exec_code, dict(grrapi=grrapi))
    # pylint: enable=exec-used
  elif flags.FLAGS.exec_file:
    execfile(flags.FLAGS.exec_file, dict(grrapi=grrapi))
  else:
    api_shell_lib.IPShell([sys.argv[0]], user_ns=dict(grrapi=grrapi))


if __name__ == "__main__":
  flags.StartMain(main)
