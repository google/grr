#!/usr/bin/env python
"""GRR API shell utility functions."""


def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    # pylint: disable=g-import-not-at-top
    # pytype: disable=import-error
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config
    # pytype: enable=import-error
    # pylint: enable=g-import-not-at-top

    cfg = Config()
    cfg.InteractiveShellEmbed.autocall = 2

    shell = InteractiveShellEmbed(config=cfg, user_ns=user_ns)
    shell(local_ns=user_ns)
  except ImportError:
    # pylint: disable=g-import-not-at-top
    from IPython import Shell  # pytype: disable=import-error
    # pylint: enable=g-import-not-at-top

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)


def ExecFile(filepath, grrapi):
  with open(filepath, "r") as filedesc:
    ast = compile(filedesc.read(), filename=filepath, mode="exec")
    exec(ast, {"grrapi": grrapi})  # pylint: disable=exec-used
