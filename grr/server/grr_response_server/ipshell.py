#!/usr/bin/env python
"""A compatibility layer for the IPython shell."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future.builtins import str


# pylint: disable=g-import-not-at-top
def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    from IPython.terminal.embed import InteractiveShellEmbed

    shell = InteractiveShellEmbed(user_ns=user_ns, banner2=str(banner))
    shell(local_ns=user_ns)
  except ImportError:
    from IPython import Shell

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)
