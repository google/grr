#!/usr/bin/env python
"""The various output plugins for GenericHunts."""



import urllib

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import rendering
from grr.lib import type_info


class HuntOutputPlugin(object):
  """The base class for output plugins.

  The way output plugins work is that for each result a hunt produces, all its
  registered output plugins get handed the result to store it in the respective
  format in turn. The methods a plugin has to provide are ProcessResponse which
  gets handed the actual result to process and Flush which is called before
  the output plugin is about to be pickled and stored in the database.
  """

  __metaclass__ = registry.MetaclassRegistry

  output_typeinfo = type_info.TypeDescriptorSet()
  description = ""
  args = {}

  def __init__(self, hunt_obj, *unused_args, **kw):
    self.token = hunt_obj.token
    for name, value in self.output_typeinfo.ParseArgs(kw):
      self.args[name] = value

    if kw:
      raise type_info.UnknownArg("%s: Args %s not known" % (
          self.__class__.__name__, kw.keys()))

  def ProcessResponse(self, response, client_id):
    pass

  def Flush(self):
    pass


class CollectionPlugin(HuntOutputPlugin):
  """An output plugin that stores the results in a collection."""

  description = "Store results in a collection."

  def __init__(self, hunt_obj, *args, **kw):
    super(CollectionPlugin, self).__init__(hunt_obj, *args, **kw)

    # The results will be written to this collection.
    self.collection = aff4.FACTORY.Create(
        hunt_obj.urn.Add("Results"), "RDFValueCollection",
        mode="rw", token=self.token)

  def ProcessResponse(self, response, client_id):
    msg = rdfvalue.GrrMessage(payload=response)
    msg.source = client_id
    self.collection.Add(msg)

  def Flush(self):
    self.collection.Flush()

  def GetCollection(self):
    return self.collection


class EmailPlugin(HuntOutputPlugin):
  """An output plugin that sends an email for each response received.

  TODO
  """

  description = "Send an email for each result."

  output_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description=("The address the results should be sent to."),
          name="email"),
      )

  template = """
<html><body><h1>GRR Hunt %(hunt_id)s produced a new result.</h1>

<p>
  Grr Hunt %(hunt_id)s just reported a response from client %(client_id)s
  (%(hostname)s): <br />
  <br />
  %(response)s
  <br />
  Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to
  access this machine. <br />
  This notification was created by %(creator)s.
</p>
%(additional_message)s
<p>Thanks,</p>
<p>The GRR team.</p>
</body></html>"""

  # A hardcoded limit on the number of results to send by mail.
  email_limit = 100

  too_many_mails_msg = ("<p> This hunt has now produced %d results so the "
                        "sending of emails will be disabled now. </p>"
                        % email_limit)

  def __init__(self, hunt_obj, *args, **kw):
    super(EmailPlugin, self).__init__(hunt_obj, *args, **kw)
    self.hunt_id = hunt_obj.session_id
    self.emails_sent = 0

  def ProcessResponse(self, response, client_id):
    """Sends an email for each response."""

    if self.emails_sent >= self.email_limit:
      return

    client = aff4.FACTORY.Open(client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME) or "unknown hostname"

    subject = "GRR Hunt %s produced a new result." % self.hunt_id

    url = urllib.urlencode((("c", client_id),
                            ("main", "HostInformation")))

    response_htm = rendering.renderers.FindRendererForObject(response).RawHTML()

    self.emails_sent += 1
    if self.emails_sent == self.email_limit:
      additional_message = self.too_many_mails_msg
    else:
      additional_message = ""

    email_alerts.SendEmail(
        self.args["email"], "grr-noreply",
        subject,
        self.template % dict(
            client_id=client_id,
            admin_ui=config_lib.CONFIG["AdminUI.url"],
            hostname=hostname,
            urn=url,
            creator=self.token.username,
            hunt_id=self.hunt_id,
            response=response_htm,
            additional_message=additional_message,
            ),
        is_html=True)
