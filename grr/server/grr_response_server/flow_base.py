#!/usr/bin/env python
"""The base class for flow objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import sys
import traceback

from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import aff4_flows
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import db_compat
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import flow_responses
from grr_response_server import notification as notification_lib
from grr_response_server import output_plugin as output_plugin_lib
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


def _TerminateFlow(rdf_flow, reason=None):
  """Does the actual termination."""
  flow_cls = registry.FlowRegistry.FlowClassByName(rdf_flow.flow_class_name)
  flow_obj = flow_cls(rdf_flow)

  if not flow_obj.IsRunning():
    # Nothing to do.
    return

  logging.info("Terminating flow %s on %s, reason: %s", rdf_flow.flow_id,
               rdf_flow.client_id, reason)

  rdf_flow.flow_state = rdf_flow.FlowState.ERROR
  rdf_flow.error_message = reason
  flow_obj.NotifyCreatorOfError()

  data_store.REL_DB.UpdateFlow(
      rdf_flow.client_id,
      rdf_flow.flow_id,
      flow_obj=rdf_flow,
      processing_on=None,
      processing_since=None,
      processing_deadline=None)


def TerminateFlow(client_id, flow_id, reason=None):
  """Terminates a flow and all of its children."""

  to_terminate = [data_store.REL_DB.ReadFlowObject(client_id, flow_id)]

  while to_terminate:
    next_to_terminate = []
    for rdf_flow in to_terminate:
      _TerminateFlow(rdf_flow, reason=reason)
      next_to_terminate.extend(
          data_store.REL_DB.ReadChildFlowObjects(rdf_flow.client_id,
                                                 rdf_flow.flow_id))
    to_terminate = next_to_terminate


class FlowBase(with_metaclass(registry.FlowRegistry, object)):
  """The base class for new style flow objects."""

  # Alternatively we can specify a single semantic protobuf that will be used to
  # provide the args.
  args_type = flow.EmptyFlowArgs

  # This is used to arrange flows into a tree view
  category = ""
  friendly_name = None

  # Behaviors set attributes of this flow. See FlowBehavior() in
  # grr_response_server/flow.py.
  behaviours = flow.FlowBehaviour("ADVANCED")

  def __init__(self, rdf_flow):
    self.rdf_flow = rdf_flow
    self.flow_requests = []
    self.flow_responses = []
    self.client_messages = []
    self.completed_requests = []
    self.replies_to_process = []
    self.replies_to_write = []

    # TODO(amoser): Remove when AFF4 is gone.
    self.token = access_control.ACLToken(username=self.creator)

    self._state = None

    self._client_version = None
    self._client_os = None
    self._client_knowledge_base = None

  def Start(self):
    """The first state of the flow."""

  def End(self, responses):
    """Final state.

    This method is called prior to destruction of the flow.

    Args:
      responses: The responses for this state.
    """

  def HeartBeat(self):
    """New-style flows don't need heart-beat, keeping for compatibility."""
    pass

  def CallState(self, next_state="", start_time=None):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked at a later time.

    Args:
       next_state: The state in this flow to be invoked.
       start_time: Start the flow at this time. This delays notification for
         flow processing into the future. Note that the flow may still be
         processed earlier if there are client responses waiting.

    Raises:
      ValueError: The next state specified does not exist.
    """
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=self.GetNextOutboundId(),
        next_state=next_state,
        start_time=start_time,
        needs_processing=True)

    self.flow_requests.append(flow_request)

  def CallStateInline(self,
                      messages=None,
                      next_state="",
                      request_data=None,
                      responses=None):
    if responses is None:
      responses = flow_responses.FakeResponses(messages, request_data)

    getattr(self, next_state)(responses)

  def CallClient(self,
                 action_cls,
                 request=None,
                 next_state=None,
                 request_data=None,
                 **kwargs):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run action may
    send back many responses that will be queued by the framework until a status
    message is sent by the client. The status message will cause the entire
    transaction to be committed to the specified state.

    Args:
       action_cls: The function to call on the client.
       request: The request to send to the client. If not specified, we create a
         new RDFValue using the kwargs.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: A dict which will be available in the RequestState
         protobuf. The Responses object maintains a reference to this protobuf
         for use in the execution of the state method. (so you can access this
         data by responses.request).
       **kwargs: These args will be used to construct the client action argument
         rdfvalue.

    Raises:
       ValueError: The request passed to the client does not have the correct
                   type.
    """
    if action_cls.in_rdfvalue is None:
      if request:
        raise ValueError(
            "Client action %s does not expect args." % action_cls.__name__)
    else:
      if request is None:
        # Create a new rdf request.
        request = action_cls.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action_cls.in_rdfvalue):
          raise ValueError("Client action expected %s but got %s" %
                           (action_cls.in_rdfvalue, type(request)))

    outbound_id = self.GetNextOutboundId()

    # Create a flow request.
    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=outbound_id,
        next_state=next_state)

    if request_data is not None:
      flow_request.request_data = rdf_protodict.Dict().FromDict(request_data)

    msg = rdf_flows.GrrMessage(
        session_id=self.rdf_flow.long_flow_id,
        name=action_cls.__name__,
        request_id=outbound_id,
        queue=self.rdf_flow.client_id,
        payload=request,
        generate_task_id=True)

    if self.rdf_flow.cpu_limit:
      cpu_usage = self.rdf_flow.cpu_time_used
      msg.cpu_limit = max(
          self.rdf_flow.cpu_limit - cpu_usage.user_cpu_time -
          cpu_usage.system_cpu_time, 0)

      if msg.cpu_limit == 0:
        raise flow.FlowError("CPU limit exceeded.")

    if self.rdf_flow.network_bytes_limit:
      msg.network_bytes_limit = max(
          self.rdf_flow.network_bytes_limit - self.rdf_flow.network_bytes_sent,
          0)
      if msg.network_bytes_limit == 0:
        raise flow.FlowError("Network limit exceeded.")

    self.flow_requests.append(flow_request)
    self.client_messages.append(msg)

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               request_data=None,
               client_id=None,
               base_session_id=None,
               **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: Any dict provided here will be available in the
         RequestState protobuf. The Responses object maintains a reference to
         this protobuf for use in the execution of the state method. (so you can
         access this data by responses.request). There is no format mandated on
         this data but it may be a serialized protobuf.
       client_id: If given, the flow is started for this client.
       base_session_id: A URN which will be used to build a URN.
       **kwargs: Arguments for the child flow.

    Returns:
       The flow_id of the child flow which was created.

    Raises:
      ValueError: The requested next state does not exist.
    """
    if not getattr(self, next_state):
      raise ValueError("Next state %s is invalid." % next_state)

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=self.GetNextOutboundId(),
        next_state=next_state)

    if request_data is not None:
      flow_request.request_data = rdf_protodict.Dict().FromDict(request_data)

    self.flow_requests.append(flow_request)

    flow_cls = registry.FlowRegistry.FlowClassByName(flow_name)

    flow.StartFlow(
        client_id=self.rdf_flow.client_id,
        flow_cls=flow_cls,
        parent_flow_obj=self,
        **kwargs)

  def SendReply(self, response, tag=None):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response: An RDFValue() instance to be sent to the parent.
      tag: If specified, tag the result with this tag.

    Raises:
      ValueError: If responses is not of the correct type.
    """
    if not isinstance(response, rdfvalue.RDFValue):
      raise ValueError("SendReply can only send RDFValues")

    if self.rdf_flow.parent_flow_id:
      response = rdf_flow_objects.FlowResponse(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          payload=response,
          flow_id=self.rdf_flow.parent_flow_id,
          tag=tag)

      self.flow_responses.append(response)
    else:
      reply = rdf_flow_objects.FlowResult(payload=response, tag=tag)
      self.replies_to_write.append(reply)
      self.replies_to_process.append(reply)

    self.rdf_flow.num_replies_sent += 1

  def SaveResourceUsage(self, status):
    """Method to tally resources."""
    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time
    self.rdf_flow.cpu_time_used.user_cpu_time += user_cpu
    self.rdf_flow.cpu_time_used.system_cpu_time += system_cpu

    self.rdf_flow.network_bytes_sent += status.network_bytes_sent

    if self.rdf_flow.cpu_limit:
      user_cpu_total = self.rdf_flow.cpu_time_used.user_cpu_time
      system_cpu_total = self.rdf_flow.cpu_time_used.system_cpu_time
      if self.rdf_flow.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our limit, stop this flow.
        raise flow.FlowError("CPU limit exceeded.")

    if (self.rdf_flow.network_bytes_limit and
        self.rdf_flow.network_bytes_limit < self.rdf_flow.network_bytes_sent):
      # We have exceeded our byte limit, stop this flow.
      raise flow.FlowError("Network bytes limit exceeded.")

  def Error(self, error_message=None, backtrace=None, status=None):
    """Terminates this flow with an error."""
    client_id = self.rdf_flow.client_id
    flow_id = self.rdf_flow.flow_id

    logging.error("Error in flow %s on %s: %s, %s", flow_id, client_id,
                  error_message, backtrace)

    if self.rdf_flow.parent_flow_id or self.rdf_flow.parent_hunt_id:
      status_msg = rdf_flow_objects.FlowStatus(
          client_id=client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          cpu_time_used=self.rdf_flow.cpu_time_used,
          network_bytes_sent=self.rdf_flow.network_bytes_sent,
          error_message=error_message,
          flow_id=self.rdf_flow.parent_flow_id,
          backtrace=backtrace)

      if status is not None:
        status_msg.status = status
      else:
        status_msg.status = rdf_flow_objects.FlowStatus.Status.ERROR

      if self.rdf_flow.parent_flow_id:
        self.flow_responses.append(status_msg)
      elif self.rdf_flow.parent_hunt_id:
        db_compat.ProcessHuntFlowError(
            self.rdf_flow,
            error_message=error_message,
            backtrace=backtrace,
            status_msg=status_msg)

    self.rdf_flow.flow_state = self.rdf_flow.FlowState.ERROR
    if backtrace is not None:
      self.rdf_flow.backtrace = backtrace
    if error_message is not None:
      self.rdf_flow.error_message = error_message

    self.NotifyCreatorOfError()

  def NotifyCreatorOfError(self):
    if self.ShouldSendNotifications():
      client_id = self.rdf_flow.client_id
      flow_id = self.rdf_flow.flow_id

      flow_ref = rdf_objects.FlowReference(client_id=client_id, flow_id=flow_id)
      notification_lib.Notify(
          self.creator, rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_FAILED,
          "Flow %s on %s terminated due to error" % (flow_id, client_id),
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.FLOW,
              flow=flow_ref))

  def _ClearAllRequestsAndResponses(self):
    client_id = self.rdf_flow.client_id
    flow_id = self.rdf_flow.flow_id

    # Remove all requests queued for deletion that we delete in the call below.
    self.completed_requests = [
        r for r in self.completed_requests
        if r.client_id != client_id or r.flow_id != flow_id
    ]

    data_store.REL_DB.DeleteAllFlowRequestsAndResponses(client_id, flow_id)

  def NotifyAboutEnd(self):
    # Sum up number of replies to write with the number of already
    # written results.
    num_results = (
        len(self.replies_to_write) + data_store.REL_DB.CountFlowResults(
            self.rdf_flow.client_id, self.rdf_flow.flow_id))
    flow_ref = rdf_objects.FlowReference(
        client_id=self.rdf_flow.client_id, flow_id=self.rdf_flow.flow_id)
    notification_lib.Notify(
        self.creator, rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        "Flow %s completed with %d %s" % (self.__class__.__name__, num_results,
                                          num_results == 1 and "result" or
                                          "results"),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=flow_ref))

  def MarkDone(self, status=None):
    """Marks this flow as done."""
    # Notify our parent flow or hunt that we are done (if there's a parent flow
    # or hunt).
    if self.rdf_flow.parent_flow_id or self.rdf_flow.parent_hunt_id:
      status = rdf_flow_objects.FlowStatus(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          status=rdf_flow_objects.FlowStatus.Status.OK,
          cpu_time_used=self.rdf_flow.cpu_time_used,
          network_bytes_sent=self.rdf_flow.network_bytes_sent,
          flow_id=self.rdf_flow.parent_flow_id)
      if self.rdf_flow.parent_flow_id:
        self.flow_responses.append(status)
      elif self.rdf_flow.parent_hunt_id:
        db_compat.ProcessHuntFlowDone(self.rdf_flow, status_msg=status)

    self.rdf_flow.flow_state = self.rdf_flow.FlowState.FINISHED

    if self.ShouldSendNotifications():
      self.NotifyAboutEnd()

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    if self.rdf_flow.parent_hunt_id:
      db_compat.ProcessHuntFlowLog(self.rdf_flow, format_str % args)
    else:
      log_entry = rdf_flow_objects.FlowLogEntry(message=format_str % args)
      data_store.REL_DB.WriteFlowLogEntries(self.rdf_flow.client_id,
                                            self.rdf_flow.flow_id, [log_entry])

  def RunStateMethod(self, method_name, request=None, responses=None):
    """Completes the request by calling the state method.

    Args:
      method_name: The name of the state method to call.
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
    """
    if self.rdf_flow.pending_termination:
      self.Error(error_message=self.rdf_flow.pending_termination.reason)
      return

    client_id = self.rdf_flow.client_id

    deadline = self.rdf_flow.processing_deadline
    if deadline and rdfvalue.RDFDatetime.Now() > deadline:
      raise flow.FlowError("Processing time for flow %s on %s expired." %
                           (self.rdf_flow.flow_id, self.rdf_flow.client_id))

    self.rdf_flow.current_state = method_name
    if request and responses:
      logging.debug("Running %s for flow %s on %s, %d responses.", method_name,
                    self.rdf_flow.flow_id, client_id, len(responses))
    else:
      logging.debug("Running %s for flow %s on %s", method_name,
                    self.rdf_flow.flow_id, client_id)

    try:
      try:
        method = getattr(self, method_name)
      except AttributeError:
        raise ValueError("Flow %s has no state method %s" %
                         (self.__class__.__name__, method_name))

      # Prepare a responses object for the state method to use:
      responses = flow_responses.Responses.FromResponses(
          request=request, responses=responses)

      if responses.status is not None:
        self.SaveResourceUsage(responses.status)

      stats_collector_instance.Get().IncrementCounter("grr_worker_states_run")

      if method_name == "Start":
        stats_collector_instance.Get().IncrementCounter(
            "flow_starts", fields=[self.rdf_flow.flow_class_name])
        method()
      else:
        method(responses)

      if self.replies_to_process:
        self._ProcessRepliesWithOutputPlugins(self.replies_to_process)
        self.replies_to_process = []

    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except
      # This flow will terminate now
      stats_collector_instance.Get().IncrementCounter(
          "flow_errors", fields=[self.rdf_flow.flow_class_name])
      logging.exception("Flow %s on %s raised %s.", self.rdf_flow.flow_id,
                        client_id, utils.SmartUnicode(e))

      self.Error(
          error_message=utils.SmartUnicode(e), backtrace=traceback.format_exc())

  def ProcessAllReadyRequests(self):
    """Processes all requests that are due to run.

    Returns:
      The number of processed requests.
    """
    request_dict = data_store.REL_DB.ReadFlowRequestsReadyForProcessing(
        self.rdf_flow.client_id,
        self.rdf_flow.flow_id,
        next_needed_request=self.rdf_flow.next_request_to_process)
    if not request_dict:
      return 0

    processed = 0
    while self.rdf_flow.next_request_to_process in request_dict:
      request, responses = request_dict[self.rdf_flow.next_request_to_process]
      self.RunStateMethod(request.next_state, request, responses)
      self.rdf_flow.next_request_to_process += 1
      processed += 1
      self.completed_requests.append(request)

    if processed and self.IsRunning() and not self.outstanding_requests:
      self.RunStateMethod("End")
      if (self.rdf_flow.flow_state == self.rdf_flow.FlowState.RUNNING and
          not self.outstanding_requests):
        self.MarkDone()

    self.PersistState()

    if not self.IsRunning():
      # All requests and responses can now be deleted.
      self._ClearAllRequestsAndResponses()

    return processed

  @property
  def outstanding_requests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return (
        self.rdf_flow.next_outbound_id - self.rdf_flow.next_request_to_process)

  def GetNextOutboundId(self):
    my_id = self.rdf_flow.next_outbound_id
    self.rdf_flow.next_outbound_id += 1
    return my_id

  def GetCurrentOutboundId(self):
    return self.rdf_flow.next_outbound_id - 1

  def GetNextResponseId(self):
    self.rdf_flow.response_count += 1
    return self.rdf_flow.response_count

  def FlushQueuedMessages(self):
    # TODO(amoser): This could be done in a single db call, might be worth
    # optimizing.

    if self.flow_requests:
      data_store.REL_DB.WriteFlowRequests(self.flow_requests)
      self.flow_requests = []

    if self.flow_responses:
      data_store.REL_DB.WriteFlowResponses(self.flow_responses)
      self.flow_responses = []

    if self.client_messages:
      client_id = self.rdf_flow.client_id
      if fleetspeak_utils.IsFleetspeakEnabledClient(client_id):
        for task in self.client_messages:
          fleetspeak_utils.SendGrrMessageThroughFleetspeak(client_id, task)
      else:
        data_store.REL_DB.WriteClientMessages(self.client_messages)

      self.client_messages = []

    if self.completed_requests:
      data_store.REL_DB.DeleteFlowRequests(self.completed_requests)
      self.completed_requests = []

    if self.replies_to_write:
      # For top-level hunt-induced flows, write results to the hunt collection.
      if self.rdf_flow.parent_hunt_id and not self.rdf_flow.parent_flow_id:
        db_compat.WriteHuntResults(self.rdf_flow.client_id,
                                   self.rdf_flow.parent_hunt_id,
                                   self.replies_to_write)
      else:
        data_store.REL_DB.WriteFlowResults(self.rdf_flow.client_id,
                                           self.rdf_flow.flow_id,
                                           self.replies_to_write)
      self.replies_to_write = []

  def _ProcessRepliesWithOutputPlugins(self, replies):
    """Processes replies with output plugins."""
    for output_plugin_state in self.rdf_flow.output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor
      output_plugin_cls = plugin_descriptor.GetPluginClass()
      output_plugin = output_plugin_cls(
          source_urn=self.rdf_flow.long_flow_id,
          args=plugin_descriptor.plugin_args,
          token=access_control.ACLToken(username=self.rdf_flow.creator))

      try:
        output_plugin.ProcessResponses(output_plugin_state.plugin_state,
                                       [r.payload for r in replies])
        output_plugin.Flush(output_plugin_state.plugin_state)
        output_plugin.UpdateState(output_plugin_state.plugin_state)

        log_item = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="SUCCESS",
            batch_size=len(replies))
        output_plugin_state.Log(log_item)

        self.Log("Plugin %s successfully processed %d flow replies.",
                 plugin_descriptor, len(replies))
      except Exception as e:  # pylint: disable=broad-except
        error = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="ERROR",
            summary=utils.SmartUnicode(e),
            batch_size=len(replies))
        output_plugin_state.Error(error)

        self.Log("Plugin %s failed to process %d replies due to: %s",
                 plugin_descriptor, len(replies), e)

  def MergeQueuedMessages(self, flow_obj):
    self.flow_requests.extend(flow_obj.flow_requests)
    flow_obj.flow_requests = []
    self.flow_responses.extend(flow_obj.flow_responses)
    flow_obj.flow_responses = []
    self.client_messages.extend(flow_obj.client_messages)
    flow_obj.client_messages = []
    self.completed_requests.extend(flow_obj.completed_requests)
    flow_obj.completed_requests = []
    self.replies_to_write.extend(flow_obj.replies_to_write)
    flow_obj.replies_to_write = []

  def ShouldSendNotifications(self):
    return bool(not self.rdf_flow.parent_flow_id and
                not self.rdf_flow.parent_hunt_id and self.creator and
                self.creator not in aff4_users.GRRUser.SYSTEM_USERS)

  def IsRunning(self):
    return self.rdf_flow.flow_state == self.rdf_flow.FlowState.RUNNING

  @property
  def client_id(self):
    return self.rdf_flow.client_id

  @property
  def client_urn(self):
    return rdfvalue.RDFURN(self.client_id)

  @property
  def state(self):
    if self._state is None:
      self._state = flow.AttributedDict(self.rdf_flow.persistent_data.ToDict())
    return self._state

  def PersistState(self):
    if self._state is not None:
      self.rdf_flow.persistent_data = self._state

  @property
  def args(self):
    return self.rdf_flow.args

  @property
  def client_version(self):
    if self._client_version is None:
      self._client_version = data_store_utils.GetClientVersion(self.client_id)

    return self._client_version

  @property
  def client_os(self):
    if self._client_os is None:
      self._client_os = data_store_utils.GetClientOs(self.client_id)

    return self._client_os

  @property
  def client_knowledge_base(self):
    if self._client_knowledge_base is None:
      self._client_knowledge_base = data_store_utils.GetClientKnowledgeBase(
          self.client_id)

    return self._client_knowledge_base

  @property
  def creator(self):
    return self.rdf_flow.creator

  @classmethod
  def GetDefaultArgs(cls, username=None):
    return cls.args_type()


def DualDBFlow(cls):
  """Decorator that creates AFF4 and RELDB flows from a given mixin."""

  if issubclass(cls, flow.GRRFlow):
    raise ValueError("Mixin class shouldn't inherit from GRRFlow.")

  if cls.__name__[-5:] != "Mixin":
    raise ValueError("Flow mixin should have a name that ends in 'Mixin'.")

  flow_name = cls.__name__[:-5]
  aff4_cls = type(flow_name, (cls, flow.GRRFlow), {})
  aff4_cls.__doc__ = cls.__doc__
  setattr(aff4_flows, flow_name, aff4_cls)

  reldb_cls = type(flow_name, (cls, FlowBase), {})
  reldb_cls.__doc__ = cls.__doc__
  setattr(sys.modules[cls.__module__], flow_name, reldb_cls)

  return cls
