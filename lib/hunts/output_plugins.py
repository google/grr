#!/usr/bin/env python
"""The various output plugins for GenericHunts."""



import threading
import urllib

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import rendering
from grr.lib import utils
from grr.proto import flows_pb2


class HuntOutputPlugin(object):
  """The base class for output plugins.

  The way output plugins work is that for each result a hunt produces, all its
  registered output plugins get handed the result to store it in the respective
  format in turn. The methods a plugin has to provide are ProcessResponse which
  gets handed the actual result to process and Flush which is called before
  the output plugin is about to be pickled and stored in the database.
  """

  __metaclass__ = registry.MetaclassRegistry

  name = ""
  description = ""
  args_type = None

  def __init__(self, collection_urn, args=None, token=None, state=None):
    """HuntOutputPlugin constructor.

    HuntOutputPlugin constructor is called during StartHuntFlow and therefore
    runs with security checks enabled (if they're enabled in the config).
    Therefore it's a bad idea to write anything to AFF4 in the constructor.

    Args:
      collection_urn: URN of the collection which results are going to be
                      processed.
      args: This plugin's arguments.
      token: Security token.
      state: Instance of rdfvalue.FlowState. Represents plugin's state. If this
             is passed, no initialization will be performed, only the state will
             be applied.
    Raises:
      ValueError: when state argument is passed together with args or token
                  arguments.
    """
    if state and (token or args):
      raise ValueError("'state' argument can't be passed together with 'args' "
                       "or 'token'.")

    if not state:
      self.state = state or rdfvalue.FlowState()
      self.state.Register("collection_urn", collection_urn)
      self.state.Register("args", args)
      self.state.Register("token", token)
      self.Initialize()
    else:
      self.state = state

    self.args = self.state.args
    self.token = self.state.token

    self.lock = threading.RLock()

  def Initialize(self):
    """Initializes the hunt output plugin.

    Initialize() is called when hunt is created. It can be used to register
    state variables. It's called on the worker, so no security checks apply.
    """

  def ProcessResponses(self, responses):
    """Processes bunch of responses.

    Multiple ProcessResponses() calls can be done in a row. They're *always*
    followed by a Flush() call. ProcessResponses() is called on the worker,
    so no security checks apply.

    NOTE: this method should be thread-safe as it may be called from multiple
    threads to improve hunt output performance.

    Args:
      responses: GrrMessages from the hunt results collection.
    """
    raise NotImplementedError()

  def Flush(self):
    """Flushes the output plugin's state.

    Flush is *always* called after a series of ProcessResponses() calls.
    Flush() is called on the worker, so no security checks apply.

    NOTE: This method doesn't have to be thread-safe as it's called after all
    ProcessResponses() calls are complete.
    """
    pass


# TODO(user): remove as soon as we don't care about old hunts with pickled
# CollectionPluginArgs and CollectionPlugin.
class CollectionPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CollectionPluginArgs


# TODO(user): remove as soon as we don't care about old hunts with pickled
# CollectionPluginArgs and CollectionPlugin.
class CollectionPlugin(HuntOutputPlugin):
  """An output plugin that stores the results in a collection."""

  description = "Store results in a collection."
  args_type = CollectionPluginArgs
  # Making this class abstract, so that it doesn't show up in the UI
  __abstract = True  # pylint: disable=invalid-name

  def ProcessResponses(self, responses):
    pass


class EmailPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.EmailPluginArgs


class EmailPlugin(HuntOutputPlugin):
  """An output plugin that sends an email for each response received.

  TODO
  """

  name = "email"
  description = "Send an email for each result."
  args_type = EmailPluginArgs

  template = """
<html><body><h1>GRR Hunt's results collection %(collection_urn)s got a new result.</h1>

<p>
  Grr Hunt's results collection %(collection_urn)s just got a response from client %(client_id)s
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

  too_many_mails_msg = ("<p> This hunt has now produced %d results so the "
                        "sending of emails will be disabled now. </p>")

  def Initialize(self):
    self.state.Register("emails_sent", 0)
    super(EmailPlugin, self).Initialize()

  def ProcessResponse(self, response):
    """Sends an email for each response."""

    if self.state.emails_sent >= self.state.args.email_limit:
      return

    client_id = response.source
    client = aff4.FACTORY.Open(client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME) or "unknown hostname"

    subject = ("GRR Hunt results collection %s got a new result." %
               self.state.collection_urn)

    url = urllib.urlencode((("c", client_id),
                            ("main", "HostInformation")))

    response_htm = rendering.FindRendererForObject(response).RawHTML()

    self.state.emails_sent += 1
    if self.state.emails_sent == self.state.args.email_limit:
      additional_message = self.too_many_mails_msg % self.state.args.email_limit
    else:
      additional_message = ""

    email_alerts.SendEmail(
        self.state.args.email, "grr-noreply",
        subject,
        self.template % dict(
            client_id=client_id,
            admin_ui=config_lib.CONFIG["AdminUI.url"],
            hostname=hostname,
            urn=url,
            creator=self.token.username,
            collection_urn=self.state.collection_urn,
            response=response_htm,
            additional_message=additional_message,
            ),
        is_html=True)

  @utils.Synchronized
  def ProcessResponses(self, responses):
    for response in responses:
      self.ProcessResponse(response)


class OutputPlugin(rdfvalue.RDFProtoStruct):
  """A proto describing the output plugin to create."""
  protobuf = flows_pb2.OutputPlugin

  def GetPluginArgsClass(self):
    plugin_cls = HuntOutputPlugin.classes.get(self.plugin_name)
    if plugin_cls is not None:
      return plugin_cls.args_type

  def GetPluginForHunt(self, hunt_obj):
    cls = HuntOutputPlugin.classes.get(self.plugin_name)
    if cls is None:
      raise KeyError("Unknown output plugin %s" % self.plugin_name)

    return cls(hunt_obj.state.context.results_collection_urn,
               args=self.plugin_args, token=hunt_obj.token)

  def GetPluginForState(self, plugin_state):
    cls = HuntOutputPlugin.classes.get(self.plugin_name)
    if cls is None:
      raise KeyError("Unknown output plugin %s" % self.plugin_name)

    return cls(None, state=plugin_state)
