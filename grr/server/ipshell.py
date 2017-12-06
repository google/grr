#!/usr/bin/env python
"""A compatibility layer for the IPython shell."""


# pylint: disable=g-import-not-at-top
def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    from IPython.terminal.embed import InteractiveShellEmbed

    shell = InteractiveShellEmbed(user_ns=user_ns, banner2=unicode(banner))
    shell(local_ns=user_ns)
  except ImportError:
    from IPython import Shell

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)
