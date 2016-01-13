#!/usr/bin/env python
"""GRR API shell implementation."""

import argparse
import sys


from grr.gui.api_client import api


class GrrApiShellArgParser(argparse.ArgumentParser):
  """API shell args parser."""

  def __init__(self):
    super(GrrApiShellArgParser, self).__init__()

    self.add_argument("api_endpoint", type=str,
                      help="API endpoint specified as host[:port]")
    self.add_argument("--page_size", type=int,
                      help="Page size used when paging through collections "
                      "of items.")


def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    # pylint: disable=g-import-not-at-top
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config
    # pylint: enable=g-import-not-at-top

    cfg = Config()
    cfg.InteractiveShellEmbed.autocall = 2

    shell = InteractiveShellEmbed(config=cfg, user_ns=user_ns,
                                  banner2=banner)
    shell(local_ns=user_ns)
  except ImportError:
    # pylint: disable=g-import-not-at-top
    from IPython import Shell
    # pylint: enable=g-import-not-at-top

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)


def main(argv=None):
  arg_parser = GrrApiShellArgParser()
  flags = arg_parser.parse_args(args=argv or [])

  grr_api = api.InitHttp(**vars(flags))

  IPShell([sys.argv[0]], user_ns=dict(grr=grr_api))


if __name__ == "__main__":
  main(sys.argv[1:])
