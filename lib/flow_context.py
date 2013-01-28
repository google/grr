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

"""This file contains a helper class for the flows.

This flow context class provides all the methods for handling flows (i.e.,
calling clients, changing state, ...).
"""


import os
import struct
import threading
import time
import traceback


import logging
from grr.client import actions
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import scheduler
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2


# Session ids below this range are reserved.
RESERVED_RANGE = 100
DEFAULT_WORKER_QUEUE_NAME = "W"


class FlowContextError(Exception):
  """Raised when there is an error during state transitions."""


class MoreDataException(Exception):
  """Raised when there is more data available."""


class HuntFlowContext(object):
  """The flow context class for hunts.

  This is essentially the same as a normal context but it processes
  all the requests that arrive regardless of any order such that one client that
  doesn't respond does not make the whole hunt wait.
  """

  process_requests_in_order = False

  def __init__(self, client_id=None, flow_name=None,
               queue_name=DEFAULT_WORKER_QUEUE_NAME, event_id=None,
               state=None, args=None, priority=None, cpu_limit=None,
               parent_flow=None, _store=None, token=None):
    """Constructor for the FlowContext.

    Args:
      client_id: The name of the client we are working with.
      flow_name: The name of the flow class of this context.
      queue_name: The name of the queue that the messages will run
                  with (default is W for general purpose workers).

      event_id: A logging event id for issuing further logs.
      state: A protobuf containing state information for this context.
      args: A protodict containing the arguments that the flow was run with.
      priority: The priority of this flow.
      cpu_limit: A limit for the cpu seconds used on the client for this flow.
      parent_flow: The URN of the parent flow or None if this is a top level
                   flow.
      _store: An optional data store to use. (Usually only used in tests).
      token: An instance of data_store.ACLToken security token.
    """
    self.queue_name = queue_name
    self.client_id = client_id
    self.parent_flow = parent_flow
    self.session_id = self._GetNewSessionID()
    if token is None:
      token = data_store.ACLToken()

    self.token = token

    # Any new requests go here during flow execution, and then we Flush them to
    # the task scheduler at once.
    self.new_request_states = []

    # These indicate the next states that are allowed from here
    self.next_states = []
    self.current_state = "Start"

    self.next_processed_request = 1
    self.next_outbound_id = 1

    self._outstanding_requests = 0
    self.data_store = _store or data_store.DB

    self.user = token.username

    self.outbound_lock = threading.Lock()

    if event_id is None:
      # If flow didn't come from the frontend or a parent flow it
      # probably came from the console so we generate an ID.
      event_id = "%s:console" % self.user

    if flow_name is None:
      flow_name = "unknown"

    # We create a flow_pb for us to be stored in
    self.flow_pb = jobs_pb2.FlowPB(
        session_id=utils.SmartUnicode(self.session_id),
        create_time=long(time.time() * 1e6),
        state=rdfvalue.Flow.Enum("RUNNING"),
        name=flow_name,
        creator=token.username,
        event_id=event_id)

    if cpu_limit is not None:
      self.flow_pb.remaining_cpu_quota = cpu_limit
      self.flow_pb.cpu_quota = cpu_limit

    if priority is not None:
      self.flow_pb.priority = priority

    if client_id is not None:
      self.flow_pb.client_id = client_id

    if state is not None:
      self.flow_pb.request_state.MergeFrom(state)

    if args is not None:
      self.flow_pb.args.MergeFrom(rdfvalue.RDFProtoDict(args).ToProto())

  def SetFlowObj(self, owning_flow):
    self.owning_flow = owning_flow

  def SetState(self, state):
    self.flow_pb.state = state

  def SetStatus(self, status):
    self.flow_pb.status = status

  def GetFlowArgs(self):
    """Shortcut function to get the arguments passed to the flow."""
    return rdfvalue.RDFProtoDict(self.flow_pb.args).ToDict()

  def GetNextOutboundId(self):
    with self.outbound_lock:
      my_id = self.next_outbound_id
      self.next_outbound_id += 1
    return my_id

  def CallState(self, messages=None, next_state="", client_id=None, delay=0):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked in a later time and receive all the
    messages we send.

    Args:
       messages: A list of rdfvalues to send. If the last one is not a
            GrrStatus, we append an OK Status.
       next_state: The state in this flow to be invoked with the responses.
       client_id: This client_id is used to schedule the request.
       delay: Delay the call to the next state by <delay> seconds.

    Raises:
       FlowContextError: if the next state is not valid.
    """
    if messages is None:
      messages = []

    # Check if the state is valid
    if not getattr(self.owning_flow, next_state):
      raise FlowContextError("Next state %s is invalid.")

    # Queue the response message to the parent flow
    with FlowManager(self.session_id, token=self.token,
                     store=self.data_store) as flow_manager:
      outbound_id = self.GetNextOutboundId()
      # Create a new request state
      request_state = rdfvalue.RequestState(id=outbound_id,
                                            session_id=self.session_id,
                                            client_id=client_id,
                                            next_state=next_state)

      flow_manager.QueueRequest(request_state)

      # Add the status message if needed.
      if not messages or not isinstance(messages[-1], rdfvalue.GrrStatus):
        messages.append(rdfvalue.GrrStatus())

      # Send all the messages
      for i, payload in enumerate(messages):
        if isinstance(payload, rdfvalue.RDFValue):
          msg = rdfvalue.GRRMessage(
              session_id=self.session_id, request_id=request_state.id,
              response_id=1+i,
              auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
              payload=payload,
              type=rdfvalue.GRRMessage.Enum("MESSAGE"))

          if isinstance(payload, rdfvalue.GrrStatus):
            msg.type = rdfvalue.GRRMessage.Enum("STATUS")

        flow_manager.QueueResponse(msg)

      self._outstanding_requests += 1

      # Notify the worker about it.
      timestamp = None
      if delay:
        timestamp = int((time.time() + delay) * 1e6)
      scheduler.SCHEDULER.NotifyQueue(self.queue_name, self.session_id,
                                      timestamp=timestamp, token=self.token)

  def _GetNewSessionID(self):
    """Returns a random integer session ID for this flow.

    Returns:
      a formatted session id string
    """
    result = struct.unpack("l", os.urandom(struct.calcsize("l")))[0] % 2**32
    return "aff4:/hunts/%s:%X" % (self.queue_name, result)

  def _GenerateParentFlow(self, client_id):
    """Returns a urn which will be used as a parent flow urn for hunt's flows.

    Flows executed from HuntFlowContext (i.e. flows issued by a hunt) have
    following urn pattern: aff4:/hunts/[hunt_id]/[client_id]/[flow_id].

    aff4:/hunts/[hunt_id]/[client_id] (an AFF4Volume) is symlinked to
    aff4:/[client_id]/flows/[hunt_id]:hunt/[flow_id].  Therefore it's easy
    to check whether hunt has been already scheduled on a given client
    (by doing Stat on a symlink).

    Args:
      client_id: Client id of the client where hunt's flow will run.

    Returns:
      RDFURN built using this pattern: aff4:/hunts/[hunt_id]/[client_id] or
      this context's session id if client_id is None.
    """
    if client_id:
      hunt_urn = rdfvalue.RDFURN(self.session_id)
      parent_flow_urn = hunt_urn.Add(client_id)

      hunt_link_urn = aff4.ROOT_URN.Add(client_id).Add("flows").Add(
          "%s:hunt" % (hunt_urn.Basename()))
      hunt_link = aff4.FACTORY.Create(hunt_link_urn, "AFF4Symlink",
                                      token=self.token)
      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(parent_flow_urn))
      hunt_link.Close()

      return str(parent_flow_urn)
    else:
      return self.session_id

  def ProcessCompletedRequests(self, thread_pool):
    """Go through the list of requests and process the completed ones.

    We take a snapshot in time of all requests and responses for this flow. We
    then process as many completed requests as possible. If responses are not
    quite here we leave it for next time.

    It is safe to call this function as many times as needed. NOTE: We assume
    that the flow queue is locked so another worker is not processing these
    messages while we are. It is safe to insert new messages to the flow:state
    queue.

    Args:
      thread_pool: For regular flows, the messages have to be processed in
                   order. Thus, the thread_pool argument is only used for hunts.
    """
    processing = []
    try:
      # The flow is dead - remove all outstanding requests and responses.
      if not self.IsRunning():
        self.owning_flow.Log("Flow complete.")
        with FlowManager(self.session_id, token=self.token,
                         store=self.data_store) as flow_manager:
          for request, responses in flow_manager.FetchRequestsAndResponses():
            flow_manager.DeleteFlowRequestStates(request, responses)

        return

      with FlowManager(self.session_id, token=self.token,
                       store=self.data_store) as flow_manager:
        for request, responses in flow_manager.FetchRequestsAndResponses():
          if request.id == 0:
            continue

          # Are there any responses at all?
          if not responses:
            continue

          if self.process_requests_in_order:

            if request.id > self.next_processed_request:
              break

            # Not the request we are looking for
            if request.id < self.next_processed_request:
              flow_manager.DeleteFlowRequestStates(request, responses)
              continue

            if request.id != self.next_processed_request:
              stats.STATS.Increment("grr_response_out_of_order")
              break

          # Check if the responses are complete (Last response must be a
          # STATUS message).
          if responses[-1].type != rdfvalue.GRRMessage.Enum("STATUS"):
            continue

          # At this point we process this request - we can remove all requests
          # and responses from the queue.
          flow_manager.DeleteFlowRequestStates(request, responses)

          # Do we have all the responses here?
          if len(responses) != responses[-1].response_id:
            # If we can retransmit do so. Note, this is different from the
            # automatic retransmission facilitated by the task scheduler (the
            # Task.ttl field) which would happen regardless of these.
            if request.transmission_count < 5:
              stats.STATS.Increment("grr_request_retransmission_count")
              request.transmission_count += 1
              self.new_request_states.append(request)
            break

          # If we get here its all good - run the flow.
          if self.IsRunning():
            self._Process(request, responses, thread_pool, processing)

          # Quit early if we are no longer alive.
          else: break

          self.next_processed_request += 1
          self._outstanding_requests -= 1

        # Are there any more outstanding requests?
        if not self.owning_flow.OutstandingRequests():
          # Allow the flow to cleanup
          if self.IsRunning():
            try:
              if self.current_state != "End":
                self.owning_flow.End(None)
            except Exception:   # pylint: disable=W0703
              # This flow will terminate now
              stats.STATS.Increment("grr_flow_errors")
              self.Error(self.client_id, traceback.format_exc())

        # This allows the End state to issue further client requests - hence
        # postpone termination.
        if not self.owning_flow.OutstandingRequests():
          stats.STATS.Increment("grr_flow_completed_count")
          logging.info("Destroying session %s(%s) for client %s",
                       self.session_id, self.owning_flow.__class__.__name__,
                       self.client_id)

          self.Terminate()

    except MoreDataException:
      # We did not read all the requests/responses in this run in order to
      # keep a low memory footprint and have to make another pass.
      scheduler.SCHEDULER.NotifyQueue(self.queue_name, self.session_id,
                                      token=self.token)

    finally:
      # We wait here until all threads are done processing and we can safely
      # pickle the flow object.
      for event in processing:
        event.wait()

  def _Process(self, request, responses, thread_pool, events=None):
    event = threading.Event()
    events.append(event)
    # In a hunt, all requests are independent and can be processed
    # in separate threads.
    thread_pool.AddTask(target=self._ProcessSingleRequest,
                        args=(request, responses, event,),
                        name="Hunt processing")

  def _ProcessSingleRequest(self, request, responses, event=None):
    """Completes the request by calling the state method.

    NOTE - we expect the state method to be suitably decorated with a
     StateHandler (otherwise this will raise because the prototypes
     are different)

    Args:
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
      event: A threading.Event() instance to signal completion of this request.
    """

    try:
      self.current_state = request.next_state
      client_id = request.client_id or self.client_id
      logging.info("%s Running %s with %d responses from %s",
                   self.session_id, request.next_state,
                   len(responses), client_id)
      getattr(self.owning_flow, request.next_state)(direct_response=None,
                                                    request=request,
                                                    responses=responses)
    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception:  # pylint: disable=W0703
      # This flow will terminate now
      stats.STATS.Increment("grr_flow_errors")

      self.Error(client_id, traceback.format_exc())

    finally:
      if event:
        event.set()

  def CallClient(self, action_name, request=None, next_state=None,
                 request_data=None, client_id=None, **kwargs):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run
    action may send back many responses. These will be queued by the
    framework until a status message is sent by the client. The status
    message will cause the entire transaction to be committed to the
    specified state.

    Args:
       action_name: The function to call on the client.

       request: The request to send to the client. If not specified (Or None) we
             create a new protobuf using the kwargs.

       next_state: The state in this flow, that responses to this
             message should go to.

       request_data: A dict which will be available in the RequestState
             protobuf. The Responses object maintains a reference to this
             protobuf for use in the execution of the state method. (so you can
             access this data by responses.request). Valid values are
             strings, unicode and protobufs.
       client_id: The request is sent to this client.

    Raises:
       FlowContextError: If next_state is not one of the allowed next states.
       RuntimeError: The request passed to the client does not have the correct
                     type.
    """
    # Retrieve the correct rdfvalue to use for this client action.
    try:
      action = actions.ActionPlugin.classes[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

    request_kw = {}
    if action.in_rdfvalue is None:
      if request:
        raise RuntimeError("Client action %s does not expect args." %
                           action_name)
    else:
      if request is None:
        # Create a new rdf request.
        request = action.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action.in_rdfvalue):
          raise RuntimeError("Client action expected %s but got %s" % (
              action.in_rdfvalue, type(request)))

      request_kw["args"] = request.SerializeToString()
      request_kw["args_age"] = int(request.age)
      request_kw["args_rdf_name"] = request.__class__.__name__

    # Check that the next state is allowed
    if next_state is None:
      raise FlowContextError("next_state is not specified for CallClient")

    if self.process_requests_in_order and next_state not in self.next_states:
      raise FlowContextError("Flow %s: State '%s' called to '%s' which is "
                             "not declared in decorator." % (
                                 self.__class__.__name__,
                                 self.current_state,
                                 next_state))

    outbound_id = self.GetNextOutboundId()
    # Create a new request state
    state = jobs_pb2.RequestState(
        id=outbound_id,
        session_id=utils.SmartUnicode(self.session_id),
        next_state=next_state,
        client_id=client_id)

    if request_data is not None:
      state.data.MergeFrom(rdfvalue.RDFProtoDict(request_data).ToProto())

    # Send the message with the request state
    msg = jobs_pb2.GrrMessage(
        session_id=utils.SmartUnicode(self.session_id), name=action_name,
        request_id=outbound_id,
        priority=self.flow_pb.priority,
        **request_kw)
    if self.flow_pb.remaining_cpu_quota:
      msg.cpu_limit = int(self.flow_pb.remaining_cpu_quota)
    state.request.MergeFrom(msg)

    # Remember the new request for later
    self.new_request_states.append(state)

    self._outstanding_requests += 1

  def CallFlow(self, flow_factory, flow_name, next_state=None,
               request_data=None, client_id=None, **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_factory: A FlowFactory object.
       flow_name: The name of the flow to invoke.

       next_state: The state in this flow, that responses to this
       message should go to.

       request_data: Any string provided here will be available in the
             RequestState protobuf. The Responses object maintains a reference
             to this protobuf for use in the execution of the state method. (so
             you can access this data by responses.request). There is no
             format mandated on this data but it may be a serialized protobuf.

       client_id: If given, the flow is started for this client.

       **kwargs: Arguments for the child flow.

    Raises:
       FlowContextError: If next_state is not one of the allowed next states.
    """
    if self.process_requests_in_order:
      # Check that the next state is allowed
      if next_state and next_state not in self.next_states:
        raise FlowContextError("Flow %s: State '%s' called to '%s' which is "
                               "not declared in decorator." % (
                                   self.__class__.__name__,
                                   self.current_state,
                                   next_state))

    client_id = client_id or self.client_id
    outbound_id = self.GetNextOutboundId()

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = jobs_pb2.RequestState(
        id=outbound_id,
        session_id=utils.SmartUnicode(self.session_id),
        client_id=client_id,
        next_state=next_state, flow_name=flow_name,
        response_count=0)

    if request_data:
      state.data.MergeFrom(rdfvalue.RDFProtoDict(request_data).ToProto())

    cpu_limit = self.flow_pb.remaining_cpu_quota or None

    # Create the new child flow but do not notify the user about it.
    child = flow_factory.StartFlow(
        client_id, flow_name, event_id=self.flow_pb.event_id,
        _request_state=state, token=self.token,
        notify_to_user=False, parent_flow=self._GenerateParentFlow(client_id),
        _store=self.data_store,
        _parent_request_queue=self.new_request_states,
        queue_name=self.queue_name, cpu_limit=cpu_limit, **kwargs)

    # Add the request state to the queue.
    self.new_request_states.append(state)

    # Keep track of our children.
    # TODO(user): This should be .Append(child)
    self.flow_pb.children.append(child)

    self._outstanding_requests += 1

  def SendReply(self, response):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response: An RDFValue() instance to be sent to the parent.

    Raises:
      RuntimeError: If responses is not of the correct type.
    """
    if not isinstance(response, rdfvalue.RDFValue):
      raise RuntimeError("SendReply does not send RDFValue")

    # Only send the reply if we have a parent and if flow's send_replies
    # attribute is True. We have a parent only if we know our parent's request.
    if self.flow_pb.HasField("request_state") and self.owning_flow.send_replies:

      request_state = self.flow_pb.request_state

      request_state.response_count += 1

      worker_queue = scheduler.SCHEDULER.QueueNameFromURN(
          request_state.session_id)

      # Make a response message
      msg = jobs_pb2.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
          type=rdfvalue.GRRMessage.Enum("MESSAGE"),
          args=response.SerializeToString(),
          args_rdf_name=response.__class__.__name__,
          args_age=int(response.age))

      try:
        # queue the response message to the parent flow
        with FlowManager(request_state.session_id, token=self.token,
                         store=self.data_store) as flow_manager:
          # Queue the response now
          flow_manager.QueueResponse(msg)
      except MoreDataException:
        pass

      finally:
        scheduler.SCHEDULER.NotifyQueue(worker_queue, request_state.session_id,
                                        token=self.token)

  def FlushMessages(self):
    """Flushes the messages that were queued with CallClient."""
    with self.outbound_lock:
      to_flush = self.new_request_states
      self.new_request_states = []

    all_tasks = []

    try:
      for destination, requests in utils.GroupBy(to_flush,
                                                 lambda x: x.client_id):

        to_schedule = [request for request in requests if request.request.name]

        # The requests contain messages - schedule the messages on the client's
        # queue.
        tasks = [scheduler.SCHEDULER.Task(queue=destination,
                                          value=request.request)
                 for request in to_schedule]

        stats.STATS.Add("grr_worker_requests_issued", len(tasks))

        # Now adjust the request state to point to the task id
        for request, task in zip(to_schedule, tasks):
          request.ts_id = task.id

        all_tasks.append(tasks)

      # Now store all RequestState proto in their flow state
      for session_id, requests in utils.GroupBy(to_flush,
                                                lambda x: x.session_id):
        try:
          with FlowManager(session_id, token=self.token,
                           store=self.data_store, sync=False) as flow_manager:
            for request in requests:
              flow_manager.QueueRequest(request)
        except MoreDataException:
          pass

    finally:
      for tasks in all_tasks:
        # In order to avoid a race we wait with scheduling the client messages.
        scheduler.SCHEDULER.Schedule(tasks, token=self.token, sync=False)

    # We write async above and flush the messages all at once.
    data_store.DB.Flush()

  def Error(self, client_id, backtrace=None):
    """Logs an error for a client."""
    logging.error("Hunt Error: %s", backtrace)
    self.owning_flow.LogClientError(client_id, backtrace=backtrace)

  def IsRunning(self):
    return self.flow_pb.state == rdfvalue.Flow.Enum("RUNNING")

  def Terminate(self, status=None):
    """Terminates this flow."""
    try:
      # Dequeue existing requests
      with FlowManager(self.session_id, token=self.token,
                       store=self.data_store) as flow_manager:
        flow_manager.DestroyFlowStates()
    except MoreDataException:
      pass

    # This flow might already not be running.
    if self.flow_pb.state != rdfvalue.Flow.Enum("RUNNING"):
      return

    if self.flow_pb.HasField("request_state"):
      logging.debug("Terminating flow %s", self.session_id)

      # Make a response or use the existing one.
      response_proto = status or rdfvalue.GrrStatus()

      user_cpu = self.flow_pb.cpu_used.user_cpu_time
      sys_cpu = self.flow_pb.cpu_used.system_cpu_time
      response_proto.cpu_time_used.user_cpu_time = user_cpu
      response_proto.cpu_time_used.system_cpu_time = sys_cpu
      response_proto.network_bytes_sent = self.flow_pb.network_bytes_sent
      response_proto.child_session_id = self.session_id

      request_state = self.flow_pb.request_state
      request_state.response_count += 1

      # Make a response message
      msg = jobs_pb2.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
          type=rdfvalue.GRRMessage.Enum("STATUS"),
          args=response_proto.SerializeToString())

      worker_queue = scheduler.SCHEDULER.QueueNameFromURN(
          request_state.session_id)

      try:
        # queue the response message to the parent flow
        with FlowManager(request_state.session_id, token=self.token,
                         store=self.data_store) as flow_manager:
          # Queue the response now
          flow_manager.QueueResponse(msg)
      finally:
        scheduler.SCHEDULER.NotifyQueue(worker_queue,
                                        request_state.session_id,
                                        token=self.token)

    # Mark as terminated.
    self.flow_pb.state = rdfvalue.Flow.Enum("TERMINATED")
    self.owning_flow.Save()

  def OutstandingRequests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self._outstanding_requests

  def __getstate__(self):
    """Controls pickling of this object."""
    stats.STATS.Increment("grr_worker_flows_pickled")

    # We have to copy the dict here because we need to pickle the flow first
    # and flush the requests later to avoid a race. Thus, we have to keep a
    # copy of the new_request_states around for flushing.
    to_pickle = self.__dict__.copy()
    to_pickle["new_request_states"] = []
    to_pickle["data_store"] = None
    to_pickle["flow_pb"] = None
    to_pickle["outbound_lock"] = None

    return to_pickle

  def UpdateProtoResources(self, status):
    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time
    self.flow_pb.cpu_used.user_cpu_time += user_cpu
    self.flow_pb.cpu_used.system_cpu_time += system_cpu
    self.flow_pb.network_bytes_sent += status.network_bytes_sent

    if self.flow_pb.remaining_cpu_quota:
      self.flow_pb.remaining_cpu_quota -= user_cpu
      self.flow_pb.remaining_cpu_quota -= system_cpu
      if self.flow_pb.remaining_cpu_quota < 0:
        # We have exceeded our quota, stop this flow.
        raise FlowContextError("CPU quota exceeded.")

  def SaveResourceUsage(self, request, responses):
    """Update the resource usage of the flow."""
    status = responses.status

    if status.child_session_id:
      user_cpu = status.cpu_time_used.user_cpu_time
      system_cpu = status.cpu_time_used.system_cpu_time

      fd = self.owning_flow.GetAFF4Object(mode="w", age=aff4.NEWEST_TIME,
                                          token=self.token)
      resources = fd.Schema.RESOURCES()
      resources.client_id = request.client_id
      resources.session_id = status.child_session_id
      resources.cpu_usage.user_cpu_time = user_cpu
      resources.cpu_usage.system_cpu_time = system_cpu
      resources.network_bytes_sent = status.network_bytes_sent

      fd.AddAttribute(resources)
      fd.Close(sync=False)

    # Do this last since it may raise "CPU quota exceeded".
    self.UpdateProtoResources(status)


class FlowContext(HuntFlowContext):
  """The context for a flow."""

  process_requests_in_order = True

  def _GetNewSessionID(self):
    """Returns a random integer session ID for this flow.

    Returns:
      a formatted session id string
    """
    random_number = struct.unpack(
        "l", os.urandom(struct.calcsize("l")))[0] % 2**32

    if self.parent_flow:
      result = rdfvalue.RDFURN(self.parent_flow)
    else:
      result = aff4.ROOT_URN
      if self.client_id:
        result = result.Add(self.client_id)
      result = result.Add("flows")

    return result.Add("%s:%X" % (self.queue_name, random_number))

  def _GenerateParentFlow(self, client_id):
    return self.session_id

  def _Process(self, request, responses, unused_thread_pool=None, event=None):
    self._ProcessSingleRequest(request, responses, event=event)

  def CallState(self, messages=None, next_state="", client_id=None, delay=0):
    client_id = client_id or self.client_id
    super(FlowContext, self).CallState(messages=messages, next_state=next_state,
                                       client_id=client_id, delay=delay)

  def CallClient(self, action_name, request=None, next_state=None,
                 request_data=None, client_id=None, **kwargs):
    client_id = client_id or self.client_id
    super(FlowContext, self).CallClient(
        action_name, request=request,
        next_state=next_state, request_data=request_data,
        client_id=client_id, **kwargs)

  def CallFlow(self, flow_factory, flow_name, next_state=None,
               request_data=None, client_id=None, **kwargs):
    client_id = client_id or self.client_id
    super(FlowContext, self).CallFlow(
        flow_factory, flow_name,
        next_state=next_state, request_data=request_data,
        client_id=client_id, **kwargs)

  def Error(self, client_id, backtrace=None):
    """Kills this flow with an error."""
    if self.flow_pb.state == rdfvalue.Flow.Enum("RUNNING"):
      # Set an error status
      reply = rdfvalue.GrrStatus()
      reply.status = rdfvalue.GrrStatus.Enum("GENERIC_ERROR")
      if backtrace:
        reply.error_message = backtrace

      self.Terminate(reply)

      self.flow_pb.state = rdfvalue.Flow.Enum("ERROR")

      if backtrace:
        logging.error("Error in flow %s (%s). Trace: %s", self.session_id,
                      client_id, backtrace)
        self.flow_pb.backtrace = backtrace
      else:
        logging.error("Error in flow %s (%s).", self.session_id, client_id)

      self.owning_flow.Save()
      self.owning_flow.Notify(
          "FlowStatus", self.client_id,
          "Flow (%s) terminated due to error" % self.session_id)

  def SaveResourceUsage(self, _, responses):
    status = responses.status

    self.UpdateProtoResources(status)


class FlowManager(object):
  """This class manages the representation of the flow within the data store."""
  # These attributes are related to a flow's internal data structures
  # Requests are protobufs of type RequestState. They have a column
  # prefix followed by the request number:
  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08X"

  # This regex will return all messages (requests or responses) in this flow
  # state.
  FLOW_MESSAGE_REGEX = "flow:.*"

  # This regex will return all the requests in order
  FLOW_REQUEST_REGEX = FLOW_REQUEST_PREFIX + ".*"

  # Each request may have any number of responses. These attributes
  # are GrrMessage protobufs. Their attribute consists of a prefix,
  # followed by the request number, followed by the response number.
  FLOW_RESPONSE_PREFIX = "flow:response:%08X:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%08X"

  # This regex will return all the responses in order
  FLOW_RESPONSE_REGEX = "flow:response:.*"

  # This is the subject name of flow state variables. We need to be
  # able to lock these independently from the actual flow.
  FLOW_TASK_TEMPLATE = "%s"
  FLOW_STATE_TEMPLATE = "%s/state"

  FLOW_TASK_REGEX = "task:.*"

  request_limit = 10000
  response_limit = 100000

  def __init__(self, session_id, store=None, sync=True, token=None):
    self.session_id = session_id
    self.subject = self.FLOW_STATE_TEMPLATE % session_id
    self.sync = sync
    self.token = token
    if store is None:
      store = data_store.DB

    self.data_store = store

    # We cache all these and write/delete in one operation.
    self.to_write = {}
    self.to_delete = []
    self.client_messages = []
    self.client_id = None

  def FetchRequestsAndResponses(self):
    """Fetches all outstanding requests and responses for this flow.

    We first cache all requests and responses for this flow in memory to
    prevent round trips.

    Yields:
      an tuple (request protobufs, list of responses messages) in ascending
      order of request ids.

    Raises:
      MoreDataException: When there is more data available than read by the
                         limited query.
    """
    subject = self.FLOW_STATE_TEMPLATE % self.session_id
    state_map = {0: {"REQUEST_STATE": jobs_pb2.RequestState(id=0)}}
    max_request_id = "00000000"

    request_count = 0
    response_count = 0
    # Get some requests
    for predicate, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit)):

      components = predicate.split(":")
      max_request_id = components[2]

      request = jobs_pb2.RequestState()
      request.ParseFromString(serialized)

      meta_data = state_map.setdefault(request.id, {})
      meta_data["REQUEST_STATE"] = request
      request_count += 1

    # Now get some responses
    for predicate, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.response_limit)):
      response_count += 1

      components = predicate.split(":")
      if components[2] > max_request_id:
        break

      response = rdfvalue.GRRMessage(serialized)
      if response.request_id in state_map:
        meta_data = state_map.setdefault(response.request_id, {})
        responses = meta_data.setdefault("RESPONSES", [])
        responses.append(response)

    for request_id in sorted(state_map):
      try:
        metadata = state_map[request_id]
        yield (metadata["REQUEST_STATE"], metadata.get("RESPONSES", []))
      except KeyError:
        pass

    if (request_count >= self.request_limit or
        response_count >= self.response_limit):
      raise MoreDataException()

  def DeleteFlowRequestStates(self, request_state, responses):
    """Deletes the request and all its responses from the flow state queue."""

    if request_state:
      self.to_delete.append(self.FLOW_REQUEST_TEMPLATE % request_state.id)

      # Remove the message from the client queue that this request forms.
      self.client_messages.append(request_state.ts_id)
      self.client_id = request_state.client_id

    # Delete all the responses by their response id.
    for response in responses:
      self.to_delete.append(self.FLOW_RESPONSE_TEMPLATE % (
          response.request_id, response.response_id))

  def DestroyFlowStates(self):
    """Deletes all states in this flow and dequeue all client messages."""
    for request_state, _ in self.FetchRequestsAndResponses():
      if request_state:
        self.client_messages.append(request_state.ts_id)
        self.client_id = request_state.client_id

    self.data_store.DeleteSubject(self.subject, token=self.token)

  def Flush(self):
    """Writes the changes in this object to the datastore."""
    try:
      self.data_store.MultiSet(self.subject, self.to_write, sync=self.sync,
                               to_delete=self.to_delete, token=self.token)

    except data_store.Error:
      pass

    scheduler.SCHEDULER.Delete(self.client_id, self.client_messages,
                               token=self.token)

    self.to_write = {}
    self.to_delete = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.Flush()

  def QueueResponse(self, message_proto):
    """Queues the message on this flow's state."""
    # Insert to the data_store
    self.to_write.setdefault(
        FlowManager.FLOW_RESPONSE_TEMPLATE % (
            message_proto.request_id, message_proto.response_id),
        []).append(message_proto.SerializeToString())

  def QueueRequest(self, request_state):
    self.to_write.setdefault(
        self.FLOW_REQUEST_TEMPLATE % request_state.id, []).append(
            request_state.SerializeToString())


class WellKnownFlowManager(FlowManager):
  """A flow manager for well known flows."""

  def FetchRequestsAndResponses(self):
    """Well known flows do not have real requests.

    This manages retrieving all the responses without requiring corresponding
    requests.

    Yields:
      A tuple of request (None) and responses.
    """
    subject = self.FLOW_STATE_TEMPLATE % self.session_id

    # Get some requests
    for _, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.request_limit)):

      # The predicate format is flow:response:REQUEST_ID:RESPONSE_ID. For well
      # known flows both request_id and response_id are randomized.
      response = rdfvalue.GRRMessage(serialized)

      yield None, [response]
