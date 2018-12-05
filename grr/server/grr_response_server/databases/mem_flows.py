#!/usr/bin/env python
"""The in memory database methods for flow handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import sys
import threading
import time

from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr_response_server import db
from grr_response_server import db_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


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
    for requests in itervalues(self.message_handler_requests):
      for r in itervalues(requests):
        res.append(r.Copy())
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, None)
        res[-1].leased_until = existing_lease

    return sorted(res, key=lambda r: -1 * r.timestamp)

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

  @utils.Synchronized
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

  @utils.Synchronized
  def UnregisterMessageHandler(self, timeout=None):
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.isAlive():
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
    for requests in itervalues(self.message_handler_requests):
      for r in itervalues(requests):
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
  def ReadClientMessages(self, client_id):
    """Reads all client messages available for a given client_id."""
    res = []
    for msgs_by_id in itervalues(self.client_messages):
      for orig_msg in sorted(itervalues(msgs_by_id), key=lambda m: m.task_id):
        if db_utils.ClientIdFromGrrMessage(orig_msg) != client_id:
          continue
        msg = orig_msg.Copy()
        current_lease = self.client_message_leases.get(msg.task_id)
        if current_lease:
          msg.leased_until, msg.leased_by, _ = current_lease
        res.append(msg)

    return res

  def _DeleteClientMessage(self, client_id, task_id):
    tasks = self.client_messages.get(client_id)
    if not tasks or task_id not in tasks:
      # TODO(amoser): Once new flows are in, reevaluate if we can raise on
      # deletion request for unknown messages.
      return
    del tasks[task_id]
    if task_id in self.client_message_leases:
      del self.client_message_leases[task_id]

  @utils.Synchronized
  def DeleteClientMessages(self, messages):
    """Deletes a list of client messages from the db."""
    to_delete = []
    for m in messages:
      client_id = db_utils.ClientIdFromGrrMessage(m)
      to_delete.append((client_id, m.task_id))

    if len(set(to_delete)) != len(to_delete):
      raise ValueError(
          "Received multiple copies of the same message to delete.")

    for client_id, task_id in to_delete:
      self._DeleteClientMessage(client_id, task_id)

  @utils.Synchronized
  def LeaseClientMessages(self, client_id, lease_time=None, limit=sys.maxsize):
    """Leases available client messages for the client with the given id."""
    leased_messages = []

    now = rdfvalue.RDFDatetime.Now()
    expiration_time = now + lease_time
    process_id_str = utils.ProcessIdString()

    leases = self.client_message_leases
    for msgs_by_id in itervalues(self.client_messages):
      for msg in sorted(itervalues(msgs_by_id), key=lambda m: m.task_id):
        if db_utils.ClientIdFromGrrMessage(msg) != client_id:
          continue

        existing_lease = leases.get(msg.task_id)
        if not existing_lease or existing_lease[0] < now:
          if existing_lease:
            lease_count = existing_lease[-1] + 1
            # >= comparison since this check happens before the lease.
            if lease_count >= db.Database.CLIENT_MESSAGES_TTL:
              self._DeleteClientMessage(client_id, msg.task_id)
              continue
            leases[msg.task_id] = (expiration_time, process_id_str, lease_count)
          else:
            leases[msg.task_id] = (expiration_time, process_id_str, 0)

          msg.leased_until = expiration_time
          msg.leased_by = process_id_str
          leased_messages.append(msg)
          if len(leased_messages) >= limit:
            break

    return leased_messages

  @utils.Synchronized
  def WriteClientMessages(self, messages):
    """Writes messages that should go to the client to the db."""
    client_ids = [db_utils.ClientIdFromGrrMessage(msg) for msg in messages]
    for client_id in client_ids:
      if client_id not in self.metadatas:
        raise db.AtLeastOneUnknownClientError(client_ids=client_ids)

    for m in messages:
      client_id = db_utils.ClientIdFromGrrMessage(m)
      self.client_messages.setdefault(client_id, {})[m.task_id] = m

  @utils.Synchronized
  def WriteFlowObject(self, flow_obj):
    """Writes a flow object to the database."""
    if flow_obj.client_id not in self.metadatas:
      raise db.UnknownClientError(flow_obj.client_id)

    clone = flow_obj.Copy()
    clone.last_update_time = rdfvalue.RDFDatetime.Now()
    self.flows[(flow_obj.client_id, flow_obj.flow_id)] = clone

  @utils.Synchronized
  def ReadFlowObject(self, client_id, flow_id):
    """Reads a flow object from the database."""
    try:
      return self.flows[(client_id, flow_id)].Copy()
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

  def ReadAllFlowObjects(self, client_id, min_create_time=None):
    """Reads all flow objects from the database for a given client."""
    res = []
    for client_flow_id, flow in iteritems(self.flows):
      if min_create_time is not None and flow.create_time < min_create_time:
        continue
      if client_flow_id[0] == client_id:
        res.append(flow.Copy())
    return res

  @utils.Synchronized
  def ReadChildFlowObjects(self, client_id, flow_id):
    """Reads flows that were started by a given flow from the database."""
    res = []
    for flow in itervalues(self.flows):
      if flow.client_id == client_id and flow.parent_flow_id == flow_id:
        res.append(flow)
    return res

  @utils.Synchronized
  def ReadFlowForProcessing(self, client_id, flow_id, processing_time):
    """Marks a flow as being processed on this worker and returns it."""
    rdf_flow = self.ReadFlowObject(client_id, flow_id)
    now = rdfvalue.RDFDatetime.Now()
    if rdf_flow.processing_on and rdf_flow.processing_deadline > now:
      raise ValueError("Flow %s on client %s is already being processed." %
                       (client_id, flow_id))
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
                 client_crash_info=db.Database.unchanged,
                 pending_termination=db.Database.unchanged,
                 processing_on=db.Database.unchanged,
                 processing_since=db.Database.unchanged,
                 processing_deadline=db.Database.unchanged):
    """Updates flow objects in the database."""

    try:
      flow = self.flows[(client_id, flow_id)]
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

    if flow_obj != db.Database.unchanged:
      self.flows[(client_id, flow_id)] = flow_obj
      flow = flow_obj

    if client_crash_info != db.Database.unchanged:
      flow.client_crash_info = client_crash_info
    if pending_termination != db.Database.unchanged:
      flow.pending_termination = pending_termination
    if processing_on != db.Database.unchanged:
      flow.processing_on = processing_on
    if processing_since != db.Database.unchanged:
      flow.processing_since = processing_since
    if processing_deadline != db.Database.unchanged:
      flow.processing_deadline = processing_deadline
    flow.last_update_time = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def UpdateFlows(self,
                  client_id_flow_id_pairs,
                  pending_termination=db.Database.unchanged):
    """Updates flow objects in the database."""
    for client_id, flow_id in client_id_flow_id_pairs:
      try:
        self.UpdateFlow(
            client_id, flow_id, pending_termination=pending_termination)
      except db.UnknownFlowError:
        pass

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
                  client_id=request.client_id, flow_id=request.flow_id))

    if flow_processing_requests:
      self.WriteFlowProcessingRequests(flow_processing_requests)

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
    """Writes a list of flow responses to the database."""
    status_available = set()
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
        status_available.add(response)

      request_key = (response.client_id, response.flow_id, response.request_id)
      requests_updated.add(request_key)
      try:
        task_ids_by_request[request_key] = response.task_id
      except AttributeError:
        pass

    # Every time we get a status we store how many responses are expected.
    for status in status_available:
      request_dict = self.flow_requests[(status.client_id, status.flow_id)]
      request = request_dict[status.request_id]
      request.nr_responses_expected = status.response_id

    # And we check for all updated requests if we need to process them.
    needs_processing = []
    for client_id, flow_id, request_id in requests_updated:
      flow_key = (client_id, flow_id)
      request_dict = self.flow_requests[flow_key]
      request = request_dict[request_id]
      if request.nr_responses_expected and not request.needs_processing:
        response_dict = self.flow_responses.setdefault(flow_key, {})
        responses = response_dict.get(request_id, {})

        if len(responses) == request.nr_responses_expected:
          request.needs_processing = True
          task_id = task_ids_by_request.get((client_id, flow_id, request_id))
          if task_id:
            self._DeleteClientMessage(client_id, task_id)

          flow = self.flows[flow_key]
          if flow.next_request_to_process == request_id:
            needs_processing.append(
                rdf_flows.FlowProcessingRequest(
                    client_id=client_id, flow_id=flow_id))

    if needs_processing:
      self.WriteFlowProcessingRequests(needs_processing)

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
          itervalues(response_dict.get(request_id, {})),
          key=lambda response: response.response_id)
      res[request_id] = (request, responses)
      next_needed_request += 1

    return res

  @utils.Synchronized
  def ReturnProcessedFlow(self, flow_obj):
    """Returns a flow that the worker was processing to the database."""
    key = (flow_obj.client_id, flow_obj.flow_id)
    next_id_to_process = flow_obj.next_request_to_process
    request_dict = self.flow_requests.get(key, {})
    if (next_id_to_process in request_dict and
        request_dict[next_id_to_process].needs_processing):
      return False

    flow_obj.processing_on = None
    flow_obj.processing_since = None
    flow_obj.processing_deadline = None
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
    return list(itervalues(self.flow_processing_requests))

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
      if self.flow_handler_thread.isAlive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_handler_thread = None

  def _HandleFlowProcessingRequestLoop(self, handler):
    """Handler thread for the FlowProcessingRequest queue."""
    while not self.flow_handler_stop:
      now = rdfvalue.RDFDatetime.Now()
      todo = []
      for r in list(itervalues(self.flow_processing_requests)):
        if r.delivery_time is None or r.delivery_time <= now:
          todo.append(r)
          del self.flow_processing_requests[(r.client_id, r.flow_id)]

      for request in todo:
        handler(request)

      time.sleep(0.2)

  def WriteFlowResults(self, client_id, flow_id, results):
    """Writes flow results for a given flow."""
    dest = self.flow_results.setdefault((client_id, flow_id), [])
    for r in results:
      to_write = r.Copy()
      to_write.timestamp = rdfvalue.RDFDatetime.Now()
      dest.append(to_write)

  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    """Reads flow results of a given flow using given query options."""
    results = sorted(
        [x.Copy() for x in self.flow_results.get((client_id, flow_id), [])],
        key=lambda r: r.timestamp)

    # This is done in order to pass the tests that try to deserialize
    # value of an unrecognized type.
    for r in results:
      cls_name = compatibility.GetName(r.payload.__class__)
      if cls_name not in rdfvalue.RDFValue.classes:
        r.payload = rdf_objects.SerializedValueOfUnrecognizedType(
            type_name=cls_name, value=r.payload.SerializeToString())

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
          if encoded_substring in i.payload.SerializeToString()
      ]

    return results[offset:offset + count]

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

  def WriteFlowLogEntries(self, client_id, flow_id, entries):
    """Writes flow log entries for a given flow."""
    dest = self.flow_log_entries.setdefault((client_id, flow_id), [])
    for e in entries:
      to_write = e.Copy()
      to_write.timestamp = rdfvalue.RDFDatetime.Now()
      dest.append(to_write)

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

  def CountFlowLogEntries(self, client_id, flow_id):
    """Returns number of flow log entries of a given flow."""
    return len(self.ReadFlowLogEntries(client_id, flow_id, 0, sys.maxsize))
