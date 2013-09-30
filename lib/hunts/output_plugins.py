#!/usr/bin/env python
"""The various output plugins for GenericHunts."""



import urllib

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import rendering
from grr.lib.aff4_objects import cronjobs
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

  args_type = None
  description = ""

  def __init__(self, hunt_obj, args=None):
    """HuntOutputPlugin constructor.

    HuntOutputPlugin constructor is called during StartHuntFlow and therefore
    runs with security checks enabled (if they're enabled in the config).
    Therefore it's a bad idea to write anything to AFF4 in the constructor.

    Args:
      hunt_obj: Hunt which results this plugin is going to process.
      args: This plugin's arguments.
    """
    self.token = hunt_obj.token
    self.args = args
    self.initialized = False

  def Initialize(self):
    """Initializes the hunt output plugin.

    Initialize() is called when first client's results are processed by the
    hunt. It's called on the worker, so no security checks apply.
    """
    self.initialized = True

  def ProcessResponse(self, response, client_id):
    """Processes the response from the given client.

    ProcessResponse() is called on the worker, so no security checks apply.

    Args:
      response: GrrMessage from the client.
      client_id: Client id of the client.
    """
    pass

  def ProcessResponses(self, responses, client_id):
    """Processes bunch of responses from the given client.

    ProcessResponses() is called on the worker, so no security checks apply.

    Args:
      responses: GrrMessages from the client.
      client_id: client id of the client.
    """
    for response in responses:
      self.ProcessResponse(response, client_id)

  def Flush(self):
    """Flushes the output plugin's state.

    Flush() is called on the worker, so no security checks apply.
    """
    pass


class CollectionPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CollectionPluginArgs


class CollectionPlugin(HuntOutputPlugin):
  """An output plugin that stores the results in a collection."""

  description = "Store results in a collection."
  args_type = CollectionPluginArgs

  def __init__(self, hunt_obj, *args, **kw):
    super(CollectionPlugin, self).__init__(hunt_obj, *args, **kw)
    self.collection_urn = hunt_obj.urn.Add(self.args.collection_name)
    self.collection = None

  def Initialize(self):
    super(CollectionPlugin, self).Initialize()

    # The results will be written to this collection.
    self.collection = aff4.FACTORY.Create(
        self.collection_urn, "RDFValueCollection", mode="rw", token=self.token)
    self.collection.SetChunksize(1024 * 1024)

  def ProcessResponse(self, response, client_id):
    msg = rdfvalue.GrrMessage(payload=response, source=client_id)
    self.collection.Add(msg)

  def ProcessResponses(self, responses, client_id):
    msgs = [rdfvalue.GrrMessage(payload=response, source=client_id)
            for response in responses]
    self.collection.AddAll(msgs)

  def Flush(self):
    self.collection.Flush()

  def GetCollection(self):
    return self.collection


class CronHuntOutputMetadata(aff4.AFF4Object):
  """Metadata AFF4 object used by CronHuntOutputFlow."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """AFF4 schema for CronHuntOutputMetadata."""

    HAS_NEW_RESULTS = aff4.Attribute(
        "aff4:has_new_results", rdfvalue.RDFBool,
        "True if there are new results in the hunt.", versioned=False)

    NUM_PROCESSED_RESULTS = aff4.Attribute(
        "aff4:num_processed_results", rdfvalue.RDFInteger,
        "Number of hunt results already processed by the cron job.",
        versioned=False, default=0)

    CRON_JOB_URN = aff4.Attribute(
        "aff4:cron_job_urn", rdfvalue.RDFURN,
        "URN of a cron job that processes this hunt's output")


class CronHuntOutputFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.CronHuntOutputFlowArgs

  def GetOutputPluginArgsClass(self):
    if self.output_plugin_name:
      output_plugin_cls = HuntOutputPlugin.classes.get(self.output_plugin_name)
      if output_plugin_cls is None:
        raise ValueError("Hunt output plugin '%s' not known by this "
                         "implementation." % self.output_plugin_name)

      # The required protobuf for this class is in args_type.
      return output_plugin_cls.args_type


class CronHuntOutputFlow(flow.GRRFlow):
  """Cron flow scheduled by CronHuntOutputPlugin.

  This flow checks hunt's results collection, and processes new results in
  batch if there are any. It updates NUM_PROCESSES_RESULT attribute of
  CronHuntOutputMetadata object to avoid processing previously processed
  results.

  This has to be inherited and StartBatch(), ProcessResult() and EndBatch()
  methods overriden.
  """

  __abstract = True  # pylint: disable=g-bad-name

  args_type = CronHuntOutputFlowArgs

  def _CheckMetadataAndProcessIfNeeded(self):
    """Checks metadata object and calls ProcessNewResults state if needed.

    Returns:
      True if there were new results to be processed. False otherwise.
    """
    metadata_obj = aff4.FACTORY.Open(
        self.state.args.metadata_urn, aff4_type="CronHuntOutputMetadata",
        mode="rw", token=self.token)

    if metadata_obj.Get(metadata_obj.Schema.HAS_NEW_RESULTS):
      metadata_obj.Set(metadata_obj.Schema.HAS_NEW_RESULTS(False))
      metadata_obj.Close()

      self.CallState(next_state="ProcessNewResults")
      return True
    else:
      return False

  def _IsHuntStarted(self):
    """Returns True if corresponding hunt is paused."""
    hunt_obj = aff4.FACTORY.Open(self.args.hunt_urn, aff4_type="GRRHunt",
                                 mode="r", token=self.token)
    return hunt_obj.GetRunner().IsHuntStarted()

  def _Disable(self):
    metadata_obj = aff4.FACTORY.Open(
        self.state.args.metadata_urn, aff4_type="CronHuntOutputMetadata",
        mode="r", token=self.token)
    cronjobs.CRON_MANAGER.DisableJob(
        metadata_obj.Get(metadata_obj.Schema.CRON_JOB_URN), token=self.token)

  def _ProcessNewResults(self):
    """Processes new hunt's results.

    Opens hunt's results collection and processes newly added results. Calls
    self.StartBatch() then self.ProcessResult() for every result and then
    self.EndBatch(). If there are no new results, self.StartBatch()
    and self.EndBatch() are not called at all.
    """
    hunt_results = aff4.FACTORY.Open(
        self.state.args.hunt_urn.Add(
            self.args.output_plugin_args.collection_name),
        aff4_type="RDFValueCollection",
        mode="r", token=self.token)

    with aff4.FACTORY.Open(
        self.state.args.metadata_urn, aff4_type="CronHuntOutputMetadata",
        mode="rw", token=self.token) as metadata_obj:
      num_processed = int(metadata_obj.Get(
          metadata_obj.Schema.NUM_PROCESSED_RESULTS))

      if len(hunt_results) > num_processed:
        self.Log("Processing %d new results.",
                 len(hunt_results) - num_processed)

        self.StartBatch()

        for i, msg in enumerate(hunt_results):
          if i >= num_processed:
            self.ProcessResult(msg)

        self.EndBatch()

        # Update NUM_PROCESSED_RESULTS so that we don't process results
        # twice.
        metadata_obj.Set(
            metadata_obj.Schema.NUM_PROCESSED_RESULTS(len(hunt_results)))

        self.Log("Done processing.")
      else:
        self.Log("No new results found (current number: %d)", num_processed)

  @flow.StateHandler(next_state="ProcessNewResults")
  def Start(self):
    """Start state."""
    if not self._CheckMetadataAndProcessIfNeeded():
      # If there are no new results, check whether hunt is still running.
      if not self._IsHuntStarted():
        # If the hunt is not running anymore, disable itself.
        self._Disable()

  @flow.StateHandler(next_state=["ProcessNewResults",
                                 "ProcessResultsAfterHuntHasStopped"])
  def ProcessNewResults(self):
    """This state is called if there are new results to process."""
    self._ProcessNewResults()

    if not self._CheckMetadataAndProcessIfNeeded():
      # If there are no new results after we processed results' batch,
      # check whether hunt is still running
      if not self._IsHuntStarted():
        # If the hunt is not running anymore, proceed to
        # ProcessResultsAfterHuntHasStopped state.
        self.CallState(next_state="ProcessResultsAfterHuntHasStopped")

  @flow.StateHandler()
  def ProcessResultsAfterHuntHasStopped(self):
    """This state is called if we detect that hunt has stopped.

    If this state is called, hunt is not running anymore. We process all
    the results that weren't processed before and then disable the cron job.
    """
    self._ProcessNewResults()
    self._Disable()

  def StartBatch(self):
    """Called before processing results batch."""
    pass

  def ProcessResult(self, result):
    """Called for every new result in hunt's results collection."""
    raise NotImplementedError()

  def EndBatch(self):
    """Called after results batch is processed."""
    pass


class CronHuntOutputPlugin(CollectionPlugin):
  """Hunt output plugin that schedules a cron job to process hunt's results."""

  # Name of the flow to be scheduled to process results. The flow should
  # be a subclass of CronHuntOutputFlow.
  cron_flow_name = None
  # Frequency of the cron job that will be scheduled to process new hunt's
  # results.
  frequency = rdfvalue.Duration("5m")

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  def __init__(self, hunt_obj, *args, **kw):
    self.hunt_urn = hunt_obj.urn
    self.output_metadata_urn = hunt_obj.urn.Add("OutputMetadata")
    super(CronHuntOutputPlugin, self).__init__(hunt_obj, *args, **kw)

  def ProcessResponse(self, response, client_id):
    """Does nothing, because results are processed by the cron job."""
    super(CronHuntOutputPlugin, self).ProcessResponse(response, client_id)

  def Flush(self):
    """Updates output metadata object and ensures that cron job is scheduled."""
    super(CronHuntOutputPlugin, self).Flush()

    if not self.cron_flow_name:
      raise ValueError("self.cron_flow_name can not be None.")

    # It's ok to call ScheduleFlow multiple times. As long as job_name
    # doesn't change, nothing will happen if there's an already running
    # job with the same name.
    cron_job_urn = cronjobs.CRON_MANAGER.ScheduleFlow(
        cron_args=rdfvalue.CreateCronJobFlowArgs(
            flow_runner_args=rdfvalue.FlowRunnerArgs(
                flow_name=self.cron_flow_name),
            flow_args=rdfvalue.CronHuntOutputFlowArgs(
                hunt_urn=self.hunt_urn,
                metadata_urn=self.output_metadata_urn,
                output_plugin_name=self.__class__.__name__,
                output_plugin_args=self.args),
            allow_overruns=False,
            periodicity=self.frequency,
            lifetime=rdfvalue.Duration("2h")
            ),
        job_name=self.hunt_urn.Basename() + "_" + self.cron_flow_name,
        disabled=False, token=self.token)

    # Update/create output metadata object. We have to set the HAS_NEW_RESULTS
    # flag so that the cron job knows that there are new results to process.
    with aff4.FACTORY.Create(
        self.output_metadata_urn, aff4_type="CronHuntOutputMetadata", mode="w",
        token=self.token) as metadata_obj:
      metadata_obj.Set(metadata_obj.Schema.HAS_NEW_RESULTS(True))
      # We have to set CRON_JOB_URN in output_metadata so that cron job knows
      # it's own URN so that it can enable/disable/delete itself.
      metadata_obj.Set(metadata_obj.Schema.CRON_JOB_URN(cron_job_urn))


class EmailPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.EmailPluginArgs


class EmailPlugin(HuntOutputPlugin):
  """An output plugin that sends an email for each response received.

  TODO
  """

  description = "Send an email for each result."
  args_type = EmailPluginArgs

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

  too_many_mails_msg = ("<p> This hunt has now produced %d results so the "
                        "sending of emails will be disabled now. </p>")

  def __init__(self, hunt_obj, *args, **kw):
    super(EmailPlugin, self).__init__(hunt_obj, *args, **kw)
    self.hunt_id = hunt_obj.session_id
    self.emails_sent = 0

  def ProcessResponse(self, response, client_id):
    """Sends an email for each response."""

    if self.emails_sent >= self.args.email_limit:
      return

    client = aff4.FACTORY.Open(client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME) or "unknown hostname"

    subject = "GRR Hunt %s produced a new result." % self.hunt_id

    url = urllib.urlencode((("c", client_id),
                            ("main", "HostInformation")))

    response_htm = rendering.FindRendererForObject(response).RawHTML()

    self.emails_sent += 1
    if self.emails_sent == self.args.email_limit:
      additional_message = self.too_many_mails_msg % self.args.email_limit
    else:
      additional_message = ""

    email_alerts.SendEmail(
        self.args.email, "grr-noreply",
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

    return cls(hunt_obj, args=self.plugin_args)
