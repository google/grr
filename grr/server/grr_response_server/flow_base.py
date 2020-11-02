#!/usr/bin/env python
# Lint as: python3
"""The base class for flow objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import traceback
from typing import Iterator, NamedTuple, Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.registry import FlowRegistry
from grr_response_core.lib.util import compatibility
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import flow_responses
from grr_response_server import hunt
from grr_response_server import notification as notification_lib
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects

FLOW_STARTS = metrics.Counter("flow_starts", fields=[("flow", str)])
FLOW_ERRORS = metrics.Counter("flow_errors", fields=[("flow", str)])
FLOW_COMPLETIONS = metrics.Counter("flow_completions", fields=[("flow", str)])
GRR_WORKER_STATES_RUN = metrics.Counter("grr_worker_states_run")
HUNT_OUTPUT_PLUGIN_ERRORS = metrics.Counter(
    "hunt_output_plugin_errors", fields=[("plugin", str)])
HUNT_RESULTS_RAN_THROUGH_PLUGIN = metrics.Counter(
    "hunt_results_ran_through_plugin", fields=[("plugin", str)])


class Error(Exception):
  """Base class for this package's exceptions."""


class FlowError(Error):
  """A generic flow error."""


# TODO(hanuszczak): Consider refactoring the interface of this class.
class FlowBehaviour(object):
  """A Behaviour is a property of a flow.

  Behaviours advertise what kind of flow this is. The flow can only advertise
  predefined behaviours.
  """

  # A constant which defines all the allowed behaviours and their descriptions.
  LEXICON = {
      # What GUI mode should this flow appear in?
      "BASIC":
          "Include in the simple UI. This flow is designed for simpler use.",
      "ADVANCED":
          "Include in advanced UI. This flow takes more experience to use.",
      "DEBUG":
          "This flow only appears in debug mode.",
  }

  def __init__(self, *args):
    self.set = set()
    for arg in args:
      if arg not in self.LEXICON:
        raise ValueError("Behaviour %s not known." % arg)

      self.set.add(str(arg))

  def __add__(self, other):
    other = str(other)

    if other not in self.LEXICON:
      raise ValueError("Behaviour %s not known." % other)

    return self.__class__(other, *list(self.set))

  def __sub__(self, other):
    other = str(other)

    result = self.set.copy()
    result.discard(other)

    return self.__class__(*list(result))

  def __iter__(self):
    return iter(self.set)


BEHAVIOUR_ADVANCED = FlowBehaviour("ADVANCED")
BEHAVIOUR_BASIC = FlowBehaviour("ADVANCED", "BASIC")
BEHAVIOUR_DEBUG = FlowBehaviour("DEBUG")


def _TerminateFlow(rdf_flow,
                   reason=None,
                   flow_state=rdf_flow_objects.Flow.FlowState.ERROR):
  """Does the actual termination."""
  flow_cls = FlowRegistry.FlowClassByName(rdf_flow.flow_class_name)
  flow_obj = flow_cls(rdf_flow)

  if not flow_obj.IsRunning():
    # Nothing to do.
    return

  logging.info("Terminating flow %s on %s, reason: %s", rdf_flow.flow_id,
               rdf_flow.client_id, reason)

  rdf_flow.flow_state = flow_state
  rdf_flow.error_message = reason
  flow_obj.NotifyCreatorOfError()

  data_store.REL_DB.UpdateFlow(
      rdf_flow.client_id,
      rdf_flow.flow_id,
      flow_obj=rdf_flow,
      processing_on=None,
      processing_since=None,
      processing_deadline=None)
  data_store.REL_DB.DeleteAllFlowRequestsAndResponses(rdf_flow.client_id,
                                                      rdf_flow.flow_id)


def TerminateFlow(client_id,
                  flow_id,
                  reason=None,
                  flow_state=rdf_flow_objects.Flow.FlowState.ERROR):
  """Terminates a flow and all of its children.

  Args:
    client_id: Client ID of a flow to terminate.
    flow_id: Flow ID of a flow to terminate.
    reason: String with a termination reason.
    flow_state: Flow state to be assigned to a flow after termination. Defaults
      to FlowState.ERROR.
  """

  to_terminate = [data_store.REL_DB.ReadFlowObject(client_id, flow_id)]

  while to_terminate:
    next_to_terminate = []
    for rdf_flow in to_terminate:
      _TerminateFlow(rdf_flow, reason=reason, flow_state=flow_state)
      next_to_terminate.extend(
          data_store.REL_DB.ReadChildFlowObjects(rdf_flow.client_id,
                                                 rdf_flow.flow_id))
    to_terminate = next_to_terminate


# This is a mypy-friendly way of defining named tuples:
# https://mypy.readthedocs.io/en/stable/kinds_of_types.html#named-tuples
class ClientPathArchiveMapping(NamedTuple):
  """Mapping between a client path and a path inside an archive."""

  client_path: db.ClientPath
  archive_path: str


class FlowBase(metaclass=FlowRegistry):
  """The base class for new style flow objects."""

  # Alternatively we can specify a single semantic protobuf that will be used to
  # provide the args.
  args_type = rdf_flows.EmptyFlowArgs

  # (Optional) An RDFProtoStruct to be produced by the flow's 'progress'
  # property. To be used by the API/UI to report on the flow's progress in a
  # structured way.
  progress_type = None

  # This is used to arrange flows into a tree view
  category = ""
  friendly_name = None

  # Behaviors set attributes of this flow. See FlowBehavior() in
  # grr_response_server/flow.py.
  behaviours = BEHAVIOUR_ADVANCED

  # Tuple, containing the union of all possible types this flow might
  # return. By default, any RDFValue migth be returned.
  result_types = (rdfvalue.RDFValue,)

  def __init__(self, rdf_flow):
    self.rdf_flow = rdf_flow
    self.flow_requests = []
    self.flow_responses = []
    self.client_action_requests = []
    self.completed_requests = []
    self.replies_to_process = []
    self.replies_to_write = []

    # TODO(amoser): Remove when AFF4 is gone.
    self.token = access_control.ACLToken(username=self.creator)

    self._state = None

    self._client_version = None
    self._client_os = None
    self._client_knowledge_base = None
    self._client_info: Optional[rdf_client.ClientInformation] = None

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
    try:
      action_identifier = action_registry.ID_BY_ACTION_STUB[action_cls]
    except KeyError:
      raise ValueError("Action class %s not known." % action_cls)

    if action_cls.in_rdfvalue is None:
      if request:
        raise ValueError("Client action %s does not expect args." % action_cls)
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

    cpu_limit_ms = None
    network_bytes_limit = None

    if self.rdf_flow.cpu_limit:
      cpu_usage = self.rdf_flow.cpu_time_used
      cpu_limit_ms = 1000 * max(
          self.rdf_flow.cpu_limit - cpu_usage.user_cpu_time -
          cpu_usage.system_cpu_time, 0)

      if cpu_limit_ms == 0:
        raise flow.FlowResourcesExceededError(
            "CPU limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id))

    if self.rdf_flow.network_bytes_limit:
      network_bytes_limit = max(
          self.rdf_flow.network_bytes_limit - self.rdf_flow.network_bytes_sent,
          0)
      if network_bytes_limit == 0:
        raise flow.FlowResourcesExceededError(
            "Network limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id))

    runtime_limit_us = self.rdf_flow.runtime_limit_us

    if runtime_limit_us and self.rdf_flow.runtime_us:
      if self.rdf_flow.runtime_us < runtime_limit_us:
        runtime_limit_us -= self.rdf_flow.runtime_us
      else:
        raise flow.FlowResourcesExceededError(
            "Runtime limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id))

    client_action_request = rdf_flows.ClientActionRequest(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        request_id=outbound_id,
        action_identifier=action_identifier,
        action_args=request,
        cpu_limit_ms=cpu_limit_ms,
        network_bytes_limit=network_bytes_limit,
        runtime_limit_us=runtime_limit_us)

    self.flow_requests.append(flow_request)
    self.client_action_requests.append(client_action_request)

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               request_data=None,
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

    flow_cls = FlowRegistry.FlowClassByName(flow_name)

    return flow.StartFlow(
        client_id=self.rdf_flow.client_id,
        flow_cls=flow_cls,
        parent_flow_obj=self,
        **kwargs)

  def SendReply(self, response, tag=None):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is saved to the database as flow result.

    Args:
      response: An RDFValue() instance to be sent to the parent.
      tag: If specified, tag the result with this tag.

    Raises:
      ValueError: If responses is not of the correct type.
    """
    if not isinstance(response, rdfvalue.RDFValue):
      raise ValueError("SendReply can only send RDFValues")

    if not any(isinstance(response, t) for t in self.result_types):
      logging.warning("Flow %s sends response of unexpected type %s.",
                      type(self).__name__,
                      type(response).__name__)

    reply = rdf_flow_objects.FlowResult(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        hunt_id=self.rdf_flow.parent_hunt_id,
        payload=response,
        tag=tag)
    if self.rdf_flow.parent_flow_id:
      response = rdf_flow_objects.FlowResponse(
          client_id=self.rdf_flow.client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          payload=response,
          flow_id=self.rdf_flow.parent_flow_id,
          tag=tag)

      self.flow_responses.append(response)
      # For nested flows we want the replies to be written,
      # but not to be processed by output plugins.
      self.replies_to_write.append(reply)
    else:
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

    if not self.rdf_flow.runtime_us:
      self.rdf_flow.runtime_us = rdfvalue.Duration(0)

    if status.runtime_us:
      self.rdf_flow.runtime_us += status.runtime_us

    if self.rdf_flow.cpu_limit:
      user_cpu_total = self.rdf_flow.cpu_time_used.user_cpu_time
      system_cpu_total = self.rdf_flow.cpu_time_used.system_cpu_time
      if self.rdf_flow.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our CPU time limit, stop this flow.
        raise flow.FlowResourcesExceededError(
            "CPU limit exceeded for {} {}.".format(
                self.rdf_flow.flow_class_name, self.rdf_flow.flow_id))

    if (self.rdf_flow.network_bytes_limit and
        self.rdf_flow.network_bytes_limit < self.rdf_flow.network_bytes_sent):
      # We have exceeded our byte limit, stop this flow.
      raise flow.FlowResourcesExceededError(
          "Network bytes limit exceeded {} {}.".format(
              self.rdf_flow.flow_class_name, self.rdf_flow.flow_id))

    if (self.rdf_flow.runtime_limit_us and
        self.rdf_flow.runtime_limit_us < self.rdf_flow.runtime_us):
      raise flow.FlowResourcesExceededError(
          "Runtime limit exceeded {} {}.".format(self.rdf_flow.flow_class_name,
                                                 self.rdf_flow.flow_id))

  def Error(self, error_message=None, backtrace=None, status=None):
    """Terminates this flow with an error."""
    FLOW_ERRORS.Increment(fields=[compatibility.GetName(self.__class__)])

    client_id = self.rdf_flow.client_id
    flow_id = self.rdf_flow.flow_id

    # backtrace is set for unexpected failures caught in a wildcard except
    # branch, thus these should be logged as error. backtrace is None for
    # faults that are anticipated in flows, thus should only be logged as
    # warning.
    if backtrace:
      logging.error("Error in flow %s on %s: %s, %s", flow_id, client_id,
                    error_message, backtrace)
    else:
      logging.warning("Error in flow %s on %s: %s:", flow_id, client_id,
                      error_message)

    if self.rdf_flow.parent_flow_id or self.rdf_flow.parent_hunt_id:
      status_msg = rdf_flow_objects.FlowStatus(
          client_id=client_id,
          request_id=self.rdf_flow.parent_request_id,
          response_id=self.GetNextResponseId(),
          cpu_time_used=self.rdf_flow.cpu_time_used,
          network_bytes_sent=self.rdf_flow.network_bytes_sent,
          runtime_us=self.rdf_flow.runtime_us,
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
        hunt.StopHuntIfCPUOrNetworkLimitsExceeded(self.rdf_flow.parent_hunt_id)

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
    """Clears all requests and responses."""
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
        "Flow %s completed with %d %s" %
        (self.__class__.__name__, num_results, num_results == 1 and "result" or
         "results"),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=flow_ref))

  def MarkDone(self, status=None):
    """Marks this flow as done."""
    FLOW_COMPLETIONS.Increment(fields=[compatibility.GetName(self.__class__)])

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
          runtime_us=self.rdf_flow.runtime_us,
          flow_id=self.rdf_flow.parent_flow_id)
      if self.rdf_flow.parent_flow_id:
        self.flow_responses.append(status)
      elif self.rdf_flow.parent_hunt_id:
        hunt_obj = hunt.StopHuntIfCPUOrNetworkLimitsExceeded(
            self.rdf_flow.parent_hunt_id)
        hunt.CompleteHuntIfExpirationTimeReached(hunt_obj)

    self.rdf_flow.flow_state = self.rdf_flow.FlowState.FINISHED

    if self.ShouldSendNotifications():
      self.NotifyAboutEnd()

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    log_entry = rdf_flow_objects.FlowLogEntry(
        client_id=self.rdf_flow.client_id,
        flow_id=self.rdf_flow.flow_id,
        hunt_id=self.rdf_flow.parent_hunt_id,
        message=format_str % args)
    data_store.REL_DB.WriteFlowLogEntries([log_entry])

  def RunStateMethod(self, method_name, request=None, responses=None):
    """Completes the request by calling the state method.

    Args:
      method_name: The name of the state method to call.
      request: A RequestState protobuf.
      responses: A list of FlowMessages responding to the request.

    Raises:
      FlowError: Processing time for the flow has expired.
    """
    if self.rdf_flow.pending_termination:
      self.Error(error_message=self.rdf_flow.pending_termination.reason)
      return

    client_id = self.rdf_flow.client_id

    deadline = self.rdf_flow.processing_deadline
    if deadline and rdfvalue.RDFDatetime.Now() > deadline:
      raise FlowError("Processing time for flow %s on %s expired." %
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

      GRR_WORKER_STATES_RUN.Increment()

      if method_name == "Start":
        FLOW_STARTS.Increment(fields=[self.rdf_flow.flow_class_name])
        method()
      else:
        method(responses)

      if self.replies_to_process:
        if self.rdf_flow.parent_hunt_id and not self.rdf_flow.parent_flow_id:
          self._ProcessRepliesWithHuntOutputPlugins(self.replies_to_process)
        else:
          self._ProcessRepliesWithFlowOutputPlugins(self.replies_to_process)

        self.replies_to_process = []

    except flow.FlowResourcesExceededError as e:
      FLOW_ERRORS.Increment(fields=[self.rdf_flow.flow_class_name])
      logging.info("Flow %s on %s exceeded resource limits: %s.",
                   self.rdf_flow.flow_id, client_id, str(e))
      self.Error(error_message=str(e))
    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except
      # TODO(amoser): We don't know what's in this exception so we have to deal
      # with all eventualities. Replace this code with a simple str(e) once
      # Python 2 support has been dropped.
      msg = compatibility.NativeStr(e)
      if compatibility.PY2:
        msg = msg.decode("utf-8", "replace")

      FLOW_ERRORS.Increment(fields=[self.rdf_flow.flow_class_name])

      self.Error(error_message=msg, backtrace=traceback.format_exc())

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
    return (self.rdf_flow.next_outbound_id -
            self.rdf_flow.next_request_to_process)

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
    """Flushes queued messages."""
    # TODO(amoser): This could be done in a single db call, might be worth
    # optimizing.

    if self.flow_requests:
      data_store.REL_DB.WriteFlowRequests(self.flow_requests)
      self.flow_requests = []

    if self.flow_responses:
      data_store.REL_DB.WriteFlowResponses(self.flow_responses)
      self.flow_responses = []

    if self.client_action_requests:
      client_id = self.rdf_flow.client_id
      if fleetspeak_utils.IsFleetspeakEnabledClient(client_id):
        for request in self.client_action_requests:
          msg = rdf_flow_objects.GRRMessageFromClientActionRequest(request)
          fleetspeak_utils.SendGrrMessageThroughFleetspeak(client_id, msg)
      else:
        data_store.REL_DB.WriteClientActionRequests(self.client_action_requests)

      self.client_action_requests = []

    if self.completed_requests:
      data_store.REL_DB.DeleteFlowRequests(self.completed_requests)
      self.completed_requests = []

    if self.replies_to_write:
      # For top-level hunt-induced flows, write results to the hunt collection.
      if self.rdf_flow.parent_hunt_id:
        data_store.REL_DB.WriteFlowResults(self.replies_to_write)
        hunt.StopHuntIfCPUOrNetworkLimitsExceeded(self.rdf_flow.parent_hunt_id)
      else:
        # Write flow results to REL_DB, even if the flow is a nested flow.
        data_store.REL_DB.WriteFlowResults(self.replies_to_write)
      self.replies_to_write = []

  def _ProcessRepliesWithHuntOutputPlugins(self, replies):
    """Applies output plugins to hunt results."""
    hunt_obj = data_store.REL_DB.ReadHuntObject(self.rdf_flow.parent_hunt_id)
    self.rdf_flow.output_plugins = hunt_obj.output_plugins
    hunt_output_plugins_states = data_store.REL_DB.ReadHuntOutputPluginsStates(
        self.rdf_flow.parent_hunt_id)
    self.rdf_flow.output_plugins_states = hunt_output_plugins_states

    created_plugins = self._ProcessRepliesWithFlowOutputPlugins(replies)

    for index, (plugin, state) in enumerate(
        zip(created_plugins, hunt_output_plugins_states)):
      if plugin is None:
        continue

      # Only do the REL_DB call if the plugin state has actually changed.
      s = state.plugin_state.Copy()
      plugin.UpdateState(s)
      if s != state.plugin_state:

        def UpdateFn(plugin_state):
          plugin.UpdateState(plugin_state)  # pylint: disable=cell-var-from-loop
          return plugin_state

        data_store.REL_DB.UpdateHuntOutputPluginState(hunt_obj.hunt_id, index,
                                                      UpdateFn)

    for plugin_def, created_plugin in zip(hunt_obj.output_plugins,
                                          created_plugins):
      if created_plugin is not None:
        HUNT_RESULTS_RAN_THROUGH_PLUGIN.Increment(
            len(replies), fields=[plugin_def.plugin_name])
      else:
        HUNT_OUTPUT_PLUGIN_ERRORS.Increment(fields=[plugin_def.plugin_name])

  def _ProcessRepliesWithFlowOutputPlugins(self, replies):
    """Processes replies with output plugins."""
    created_output_plugins = []
    for index, output_plugin_state in enumerate(
        self.rdf_flow.output_plugins_states):
      plugin_descriptor = output_plugin_state.plugin_descriptor
      output_plugin_cls = plugin_descriptor.GetPluginClass()
      output_plugin = output_plugin_cls(
          source_urn=self.rdf_flow.long_flow_id,
          args=plugin_descriptor.plugin_args,
          token=access_control.ACLToken(username=self.rdf_flow.creator))

      try:
        # TODO(user): refactor output plugins to use FlowResponse
        # instead of GrrMessage.
        output_plugin.ProcessResponses(
            output_plugin_state.plugin_state,
            [r.AsLegacyGrrMessage() for r in replies])
        output_plugin.Flush(output_plugin_state.plugin_state)
        output_plugin.UpdateState(output_plugin_state.plugin_state)

        data_store.REL_DB.WriteFlowOutputPluginLogEntries([
            rdf_flow_objects.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id="%d" % index,
                log_entry_type=rdf_flow_objects.FlowOutputPluginLogEntry
                .LogEntryType.LOG,
                message="Processed %d replies." % len(replies))
        ])

        self.Log("Plugin %s successfully processed %d flow replies.",
                 plugin_descriptor, len(replies))

        created_output_plugins.append(output_plugin)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Plugin %s failed to process %d replies.",
                          plugin_descriptor, len(replies))
        created_output_plugins.append(None)

        data_store.REL_DB.WriteFlowOutputPluginLogEntries([
            rdf_flow_objects.FlowOutputPluginLogEntry(
                client_id=self.rdf_flow.client_id,
                flow_id=self.rdf_flow.flow_id,
                hunt_id=self.rdf_flow.parent_hunt_id,
                output_plugin_id="%d" % index,
                log_entry_type=rdf_flow_objects.FlowOutputPluginLogEntry
                .LogEntryType.ERROR,
                message="Error while processing %d replies: %s" %
                (len(replies), str(e)))
        ])

        self.Log("Plugin %s failed to process %d replies due to: %s",
                 plugin_descriptor, len(replies), e)

    return created_output_plugins

  def MergeQueuedMessages(self, flow_obj):
    """Merges queued messages."""
    self.flow_requests.extend(flow_obj.flow_requests)
    flow_obj.flow_requests = []
    self.flow_responses.extend(flow_obj.flow_responses)
    flow_obj.flow_responses = []
    self.client_action_requests.extend(flow_obj.client_action_requests)
    flow_obj.client_action_requests = []
    self.completed_requests.extend(flow_obj.completed_requests)
    flow_obj.completed_requests = []
    self.replies_to_write.extend(flow_obj.replies_to_write)
    flow_obj.replies_to_write = []

  def ShouldSendNotifications(self):
    return bool(not self.rdf_flow.parent_flow_id and
                not self.rdf_flow.parent_hunt_id and self.creator and
                self.creator not in access_control.SYSTEM_USERS)

  def IsRunning(self):
    return self.rdf_flow.flow_state == self.rdf_flow.FlowState.RUNNING

  def GetProgress(self) -> rdf_structs.RDFProtoStruct:
    if self.__class__.progress_type is not None:
      raise NotImplementedError(
          "GetProgress() methods has to be implemented "
          "on a flow with defined 'progress_type' attribute.")

  def GetFilesArchiveMappings(
      self, flow_results: Iterator[rdf_flow_objects.FlowResult]
  ) -> Iterator[ClientPathArchiveMapping]:
    """Returns a mapping used to generate flow results archive.

    If this is implemented by a flow, then instead of generating
    a general-purpose archive with all files referenced in the
    results present, an archive would be generated with
    just the files referenced in the mappings.

    Args:
      flow_results: An iterator for flow results.

    Returns:
      An iterator of mappings from REL_DB's ClientPaths to archive paths.
    Raises:
      NotImplementedError: if not implemented by a subclass.
    """
    raise NotImplementedError("GetFilesArchiveMappings() not implemented")

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
  def client_info(self) -> rdf_client.ClientInformation:
    if self._client_info is not None:
      return self._client_info

    client_info = data_store_utils.GetClientInformation(self.client_id)
    self._client_info = client_info

    return client_info

  @property
  def creator(self):
    return self.rdf_flow.creator

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username  # Unused.
    return cls.args_type()

  @classmethod
  def CreateFlowInstance(cls, flow_object: rdf_flow_objects.Flow) -> "FlowBase":
    flow_cls = FlowRegistry.FlowClassByName(flow_object.flow_class_name)
    return flow_cls(flow_object)
