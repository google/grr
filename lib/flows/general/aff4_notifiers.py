#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""EventListener flows used to notify about AFF4 changes."""


from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

flags.DEFINE_string("aff4_change_email", None,
                    "Enail used by AFF4NotificationEmailListener to notify "
                    "about AFF4 changes.")


class AFF4NotificationEmailListener(flow.EventListener):
  """Email notificator to be used with AFF4 change notifiers."""
  EVENTS = ["AFF4ChangeNotifyByEmail"]

  well_known_session_id = "aff4:/flows/W:AFF4ChangeNotifyByEmailHandler"

  mail_template = """<html><body><h1>AFF4 change notification</h1>
Following path got modified: %(path)s"
</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, unused_event=None):
    """Process an event message."""

    # Only accept authenticated messages
    if message.auth_state != rdfvalue.GRRMessage.Enum("AUTHENTICATED"):
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
