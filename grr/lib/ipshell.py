#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A compatibility layer for the IPython shell."""




# pylint: disable=g-import-not-at-top
def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config

    cfg = Config()
    cfg.InteractiveShellEmbed.autocall = 2

    shell = InteractiveShellEmbed(config=cfg, user_ns=user_ns,
                                  banner2=unicode(banner))
    shell(local_ns=user_ns)
  except ImportError:
    from IPython import Shell

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)
