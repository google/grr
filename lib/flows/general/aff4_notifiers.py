#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""EventListener flows used to notify about AFF4 changes."""


from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

flags.DEFINE_string("aff4_change_email", None,
                    "Enail used by AFF4NotificationEmailListener to notify "
                    "about AFF4 changes.")


class AFF4NotificationEmailListener(flow.EventListener):
  """Email notificator to be used with AFF4 change notifiers."""
  EVENTS = ["AFF4ChangeNotifyByEmail"]

  well_known_session_id = rdfvalue.SessionID(
      "aff4:/flows/W:AFF4ChangeNotifyByEmailHandler")

  mail_template = """<html><body><h1>AFF4 change notification</h1>
Following path got modified: %(path)s"
</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, unused_event=None):
    """Process an event message."""

    # Only accept authenticated messages
    auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
    if message.auth_state != auth_state:
      return

    if not flags.FLAGS.aff4_change_email:
      return

    urn = aff4.RDFURN()
    urn.ParseFromString(message.args)

    subject = "AFF4 change: %s" % utils.SmartStr(urn)
    email_alerts.SendEmail(flags.FLAGS.aff4_change_email, "GRR server",
                           subject,
                           self.mail_template % dict(
                               path=utils.SmartStr(urn)),
                           is_html=True)
