#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""Stubs of client actions which can not be loaded on the server.

For example, some client actions require modules which only exist on the client
operating system (e.g. windows specific client actions can not load on the
server.)
"""


from grr.client import actions
from grr.lib import rdfvalue


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_rdfvalue = rdfvalue.WMIRequest
  out_rdfvalue = rdfvalue.Dict


# The following are deprecated client actions which have been removed.
class GetConfig(actions.ActionPlugin):
  """Get configuration - DEPRECATED."""
  out_rdfvalue = rdfvalue.GRRConfig
