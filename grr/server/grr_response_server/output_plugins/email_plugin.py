#!/usr/bin/env python
"""Email output plugin."""

from typing import Iterable

import jinja2

from grr_response_core import config
from grr_response_proto import flows_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import output_plugin


class EmailOutputPlugin(
    output_plugin.OutputPluginProto[output_plugin_pb2.EmailOutputPluginArgs]
):
  """An output plugin that sends an email for each response received."""

  name = "email"
  description = "Send an email for each result."
  args_type = output_plugin_pb2.EmailOutputPluginArgs

  subject_template = jinja2.Template(
      "GRR got a new result batch in {{ source_urn }}.", autoescape=True
  )
  template = jinja2.Template(
      """
<html><body><h1>GRR got a new result batch in {{ source_urn }}.</h1>

<p>
  Grr just got a new result batch (size {{ num_responses }}) in {{ source_urn }} from client {{ client_id }}
  ({{ hostname }}).<br />
  <br />
  Click <a href='{{ admin_ui_url }}/v2{{ client_fragment_id }}'> here </a> to
  access this machine. <br />
</p>
<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
      autoescape=True,
  )

  def ProcessResults(self, responses: Iterable[flows_pb2.FlowResult]) -> None:
    """Sends an email for each response."""
    responses = list(responses)
    if len(responses) < 1:
      return

    response = responses[0]
    num_responses = len(responses)

    client_id = response.client_id
    client = data_store.REL_DB.ReadClientSnapshot(client_id)
    hostname = client.knowledge_base.fqdn or "unknown hostname"
    client_fragment_id = "/clients/%s" % client_id

    subject = self.__class__.subject_template.render(
        source_urn=str(self.source_urn)
    )
    body = self.__class__.template.render(
        client_id=client_id,
        client_fragment_id=client_fragment_id,
        admin_ui_url=config.CONFIG["AdminUI.url"],
        source_urn=self.source_urn,
        num_responses=num_responses,
        signature=config.CONFIG["Email.signature"],
        hostname=hostname,
    )

    email_alerts.EMAIL_ALERTER.SendEmail(
        self.args.email_address, "grr-noreply", subject, body, is_html=True
    )
