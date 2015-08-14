#!/usr/bin/env python
"""Eventlistener flows used to notify about AFF4 changes."""


from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows


class AFF4NotificationEmailListener(flow.EventListener):
  """Email notificator to be used with AFF4 change notifiers."""
  EVENTS = ["AFF4ChangeNotifyByEmail"]

  well_known_session_id = rdfvalue.SessionID(
      flow_name="AFF4ChangeNotifyByEmailHandler")

  mail_template = """<html><body><h1>AFF4 change notification</h1>
Following path got modified: %(path)s"
</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, unused_event=None):
    """Process an event message."""

    # Only accept authenticated messages
    auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
    if message.auth_state != auth_state:
      return

    change_email = config_lib.CONFIG.Get("AFF4.change_email")
    if not change_email:
      return

    urn = aff4.RDFURN(message.args)

    subject = "AFF4 change: %s" % utils.SmartStr(urn)
    email_alerts.EMAIL_ALERTER.SendEmail(
        change_email, "GRR server", subject, self.mail_template % dict(
            path=utils.SmartStr(urn)),
        is_html=True)
