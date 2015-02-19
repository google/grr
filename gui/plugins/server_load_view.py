#!/usr/bin/env python
"""Show server load information.

This module provides a monitoring UI for inspecting current state of a server
part of GRR deployment.
"""



from grr.gui import renderers


class ServerLoadView(renderers.AngularDirectiveRenderer):
  """Show server load information."""
  description = "Server Load"
  behaviours = frozenset(["GeneralAdvanced"])

  directive = "grr-server-load"
