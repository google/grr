#!/usr/bin/env python
"""The in memory database methods for flow handling."""

import collections
import logging
import sys
import threading
import time

from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):
  """Base class for exceptions triggered in this package."""


class TimeOutWhileWaitingForFlowsToBeProcessedError(Error):
  """Raised by WaitUntilNoFlowsToProcess when waiting longer than time limit."""


class InMemoryDBFlowMixin(object):
  """InMemoryDB mixin for flow handling."""

  @utils.Synchronized
  def WriteMessageHandlerRequests(self, requests):
    """Writes a list of message handler requests to the database."""
    now = rdfvalue.RDFDatetime.Now()
    for r in requests:
      flow_dict = self.message_handler_requests.setdefault(r.handler_name, {})
      cloned_request = r.Copy()
      cloned_request.timestamp = now
      flow_dict[cloned_request.request_id] = cloned_request

  @utils.Synchronized
  def ReadMessageHandlerRequests(self):
    """Reads all message handler requests from the database."""
    res = []
    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        res.append(r.Copy())
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, None)
        res[-1].leased_until = existing_lease

    return sorted(res, key=lambda r: r.timestamp, reverse=True)

  @utils.Synchronized
  def DeleteMessageHandlerRequests(self, requests):
    """Deletes a list of message handler requests from the database."""

    for r in requests:
      flow_dict = self.message_handler_requests.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]
      flow_dict = self.message_handler_leases.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]

  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    """Leases a number of message handler requests up to the indicated limit."""
    self.UnregisterMessageHandler()

    self.handler_stop = False
    self.handler_thread = threading.Thread(
        name="message_handler",
        target=self._MessageHandlerLoop,
        args=(handler, lease_time, limit))
    self.handler_thread.daemon = True
    self.handler_thread.start()

  def UnregisterMessageHandler(self, timeout=None):
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.is_alive():
        raise RuntimeError("Message handler thread did not join in time.")
      self.handler_thread = None

  def _MessageHandlerLoop(self, handler, lease_time, limit):
    while not self.handler_stop:
      try:
        msgs = self._LeaseMessageHandlerRequests(lease_time, limit)
        if msgs:
          handler(msgs)
        else:
          time.sleep(0.2)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_LeaseMessageHandlerRequests raised %s.", e)

  @utils.Synchronized
  def _LeaseMessageHandlerRequests(self, lease_time, limit):
    """Read and lease some outstanding message handler requests."""
    leased_requests = []

    now = rdfvalue.RDFDatetime.Now()
    zero = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
    expiration_time = now + lease_time

    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, zero)
        if existing_lease < now:
          leases.setdefault(r.handler_name, {})[r.request_id] = expiration_time
          r.leased_until = expiration_time
          r.leased_by = utils.ProcessIdString()
          leased_requests.append(r)
          if len(leased_requests) >= limit:
            break

    return leased_requests

  @utils.Synchronized
  def ReadAllClientActionRequests(self, client_id):
    """Reads all client action requests available for a given client_id."""
    res = []
    for key, orig_request in self.client_action_requests.items():
      request_client_id, _, _ = key
      if request_client_id != client_id:
        continue

      request = orig_request.Copy()
      current_lease = self.client_action_request_leases.get(key)
      request.ttl = db.Database.CLIENT_MESSAGES_TTL
      if current_lease is not None:
        request.leased_until, request.leased_by, leased_count = current_lease
        request.ttl -= leased_count
      else:
        request.leased_until = None
        request.leased_by = None
      res.append(request)

    return res

  def _DeleteClientActionRequest(self, client_id, flow_id, request_id):
    key = (client_id, flow_id, request_id)
    self.client_action_requests.pop(key, None)
    self.client_action_request_leases.pop(key, None)

  @utils.Synchronized
  def DeleteClientActionRequests(self, requests):
    """Deletes a list of client action requests from the db."""
    to_delete = []
    for r in requests:
      to_delete.append((r.client_id, r.flow_id, r.request_id))

    if len(set(to_delete)) != len(to_delete):
      raise ValueError(
          "Received multiple copies of the same action request to delete.")

    for client_id, flow_id, request_id in to_delete:
      self._DeleteClientActionRequest(client_id, flow_id, request_id)

  @utils.Synchronized
  def LeaseClientActionRequests(self,
                                client_id,
                                lease_time=None,
                                limit=sys.maxsize):
    """Leases available client action requests for a client."""

    leased_requests = []

    now = rdfvalue.RDFDatetime.Now()
    expiration_time = now + lease_time
    process_id_str = utils.ProcessIdString()

    leases = self.client_action_request_leases
    # Can't use an iterator here since the dict might change when requests get
    # deleted.
    for key, request in sorted(self.client_action_requests.items()):
      if key[0] != client_id:
        continue

      existing_lease = leases.get(key)
      if not existing_lease or existing_lease[0] < now:
        if existing_lease:
          lease_count = existing_lease[-1] + 1
          if lease_count > db.Database.CLIENT_MESSAGES_TTL:
            self._DeleteClientActionRequest(*key)
            continue
        else:
          lease_count = 1

        leases[key] = (expiration_time, process_id_str, lease_count)
        request.leased_until = expiration_time
        request.leased_by = process_id_str
        request.ttl = db.Database.CLIENT_MESSAGES_TTL - lease_count
        leased_requests.append(request)
        if len(leased_requests) >= limit:
          break

    return leased_requests

  @utils.Synchronized
  def WriteClientActionRequests(self, requests):
    """Writes messages that should go to the client to the db."""
    for r in requests:
      req_dict = self.flow_requests.get((r.client_id, r.flow_id), {})
      if r.request_id not in req_dict:
        request_keys = [(r.client_id, r.flow_id, r.request_id) for r in requests
                       ]
        raise db.AtLeastOneUnknownRequestError(request_keys)

    for r in requests:
      request_key = (r.client_id, r.flow_id, r.request_id)
      self.client_action_requests[request_key] = r

  @utils.Synchronized
  def WriteFlowObject(self, flow_obj, allow_update=True):
    """Writes a flow object to the database."""
    if flow_obj.client_id not in self.metadatas:
      raise db.UnknownClientError(flow_obj.client_id)

    key = (flow_obj.client_id, flow_obj.flow_id)

    if not allow_update and key in self.flows:
      raise db.FlowExistsError(flow_obj.client_id, flow_obj.flow_id)

    now = rdfvalue.RDFDatetime.Now()

    clone = flow_obj.Copy()
    clone.last_update_time = now
    clone.create_time = now

    self.flows[key] = clone

  @utils.Synchronized
  def ReadFlowObject(self, client_id, flow_id):
    """Reads a flow object from the database."""
    try:
      return self.flows[(client_id, flow_id)].Copy()
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

  @utils.Synchronized
  def ReadAllFlowObjects(
      self,
      client_id: Optional[Text] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
  ) -> List[rdf_flow_objects.Flow]:
    """Returns all flow objects."""
    res = []
    for flow in self.flows.values():
      if ((client_id is None or flow.client_id == client_id) and
          (parent_flow_id is None or flow.parent_flow_id == parent_flow_id) and
          (min_create_time is None or flow.create_time >= min_create_time) and
          (max_create_time is None or flow.create_time <= max_create_time) and
          (include_child_flows or not flow.parent_flow_id) and
          (not_created_by is None or flow.creator not in not_created_by)):
        res.append(flow.Copy())
    return res

  @utils.Synchronized
  def LeaseFlowForProcessing(self, client_id, flow_id, processing_time):
    """Marks a flow as being processed on this worker and returns it."""
    rdf_flow = self.ReadFlowObject(client_id, flow_id)
    if rdf_flow.parent_hunt_id:
      rdf_hunt = self.ReadHuntObject(rdf_flow.parent_hunt_id)
      if not rdf_hunt_objects.IsHuntSuitableForFlowProcessing(
          rdf_hunt.hunt_state):
        raise db.ParentHuntIsNotRunningError(client_id, flow_id,
                                             rdf_hunt.hunt_id,
                                             rdf_hunt.hunt_state)

    now = rdfvalue.RDFDatetime.Now()
    if rdf_flow.processing_on and rdf_flow.processing_deadline > now:
      raise ValueError("Flow %s on client %s is already being processed." %
                       (flow_id, client_id))
    processing_deadline = now + processing_time
    process_id_string = utils.ProcessIdString()
    self.UpdateFlow(
        client_id,
        flow_id,
        processing_on=process_id_string,
        processing_since=now,
        processing_deadline=processing_deadline)
    rdf_flow.processing_on = process_id_string
    rdf_flow.processing_since = now
    rdf_flow.processing_deadline = processing_deadline
    return rdf_flow

  @utils.Synchronized
  def UpdateFlow(self,
                 client_id,
                 flow_id,
                 flow_obj=db.Database.unchanged,
                 flow_state=db.Database.unchanged,
                 client_crash_info=db.Database.unchanged,
                 processing_on=db.Database.unchanged,
                 processing_since=db.Database.unchanged,
                 processing_deadline=db.Database.unchanged):
    """Updates flow objects in the database."""

    try:
      flow = self.flows[(client_id, flow_id)]
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

    if flow_obj != db.Database.unchanged:
      new_flow = flow_obj.Copy()

      # Some fields cannot be updated.
      new_flow.client_id = flow.client_id
      new_flow.flow_id = flow.flow_id
      new_flow.long_flow_id = flow.long_flow_id
      new_flow.parent_flow_id = flow.parent_flow_id
      new_flow.parent_hunt_id = flow.parent_hunt_id
      new_flow.flow_class_name = flow.flow_class_name
      new_flow.creator = flow.creator

      self.flows[(client_id, flow_id)] = new_flow
      flow = new_flow

    if flow_state != db.Database.unchanged:
      flow.flow_state = flow_state
    if client_crash_info != db.Database.unchanged:
      flow.client_crash_info = client_crash_info
    if processing_on != db.Database.unchanged:
      flow.processing_on = processing_on
    if processing_since != db.Database.unchanged:
      flow.processing_since = processing_since
    if processing_deadline != db.Database.unchanged:
      flow.processing_deadline = processing_deadline
    flow.last_update_time = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def WriteFlowRequests(self, requests):
    """Writes a list of flow requests to the database."""
    flow_processing_requests = []

    for request in requests:
      if (request.client_id, request.flow_id) not in self.flows:
        raise db.AtLeastOneUnknownFlowError([(request.client_id,
                                              request.flow_id)])

    for request in requests:
      key = (request.client_id, request.flow_id)
      request_dict = self.flow_requests.setdefault(key, {})
      request_dict[request.request_id] = request.Copy()
      request_dict[request.request_id].timestamp = rdfvalue.RDFDatetime.Now()

      if request.needs_processing:
        flow = self.flows[(request.client_id, request.flow_id)]
        if flow.next_request_to_process == request.request_id:
          flow_processing_requests.append(
              rdf_flows.FlowProcessingRequest(
                  client_id=request.client_id,
                  flow_id=request.flow_id,
                  delivery_time=request.start_time))

    if flow_processing_requests:
      self.WriteFlowProcessingRequests(flow_processing_requests)

  @utils.Synchronized
  def UpdateIncrementalFlowRequests(
      self, client_id: str, flow_id: str,
      next_response_id_updates: Dict[int, int]) -> None:
    """Updates incremental flow requests."""
    if (client_id, flow_id) not in self.flows:
      raise db.UnknownFlowError(client_id, flow_id)

    request_dict = self.flow_requests[(client_id, flow_id)]
    for request_id, next_response_id in next_response_id_updates.items():
      request_dict[request_id].next_response_id = next_response_id
      request_dict[request_id].timestamp = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def DeleteFlowRequests(self, requests):
    """Deletes a list of flow requests from the database."""
    for request in requests:
      if (request.client_id, request.flow_id) not in self.flows:
        raise db.UnknownFlowError(request.client_id, request.flow_id)

    for request in requests:
      key = (request.client_id, request.flow_id)
      request_dict = self.flow_requests.get(key, {})
      try:
        del request_dict[request.request_id]
      except KeyError:
        raise db.UnknownFlowRequestError(request.client_id, request.flow_id,
                                         request.request_id)

      response_dict = self.flow_responses.get(key, {})
      try:
        del response_dict[request.request_id]
      except KeyError:
        pass

  @utils.Synchronized
  def WriteFlowResponses(self, responses):
    """Writes FlowMessages and updates corresponding requests."""
    status_available = {}
    requests_updated = set()
    task_ids_by_request = {}

    for response in responses:
      flow_key = (response.client_id, response.flow_id)
      if flow_key not in self.flows:
        logging.error("Received response for unknown flow %s, %s.",
                      response.client_id, response.flow_id)
        continue

      request_dict = self.flow_requests.get(flow_key, {})
      if response.request_id not in request_dict:
        logging.error("Received response for unknown request %s, %s, %d.",
                      response.client_id, response.flow_id, response.request_id)
        continue

      response_dict = self.flow_responses.setdefault(flow_key, {})
      clone = response.Copy()
      clone.timestamp = rdfvalue.RDFDatetime.Now()

      response_dict.setdefault(response.request_id,
                               {})[response.response_id] = clone

      if isinstance(response, rdf_flow_objects.FlowStatus):
        status_available[(response.client_id, response.flow_id,
                          response.request_id, response.response_id)] = response

      request_key = (response.client_id, response.flow_id, response.request_id)
      requests_updated.add(request_key)
      try:
        task_ids_by_request[request_key] = response.task_id
      except AttributeError:
        pass

    # Every time we get a status we store how many responses are expected.
    for status in status_available.values():
      request_dict = self.flow_requests[(status.client_id, status.flow_id)]
      request = request_dict[status.request_id]
      request.nr_responses_expected = status.response_id

    # And we check for all updated requests if we need to process them.
    needs_processing = []
    for client_id, flow_id, request_id in requests_updated:
      flow_key = (client_id, flow_id)
      flow = self.flows[flow_key]
      request_dict = self.flow_requests[flow_key]
      request = request_dict[request_id]

      added_for_processing = False
      if request.nr_responses_expected and not request.needs_processing:
        response_dict = self.flow_responses.setdefault(flow_key, {})
        responses = response_dict.get(request_id, {})

        if len(responses) == request.nr_responses_expected:
          request.needs_processing = True
          self._DeleteClientActionRequest(client_id, flow_id, request_id)

          if flow.next_request_to_process == request_id:
            added_for_processing = True
            needs_processing.append(
                rdf_flows.FlowProcessingRequest(
                    client_id=client_id, flow_id=flow_id))

      if (request.callback_state and
          flow.next_request_to_process == request_id and
          not added_for_processing):
        needs_processing.append(
            rdf_flows.FlowProcessingRequest(
                client_id=client_id, flow_id=flow_id))

    if needs_processing:
      self.WriteFlowProcessingRequests(needs_processing)

    return needs_processing

  @utils.Synchronized
  def ReadAllFlowRequestsAndResponses(self, client_id, flow_id):
    """Reads all requests and responses for a given flow from the database."""
    flow_key = (client_id, flow_id)
    try:
      self.flows[flow_key]
    except KeyError:
      return []

    request_dict = self.flow_requests.get(flow_key, {})
    response_dict = self.flow_responses.get(flow_key, {})

    res = []
    for request_id in sorted(request_dict):
      res.append((request_dict[request_id], response_dict.get(request_id, {})))

    return res

  @utils.Synchronized
  def DeleteAllFlowRequestsAndResponses(self, client_id, flow_id):
    """Deletes all requests and responses for a given flow from the database."""
    flow_key = (client_id, flow_id)
    try:
      self.flows[flow_key]
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

    try:
      del self.flow_requests[flow_key]
    except KeyError:
      pass

    try:
      del self.flow_responses[flow_key]
    except KeyError:
      pass

  @utils.Synchronized
  def ReadFlowRequestsReadyForProcessing(self,
                                         client_id,
                                         flow_id,
                                         next_needed_request=None):
    """Reads all requests for a flow that can be processed by the worker."""
    request_dict = self.flow_requests.get((client_id, flow_id), {})
    response_dict = self.flow_responses.get((client_id, flow_id), {})

    # Do a pass for completed requests.
    res = {}
    for request_id in sorted(request_dict):
      # Ignore outdated requests.
      if request_id < next_needed_request:
        continue
      # The request we are currently looking for is not in yet, we are done.
      if request_id != next_needed_request:
        break
      request = request_dict[request_id]

      if not request.needs_processing:
        break

      responses = sorted(
          response_dict.get(request_id, {}).values(),
          key=lambda response: response.response_id)
      # Serialize/deserialize responses to better simulate the
      # real DB behavior (where serialization/deserialization is almost
      # guaranteed to be done).
      # TODO(user): change mem-db implementation to do
      # serialization/deserialization everywhere in a generic way.
      responses = [
          r.__class__.FromSerializedBytes(r.SerializeToBytes())
          for r in responses
      ]
      res[request_id] = (request, responses)
      next_needed_request += 1

    # Do a pass for incremental requests.
    for request_id in request_dict:
      # Ignore outdated and processed requests.
      if request_id < next_needed_request:
        continue

      request = request_dict[request_id]
      if not request.callback_state:
        continue

      responses = response_dict.get(request_id, {}).values()
      responses = [
          r for r in responses if r.response_id >= request.next_response_id
      ]
      responses = sorted(responses, key=lambda response: response.response_id)

      # Serialize/deserialize responses to better simulate the
      # real DB behavior (where serialization/deserialization is almost
      # guaranteed to be done).
      # TODO(user): change mem-db implementation to do
      # serialization/deserialization everywhere in a generic way.
      responses = [
          r.__class__.FromSerializedBytes(r.SerializeToBytes())
          for r in responses
      ]
      res[request_id] = (request, responses)

    return res

  @utils.Synchronized
  def ReleaseProcessedFlow(self, flow_obj):
    """Releases a flow that the worker was processing to the database."""
    key = (flow_obj.client_id, flow_obj.flow_id)
    next_id_to_process = flow_obj.next_request_to_process
    request_dict = self.flow_requests.get(key, {})
    if (next_id_to_process in request_dict and
        request_dict[next_id_to_process].needs_processing):
      return False

    self.UpdateFlow(
        flow_obj.client_id,
        flow_obj.flow_id,
        flow_obj=flow_obj,
        processing_on=None,
        processing_since=None,
        processing_deadline=None)
    return True

  def _InlineProcessingOK(self, requests):
    for r in requests:
      if r.delivery_time is not None:
        return False
    return True

  @utils.Synchronized
  def WriteFlowProcessingRequests(self, requests):
    """Writes a list of flow processing requests to the database."""
    # If we don't have a handler thread running, we might be able to process the
    # requests inline. If we are not, we start the handler thread for real and
    # queue the requests normally.
    if not self.flow_handler_thread and self.flow_handler_target:
      if self._InlineProcessingOK(requests):
        for r in requests:
          self.flow_handler_target(r)
        return
      else:
        self._RegisterFlowProcessingHandler(self.flow_handler_target)
        self.flow_handler_target = None

    now = rdfvalue.RDFDatetime.Now()
    for r in requests:
      cloned_request = r.Copy()
      cloned_request.timestamp = now
      key = (r.client_id, r.flow_id)
      self.flow_processing_requests[key] = cloned_request

  @utils.Synchronized
  def ReadFlowProcessingRequests(self):
    """Reads all flow processing requests from the database."""
    return list(self.flow_processing_requests.values())

  @utils.Synchronized
  def AckFlowProcessingRequests(self, requests):
    """Deletes a list of flow processing requests from the database."""
    for r in requests:
      key = (r.client_id, r.flow_id)
      if key in self.flow_processing_requests:
        del self.flow_processing_requests[key]

  @utils.Synchronized
  def DeleteAllFlowProcessingRequests(self):
    self.flow_processing_requests = {}

  def RegisterFlowProcessingHandler(self, handler):
    """Registers a message handler to receive flow processing messages."""
    self.UnregisterFlowProcessingHandler()

    # For the in memory db, we just call the handler straight away if there is
    # no delay in starting times so we don't run the thread here.
    self.flow_handler_target = handler

    for request in self._GetFlowRequestsReadyForProcessing():
      handler(request)
      with self.lock:
        self.flow_processing_requests.pop((request.client_id, request.flow_id),
                                          None)

  def _RegisterFlowProcessingHandler(self, handler):
    """Registers a handler to receive flow processing messages."""
    self.flow_handler_stop = False
    self.flow_handler_thread = threading.Thread(
        name="flow_processing_handler",
        target=self._HandleFlowProcessingRequestLoop,
        args=(handler,))
    self.flow_handler_thread.daemon = True
    self.flow_handler_thread.start()

  def UnregisterFlowProcessingHandler(self, timeout=None):
    """Unregisters any registered flow processing handler."""
    self.flow_handler_target = None

    if self.flow_handler_thread:
      self.flow_handler_stop = True
      self.flow_handler_thread.join(timeout)
      if self.flow_handler_thread.is_alive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_handler_thread = None

  @utils.Synchronized
  def _GetFlowRequestsReadyForProcessing(self):
    now = rdfvalue.RDFDatetime.Now()
    todo = []
    for r in list(self.flow_processing_requests.values()):
      if r.delivery_time is None or r.delivery_time <= now:
        todo.append(r)

    return todo

  def WaitUntilNoFlowsToProcess(self, timeout=None):
    """Waits until flow processing thread is done processing flows.

    Args:
      timeout: If specified, is a max number of seconds to spend waiting.

    Raises:
      TimeOutWhileWaitingForFlowsToBeProcessedError: if timeout is reached.
    """
    t = self.flow_handler_thread
    if not t:
      return

    start_time = time.time()
    while True:
      with self.lock:
        # If the thread is dead, or there are no requests
        # to be processed/being processed, we stop waiting
        # and return from the function.
        if (not t.is_alive() or
            (not self._GetFlowRequestsReadyForProcessing() and
             not self.flow_handler_num_being_processed)):
          return

      time.sleep(0.2)

      if timeout and time.time() - start_time > timeout:
        raise TimeOutWhileWaitingForFlowsToBeProcessedError(
            "Flow processing didn't finish in time.")

  def _HandleFlowProcessingRequestLoop(self, handler):
    """Handler thread for the FlowProcessingRequest queue."""
    while not self.flow_handler_stop:
      with self.lock:
        todo = self._GetFlowRequestsReadyForProcessing()
        for request in todo:
          self.flow_handler_num_being_processed += 1
          del self.flow_processing_requests[(request.client_id,
                                             request.flow_id)]

      for request in todo:
        handler(request)
        with self.lock:
          self.flow_handler_num_being_processed -= 1

      time.sleep(0.2)

  @utils.Synchronized
  def _WriteFlowResultsOrErrors(self, container, items):
    for i in items:
      dest = container.setdefault((i.client_id, i.flow_id), [])
      to_write = i.Copy()
      to_write.timestamp = rdfvalue.RDFDatetime.Now()
      dest.append(to_write)

  def WriteFlowResults(self, results):
    """Writes flow results for a given flow."""
    self._WriteFlowResultsOrErrors(self.flow_results, results)

  @utils.Synchronized
  def _ReadFlowResultsOrErrors(self,
                               container,
                               client_id,
                               flow_id,
                               offset,
                               count,
                               with_tag=None,
                               with_type=None,
                               with_substring=None):
    """Reads flow results/errors of a given flow using given query options."""
    results = sorted(
        [x.Copy() for x in container.get((client_id, flow_id), [])],
        key=lambda r: r.timestamp)

    # This is done in order to pass the tests that try to deserialize
    # value of an unrecognized type.
    for r in results:
      cls_name = compatibility.GetName(r.payload.__class__)
      if cls_name not in rdfvalue.RDFValue.classes:
        r.payload = rdf_objects.SerializedValueOfUnrecognizedType(
            type_name=cls_name, value=r.payload.SerializeToBytes())

    if with_tag is not None:
      results = [i for i in results if i.tag == with_tag]

    if with_type is not None:
      results = [
          i for i in results
          if compatibility.GetName(i.payload.__class__) == with_type
      ]

    if with_substring is not None:
      encoded_substring = with_substring.encode("utf8")
      results = [
          i for i in results
          if encoded_substring in i.payload.SerializeToBytes()
      ]

    return results[offset:offset + count]

  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    """Reads flow results of a given flow using given query options."""
    return self._ReadFlowResultsOrErrors(
        self.flow_results,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_substring=with_substring)

  @utils.Synchronized
  def CountFlowResults(self, client_id, flow_id, with_tag=None, with_type=None):
    """Counts flow results of a given flow using given query options."""
    return len(
        self.ReadFlowResults(
            client_id,
            flow_id,
            0,
            sys.maxsize,
            with_tag=with_tag,
            with_type=with_type))

  @utils.Synchronized
  def CountFlowResultsByType(self, client_id, flow_id):
    """Returns counts of flow results grouped by result type."""
    result = collections.Counter()
    for hr in self.ReadFlowResults(client_id, flow_id, 0, sys.maxsize):
      key = compatibility.GetName(hr.payload.__class__)
      result[key] += 1

    return result

  def WriteFlowErrors(self, errors):
    """Writes flow errors for a given flow."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    self._WriteFlowResultsOrErrors(self.flow_errors, errors)

  def ReadFlowErrors(self,
                     client_id,
                     flow_id,
                     offset,
                     count,
                     with_tag=None,
                     with_type=None):
    """Reads flow errors of a given flow using given query options."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._ReadFlowResultsOrErrors(
        self.flow_errors,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type)

  @utils.Synchronized
  def CountFlowErrors(self, client_id, flow_id, with_tag=None, with_type=None):
    """Counts flow errors of a given flow using given query options."""
    return len(
        self.ReadFlowErrors(
            client_id,
            flow_id,
            0,
            sys.maxsize,
            with_tag=with_tag,
            with_type=with_type))

  @utils.Synchronized
  def CountFlowErrorsByType(self, client_id, flow_id):
    """Returns counts of flow errors grouped by error type."""
    result = collections.Counter()
    for hr in self.ReadFlowErrors(client_id, flow_id, 0, sys.maxsize):
      key = compatibility.GetName(hr.payload.__class__)
      result[key] += 1

    return result

  @utils.Synchronized
  def WriteFlowLogEntry(self, entry: rdf_flow_objects.FlowLogEntry) -> None:
    """Writes a single flow log entry to the database."""
    key = (entry.client_id, entry.flow_id)

    if key not in self.flows:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id)

    entry = entry.Copy()
    entry.timestamp = rdfvalue.RDFDatetime.Now()

    self.flow_log_entries.setdefault(key, []).append(entry)

  @utils.Synchronized
  def ReadFlowLogEntries(self,
                         client_id,
                         flow_id,
                         offset,
                         count,
                         with_substring=None):
    """Reads flow log entries of a given flow using given query options."""
    entries = sorted(
        self.flow_log_entries.get((client_id, flow_id), []),
        key=lambda e: e.timestamp)

    if with_substring is not None:
      entries = [i for i in entries if with_substring in i.message]

    return entries[offset:offset + count]

  @utils.Synchronized
  def CountFlowLogEntries(self, client_id, flow_id):
    """Returns number of flow log entries of a given flow."""
    return len(self.ReadFlowLogEntries(client_id, flow_id, 0, sys.maxsize))

  @utils.Synchronized
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: rdf_flow_objects.FlowOutputPluginLogEntry,
  ) -> None:
    """Writes a single output plugin log entry to the database."""
    key = (entry.client_id, entry.flow_id)

    if key not in self.flows:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id)

    entry = entry.Copy()
    entry.timestamp = rdfvalue.RDFDatetime.Now()

    self.flow_output_plugin_log_entries.setdefault(key, []).append(entry)

  @utils.Synchronized
  def ReadFlowOutputPluginLogEntries(self,
                                     client_id,
                                     flow_id,
                                     output_plugin_id,
                                     offset,
                                     count,
                                     with_type=None):
    """Reads flow output plugin log entries."""
    entries = sorted(
        self.flow_output_plugin_log_entries.get((client_id, flow_id), []),
        key=lambda e: e.timestamp)

    entries = [e for e in entries if e.output_plugin_id == output_plugin_id]

    if with_type is not None:
      entries = [e for e in entries if e.log_entry_type == with_type]

    return entries[offset:offset + count]

  @utils.Synchronized
  def CountFlowOutputPluginLogEntries(self,
                                      client_id,
                                      flow_id,
                                      output_plugin_id,
                                      with_type=None):
    """Returns number of flow output plugin log entries of a given flow."""

    return len(
        self.ReadFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            0,
            sys.maxsize,
            with_type=with_type))

  @utils.Synchronized
  def WriteScheduledFlow(
      self, scheduled_flow: rdf_flow_objects.ScheduledFlow) -> None:
    """See base class."""
    if scheduled_flow.client_id not in self.metadatas:
      raise db.UnknownClientError(scheduled_flow.client_id)

    if scheduled_flow.creator not in self.users:
      raise db.UnknownGRRUserError(scheduled_flow.creator)

    full_id = (scheduled_flow.client_id, scheduled_flow.creator,
               scheduled_flow.scheduled_flow_id)
    self.scheduled_flows[full_id] = scheduled_flow.Copy()

  @utils.Synchronized
  def DeleteScheduledFlow(self, client_id: str, creator: str,
                          scheduled_flow_id: str) -> None:
    """See base class."""
    try:
      self.scheduled_flows.pop((client_id, creator, scheduled_flow_id))
    except KeyError:
      raise db.UnknownScheduledFlowError(
          client_id=client_id,
          creator=creator,
          scheduled_flow_id=scheduled_flow_id)

  @utils.Synchronized
  def ListScheduledFlows(
      self, client_id: str,
      creator: str) -> Sequence[rdf_flow_objects.ScheduledFlow]:
    """See base class."""
    return [
        sf.Copy()
        for sf in self.scheduled_flows.values()
        if sf.client_id == client_id and sf.creator == creator
    ]
