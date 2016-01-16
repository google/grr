#!/usr/bin/env python
"""Stubs of client actions which can not be loaded on the server.

For example, some client actions require modules which only exist on the client
operating system (e.g. windows specific client actions can not load on the
server.)
"""


from grr.client import actions
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict as rdf_protodict


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_rdfvalue = rdf_client.WMIRequest
  out_rdfvalues = [rdf_protodict.Dict]


class OSXEnumerateRunningServices(actions.ActionPlugin):
  """Enumerate all running launchd jobs."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_client.OSXServiceInformation]
