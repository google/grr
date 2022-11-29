#!/usr/bin/env python
"""Raw access server-side only API shell."""

import os
import sys

from absl import app
from absl import flags

from grr_api_client import api
from grr_api_client import api_shell_lib
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector
from grr_response_server import server_startup
from grr_response_server.bin import api_shell_raw_access_lib
from grr_response_server.gui import api_call_context

_PAGE_SIZE = flags.DEFINE_integer(
    "page_size", 1000,
    "Page size used when paging through collections of items. Default is 1000.")

_USERNAME = flags.DEFINE_string(
    "username", None, "Username to use when making raw API calls. If not "
    "specified, USER environment variable value will be used.")

_EXEC_CODE = flags.DEFINE_string(
    "exec_code", None,
    "If present, no IPython shell is started but the code given in "
    "the flag is run instead (comparable to the -c option of "
    "IPython). The code will be able to use a predefined "
    "global 'grrapi' object.")

_EXEC_FILE = flags.DEFINE_string(
    "exec_file", None,
    "If present, no IPython shell is started but the code given in "
    "command file is supplied as input instead. The code "
    "will be able to use a predefined global 'grrapi' "
    "object.")

_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the API shell version number and exit immediately.")


def main(argv=None):
  del argv  # Unused.

  if _VERSION.value:
    print("GRR API shell {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  config.CONFIG.AddContext(contexts.CONSOLE_CONTEXT,
                           "Context applied when running the console binary.")
  server_startup.Init()
  fleetspeak_connector.Init()

  username = _USERNAME.value
  if not username:
    username = os.environ["USER"]

  if not username:
    print("Username has to be specified with either --username flag or "
          "USER environment variable.")
    sys.exit(1)

  grrapi = api.GrrApi(
      connector=api_shell_raw_access_lib.RawConnector(
          context=api_call_context.ApiCallContext(username=username),
          page_size=_PAGE_SIZE.value))

  if _EXEC_CODE.value and _EXEC_FILE.value:
    print("--exec_code --exec_file flags can't be supplied together.")
    sys.exit(1)
  elif _EXEC_CODE.value:
    # pylint: disable=exec-used
    exec(_EXEC_CODE.value, dict(grrapi=grrapi))
    # pylint: enable=exec-used
  elif _EXEC_FILE.value:
    api_shell_lib.ExecFile(_EXEC_FILE.value, grrapi)
  else:
    api_shell_lib.IPShell([sys.argv[0]], user_ns=dict(grrapi=grrapi))


if __name__ == "__main__":
  app.run(main)
