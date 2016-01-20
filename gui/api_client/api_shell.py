#!/usr/bin/env python
"""GRR API shell implementation."""

import argparse
import sys


from grr.gui.api_client import api
from grr.gui.api_client import api_shell_lib


class GrrApiShellArgParser(argparse.ArgumentParser):
  """API shell args parser."""

  def __init__(self):
    super(GrrApiShellArgParser, self).__init__()

    self.add_argument("api_endpoint", type=str,
                      help="API endpoint specified as host[:port]")
    self.add_argument("--page_size", type=int,
                      help="Page size used when paging through collections "
                      "of items.")


def main(argv=None):
  arg_parser = GrrApiShellArgParser()
  flags = arg_parser.parse_args(args=argv or [])

  grr_api = api.InitHttp(**vars(flags))

  api_shell_lib.IPShell([sys.argv[0]], user_ns=dict(grr=grr_api))


if __name__ == "__main__":
  main(sys.argv[1:])
