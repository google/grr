#!/usr/bin/env python
"""A collection of compatibility fixes for client."""
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client


class RDFFindSpec(rdf_client.FindSpec):
  """Clients prior to 2.9.1.0 used this name for this protobuf.

  We need to understand it on the server as well if a response from an old
  client comes in so we define an alias here.
  """


class ClientCompatibility(flow.EventListener):

  EVENTS = ["ClientStartup"]

  well_known_session_id = rdfvalue.SessionID(flow_name="TemporaryFix")

  @flow.EventHandler(allow_client_access=True, auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    client_id = message.source
    # Older client versions do not sent the RDFValue type name explicitly.
    if event is None:
      event = rdf_client.StartupInfo(message.args)

    client_info = event.client_info

    if client_info.client_version < 2910:
      python_hack_root_urn = config_lib.CONFIG.Get("Config.python_hack_root")
      hack_urn = python_hack_root_urn.Add("find_fix.py")

      fd = aff4.FACTORY.Open(hack_urn, token=self.token)
      python_blob = fd.Get(fd.Schema.BINARY)
      if python_blob is None:
        raise flow.FlowError("Python hack %s not found." % hack_urn)

      self.CallClient(client_id, "ExecutePython", python_code=python_blob)
