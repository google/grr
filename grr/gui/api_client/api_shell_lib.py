#!/usr/bin/env python
"""GRR API shell utility functions."""


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
