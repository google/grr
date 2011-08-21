#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""This file defines the base classes for Flows.

A Flow is a state machine which executes actions on the
client. Messages are transmitted between the flow object and the
client with their responses introduced into a state handler within the
flow.
"""


import cPickle as pickle
import functools
import getpass
import operator
import os
import pdb
import re
import struct
import time
import traceback

from M2Crypto import BIO
from M2Crypto import RSA
from M2Crypto import X509

from google.protobuf import message
from grr.client import conf as flags
import logging
from grr.client import actions
from grr.client import client_actions
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import data_store
from grr.lib import key_utils
from grr.lib import log
from grr.lib import registry
from grr.lib import scheduler
from grr.lib import server_stubs
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2

# Session ids below this range are reserved.
RESERVED_RANGE = 100
DEFAULT_WORKER_QUEUE_NAME = "W"

flags.DEFINE_bool("task_scheduler_queue_flush", None,
                  "Cleanup the task scheduler queues before starting")

FLAGS = flags.FLAGS


# Counters defined here
stats.STATS.grr_worker_states_run = 0
stats.STATS.grr_flows_created = 0
stats.STATS.grr_worker_flows_pickled = 0
stats.STATS.grr_response_out_of_order = 0
stats.STATS.grr_worker_requests_complete = 0
stats.STATS.grr_worker_requests_issued = 0
stats.STATS.grr_flow_errors = 0
stats.STATS.grr_worker_well_known_flow_requests = 0
stats.STATS.grr_flow_invalid_flow_count = 0
stats.STATS.grr_unique_clients = 0
stats.STATS.grr_unknown_clients = 0
stats.STATS.grr_flow_completed_count = 0


# Valid client ids
CLIENT_ID_RE = re.compile(r"^C\.[0-9a-f]{16}$")


class Responses(object):
  """An object encapsulating all the responses to a request.

  This object is normally only instantiated from the flow StateHandler
  decorator.
  """

  def __init__(self, request=None, responses=None, in_protobuf=None,
               auth_required=True):
    self.status = None    # A jobs_pb2.GrrStatus proto
    self.request = request
    self._auth_required = auth_required
    if request:
      self.request_data = utils.ProtoDict(request.data)

    if responses:
      # This may not be needed if we can assume that responses are
      # returned in lexical order from the data_store.
      responses.sort(key=operator.attrgetter("response_id"))
      self._responses = []

      # The iterator that was returned as part of these responses. This should
      # be passed back to actions that expect an iterator.
      self.iterator = jobs_pb2.Iterator()

      # Filter the responses by authorized states
      for msg in responses:
        # Check if the message is authenticated correctly.
        if msg.auth_state == jobs_pb2.GrrMessage.DESYNCHRONIZED or (
            self._auth_required and
            msg.auth_state != jobs_pb2.GrrMessage.AUTHENTICATED):
          logging.info("%s: Messages must be authenticated (Auth state %s)",
                       msg.session_id, msg.auth_state)

          # Skip this message - it is invalid
          continue

        # Check for iterators
        if msg.type == jobs_pb2.GrrMessage.ITERATOR:
          self.iterator.ParseFromString(msg.args)
          continue

        # Look for a status message
        if msg.type == jobs_pb2.GrrMessage.STATUS:
          # Our status is set to the first status message that we see in
          # the responses. We ignore all other messages after that.
          self.status = jobs_pb2.GrrStatus()
          self.status.ParseFromString(msg.args)
          # Check this to see if the call succeeded
          self.success = self.status.status == jobs_pb2.GrrStatus.OK

          # Ignore all other messages
          break

        # Use this message
        self._responses.append(msg)

      if self.status is None:
        raise FlowError("No valid Status message.")

    self._in_protobuf = in_protobuf
    # This is the raw message accessible while going through the iterator
    self.message = None

  def __iter__(self):
    """An iterator which returns all the responses in order."""
    old_response_id = None
    for self.message in self._responses:
      # Handle retransmissions
      if self.message.response_id == old_response_id:
        continue
      else:
        old_response_id = self.message.response_id

      # Only process messages
      if self.message.type != jobs_pb2.GrrMessage.MESSAGE:
        continue

      if self._in_protobuf:
        protobuf = self._in_protobuf
      else:
        try:
          action_cls = actions.ActionPlugin.classes[self.request.request.name]
          protobuf = action_cls.out_protobuf
        except KeyError:
          logging.info("Cant parse response from %s", self.request.request.name)
          protobuf = jobs_pb2.GrrMessage

      result = protobuf()
      result.ParseFromString(self.message.args)

      yield result

  def First(self):
    """A convenience method to return the first response."""
    for x in self:
      return x

  def __len__(self):
    return len(self._responses)

  def GetRequestArgPb(self):
    """Retrieves the argument protobuf for the original request."""
    try:
      action_cls = actions.ActionPlugin.classes[self.request.request.name]
      protobuf = action_cls.out_protobuf
      req = protobuf()
      req.ParseFromString(self.request.request.args)
      return req

    except KeyError:
      logging.info("Cant parse response from %s", self.request.request.name)
      return None


def StateHandler(in_protobuf=None, next_state="End", auth_required=True):
  """A convenience decorator for state methods.

  Args:
    in_protobuf: The protobuf class we will convert the message from.

    next_state: One or more next states possible from here (can be a
                string or a list of strings). If a state attempts to
                redirect to a state other than on this (with
                CallClient) an exception is raised.

    auth_required: Do we require messages to be authenticated? If the
                message is not authenticated we raise.

  Returns:
    A decorator
  """

  def Decorator(f):
    """Initialised Decorator."""
    # Allow next_state to be a single string
    if type(next_state) is str:
      next_states = [next_state]
    else:
      next_states = next_state

    @functools.wraps(f)
    def Decorated(self, request=None, responses=None):
      """A decorator."""
      # Record the permitted next states so CallClient() can check.
      self.next_states = next_states

      # Prepare a responses object for the state method to use:
      responses = Responses(request=request,
                            responses=responses,
                            in_protobuf=in_protobuf,
                            auth_required=auth_required)

      stats.STATS.grr_worker_states_run += 1
      # Run the state method (Allow for flexibility in prototypes)
      args = [self, responses]
      res = f(*args[:f.func_code.co_argcount])

      return res

    # Make sure the state function itself knows where its allowed to
    # go (This is used to introspect the state graph).
    Decorated.next_states = next_states

    return Decorated

  return Decorator


class FlowManager(object):
  """This class manages the representation of the flow within the data store."""
  # These attributes are related to a flow's internal data structures
  # Requests are protobufs of type RequestState. They have a column
  # prefix followed by the request number:
  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08d"

  # This regex will return all messages (requests or responses) in this flow
  # state.
  FLOW_MESSAGE_REGEX = "flow:.*"

  # This regex will return all the requests in order
  FLOW_REQUEST_REGEX = FLOW_REQUEST_PREFIX + ".*"

  # Each request may have any number of responses. These attributes
  # are GrrMessage protobufs. Their attribute consist of a prefix,
  # followed by the request number, followed by the response number.
  FLOW_RESPONSE_PREFIX = "flow:response:%04d:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%04d"

  # This regex will return all the responses to a request in order
  FLOW_RESPONSE_REGEX = FLOW_RESPONSE_PREFIX + ".*"

  # This is the subject name of flow state variables. We need to be
  # able to lock these independently from the actual flow.
  FLOW_TASK_TEMPLATE = "task:%s"
  FLOW_STATE_TEMPLATE = "task:%s:state"

  def __init__(self, session_id):
    self.session_id = session_id
    self.subject = self.FLOW_STATE_TEMPLATE % session_id

    # We cache all these and write/delete in one operation.
    self.to_write = {}
    self.to_delete = []
    self.client_messages = []
    self.client_id = None

  def FetchRequestsAndResponses(self):
    """Fetch all outstanding requests and responses for this flow.

    We first cache all requests and responses for this flow in memory to
    prevent round trips.

    Yields:
      an tuple (request protobufs, list of responses messages) in ascending
      order of request ids.
    """
    subject = self.FLOW_STATE_TEMPLATE % self.session_id

    cached_state_messages = data_store.DB.ResolveRegex(
        subject, self.FLOW_MESSAGE_REGEX)

    # Sort the requests in ascending order of request id
    cached_state_messages.sort(key=lambda x: x[0])

    # Sort the states into an ordered list of requests and responses.
    for request_predicate, serialized_request, _ in cached_state_messages:
      if not re.match(self.FLOW_REQUEST_REGEX, request_predicate):
        continue

      request = jobs_pb2.RequestState()
      request.ParseFromString(serialized_request)

      response_regex = self.FLOW_RESPONSE_REGEX % request.id
      responses = []

      # Grab all the responses
      for response_predicate, serialized_response, _ in cached_state_messages:
        if not re.match(response_regex, response_predicate):
          continue

        response = jobs_pb2.GrrMessage()
        response.ParseFromString(serialized_response)
        responses.append(response)

      yield (request, responses)

  def DeleteFlowRequestStates(self, request_state, responses):
    """Delete the request and all its responses from the flow state queue."""
    self.to_delete.append(self.FLOW_REQUEST_TEMPLATE % request_state.id)
    for i in range(0, responses + 1):
      self.to_delete.append(self.FLOW_RESPONSE_TEMPLATE % (request_state.id, i))

    self.client_messages.append(request_state.ts_id)
    self.client_id = request_state.client_id

  def Flush(self):
    data_store.DB.DeleteAttributes(self.subject, self.to_delete)
    try:
      data_store.DB.MultiSet(self.subject, self.to_write, sync=False)
    except data_store.Error:
      pass

    SCHEDULER.Delete(self.client_id, self.client_messages)
    self.to_write = {}
    self.to_delete = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Support 'with' protocol."""
    self.Flush()

  def QueueResponse(self, message_proto):
    """Queues the message on this flow's state."""
    # Insert to the data_store
    self.to_write[FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message_proto.request_id, message_proto.response_id)] = message_proto

  def QueueRequest(self, request_state):
    self.to_write[self.FLOW_REQUEST_TEMPLATE % request_state.id] = request_state


class GRRFlow(object):
  """A GrrFlow class.

  Flows exist on the server to maintain session state. A flow is a
  state machine with each state being called when a new message is
  received.

  Do not instantiate flows directly. Flows are usually launched from
  FACTORY.StartFlow().
  """

  # This is used to arrange flows into a tree view
  category = ""

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, client_id=None, queue_name=DEFAULT_WORKER_QUEUE_NAME,
               user=None, event_id=None):
    """Constructor for the Flow.

    Args:
       client_id: The name of the client we are working with.

       queue_name: The name of the queue that the messages will run
           with (default is W for general purpose workers).

       user: The user name launching the flow.
       event_id: A logging event id for issuing further logs.
    """
    self.session_id = self._GetNewSessionID(queue_name)
    self.client_id = client_id

    # Any new requests go here during flow execution, and then we Flush them to
    # the task scheduler at once.
    self.new_request_states = []

    # These indicate the next states that are allowed from here
    self.next_states = []
    self.current_state = "Start"

    self.next_processed_request = 1
    self.next_outbound_id = 1

    self._outstanding_requests = 0

    if user is None:
      # Find the username of the logged in user.
      user = getpass.getuser()

    self.user = user
    if event_id is None:
      # If flow didn't come from the frontend or a parent flow it
      # probably came from the console so we generate an ID.
      event_id = "%s:console" % user

    # We create a flow_pb for us to be stored in
    self.flow_pb = jobs_pb2.FlowPB(session_id=self.session_id,
                                   create_time=long(time.time() * 1e6),
                                   state=jobs_pb2.FlowPB.RUNNING,
                                   name=self.__class__.__name__,
                                   creator=user,
                                   event_id=event_id)

    stats.STATS.grr_flows_created += 1

    self.Log("%s: %s initiated %s for client %s", event_id, user,
             self.__class__.__name__, self.client_id)

  def _GetNewSessionID(self, queue_name):
    """Returns a random integer session ID.

    This id is used to refer to the serialized flow in the task
    master. If a collision occurs the flow objects will be
    overwritten.

    TODO(user): Check the task scheduler here for a session of this
    same ID to avoid possible collisions.

    Args:
      queue_name: The name of the queue to prefix to the session id

    Returns:
      a formatted session id string
    """
    while 1:
      result = struct.unpack("l", os.urandom(struct.calcsize("l")))[0] % 2**32
      # Ensure session ids are larger than the reserved ones
      if result > RESERVED_RANGE:
        return "%s:%X" % (queue_name, result)

  def GetFlowArgs(self):
    """Shortcut function to get the arguments passed to the flow."""
    return utils.ProtoDict(self.flow_pb.args).ToDict()

  def __getstate__(self):
    """Controls pickling of this object."""
    self.flow_pb = None
    stats.STATS.grr_worker_flows_pickled += 1

    return self.__dict__

  def ProcessCompletedRequests(self, unused_messages=None):
    """Go through the list of requests and process the completed ones.

    We take a snapshot in time of all requests and responses for this flow. We
    then process as many completed requests as possible. If responses are not
    quite here we leave it for next time.

    It is safe to call this function as many times as needed. NOTE: We assume
    that the flow queue is locked so another worker is not processing these
    messages while we are. It is safe to insert new messages to the flow:state
    queue.

    Args:
      unused_messages: These are the messages that came in from the
      client this time. For regular flows these are unused because the
      real messages are queues in the flow_pb.
    """
    with FlowManager(self.session_id) as flow_manager:
      for request, responses in flow_manager.FetchRequestsAndResponses():
        # Are there any responses at all?
        if not responses: break

        # Not the request we are looking for
        if request.id < self.next_processed_request:
          flow_manager.DeleteFlowRequestStates(request, len(responses))
          continue

        if request.id != self.next_processed_request:
          stats.STATS.grr_response_out_of_order += 1
          break

        # Check if the responses are complete (Last response must be a STATUS
        # message).
        if responses[-1].type != jobs_pb2.GrrMessage.STATUS:
          break

        # At this point we process this request - we can remove all requests and
        # responses from the queue.
        flow_manager.DeleteFlowRequestStates(request, len(responses))

        # Do we have all the responses here?
        if len(responses) != responses[-1].response_id:
          # If we can retransmit do so. Note, this is different from the
          # automatic retransmission facilitated by the task scheduler (the
          # Task.ttl field) which would happen regardless of these.
          if request.transmission_count < 5:
            request.transmission_count += 1
            self.new_request_states.append(request)

          break

        # If we get here its all good - run the flow.
        if self.IsRunning():
          self._ProcessSingleRequest(request, responses)
        # Quit early if we are no longer alive.
        else: break

        self.next_processed_request += 1
        self._outstanding_requests -= 1

      # Are there any more outstanding requests?
      if not self.OutstandingRequests():
        stats.STATS.grr_flow_completed_count += 1
        logging.info("Destroying session %s for client %s",
                     self.session_id, self.client_id)

        # Allow the flow to cleanup
        if self.IsRunning():
          self.End()

        self.Terminate()

  def _ProcessSingleRequest(self, request, responses):
    """Complete the request by calling the state method.

    NOTE - we expect the state method to be suitably decorated with a
     StateHandler (otherwise this will raise because the prototypes
     are different)

    Args:
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
    """
    try:
      self.current_state = request.next_state
      logging.info("%s Running %s with %d responses from %s",
                   self.session_id, self.current_state,
                   len(responses), self.client_id)
      getattr(self, self.current_state)(request=request, responses=responses)
    except Exception:
      # This flow will terminate now
      stats.STATS.grr_worker_flow_errors += 1

      self.Error(traceback.format_exc())

  def Start(self, unused_message=None):
    """The first state of the flow."""
    pass

  def End(self):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.
    """

  def Error(self, backtrace=None):
    """Kill this flow with an error."""
    if self.flow_pb.state == jobs_pb2.FlowPB.RUNNING:
      logging.error("Error in flow %s", self.session_id)
      self.flow_pb.state = jobs_pb2.FlowPB.ERROR
      # Set an error status
      self.SendReply(jobs_pb2.GrrStatus(
          status=jobs_pb2.GrrStatus.GENERIC_ERROR))
      if backtrace:
        logging.error(backtrace)
        self.flow_pb.backtrace = backtrace
      self.Save()
      if FLAGS.debug:
        pdb.post_mortem()

  def Terminate(self):
    """Terminate this flow."""
    # Just mark as terminated
    # This flow might already not be running
    if self.flow_pb.state == jobs_pb2.FlowPB.RUNNING:
      logging.debug("Terminating flow %s", self.session_id)
      self.SendReply(jobs_pb2.GrrStatus())
      self.flow_pb.state = jobs_pb2.FlowPB.TERMINATED
      self.Save()

  def Load(self):
    """Load the flow from storage.

    This hook point is called after retrieval from storage and prior to state
    execution.
    """

  def Save(self):
    """Save the flow to disk.

    This hook point is called before we get dumped to storage. Note that for
    efficiency we do not generally get serialized on every state transition but
    we may be serialized on any transition.

    If we want to hold something which should only exist while running and not
    in serialized form (e.g. database handle), we can override the Load() and
    Save() methods to remove the object during Save() and recreate it during
    Load().
    """

  def Dump(self):
    """Returns a FlowPB protobuf with ourselves in it.

    Returns:
        a FlowPB protobuf.
    """
    # Allow the flow author to hook this
    self.Save()

    # Flush the messages to the client
    self.FlushMessages()
    result = self.flow_pb
    result.pickle = ""
    result.pickle = pickle.dumps(self)

    return result

  def CallClient(self, action_name, args_pb=None, next_state=None,
                 request_data=None, **kwargs):
    """Call the client asynchronously.

    This sends a message to the client to invoke an Action. The run
    action may send back many responses. These will be queued by the
    framework until a status message is sent by the client. The status
    message will cause the entire transaction to be committed to the
    specified state.

    Args:
       action_name: The function to call on the client.

       args_pb: A protobuf to send to the client. If not specified (Or None) we
             create a new protobuf using the kwargs.

       next_state: The state in this flow, that responses to this
       message should go to.

       request_data: A dict which will be available in the RequestState
             protobuf. The Responses object maintains a reference to this
             protobuf for use in the execution of the state method. (so you can
             access this data by responses.request.data). Valid values are
             strings, unicode and protobufs.

      kwargs: initializer for the required message in case args is not provided.

    Raises:
       FlowError: If next_state is not one of the allowed next states.
    """
    if args_pb is None:
      # Retrieve the correct protobuf to use to send to the action
      try:
        proto_cls = actions.ActionPlugin.classes[action_name].in_protobuf
      except KeyError:
        proto_cls = None

      if proto_cls is None: proto_cls = jobs_pb2.DataBlob

      args_pb = proto_cls(**kwargs)

    # Check that the next state is allowed
    if next_state is None:
      raise FlowError("next_state is not specified for CallClient")

    if next_state not in self.next_states:
      raise FlowError("Flow %s: State '%s' called to '%s' which is "
                      "not declared in decorator." % (
                          self.__class__.__name__,
                          self.current_state,
                          next_state))

    # Create a new request state
    state = jobs_pb2.RequestState(id=self.next_outbound_id,
                                  session_id=self.session_id,
                                  next_state=next_state,
                                  client_id=self.client_id)

    if request_data is not None:
      state.data.MergeFrom(utils.ProtoDict(request_data).ToProto())

    # Send the message with the request state
    state.request.MergeFrom(jobs_pb2.GrrMessage(
        session_id=self.session_id, name=action_name,
        request_id=self.next_outbound_id, args=args_pb.SerializeToString()))

    # Remember the new request for later
    self.new_request_states.append(state)

    self.next_outbound_id += 1
    self._outstanding_requests += 1

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    """Create a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.

       next_state: The state in this flow, that responses to this
       message should go to.

       request_data: Any string provided here will be available in the
             RequestState protobuf. The Responses object maintains a reference
             to this protobuf for use in the execution of the state method. (so
             you can access this data by responses.request.data). There is no
             format mandated on this data but it may be a serialized protobuf.

       kwargs: Arguments for the child flow.

    Raises:
       FlowError: If next_state is not one of the allowed next states.
    """
    # Check that the next state is allowed
    if next_state and next_state not in self.next_states:
      raise FlowError("Flow %s: State '%s' called to '%s' which is "
                      "not declared in decorator." % (
                          self.__class__.__name__,
                          self.current_state,
                          next_state))

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = jobs_pb2.RequestState(id=self.next_outbound_id,
                                  session_id=self.session_id,
                                  next_state=next_state,
                                  response_count=0)

    if request_data:
      state.data.MergeFrom(utils.ProtoDict(request_data).ToProto())

    # Create the new child flow
    FACTORY.StartFlow(self.client_id, flow_name,
                      user=self.flow_pb.creator,
                      event_id=self.flow_pb.event_id,
                      _request_state=state,
                      **kwargs)

    # Add the request state to the queue.
    self.new_request_states.append(state)

    self.next_outbound_id += 1
    self._outstanding_requests += 1

  def SendReply(self, response_proto):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response_proto: A protobuf to be sent to the parent.
    """
    # We have a parent only if we know our parent's request state.
    if self.flow_pb.HasField("request_state"):
      request_state = self.flow_pb.request_state

      request_state.response_count += 1

      # queue the response message to the parent flow
      with FlowManager(request_state.session_id) as flow_manager:
        # Make a response message
        msg = jobs_pb2.GrrMessage(
            session_id=request_state.session_id,
            request_id=request_state.id,
            response_id=request_state.response_count,
            auth_state=jobs_pb2.GrrMessage.AUTHENTICATED,
            args=response_proto.SerializeToString())

        if isinstance(response_proto, jobs_pb2.GrrStatus):
          msg.type = jobs_pb2.GrrMessage.STATUS

          # Status messages are also sent to their worker queues
          worker_queue = msg.session_id.split(":")[0]
          SCHEDULER.Schedule([
              SCHEDULER.Task(queue=worker_queue, value=msg)])

        # Queue the response now
        flow_manager.QueueResponse(msg)

  def FlushMessages(self):
    """Flushes the messages that were queued with CallClient."""
    # The most important thing here is to adjust request.ts_id to the correct
    # task scheduler id which we get when queuing the messages in the requests.
    # We schedule all the tasks at once on the client queue, then adjust the
    # ts_id and then queue the request states on the flow's state queue.
    for destination, requests in utils.GroupBy(self.new_request_states,
                                               lambda x: x.client_id):
      # The requests contain messages - schedule the messages on the client's
      # queue
      tasks = [SCHEDULER.Task(queue=destination, value=request.request)
               for request in requests]

      # This will update task.id to the correct value
      SCHEDULER.Schedule(tasks)
      stats.STATS.grr_worker_requests_issued += len(tasks)

      # Now adjust the request state to point to the task id
      for request, task in zip(requests, tasks):
        request.ts_id = task.id

    # Now store all RequestState proto in their flow state
    for session_id, requests in utils.GroupBy(self.new_request_states,
                                              lambda x: x.session_id):
      with FlowManager(session_id) as flow_manager:
        for request in requests:
          flow_manager.QueueRequest(request)

    # Clear the queue
    self.new_request_states = []

  def OutstandingRequests(self):
    """Return the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self._outstanding_requests

  def IsRunning(self):
    return self.flow_pb.state == jobs_pb2.FlowPB.RUNNING

  def Log(self, format_str, *args):
    """Log the message using the flow's standard logging.

    Args:
      format_str: Format string
      args: arguements to the format string
    """
    logging.warning(format_str, *args)


class WellKnownFlow(GRRFlow):
  """A flow with a well known session_id.

  Since clients always need to communicate with a flow, it is
  impossible for them to asynchronously begin communication with the
  server because normally the flow's session ID is randomly
  generated. Sometimes we want the client to communicate with the
  server spontaneously - so it needs a well known session ID.

  This base class defines such flows with a well known
  session_id. Clients can communicate with these flows by themselves
  without prior arrangement.

  Note that necessarily well known flows do not have any state and
  therefore do not need state handlers. In this regard a WellKnownFlow
  is basically an RPC mechanism - if you need to respond with a
  complex sequence of actions you will need to spawn a new flow from
  here..
  """
  # This is the session_id that will be used to register these flows
  well_known_session_id = None

  # Well known flows are not browsable
  category = None

  def __init__(self, *args, **kwargs):
    GRRFlow.__init__(self, *args, **kwargs)

    # Tag this flow as well known
    self.flow_pb.state = jobs_pb2.FlowPB.WELL_KNOWN

  def _GetNewSessionID(self, unused_queue_name):
    # Always return a well known session id for this flow:
    return self.well_known_session_id

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed
    return 1

  def ProcessCompletedRequests(self, messages=None):
    """For WellKnownFlows we receive these messages directly."""
    stats.STATS.grr_worker_well_known_flow_requests += 1
    for msg in messages:
      if msg.request_id != 0:
        raise RuntimeError("WellKnownFlows must have request_id 0")

      self.ProcessMessage(msg)

  def ProcessMessage(self, msg):
    """This is where messages get processed.

    Override in derived classes:

    Args:
       msg: The GrrMessage sent by the client. Note that this
            message is not authenticated.
    """


class FlowFactory(object):
  """A factory for flow objects.

  This class also presents some useful utility functions for managing
  flows.
  """

  def StartFlow(self, client_id, flow_name,
                queue_name=DEFAULT_WORKER_QUEUE_NAME, user=None, event_id=None,
                _request_state=None, **kw):
    """Create and execute a new flow.

    Args:
      client_id: The URL of an existing client or None for well known flows.
      flow_name: The name of the flow to start (from the registry).
      queue_name: The name of the queue to invoke the flow.
      user: The user name launching the flow.
      event_id: A logging event id for issuing further logs.
      _request_state: A parent flow's request state (Used internally only).
      kw: flow specific keywords to be passed to the constructor.

    Returns:
      the session id of the flow.

    Raises:
      IOError: If the client_id is invalid.
    """
    client = None
    if client_id is not None:
      # This client must exist already or this will raise
      client = aff4.FACTORY.Open(client_id)
      # This duck typing checks that its an actual client.
      client_id = client.client_id
      if not client_id:
        raise IOError("Client invalid")

    try:
      flow_cls = GRRFlow.classes[flow_name]
    except KeyError:
      stats.STATS.grr_flow_invalid_flow_count += 1
      raise RuntimeError("Unable to locate flow %s" % flow_name)

    flow_obj = flow_cls(client_id=client_id, queue_name=queue_name,
                        user=user, event_id=event_id, **kw)

    if _request_state is not None:
      flow_obj.flow_pb.request_state.MergeFrom(_request_state)

    # Populate the flow proto with the args for auditing/viewing.
    flow_obj.flow_pb.args.MergeFrom(utils.ProtoDict(kw).ToProto())

    if client is not None:
      flow_urn = aff4.FLOW_SWITCH_URN.Add(flow_obj.session_id)

      # Add this flow to the client
      client.AddAttribute(client.Schema.FLOW, flow_urn)
      client.Flush()

    logging.info("Scheduling %s on %s(%s): %s",
                 flow_name, client_id, flow_obj.session_id, kw)

    # Just run the first state. This must send something to the
    # client.
    flow_obj.Start()

    ## Push the new flow onto the queue
    task = SCHEDULER.Task(queue=flow_obj.session_id, id=1,
                          value=flow_obj.Dump())

    SCHEDULER.Schedule([task])

    return flow_obj.session_id

  def ListFlow(self, client_id, limit=1000):
    """Fetch the flow based on session_id.

    Args:
      client_id: Id of the client to retrieve tasks for.
      limit: Max number of flows to retrieve.

    Returns:
      A list of flow protobufs.
    """
    tasks = SCHEDULER.Query(queue=client_id, limit=limit,
                            decoder=jobs_pb2.FlowPB)
    live = [t for t in tasks if t.value.state != jobs_pb2.FlowPB.TERMINATED]
    return live

  def FetchFlow(self, session_id, sync=True, lock=True):
    """Fetch the flow based on session_id.

    This also grabs a lock on the flow. We might block here for some
    time.

    Args:
      session_id: Session id for the flow.
      sync: be synchronous - if we cant get the lock on a flow we wait
            until we do. If False we raise a LockError()
      lock: Should we lock the flow.

    Returns:
      A flow protobuf.

    Raises:
      LockError: If we are asynchronous and can not obtain the lock.
    """
    # Try to grab the lock on the flow
    while True:
      # Does the flow exist? Fail early if it doesn't
      flow_tasks = SCHEDULER.Query(queue=session_id, decoder=jobs_pb2.FlowPB,
                                   limit=1)

      if not flow_tasks:
        logging.error("Flow %s does not exist", session_id)
        return None

      # Flow is terminated do not lock it
      if flow_tasks[0].value.state == jobs_pb2.FlowPB.TERMINATED:
        return flow_tasks[0].value

      # If we dont need to lock it - we are done
      if not lock: break

      flow_tasks = SCHEDULER.QueryAndOwn(
          queue=session_id,
          limit=1,
          decoder=jobs_pb2.FlowPB,
          lease_seconds=60)

      if flow_tasks: break

      # We can not wait - just raise now
      if not sync: raise LockError(session_id)

      logging.info("Waiting for flow %s", session_id)
      time.sleep(1)

    flow_pb = flow_tasks[0].value
    logging.info("Got flow %s %s", session_id, flow_pb.name)
    flow_pb.ts_id = flow_tasks[0].id

    return flow_pb

  def ReturnFlow(self, flow_pb):
    """Returns the flow when we are done with it.

    If the flow is marked as terminated we can delete it now.

    Args:
      flow_pb: flow proto
    """
    # Is this flow still alive?
    if flow_pb.state != jobs_pb2.FlowPB.TERMINATED:
      logging.info("Returning flow %s", flow_pb.session_id)

      # Re-insert it into the Task Scheduler
      flow_task = SCHEDULER.Task(queue=flow_pb.session_id,
                                 id=flow_pb.ts_id, value=flow_pb)

      SCHEDULER.Schedule([flow_task])
    else:
      logging.info("Deleting flow %s", flow_pb.session_id)
      self.DeleteFlow(flow_pb)

  def DeleteFlow(self, flow_pb):
    """Deletes the flow from the Task Scheduler."""
    flow_pb.state = jobs_pb2.FlowPB.TERMINATED
    flow_task = SCHEDULER.Task(
        queue=flow_pb.session_id, id=flow_pb.ts_id, value=flow_pb)
    SCHEDULER.Schedule([flow_task])

  def LoadFlow(self, flow_pb):
    """Restore the flow stored in flow_pb.

    We might want to make this more flexible down the track
    (e.g. autoload new flows to avoid having to restart workers.)

    Args:
      flow_pb: The flow protobuf

    Returns:
      A complete flow object.

    Raises:
      pickle.UnpicklingError: if we are unable to restore this flow.
    """
    try:
      result = pickle.loads(flow_pb.pickle)
      # Allow the flow to hook the load operation.
      result.Load()
    except (pickle.UnpicklingError, message.Error), e:
      logging.error("Unable to handle Flow %s: %s", flow_pb.name, e)
      raise FlowError(flow_pb.name)

    # Restore the flow_pb here
    result.flow_pb = flow_pb

    return result


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using AFF4."""

  def __init__(self, keystore_path):
    self.client_cache = utils.FastStore(100)
    super(ServerCommunicator, self).__init__(keystore_path)

  def GetRSAPublicKey(self, common_name="Server"):
    """Retrieve the public key for the common_name from data_store.

    This maintains a cache of key pairs or loads them instead from
    data_store.

    Args:
      common_name: The common_name of the key we need.

    Returns:
      A valid rsa public key.

    Raises:
       communicator.UnknownClientCert: cert not found - this will cause the
       client to re-enroll thereby updating our certificate store.
    """
    # We dont want a unicode object here
    common_name = str(common_name)

    try:
      client = self.client_cache.Get(common_name)
      cert = client.Get(client.Schema.CERT)
      return cert.GetPubKey()

    except KeyError:
      stats.STATS.grr_unique_clients += 1

      try:
        # Fetch the client's cert
        client = aff4.FACTORY.Open(common_name)
        cert = client.Get(client.Schema.CERT)
        if not cert:
          raise communicator.UnknownClientCert("Cert not found")

        if cert.common_name != common_name:
          logging.error("Stored cert mismatch for %s", common_name)
          raise communicator.UnknownClientCert("Stored cert mismatch")

        self.client_cache.Put(common_name, client)

        return cert.GetPubKey()

      except IOError:
        # Fall through to an error.
        stats.STATS.grr_unknown_clients += 1
        logging.info("Failed to retrieve certificate for %s, "
                     "message unauthenticated", common_name)

        raise communicator.UnknownClientCert("No client found")

  def _LoadOurCertificate(self, certificate_path):
    """Load servers certificate with addition of keystore support."""
    server_pem = key_utils.GetCert(certificate_path)
    self.cert = X509.load_cert_string(server_pem)

    # Make sure its valid
    private_key = RSA.load_key_string(server_pem)

    # We must store it encoded in pem format due to M2Crypto referencing bugs,
    # so we just encode it with no password.
    bio = BIO.MemoryBuffer()
    private_key.save_key_bio(bio, None)
    self.private_key = bio.getvalue()

    # Our common name
    self.common_name = self._GetCNFromCert(self.cert)

  def VerifyMessageSignature(self, signed_message_list):
    """Verify the message list signature.

    In the server we check that the timestamp is later than the ping timestamp
    stored with the client. This ensures that client responses can not be
    replayed.

    Args:
       signed_message_list: The SignedMessageList proto from the server.

    Returns:
       a jobs_pb2.GrrMessage.AuthorizationState.
    """
    # messages are not authenticated
    auth_state = jobs_pb2.GrrMessage.UNAUTHENTICATED

    # Verify the incoming message.
    digest = self.hash_function(signed_message_list.message_list).digest()

    try:
      remote_name = signed_message_list.source
      remote_public_key = self.GetRSAPublicKey(remote_name)
      remote_public_key.verify(digest, signed_message_list.signature,
                               self.hash_function_name)

      # Check the timestamp
      client = self.client_cache.Get(remote_name)

      # The very first packet we see from the client we do not have its clock
      remote_time = client.Get(client.Schema.CLOCK) or 0
      client_time = signed_message_list.timestamp
      if client_time > long(remote_time):
        auth_state = jobs_pb2.GrrMessage.AUTHENTICATED
        stats.STATS.grr_authenticated_messages += 1

        # Update the timestamp
        client.Set(client.Schema.CLOCK, aff4.RDFDatetime(client_time))
        client.Flush()

      else:
        # This is likely an old message
        auth_state = jobs_pb2.GrrMessage.DESYNCHRONIZED

    except communicator.UnknownClientCert:
      stats.STATS.grr_unauthenticated_messages += 1

    return auth_state


class FrontEndServer(object):
  """This is the front end server.

  This class interfaces clients into the GRR backend system. We process message
  bundles to and from the client, without caring how message bundles are
  transmitted to the client.

  - receives an encrypted message parcel from clients.
  - Decrypts messages from this.
  - schedules the messages to their relevant queues.
  - Collects the messages from the client queue
  - Bundles and encrypts the messages for the client.
  """

  def __init__(self, keystore_path, logger, max_queue_size=50,
               message_expiry_time=120, max_retransmission_time=10):
    # This object manages our crypto
    self._communicator = ServerCommunicator(keystore_path)

    self.receive_thread_pool = {}
    self._logger = logger
    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size

  def HandleMessageBundles(self, request_comms, response_comms, event_id):
    """Processes a queue of messages as passed from the client.

    We basically dispatch all the GrrMessages in the queue to the task
    master for backend processing. We then retrieve from the TS the
    messages destined for this client.

    Args:
       request_comms: A ClientCommunication protobuf with messages sent by the
       client. source should be set to the client CN.

       response_comms: A ClientCommunication protobuf of jobs destined to this
       client.

       event_id: A logging event id for issuing further logs.

    Returns:
       tuple of (source, message_count) where message_count is the number of
       messages received from the client with common name source.
    """
    messages, source, timestamp = self._communicator.DecodeMessages(
        request_comms)

    self.ReceiveMessages(messages, source, event_id)

    # We send the client a maximum of self..max_queue_size messages
    required_count = max(0, self.max_queue_size - request_comms.queue_size)

    message_list = jobs_pb2.MessageList()
    self.DrainTaskSchedulerQueueForClient(source, required_count, message_list)

    # Encode the message_list in the response_comms
    try:
      self._communicator.EncodeMessages(
          message_list, response_comms, destination=str(source),
          timestamp=timestamp)
    except IOError:
      pass

    return source, len(messages)

  def DrainTaskSchedulerQueueForClient(self, client_name, max_count,
                                       response_message):
    """Drains the client's Task Scheduler queue.

    1) Get all messages in the client queue.
    2) Sort these into a set of session_ids.
    3) Use data_store.DB.ResolveRegex() to query all requests.
    4) Delete all responses for retransmitted messages (if needed).

    Args:
       client_name: CN of client (also TS queue name)

       max_count: The maximum number of messages we will issue for the
                  client.

       response_message: a MessageList object we fill for with GrrMessages

    """
    # Drain the queue for this client:
    new_tasks = SCHEDULER.QueryAndOwn(
        queue=client_name,
        limit=max_count,
        lease_seconds=self.message_expiry_time,
        decoder=jobs_pb2.GrrMessage)

    response_message.job.extend([x.value for x in new_tasks])
    stats.STATS.grr_messages_sent += len(new_tasks)

  def ReceiveMessages(self, messages, source, event_id):
    """Receive and process the messages from the source.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      messages: A list of GrrMessage protos.
      source: The client the messages came from.
      event_id: Unique identifier for an event for logging.
    """
    tasks_to_send = []
    for session_id, messages in utils.GroupBy(
        messages, operator.attrgetter("session_id")):

      # Remove and handle messages to WellKnownFlows
      messages = self.HandleWellKnownFlows(session_id, messages)
      if not messages: continue

      with FlowManager(session_id) as flow_manager:
        for msg in messages:
          flow_manager.QueueResponse(msg)
          # For status messages also send to their worker queues.
          if msg.type == jobs_pb2.GrrMessage.STATUS:
            queue = self.GetQueueName(session_id)
            tasks_to_send.append(SCHEDULER.Task(queue=queue, value=msg))

    SCHEDULER.Schedule(tasks_to_send)

  def HandleWellKnownFlows(self, queue, messages):
    """Hands off messages to well known flows."""
    result = []
    tasks_to_send = []

    for msg in messages:
      # This message should go directly to a WellKnownFlow
      if msg.request_id == 0:
        tasks_to_send.append(SCHEDULER.Task(
            queue=self.GetQueueName(queue), value=msg))

        stats.STATS.grr_well_known_flow_requests += 1
      else:
        result.append(msg)

    SCHEDULER.Schedule(tasks_to_send)
    return result

  def GetQueueName(self, session_id):
    # Session id has to be of the form queue_name:number
    try:
      queue_name, _ = session_id.split(":", 1)
    except ValueError:
      logging.error("Message has invalid session id %s",
                    session_id)
      raise RuntimeError("Message has invalid session_id")

    return queue_name


class FlowError(Exception):
  """Raised when we can not retrieve the flow."""


class LockError(FlowError):
  """Raised when we fail to grab a lock on the flow object."""


class GRRWorker(object):
  """A GRR worker."""

  # time to wait before polling when no jobs are currently in the
  # task scheduler (sec)
  POLLING_INTERVAL = 2

  def __init__(self, queue_name=None):
    """Constructor.

    Args:
      queue_name: The name of the queue we use to fetch new messages
      from.
    """
    self.queue_name = queue_name

    # Initialize the logging component.
    self._logger = log.GrrLogger(component=self.__class__.__name__)

  def Run(self):
    """Event loop."""
    while 1:
      processed = self.RunOnce()
      if processed == 0:
        time.sleep(self.POLLING_INTERVAL)

  def RunOnce(self):
    """Process one set of messages from Task Scheduler.

    The worker processes new jobs from the task master. For each job
    we retrieve the session from the Task Scheduler.

    Returns:
        Total number of messages processed by this call.
    """
    # Any jobs for us?
    new_tasks = SCHEDULER.QueryAndOwn(
        queue=self.queue_name,
        limit=50,
        decoder=jobs_pb2.GrrMessage,
        lease_seconds=600)

    try:
      self.ProcessMessages(new_tasks)
    # We need to keep going no matter what
    except Exception, e:
      logging.error("Error processing message %s. %s.", e,
                    traceback.format_exc())

      if FLAGS.debug:
        pdb.post_mortem()

    return len(new_tasks)

  def ProcessMessages(self, tasks):
    """Process all the flows in the messages.

    Precondition: All tasks come from the same queue (self.queue_name).

    Note that the server actually completes the requests in the
    flow when receiving the messages from the client. We do not really
    look at the messages here at all any more - we just work from the
    completed messages in the flow proto.

    Args:
        tasks: A list of tasks.
    """
    for session_id, flow_tasks in utils.GroupBy(
        tasks, operator.attrgetter("value.session_id")):
      flow_pb = None

      # Take a lease on the flow:
      try:
        flow_pb = FACTORY.FetchFlow(session_id)
        if flow_pb is None: continue

        flow_obj = FACTORY.LoadFlow(flow_pb)

        try:
          flow_obj.ProcessCompletedRequests([t.value for t in flow_tasks])
        except FlowError, e:
          # Something went wrong - log it
          self.flow_pb.state = jobs_pb2.FlowPB.ERROR
          if not flow_pb.backtrace:
            flow_pb.backtrace = traceback.format_exc()

          logging.error("Flow %s: %s", flow_obj, e)

        # Re-serialize the flow
        flow_obj.Dump()

      finally:
        # Now remove the messages from the queue.
        SCHEDULER.Delete(self.queue_name, flow_tasks)

        # Unlock this flow
        if flow_pb:
          FACTORY.ReturnFlow(flow_pb)


def FlushTS():
  """Remove stale sessions from task master."""
  for queue in SCHEDULER.ListQueues():
    SCHEDULER.DropQueue(queue)

# These are globally available handles to factories


class FlowInit(aff4.AFF4InitHook):
  """Ensure that the Well known flows exist."""

  def __init__(self, **unused_kwargs):
    # Make global handlers
    global SCHEDULER
    global FACTORY

    if FACTORY is None:
      FACTORY = FlowFactory()

    if SCHEDULER is None:
      SCHEDULER = scheduler.TaskScheduler()

    # Find all the plugins that should be a WellKnownFlow
    for name, cls in GRRFlow.classes.items():
      if issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        # WellKnownFlows do not have state so its safer for us to always
        # overwrite them. This ensures we always have the latest version.
        FACTORY.StartFlow(None, name)


# A global factory that can be used to create new flows
FACTORY = None
SCHEDULER = None


def Init():
  """Initialise the flow subsystem."""
  aff4.AFF4Init()
  if FLAGS.task_scheduler_queue_flush:
    FlushTS()

