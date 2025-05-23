#!/usr/bin/env python
"""Email live output plugin."""

import jinja2

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import output_plugin


class EmailOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.EmailOutputPluginArgs
  rdf_deps = [
      rdf_standard.DomainEmailAddress,
  ]


class EmailOutputPlugin(output_plugin.OutputPlugin):
  """An output plugin that sends an email for each response received."""

  name = "email"
  description = "Send an email for each result."
  args_type = EmailOutputPluginArgs

  subject_template = jinja2.Template(
      "GRR got a new result in {{ source_urn }}.", autoescape=True
  )
  template = jinja2.Template(
      """
<html><body><h1>GRR got a new result in {{ source_urn }}.</h1>

<p>
  Grr just got a response in {{ source_urn }} from client {{ client_id }}
  ({{ hostname }}).<br />
  <br />
  Click <a href='{{ admin_ui_url }}/v2{{ client_fragment_id }}'> here </a> to
  access this machine. <br />
</p>
{{ additional_message }}
<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
      autoescape=True,
  )

  too_many_mails_msg = (
      "<p> This hunt has now produced %d results so the "
      "sending of emails will be disabled now. </p>"
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.emails_sent = 0

  def InitializeState(self, state):
    state.emails_sent = 0

  @utils.Synchronized
  def IncrementCounter(self):
    self.emails_sent += 1
    return self.emails_sent

  def ProcessResponse(self, state, response):
    """Sends an email for each response."""
    emails_left = self.args.emails_limit - self.IncrementCounter()
    if emails_left < 0:
      return

    client_id = response.client_id
    client = data_store.REL_DB.ReadClientSnapshot(client_id)
    hostname = client.knowledge_base.fqdn or "unknown hostname"
    client_fragment_id = "/clients/%s" % client_id

    if emails_left == 0:
      additional_message = self.too_many_mails_msg % self.args.emails_limit
    else:
      additional_message = ""

    subject = self.__class__.subject_template.render(
        source_urn=str(self.source_urn)
    )
    body = self.__class__.template.render(
        client_id=client_id,
        client_fragment_id=client_fragment_id,
        admin_ui_url=config.CONFIG["AdminUI.url"],
        source_urn=self.source_urn,
        additional_message=additional_message,
        signature=config.CONFIG["Email.signature"],
        hostname=hostname,
    )

    email_alerts.EMAIL_ALERTER.SendEmail(
        self.args.email_address, "grr-noreply", subject, body, is_html=True
    )

  def ProcessResponses(self, state, responses):
    for response in responses:
      self.ProcessResponse(state, response)

  def UpdateState(self, state):
    state.emails_sent += self.emails_sent
