#!/usr/bin/env python
"""Email live output plugin."""


import jinja2

from grr import config
from grr.lib import utils
from grr.lib.rdfvalues import standard
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import email_alerts
from grr.server.grr_response_server import output_plugin


class EmailOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.EmailOutputPluginArgs
  rdf_deps = [
      standard.DomainEmailAddress,
  ]


class EmailOutputPlugin(output_plugin.OutputPlugin):
  """An output plugin that sends an email for each response received."""

  name = "email"
  description = "Send an email for each result."
  args_type = EmailOutputPluginArgs
  produces_output_streams = False

  subject_template = jinja2.Template(
      "GRR got a new result in {{ source_urn }}.", autoescape=True)
  template = jinja2.Template(
      """
<html><body><h1>GRR got a new result in {{ source_urn }}.</h1>

<p>
  Grr just got a response in {{ source_urn }} from client {{ client_id }}
  ({{ hostname }}).<br />
  <br />
  Click <a href='{{ admin_ui_url }}/#{{ client_fragment_id }}'> here </a> to
  access this machine. <br />
  This notification was created by {{ creator }}.
</p>
{{ additional_message }}
<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
      autoescape=True)

  too_many_mails_msg = ("<p> This hunt has now produced %d results so the "
                        "sending of emails will be disabled now. </p>")

  def InitializeState(self):
    super(EmailOutputPlugin, self).InitializeState()
    self.state.emails_sent = 0

  @utils.Synchronized
  def IncrementCounter(self):
    self.state.emails_sent += 1
    return self.state.args.emails_limit - self.state.emails_sent

  def ProcessResponse(self, response):
    """Sends an email for each response."""
    emails_left = self.IncrementCounter()
    if emails_left < 0:
      return

    client_id = response.source
    client = aff4.FACTORY.Open(client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME) or "unknown hostname"
    client_fragment_id = "/clients/%s" % client_id.Basename()

    if emails_left == 0:
      additional_message = (
          self.too_many_mails_msg % self.state.args.emails_limit)
    else:
      additional_message = ""

    subject = self.__class__.subject_template.render(
        source_urn=utils.SmartUnicode(self.state.source_urn))
    body = self.__class__.template.render(
        client_id=client_id,
        client_fragment_id=client_fragment_id,
        admin_ui_url=config.CONFIG["AdminUI.url"],
        source_urn=self.state.source_urn,
        additional_message=additional_message,
        signature=config.CONFIG["Email.signature"],
        hostname=utils.SmartUnicode(hostname),
        creator=utils.SmartUnicode(self.token.username))

    email_alerts.EMAIL_ALERTER.SendEmail(
        self.state.args.email_address,
        "grr-noreply",
        utils.SmartStr(subject),
        utils.SmartStr(body),
        is_html=True)

  def ProcessResponses(self, responses):
    for response in responses:
      self.ProcessResponse(response)
