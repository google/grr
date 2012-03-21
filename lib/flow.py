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
import operator
import pdb
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
from grr.lib import flow_context
from grr.lib import key_utils
from grr.lib import log
from grr.lib import registry
from grr.lib import scheduler
from grr.lib import server_stubs
from grr.lib import stats
from grr.lib import threadpool
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_integer("threadpool_size", 500,
                     "Number of threads in the shared thread pool.")

flags.DEFINE_integer("worker_task_limit", 2000,
                     "Limits the number of tasks a worker retrieves every poll")

FLAGS = flags.FLAGS

FLAGS.databuffer_expensive_check = False


class FlowError(Exception):
  """Raised when we can not retrieve the flow."""


class FlowVarz(registry.InitHook):
  def RunOnce(self):
    """Exports our vars."""
    # Counters defined here
    stats.STATS.RegisterVar("grr_flow_completed_count")
    stats.STATS.RegisterVar("grr_flow_errors")
    stats.STATS.RegisterVar("grr_flow_invalid_flow_count")
    stats.STATS.RegisterVar("grr_flows_created")
    stats.STATS.RegisterMap("grr_frontendserver_handle_time", "times",
                            precision=0)
    stats.STATS.RegisterTimespanAvg(
        "grr_frontendserver_handle_time_running_avg", 60)
    stats.STATS.RegisterVar("grr_messages_sent")
    stats.STATS.RegisterVar("grr_response_out_of_order")
    stats.STATS.RegisterVar("grr_unique_clients")
    stats.STATS.RegisterVar("grr_unknown_clients")
    stats.STATS.RegisterVar("grr_well_known_flow_requests")
    stats.STATS.RegisterVar("grr_worker_flows_pickled")
    stats.STATS.RegisterVar("grr_worker_requests_complete")
    stats.STATS.RegisterVar("grr_worker_requests_issued")
    stats.STATS.RegisterVar("grr_worker_states_run")
    stats.STATS.RegisterVar("grr_worker_well_known_flow_requests")


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

      # If the protobufs came as responses from another flow, we look up their
      # type.
      flow_name = self.request.flow_name
      if self._in_protobuf:
        protobuf = self._in_protobuf
      elif flow_name:
        protobuf = GRRFlow.classes.get(flow_name, GRRFlow).out_protobuf
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

  def __nonzero__(self):
    return bool(self._responses)

  def GetRequestArgPb(self):
    """Retrieves the argument protobuf for the original request."""
    try:
      action_cls = actions.ActionPlugin.classes[self.request.request.name]
      protobuf = action_cls.in_protobuf
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
      """A decorator that defines allowed follow up states for a method."""
      # Record the permitted next states so CallClient() can check.
      self.context.next_states = next_states

      # Prepare a responses object for the state method to use:
      responses = Responses(request=request,
                            responses=responses,
                            in_protobuf=in_protobuf,
                            auth_required=auth_required)

      stats.STATS.Increment("grr_worker_states_run")
      # Run the state method (Allow for flexibility in prototypes)
      args = [self, responses]
      res = f(*args[:f.func_code.co_argcount])

      return res

    # Make sure the state function itself knows where its allowed to
    # go (This is used to introspect the state graph).
    Decorated.next_states = next_states

    return Decorated

  return Decorator


class GRRFlow(object):
  """A GRRFlow class.

  Flows exist on the server to maintain session state. A flow is a
  state machine with each state being called when a new message is
  received.

  Do not instantiate flows directly. Flows are usually launched from
  FACTORY.StartFlow().
  """

  # This is used to arrange flows into a tree view
  category = ""

  __metaclass__ = registry.MetaclassRegistry

  # Should ACLs be enforced on this flow? This implies the user must have full
  # access to the client before they can run this flow.
  ACL_ENFORCED = True

  # These are the protobufs that this flow sends back to its caller if present.
  out_protobuf = None

  # Should we notify to the user about the progress of this flow?
  def __init__(self, context=None, notify_to_user=True):
    """Constructor for the Flow.

    Args:
      context: A FlowContext object that will save the state for this flow.
      notify_to_user: Should this flow notify completion to the user that
                      started it?
    Raises:
      RuntimeError: No context object was passed to this flow.
    """
    self.notify_to_user = notify_to_user

    if context is None:
      raise RuntimeError("No context given for flow %s." %
                         self.__class__.__name__)

    self.context = context
    self.context.SetFlowObj(self)

    stats.STATS.Increment("grr_flows_created")

  # Set up some proxy methods to allow easy access to the context.
  def GetFlowArgs(self):
    return self.context.GetFlowArgs()

  def CallClient(self, action_name, args_pb=None, next_state=None,
                 request_data=None, **kwargs):
    return self.context.CallClient(action_name, args_pb, next_state,
                                   request_data, **kwargs)

  def CallState(self, messages=None, next_state=""):
    return self.context.CallState(messages, next_state)

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    return self.context.CallFlow(FACTORY, flow_name, next_state, request_data,
                                 **kwargs)

  def FlushMessages(self):
    return self.context.FlushMessages()

  def ProcessCompletedRequests(self, unused_thread_pool, unused_messages=None):
    return self.context.ProcessCompletedRequests(unused_thread_pool,
                                                 unused_messages)

  def OutstandingRequests(self):
    return self.context.OutstandingRequests()

  def SendReply(self, response_proto):
    return self.context.SendReply(response_proto)

  def Error(self, backtrace=None):
    return self.context.Error(backtrace)

  def SetState(self, state):
    return self.context.SetState(state)

  def Terminate(self):
    return self.context.Terminate()

  def IsRunning(self):
    return self.context.IsRunning()

  @property
  def data_store(self):
    return self.context.data_store

  @data_store.setter
  def data_store(self, datastore):
    self.context.data_store = datastore

  @property
  def session_id(self):
    return self.context.session_id

  @session_id.setter
  def session_id(self, session_id):
    self.context.session_id = session_id
    self.context.flow_pb.session_id = session_id

  @property
  def client_id(self):
    return self.context.client_id

  @client_id.setter
  def client_id(self, client_id):
    self.context.client_id = client_id

  @property
  def user(self):
    return self.context.user

  @user.setter
  def user(self, user):
    self.context.user = user

  @property
  def flow_pb(self):
    return self.context.flow_pb

  @flow_pb.setter
  def flow_pb(self, flow_pb):
    self.context.flow_pb = flow_pb

  @property
  def token(self):
    return self.context.token

  def Start(self, unused_message=None):
    """The first state of the flow."""
    pass

  @StateHandler()
  def End(self):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.
    """
    self.Notify("FlowStatus", self.client_id,
                "Flow %s completed" % self.__class__.__name__)

  def Load(self):
    """Loads the flow from storage.

    This hook point is called after retrieval from storage and prior to state
    execution.
    """

  def Save(self):
    """Saves the flow to disk.

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

    result = self.flow_pb
    result.pickle = ""
    result.pickle = pickle.dumps(self)
    return result

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    logging.info(format_str, *args)

    try:
      # The status message is always in unicode
      status = format_str % args
    except TypeError:
      logging.error("Tried to log a format string with the wrong number "
                    "of arguments: %s", format_str)
      status = format_str

    self.context.SetStatus(utils.SmartUnicode(status))

    # Add the message to the flow's log attribute
    self.data_store.Set(scheduler.SCHEDULER.QueueToSubject(self.session_id),
                        aff4.AFF4Object.GRRFlow.SchemaCls.LOG,
                        status, replace=False, sync=False, token=self.token)

  def Status(self, format_str, *args):
    """Flows can call this method to set a status message visible to users."""
    self.Log(format_str, *args)

  def Notify(self, message_type, subject, msg):
    """Send a notification to the originating user.

    Args:
       message_type: The type of the message. This allows the admin ui to format
         a link to the origial object.
       subject: The urn of the AFF4 object of interest in this link.
       msg: A free form textual message.
    """
    if self.notify_to_user:
      # Prefix the message with the hostname of the client we are running
      # against.
      if self.client_id:
        client_fd = aff4.FACTORY.Open(self.client_id, mode="rw",
                                      token=self.token)
        hostname = client_fd.Get(client_fd.Schema.HOSTNAME) or ""
        client_msg = "%s: %s" % (hostname, msg)

      # Add notification to the User object.
      fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(
          self.token.username), "GRRUser", mode="rw", token=self.token)

      # Queue notifications to the user.
      fd.Notify(message_type, subject, client_msg, self.session_id)
      fd.Close()

      # Add notifications to the flow.
      notification = jobs_pb2.Notification(
          type=message_type, subject=utils.SmartUnicode(subject),
          message=utils.SmartUnicode(msg), source=self.session_id,
          timestamp=long(time.time() * 1e6))

      self.data_store.Set(scheduler.SCHEDULER.QueueToSubject(self.session_id),
                          aff4.AFF4Object.GRRFlow.SchemaCls.NOTIFICATION,
                          notification, replace=False, sync=False,
                          token=self.token)


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
    self.SetState(jobs_pb2.FlowPB.WELL_KNOWN)
    self.session_id = self.well_known_session_id

  def CallState(self, messages=None, next_state=None):
    """Well known flows have no states to call."""
    pass

  def _GetNewSessionID(self, unused_queue_name):
    # Always return a well known session id for this flow:
    return self.well_known_session_id

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed
    return 1

  def ProcessCompletedRequests(self, thread_pool, messages=None):
    """For WellKnownFlows we receive these messages directly."""
    stats.STATS.Increment("grr_worker_well_known_flow_requests")

    for msg in messages:
      if msg.request_id != 0:
        raise RuntimeError("WellKnownFlows must have request_id 0")

      thread_pool.AddTask(target=self.ProcessMessage,
                          args=(msg,), name=self.__class__.__name__)

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

  def __init__(self):
    self.outstanding_flows = set()

  def StartFlow(self, client_id, flow_name,
                queue_name=flow_context.DEFAULT_WORKER_QUEUE_NAME,
                event_id=None, token=None, _request_state=None, _store=None,
                **kw):
    """Creates and executes a new flow.

    Args:
      client_id: The URL of an existing client or None for well known flows.
      flow_name: The name of the flow to start (from the registry).
      queue_name: The name of the queue to invoke the flow.
      event_id: A logging event id for issuing further logs.
      token: The access token to be used for this request.
      _request_state: A parent flow's request state (Used internally only).
      _store: The data store to use for running this flow (only used for
              testing).
      **kw: flow specific keywords to be passed to the constructor.

    Returns:
      the session id of the flow.

    Raises:
      IOError: If the client_id is invalid.
    """
    try:
      flow_cls = GRRFlow.classes[flow_name]
    except KeyError:
      stats.STATS.Increment("grr_flow_invalid_flow_count")
      raise RuntimeError("Unable to locate flow %s" % flow_name)

    # Make sure we are allowed to run this flow.
    data_store.DB.security_manager.CheckAccess(token, [aff4.ROOT_URN.Add(
        client_id).Add(flow_name)], "x")

    # From now on we run with supervisor access
    if token is None:
      token = data_store.ACLToken()
    else:
      token = token.Copy()

    token.supervisor = True

    context = flow_context.FlowContext(client_id=client_id,
                                       flow_name=flow_cls.__name__,
                                       queue_name=queue_name,
                                       event_id=event_id, _store=_store,
                                       state=_request_state, token=token,
                                       args=utils.ProtoDict(kw).ToProto())
    flow_obj = flow_cls(context=context, **kw)

    if client_id is not None:
      # This client may not exist already but we create it anyway.
      client = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)

      flow_urn = aff4.FLOW_SWITCH_URN.Add(flow_obj.session_id)

      # Add this flow to the client
      client.AddAttribute(client.Schema.FLOW, flow_urn)
      client.Flush()

    logging.info("Scheduling %s(%s) on %s: %s", flow_obj.session_id,
                 flow_name, client_id, kw)

    # Just run the first state. NOTE: The Start flow always runs on the thread
    # that starts the flow so it must be very fast, basically just CallClient()
    # CallFlow() or CallState(). If a long delay is needed, this should call
    # CallState() and put the heavy lifting in another state.
    flow_obj.Start()

    # The flow does not need to actually remain running.
    if not flow_obj.OutstandingRequests():
      flow_obj.Terminate()

    # Push the new flow onto the queue
    task = scheduler.SCHEDULER.Task(queue=flow_obj.session_id, id=1,
                                    value=flow_obj.Dump())

    # There is a potential race here where we write the client requests first
    # and pickle the flow later. To avoid this, we have to keep the order and
    # schedule the tasks synchronously.
    scheduler.SCHEDULER.Schedule([task], sync=True, token=token)

    flow_obj.FlushMessages()

    return flow_obj.session_id

  def ListFlow(self, client_id, limit=1000, token=None):
    """Fetches the flow based on session_id.

    Args:
      client_id: Id of the client to retrieve tasks for.
      limit: Max number of flows to retrieve.
      token: The access token to be used for this request.

    Returns:
      A list of flow protobufs.
    """
    tasks = scheduler.SCHEDULER.Query(queue=client_id, limit=limit,
                                      decoder=jobs_pb2.FlowPB, token=token)
    live = [t for t in tasks if t.value.state != jobs_pb2.FlowPB.TERMINATED]
    return live

  def FetchFlow(self, session_id, sync=True, lock=True, token=None):
    """Fetches the flow based on session_id.

    This also grabs a lock on the flow. We might block here for some
    time.

    Args:
      session_id: Session id for the flow.
      sync: be synchronous - if we cant get the lock on a flow we wait
            until we do. If False we raise a LockError()
      lock: Should we lock the flow.
      token: The access token to be used for this request.

    Returns:
      A flow protobuf.

    Raises:
      LockError: If we are asynchronous and can not obtain the lock.
    """
    # Try to grab the lock on the flow
    while True:
      # Does the flow exist? Fail early if it doesn't
      flow_tasks = scheduler.SCHEDULER.Query(queue=session_id,
                                             decoder=jobs_pb2.FlowPB,
                                             limit=1, token=token)

      if not flow_tasks:
        logging.error("Flow %s does not exist", session_id)
        return None

      # Flow is terminated do not lock it
      if flow_tasks[0].value.state == jobs_pb2.FlowPB.TERMINATED:
        return flow_tasks[0].value

      # If we dont need to lock it - we are done
      if not lock: break

      flow_tasks = scheduler.SCHEDULER.QueryAndOwn(
          queue=session_id,
          limit=1,
          decoder=jobs_pb2.FlowPB,
          lease_seconds=6000, token=token)

      self.outstanding_flows.add(session_id)

      if flow_tasks: break

      # We can not wait - just raise now
      if not sync: raise LockError(session_id)

      logging.info("Waiting for flow %s", session_id)
      time.sleep(1)

    flow_pb = flow_tasks[0].value
    logging.info("Got flow %s %s", session_id, flow_pb.name)
    flow_pb.ts_id = flow_tasks[0].id

    return flow_pb

  def ReturnFlow(self, flow_pb, token=None):
    """Returns the flow when we are done with it.

    If the flow is marked as terminated we can delete it now.

    Args:
      flow_pb: flow proto
      token: The access token to be used for this request.
    """
    self.outstanding_flows.discard(flow_pb.session_id)

    # Is this flow still alive?
    if flow_pb.state != jobs_pb2.FlowPB.TERMINATED:
      logging.info("Returning flow %s", flow_pb.session_id)

      # Re-insert it into the Task Scheduler
      flow_task = scheduler.SCHEDULER.Task(queue=flow_pb.session_id,
                                           id=flow_pb.ts_id, value=flow_pb)

      scheduler.SCHEDULER.Schedule([flow_task], token=token)
    else:
      logging.info("Deleting flow %s", flow_pb.session_id)
      flow_pb.state = jobs_pb2.FlowPB.TERMINATED
      flow_task = scheduler.SCHEDULER.Task(
          queue=flow_pb.session_id, id=flow_pb.ts_id, value=flow_pb)
      scheduler.SCHEDULER.Schedule([flow_task], token=token)
      self.DeleteFlow(flow_pb, token=token)

  def TerminateFlow(self, flow_id, reason=None, token=None, force=False,
                    _store=None):
    """Terminate a flow.

    Args:
      flow_id: The flow session_id to terminate.
      reason: A reason to log.
      token: The access token to be used for this request.
      force: If True then terminate locked flows hard.
      _store: The data store to use for running this flow (only used for
         testing)

    Raises:
      FlowError: If the flow can not be found.
    """
    flow_pb = self.FetchFlow(flow_id, sync=False,
                             lock=not force, token=token)

    if flow_pb.state != jobs_pb2.FlowPB.RUNNING:
      raise FlowError("Flow can not be terminated - "
                      "it is not in the running state.")

    flow_obj = self.LoadFlow(flow_pb)
    if not flow_obj:
      raise FlowError("Could not terminate flow %s" % flow_id)

    # Override the data store for testing.
    if _store:
      flow_obj.data_store = _store

    if token is None:
      token = data_store.ACLToken()

    if reason is None:
      reason = "Manual termination by console."

    flow_obj.Error(reason)
    flow_obj.Log("Terminated by user {0}. Reason: {1}".format(token.username,
                                                              reason))
    # Make sure we are only allowed to terminate this flow, if we are allowed to
    # run it.
    data_store.DB.security_manager.CheckAccess(token, [aff4.ROOT_URN.Add(
        flow_obj.client_id).Add(flow_obj.__class__.__name__)], "x")

    # From now on we run with supervisor access
    super_token = data_store.ACLToken()
    super_token.supervisor = True

    # Also terminate its children
    for child in flow_pb.children:
      self.TerminateFlow(child, reason=None, token=super_token, force=force)

    self.ReturnFlow(flow_obj.flow_pb, token=super_token)

  def DeleteFlow(self, flow_pb, token=None):
    """Deletes the flow from the Task Scheduler."""
    flow_pb.state = jobs_pb2.FlowPB.TERMINATED
    flow_task = scheduler.SCHEDULER.Task(
        queue=flow_pb.session_id, id=flow_pb.ts_id, value=flow_pb)
    scheduler.SCHEDULER.Schedule([flow_task], token=token, sync=True)

  def LoadFlow(self, flow_pb):
    """Restores the flow stored in flow_pb.

    We might want to make this more flexible down the track
    (e.g. autoload new flows to avoid having to restart workers.)

    Args:
      flow_pb: The flow protobuf
    Returns:
      A complete flow object.

    Raises:
      FlowError: if we are unable to restore this flow.
    """
    if flow_pb is None: return

    try:
      result = pickle.loads(flow_pb.pickle)
      result.data_store = data_store.DB

      # Allow the flow to hook the load operation.
      result.Load()
    except (pickle.UnpicklingError, message.Error, ImportError), e:
      logging.error("Unable to handle Flow %s: %s", flow_pb.name, e)
      raise FlowError(flow_pb.name)

    # Restore the flow_pb here
    result.flow_pb = flow_pb

    return result


class ServerPubKeyCache(communicator.PubKeyCache):
  """A public key cache used by servers getting the key from the AFF4 client."""

  def __init__(self, client_cache, token=None):
    self.client_cache = client_cache
    self.token = token

  def GetRSAPublicKey(self, common_name="Server"):
    """Retrieves the public key for the common_name from data_store.

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

    except (KeyError, AttributeError):
      stats.STATS.Increment("grr_unique_clients")

      # Fetch the client's cert - We will be updating its clock attribute.
      client = aff4.FACTORY.Create(common_name, "VFSGRRClient", mode="rw",
                                   token=self.token)
      cert = client.Get(client.Schema.CERT)
      if not cert:
        raise communicator.UnknownClientCert("Cert not found")

      if cert.common_name != common_name:
        logging.error("Stored cert mismatch for %s", common_name)
        raise communicator.UnknownClientCert("Stored cert mismatch")

      self.client_cache.Put(common_name, client)

      return cert.GetPubKey()


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using AFF4."""

  def __init__(self, certificate, token=None):
    self.client_cache = utils.FastStore(100)
    self.token = token
    super(ServerCommunicator, self).__init__(certificate)
    self.pub_key_cache = ServerPubKeyCache(self.client_cache, token=token)

  def GetCipher(self, common_name="Server"):
    # This ensures the client is cached
    client = self.client_cache.Get(common_name)
    cipher = client.Get(client.Schema.CIPHER)
    if cipher:
      return cipher.data

    raise KeyError("Cipher not found.")

  def SetCipher(self, common_name, cipher):
    try:
      client = self.client_cache.Get(common_name)
    except KeyError:
      # Fetch the client's cert
      client = aff4.FACTORY.Create(common_name, "VFSGRRClient",
                                   token=self.token)
      self.client_cache.Put(common_name, client)

    client.Set(client.Schema.CIPHER(cipher))

  def _LoadOurCertificate(self, certificate_path):
    """Loads servers certificate with addition of keystore support."""
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
    self.common_name = self.pub_key_cache.GetCNFromCert(self.cert)

  def VerifyMessageSignature(self, response_comms, signed_message_list,
                             cipher, api_version):
    """Verifies the message list signature.

    In the server we check that the timestamp is later than the ping timestamp
    stored with the client. This ensures that client responses can not be
    replayed.

    Args:
       response_comms: The raw response_comms protobuf.
       signed_message_list: The SignedMessageList proto from the server.
       cipher: The cipher object that should be used to verify the message.
       api_version: The api version we should use.

    Returns:
       a jobs_pb2.GrrMessage.AuthorizationState.
    """
    result = jobs_pb2.GrrMessage.UNAUTHENTICATED
    try:
      if api_version >= 3:
        # New version:
        if cipher.HMAC(response_comms.encrypted) != response_comms.hmac:
          raise communicator.DecryptionError("HMAC does not match.")

        if cipher.signature_verified:
          result = jobs_pb2.GrrMessage.AUTHENTICATED

      else:
        # Fake the metadata
        cipher.cipher_metadata = jobs_pb2.CipherMetadata(
            source=signed_message_list.source)

        # Verify the incoming message.
        digest = cipher.hash_function(
            signed_message_list.message_list).digest()

        remote_public_key = self.pub_key_cache.GetRSAPublicKey(
            signed_message_list.source)

        try:
          stats.STATS.Increment("grr_rsa_operations")
          remote_public_key.verify(digest, signed_message_list.signature,
                                   cipher.hash_function_name)
        except RSA.RSAError, e:
          raise communicator.DecryptionError(e)

        result = jobs_pb2.GrrMessage.AUTHENTICATED

      if result == jobs_pb2.GrrMessage.AUTHENTICATED:
        # Check the timestamp
        client = self.client_cache.Get(cipher.cipher_metadata.source)

        # The very first packet we see from the client we do not have its clock
        remote_time = client.Get(client.Schema.CLOCK) or 0
        client_time = signed_message_list.timestamp
        if client_time > long(remote_time):
          stats.STATS.Increment("grr_authenticated_messages")

          # Update the timestamp
          client.Set(client.Schema.CLOCK, aff4.RDFDatetime(client_time))

          # If we are prepared to live with a slight risk of replay we can
          # remove this.
          client.Flush()

        else:
          # This is likely an old message
          return jobs_pb2.GrrMessage.DESYNCHRONIZED

    except (communicator.UnknownClientCert, KeyError):
      stats.STATS.Increment("grr_unauthenticated_messages")

    return result


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

  def __init__(self, certificate, logger, max_queue_size=50,
               message_expiry_time=120, max_retransmission_time=10, store=None,
               threadpool_prefix="grr_threadpool"):
    # Identify ourselves as the server.
    self.token = data_store.ACLToken("FrontEndServer", "Implied.")
    self.token.supervisor = True

    # This object manages our crypto
    self._communicator = ServerCommunicator(certificate, token=self.token)
    self.data_store = store or data_store.DB
    self.receive_thread_pool = {}
    self._logger = logger
    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size
    self.thread_pool = threadpool.ThreadPool.Factory(threadpool_prefix,
                                                     FLAGS.threadpool_size)
    self.thread_pool.Start()

    # Well known flows are run on the front end.
    self.well_known_flows = {}
    for name, cls in GRRFlow.classes.items():
      if issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        context = flow_context.FlowContext(flow_name=name, token=self.token)
        self.well_known_flows[
            cls.well_known_session_id] = cls(context)

  @stats.Timed("grr_frontendserver_handle_time")
  @stats.TimespanAvg("grr_frontendserver_handle_time_running_avg")
  def HandleMessageBundles(self, request_comms, response_comms):
    """Processes a queue of messages as passed from the client.

    We basically dispatch all the GrrMessages in the queue to the task scheduler
    for backend processing. We then retrieve from the TS the messages destined
    for this client.

    Args:
       request_comms: A ClientCommunication protobuf with messages sent by the
       client. source should be set to the client CN.

       response_comms: A ClientCommunication protobuf of jobs destined to this
       client.

    Returns:
       tuple of (source, message_count) where message_count is the number of
       messages received from the client with common name source.
    """
    messages, source, timestamp = self._communicator.DecodeMessages(
        request_comms)

    self.thread_pool.AddTask(
        target=self.ReceiveMessages, args=(messages,),
        name="ReceiveMessages")

    # We send the client a maximum of self.max_queue_size messages
    required_count = max(0, self.max_queue_size - request_comms.queue_size)

    message_list = jobs_pb2.MessageList()
    tasks = self.DrainTaskSchedulerQueueForClient(source, required_count,
                                                  message_list)

    # Encode the message_list in the response_comms using the same API version
    # the client used.
    try:
      self._communicator.EncodeMessages(
          message_list, response_comms, destination=str(source),
          timestamp=timestamp, api_version=request_comms.api_version)
    except communicator.UnknownClientCert:
      # We can not encode messages to the client yet because we do not have the
      # client certificate - return them to the queue so we can try again later.
      scheduler.SCHEDULER.Schedule(tasks, token=self.token)
      raise

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
    Returns:
       The tasks respresenting the messages returned. If we can not send them,
       we can reschedule them for later.
    """
    # Drain the queue for this client:
    new_tasks = scheduler.SCHEDULER.QueryAndOwn(
        queue=client_name,
        limit=max_count, token=self.token,
        lease_seconds=self.message_expiry_time,
        decoder=jobs_pb2.GrrMessage)

    response_message.job.extend([x.value for x in new_tasks])
    stats.STATS.Add("grr_messages_sent", len(new_tasks))

    return new_tasks

  def ReceiveMessages(self, messages):
    """Receives and processes the messages from the source.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      messages: A list of GrrMessage protos.
    """
    tasks_to_send = []
    for session_id, messages in utils.GroupBy(
        messages, operator.attrgetter("session_id")):

      # Remove and handle messages to WellKnownFlows
      messages = self.HandleWellKnownFlows(messages)
      if not messages: continue

      with flow_context.FlowManager(session_id, token=self.token,
                                    store=self.data_store) as flow_manager:
        for msg in messages:
          flow_manager.QueueResponse(msg)
          # For status messages also send to their worker queues.
          if msg.type == jobs_pb2.GrrMessage.STATUS:
            queue = self.GetQueueName(session_id)
            tasks_to_send.append(
                scheduler.SCHEDULER.Task(queue=queue, value=msg))

    scheduler.SCHEDULER.Schedule(tasks_to_send, token=self.token, sync=True)

  def HandleWellKnownFlows(self, messages):
    """Hands off messages to well known flows."""
    result = []

    for msg in messages:
      # This message should go directly to a WellKnownFlow
      if msg.request_id == 0:

        # Process this inline if we can.
        try:
          flow = self.well_known_flows[msg.session_id]
          flow.ProcessCompletedRequests(self.thread_pool, [msg])
        except KeyError:
          queue = self.GetQueueName(msg.session_id)
          scheduler.SCHEDULER.Schedule(
              scheduler.SCHEDULER.Task(queue=queue, value=msg),
              token=self.token)

        stats.STATS.Increment("grr_well_known_flow_requests")
      else:
        result.append(msg)

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


class LockError(FlowError):
  """Raised when we fail to grab a lock on the flow object."""


def ProcessCompletedRequests(flow_obj, thread_pool, reqs):
  flow_obj.ProcessCompletedRequests(thread_pool, reqs)


class GRRWorker(object):
  """A GRR worker."""

  # time to wait before polling when no jobs are currently in the
  # task scheduler (sec)
  POLLING_INTERVAL = 2
  SHORT_POLLING_INTERVAL = 0.3
  SHORT_POLL_TIME = 30

  # A class global threadpool to be used for all workers.
  thread_pool = None

  def __init__(self, queue_name=None, threadpool_prefix="grr_threadpool",
               threadpool_size=0, token=None):
    """Constructor.

    Args:
      queue_name: The name of the queue we use to fetch new messages
      from.
      threadpool_prefix: A name for the thread pool used by this worker.
      threadpool_size: The number of workers to start in this thread pool.
      token: The token to use for the worker.

    Raises:
      RuntimeError: If the token is not provided.
    """
    self.queue_name = queue_name

    if token is None:
      raise RuntimeError("A valid ACLToken is required.")

    # Make the thread pool a global so it can be reused for all workers.
    if GRRWorker.thread_pool is None:
      if threadpool_size == 0:
        threadpool_size = FLAGS.threadpool_size

      GRRWorker.thread_pool = threadpool.ThreadPool.Factory(threadpool_prefix,
                                                            threadpool_size)
      GRRWorker.thread_pool.Start()

    self.token = token

    # Initialize the logging component.
    self._logger = log.GrrLogger(component=self.__class__.__name__)

    self.last_active = 0

    # Well known flows are just instantiated.
    self.well_known_flows = {}
    for name, cls in GRRFlow.classes.items():
      if issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        context = flow_context.FlowContext(flow_name=name, token=self.token)
        self.well_known_flows[
            cls.well_known_session_id] = cls(context=context)

  def Run(self):
    """Event loop."""
    try:
      while 1:
        processed = self.RunOnce()

        if processed == 0:
          if time.time() - self.last_active > self.SHORT_POLL_TIME:
            time.sleep(self.POLLING_INTERVAL)
          else:
            time.sleep(self.SHORT_POLLING_INTERVAL)
        else:
          self.last_active = time.time()

    except KeyboardInterrupt:
      logging.info("Caught interrupt, exiting.")
      self.thread_pool.Join()

  def RunOnce(self):
    """Processes one set of messages from Task Scheduler.

    The worker processes new jobs from the task master. For each job
    we retrieve the session from the Task Scheduler.

    Returns:
        Total number of messages processed by this call.
    """

    # Any jobs for us?
    new_tasks = scheduler.SCHEDULER.QueryAndOwn(
        queue=self.queue_name,
        limit=FLAGS.worker_task_limit,
        decoder=jobs_pb2.GrrMessage, token=self.token,
        lease_seconds=600)

    try:
      self.ProcessMessages(new_tasks)
    # We need to keep going no matter what.
    except Exception, e:
      logging.error("Error processing message %s. %s.", e,
                    traceback.format_exc())

      if FLAGS.debug:
        pdb.post_mortem()

    return len(new_tasks)

  def ProcessMessages(self, tasks):
    """Processes all the flows in the messages.

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
      self.thread_pool.AddTask(target=self._ProcessMessages,
                               args=(session_id, flow_tasks),
                               name=self.__class__.__name__)

  def _ProcessMessages(self, session_id, flow_tasks):
    """Does the real work."""
    if session_id in self.well_known_flows:
      self.well_known_flows[session_id].ProcessCompletedRequests(
          self.thread_pool, [t.value for t in flow_tasks])
      return

    flow_pb = None
    # Take a lease on the flow:
    try:
      flow_pb = FACTORY.FetchFlow(session_id, sync=False, token=self.token)
    except LockError:
      # Some other thread already has a lock on this flow so we
      # reschedule the tasks for later
      # We keep the old TTL or the messages will be removed
      # from the queue after being unable to lock the flow various times.
      for task in flow_tasks:
        task.ttl += 1
      scheduler.SCHEDULER.Schedule(flow_tasks, token=self.token)
      return

    if flow_pb is None: return
    try:
      flow_obj = FACTORY.LoadFlow(flow_pb)
      flow_obj.ProcessCompletedRequests(self.thread_pool,
                                        [t.value for t in flow_tasks])

      # Re-serialize the flow
      flow_obj.Dump()
      flow_obj.FlushMessages()

    except FlowError, e:
      # Something went wrong - log it
      self.flow_pb.state = jobs_pb2.FlowPB.ERROR
      if not flow_pb.backtrace:
        flow_pb.backtrace = traceback.format_exc()

        logging.error("Flow %s: %s", flow_obj, e)

    finally:
      # Now remove the messages from the queue.
      scheduler.SCHEDULER.Delete(self.queue_name, flow_tasks, token=self.token)

      # Unlock this flow
      if flow_pb:
        FACTORY.ReturnFlow(flow_pb, token=self.token)


# These are globally available handles to factories


class FlowInit(aff4.AFF4InitHook):
  """Ensures that the Well known flows exist."""

  def __init__(self):
    # Make global handlers
    global FACTORY

    FACTORY = FlowFactory()


# A global factory that can be used to create new flows
FACTORY = None

