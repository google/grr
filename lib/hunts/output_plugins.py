#!/usr/bin/env python
"""The various output plugins for GenericHunts."""



import csv
import threading
import urllib

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import export
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


class EmailPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.EmailPluginArgs


class EmailPlugin(HuntOutputPlugin):
  """An output plugin that sends an email for each response received."""

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
<p>%(signature)s</p>
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
            signature=config_lib.CONFIG["Email.signature"]
            ),
        is_html=True)

  @utils.Synchronized
  def ProcessResponses(self, responses):
    for response in responses:
      self.ProcessResponse(response)


class CSVOutputPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CSVOutputPluginArgs


class CSVOutputPlugin(HuntOutputPlugin):
  """Hunt output plugin that writes hunt's results to CSV file on AFF4.

  CSV files are written incrementally. After every batch of results is written,
  the file can be downloaded.

  TODO(user): add support for zipped CSV files. Produce compressed CSV
  files while retaining the capability to do incremental updates and have files
  in downloadable state after every update is not exactly trivial.
  """

  name = "csv"
  description = "Write CSV file to AFF4"
  args_type = CSVOutputPluginArgs

  def Initialize(self):
    super(CSVOutputPlugin, self).Initialize()
    self.state.Register("files_by_type", {})
    self.state.Register("last_updated", rdfvalue.RDFDatetime().Now())

  def ProcessResponses(self, responses):
    default_metadata = rdfvalue.ExportedMetadata(
        source_urn=self.state.collection_urn)

    if self.state.args.convert_values:
      # This is thread-safe - we just convert the values.
      converted_responses = export.ConvertValues(
          default_metadata, responses, token=self.state.token,
          options=self.state.args.export_options)
    else:
      converted_responses = responses

    # This is not thread-safe, therefore WriteValueToCSVFile is synchronized.
    self.WriteValuesToCSVFile(converted_responses)

  def GetCSVHeader(self, value_class, prefix=""):
    header = []
    for type_info in value_class.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        header.extend(
            self.GetCSVHeader(type_info.type, prefix=type_info.name + "."))
      else:
        header.append(prefix + type_info.name)

    return header

  def WriteCSVHeader(self, output_file, value_type):
    value_class = rdfvalue.RDFValue.classes[value_type]
    csv.writer(output_file).writerow(self.GetCSVHeader(value_class))

  def GetCSVRow(self, value):
    row = []
    for type_info in value.__class__.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        row.extend(self.GetCSVRow(value.Get(type_info.name)))
      else:
        row.append(value.Get(type_info.name))

    return row

  def WriteCSVRow(self, output_file, value):
    csv.writer(output_file).writerow(self.GetCSVRow(value))

  def GetOutputFile(self, value_type):
    """Initializes output AFF4Image for a given value type."""
    try:
      output_file = self.state.files_by_type[value_type]
    except KeyError:
      if self.state.args.output_dir:
        output_urn = self.state.args.output_dir.Add(value_type + ".csv")
        output_file = aff4.FACTORY.Create(output_urn, "AFF4Image",
                                          token=self.token)
      else:
        output_file = aff4.FACTORY.Create(None, "TempImageFile",
                                          token=self.token)
        output_file.urn = output_file.urn.Add(value_type + ".csv")

      self.WriteCSVHeader(output_file, value_type)
      self.state.files_by_type[value_type] = output_file

    return output_file

  @utils.Synchronized
  def WriteValuesToCSVFile(self, values):
    for value in values:
      output_file = self.GetOutputFile(value.__class__.__name__)
      self.WriteCSVRow(output_file, value)

  def Flush(self):
    for output_file in self.state.files_by_type.values():
      output_file.Flush()
    self.last_updated = rdfvalue.RDFDatetime().Now()


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
