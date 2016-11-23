#!/usr/bin/env python
"""GRR API shell implementation."""

import argparse
import sys


import logging

from grr.gui.api_client import api
from grr.gui.api_client import api_shell_lib


class GrrApiShellArgParser(argparse.ArgumentParser):
  """API shell args parser."""

  def __init__(self):
    super(GrrApiShellArgParser, self).__init__()

    self.add_argument(
        "api_endpoint", type=str, help="API endpoint specified as host[:port]")
    self.add_argument(
        "--page_size",
        type=int,
        help="Page size used when paging through collections "
        "of items.")
    self.add_argument(
        "--basic_auth_username",
        type=str,
        help="HTTP basic auth username (HTTP basic auth will be used if this "
        "flag is set.")
    self.add_argument(
        "--basic_auth_password",
        type=str,
        help="HTTP basic auth password (will be used if basic_auth_username is "
        "set.")
    self.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug logging.")


def main(argv=None):
  arg_parser = GrrApiShellArgParser()
  flags = arg_parser.parse_args(args=argv or [])

  logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stderr))
  if flags.debug:
    logging.getLogger().setLevel(logging.DEBUG)

  auth = None
  if flags.basic_auth_username:
    auth = (flags.basic_auth_username, flags.basic_auth_password or "")

  grrapi = api.InitHttp(
      api_endpoint=flags.api_endpoint, page_size=flags.page_size, auth=auth)

  api_shell_lib.IPShell([sys.argv[0]], user_ns=dict(grrapi=grrapi))


if __name__ == "__main__":
  main(sys.argv[1:])
