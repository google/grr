#!/usr/bin/env python
# Lint as: python3
"""Message handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue

# TODO(amoser): Investigate if we can have a single place (handler_registry.py)
# where we define all the information needed for running message handlers.

session_id_map = {
    str(rdfvalue.SessionID(queue=rdfvalue.RDFURN("E"), flow_name="Enrol")):
        "Enrol",
    str(rdfvalue.SessionID(queue=rdfvalue.RDFURN("S"), flow_name="Stats")):
        "StatsHandler",
    str(rdfvalue.SessionID(flow_name="ClientAlert")):
        "ClientAlertHandler",
    str(rdfvalue.SessionID(flow_name="Foreman")):
        "ForemanHandler",
    str(rdfvalue.SessionID(flow_name="NannyMessage")):
        "NannyMessageHandler",
    str(rdfvalue.SessionID(flow_name="Startup")):
        "ClientStartupHandler",
    str(rdfvalue.SessionID(flow_name="TransferStore")):
        "BlobHandler",
}



class MessageHandler(object):
  """The base class for all message handlers."""

  handler_name = ""

  def ProcessMessages(self, msgs):
    """This is where messages get processed.

    Override in derived classes.

    Args:
      msgs: The GrrMessages sent by the client.
    """
