#!/usr/bin/env python
"""GRR API shell implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging
import sys


from builtins import str  # pylint: disable=redefined-builtin

from grr_api_client import api
from grr_api_client import api_shell_lib


class GrrApiShellArgParser(argparse.ArgumentParser):
  """API shell args parser."""

  def __init__(self):
    super(GrrApiShellArgParser, self).__init__()

    self.add_argument(
        "api_endpoint", type=str, help="API endpoint specified as host[:port]")

    self.add_argument(
        "--page_size",
        type=int,
        help="Page size used when paging through collections of items.")
    self.add_argument(
        "--basic_auth_username",
        type=str,
        help="HTTP basic auth username (HTTP basic auth will be used if this "
        "flag is set).")
    self.add_argument(
        "--basic_auth_password",
        type=str,
        help="HTTP basic auth password (will be used if basic_auth_username is "
        "set).")
    self.add_argument(
        "--no-check-certificate",
        dest="no_check_certificate",
        action="store_true",
        help="If set, don't verify server's SSL certificate.")
    self.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug logging.")
    self.add_argument(
        "--exec_code",
        type=str,
        help="If present, no console is started but the code given "
        "in the flag is run instead (comparable to the -c option "
        "of IPython). The code will be able to use a predefined "
        "global 'grrapi' object.")
    self.add_argument(
        "--exec_file",
        type=str,
        help="If present, no console is started but the code given "
        "in command file is supplied as input instead. The code "
        "will be able to use a predefined global 'grrapi' "
        "object.")


def main(argv=None):
  if not argv:
    argv = sys.argv[1:]

  arg_parser = GrrApiShellArgParser()
  flags = arg_parser.parse_args(args=argv)

  logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stderr))
  if flags.debug:
    logging.getLogger().setLevel(logging.DEBUG)

  auth = None
  if flags.basic_auth_username:
    auth = (flags.basic_auth_username, flags.basic_auth_password or "")

  verify = True
  if flags.no_check_certificate:
    verify = False

  grrapi = api.InitHttp(
      api_endpoint=flags.api_endpoint,
      page_size=flags.page_size,
      auth=auth,
      verify=verify)

  if flags.exec_code and flags.exec_file:
    print("--exec_code --exec_file flags can't be supplied together")
    sys.exit(1)
  elif flags.exec_code:
    # pylint: disable=exec-used
    exec (flags.exec_code, dict(grrapi=grrapi))
    # pylint: enable=exec-used
  elif flags.exec_file:
    api_shell_lib.ExecFile(flags.exec_file, grrapi)
  else:
    api_shell_lib.IPShell([sys.argv[0]], user_ns=dict(grrapi=grrapi))


if __name__ == "__main__":
  main(sys.argv[1:])
