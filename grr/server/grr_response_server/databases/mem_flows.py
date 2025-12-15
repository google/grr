#!/usr/bin/env python
"""The in memory database methods for flow handling."""

import collections
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
import logging
import sys
import threading
import time
from typing import Any, NewType, Optional, TypeVar, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.models import hunts as models_hunts
from grr_response_proto import rrg_pb2


T = TypeVar("T")

ClientID = NewType("ClientID", str)
FlowID = NewType("FlowID", str)
Username = NewType("Username", str)
HandlerName = NewType("HandlerName", str)
RequestID = NewType("RequestID", int)


class Error(Exception):
  """Base class for exceptions triggered in this package."""


class TimeOutWhileWaitingForFlowsToBeProcessedError(Error):
  """Raised by WaitUntilNoFlowsToProcess when waiting longer than time limit."""


class InMemoryDBFlowMixin(object):
  """InMemoryDB mixin for flow handling."""

  flows: dict[tuple[ClientID, FlowID], flows_pb2.Flow]
  flow_results: dict[tuple[str, str], list[flows_pb2.FlowResult]]
  flow_errors: dict[tuple[str, str], list[flows_pb2.FlowError]]
  flow_log_entries: dict[tuple[str, str], list[flows_pb2.FlowLogEntry]]
  flow_output_plugin_log_entries: dict[
      tuple[str, str], list[flows_pb2.FlowOutputPluginLogEntry]
  ]
  flow_responses: dict[
      tuple[str, str], dict[int, dict[int, flows_pb2.FlowResponse]]
  ]
  flow_requests: dict[tuple[str, str], dict[int, flows_pb2.FlowRequest]]

  scheduled_flows: dict[
      tuple[ClientID, Username, FlowID], flows_pb2.ScheduledFlow
  ]

  handler_thread: threading.Thread
  flow_handler_thread: threading.Thread
  lock: threading.RLock
  flow_handler_num_being_processed: int
  message_handler_requests: dict[
      HandlerName, dict[RequestID, objects_pb2.MessageHandlerRequest]
  ]
  message_handler_leases: dict[
      HandlerName, dict[RequestID, int]  # lease expiration time in us
  ]
  flow_processing_requests: dict[
      tuple[str, str, str], flows_pb2.FlowProcessingRequest
  ]
  rrg_logs: dict[tuple[str, str], dict[tuple[str, int], rrg_pb2.Log]]

  # Maps client_id to client metadata.
  metadatas: dict[str, Any]
  users: dict[str, objects_pb2.GRRUser]

  @utils.Synchronized
  def WriteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Writes a list of message handler requests to the database."""
    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    for r in requests:
      flow_dict = self.message_handler_requests.setdefault(
          HandlerName(r.handler_name), {}
      )
      cloned_request = objects_pb2.MessageHandlerRequest()
      cloned_request.CopyFrom(r)
      cloned_request.timestamp = now
      flow_dict[cloned_request.request_id] = cloned_request

  @utils.Synchronized
  def ReadMessageHandlerRequests(
      self,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    """Reads all message handler requests from the database."""
    res = []
    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        res.append(r)
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, None)
        if existing_lease is not None:
          res[-1].leased_until = existing_lease
        else:
          res[-1].ClearField("leased_until")

    return sorted(res, key=lambda r: r.timestamp, reverse=True)

  @utils.Synchronized
  def DeleteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Deletes a list of message handler requests from the database."""

    for r in requests:
      flow_dict = self.message_handler_requests.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]
      flow_dict = self.message_handler_leases.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]

  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Leases a number of message handler requests up to the indicated limit."""
    self.UnregisterMessageHandler()

    self.handler_stop = False
    self.handler_thread = threading.Thread(
        name="message_handler",
        target=self._MessageHandlerLoop,
        args=(handler, lease_time, limit),
    )
    self.handler_thread.daemon = True
    self.handler_thread.start()

  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.is_alive():
        raise RuntimeError("Message handler thread did not join in time.")
      self.handler_thread = None

  def _MessageHandlerLoop(
      self,
      handler: Callable[[Iterable[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Loop to handle outstanding requests."""
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
  def _LeaseMessageHandlerRequests(
      self,
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> list[objects_pb2.MessageHandlerRequest]:
    """Read and lease some outstanding message handler requests."""
    leased_requests = []

    now = rdfvalue.RDFDatetime.Now()
    now_us = now.AsMicrosecondsSinceEpoch()
    expiration_time = now + lease_time
    expiration_time_us = expiration_time.AsMicrosecondsSinceEpoch()

    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, 0)
        if existing_lease < now_us:
          leases.setdefault(HandlerName(r.handler_name), {})[
              r.request_id
          ] = expiration_time_us
          r.leased_until = expiration_time_us
          r.leased_by = utils.ProcessIdString()
          leased_requests.append(r)
          if len(leased_requests) >= limit:
            break

    return leased_requests

  @utils.Synchronized
  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
  ) -> None:
    """Writes a flow object to the database."""
    if flow_obj.client_id not in self.metadatas:
      raise db.UnknownClientError(flow_obj.client_id)

    key = (ClientID(flow_obj.client_id), FlowID(flow_obj.flow_id))

    if not allow_update and key in self.flows:
      raise db.FlowExistsError(flow_obj.client_id, flow_obj.flow_id)

    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    clone = flows_pb2.Flow()
    clone.CopyFrom(flow_obj)
    clone.last_update_time = now
    clone.create_time = now

    self.flows[key] = clone

  @utils.Synchronized
  def ReadFlowObject(self, client_id: str, flow_id: str) -> flows_pb2.Flow:
    """Reads a flow object from the database."""
    try:
      return self.flows[(client_id, flow_id)]
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

  @utils.Synchronized
  def ReadAllFlowObjects(
      self,
      client_id: Optional[str] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
  ) -> list[flows_pb2.Flow]:
    """Returns all flow objects."""
    res = []
    for flow in self.flows.values():
      if client_id is not None and client_id != flow.client_id:
        continue
      if parent_flow_id is not None and parent_flow_id != flow.parent_flow_id:
        continue
      if (
          min_create_time is not None
          and flow.create_time < min_create_time.AsMicrosecondsSinceEpoch()
      ):
        continue
      if (
          max_create_time is not None
          and flow.create_time > max_create_time.AsMicrosecondsSinceEpoch()
      ):
        continue
      if not include_child_flows and flow.parent_flow_id:
        continue
      if not_created_by is not None and flow.creator in list(not_created_by):
        continue
      res.append(flow)
    return res

  @utils.Synchronized
  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
  ) -> flows_pb2.Flow:
    """Marks a flow as being processed on this worker and returns it."""
    flow = self.ReadFlowObject(client_id, flow_id)
    if flow.parent_hunt_id:
      # ReadHuntObject is implemented in the db.Database class.
      hunt_obj = self.ReadHuntObject(flow.parent_hunt_id)  # pytype: disable=attribute-error
      if not models_hunts.IsHuntSuitableForFlowProcessing(hunt_obj.hunt_state):
        raise db.ParentHuntIsNotRunningError(
            client_id, flow_id, hunt_obj.hunt_id, hunt_obj.hunt_state
        )

    now = rdfvalue.RDFDatetime.Now()
    if flow.processing_on and flow.processing_deadline > int(now):
      raise ValueError(
          "Flow %s on client %s is already being processed."
          % (flow_id, client_id)
      )
    processing_deadline = now + processing_time
    process_id_string = utils.ProcessIdString()

    # We avoid calling `UpdateFlow` here because it will update the
    # `last_update_time` field. Other DB implementations avoid this change,
    # so we want to preserve the same behavior here.
    flow_clone = flows_pb2.Flow()
    flow_clone.CopyFrom(flow)
    flow_clone.processing_on = process_id_string
    flow_clone.processing_since = int(now)
    flow_clone.processing_deadline = int(processing_deadline)
    self.flows[(ClientID(client_id), FlowID(flow_id))] = flow_clone

    flow.processing_on = process_id_string
    flow.processing_since = int(now)
    flow.processing_deadline = int(processing_deadline)
    return flow

  @utils.Synchronized
  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[
          flows_pb2.Flow, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      processing_on: Optional[
          Union[str, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
  ) -> None:
    """Updates flow objects in the database."""
    try:
      flow = self.flows[(client_id, flow_id)]
    except KeyError:
      raise db.UnknownFlowError(client_id, flow_id)

    if isinstance(flow_obj, flows_pb2.Flow):
      new_flow = flows_pb2.Flow()
      new_flow.CopyFrom(flow_obj)

      # Some fields cannot be updated.
      new_flow.client_id = flow.client_id
      new_flow.flow_id = flow.flow_id
      if flow.long_flow_id:
        new_flow.long_flow_id = flow.long_flow_id
      if flow.parent_flow_id:
        new_flow.parent_flow_id = flow.parent_flow_id
      if flow.parent_hunt_id:
        new_flow.parent_hunt_id = flow.parent_hunt_id
      if flow.flow_class_name:
        new_flow.flow_class_name = flow.flow_class_name
      if flow.creator:
        new_flow.creator = flow.creator

      flow = new_flow
    if isinstance(flow_state, flows_pb2.Flow.FlowState.ValueType):
      flow.flow_state = flow_state
    if isinstance(client_crash_info, jobs_pb2.ClientCrash):
      flow.client_crash_info.CopyFrom(client_crash_info)
    if (
        isinstance(processing_on, str)
        and processing_on is not db.Database.UNCHANGED
    ):
      flow.processing_on = processing_on
    elif processing_on is None:
      flow.ClearField("processing_on")
    if isinstance(processing_since, rdfvalue.RDFDatetime):
      flow.processing_since = int(processing_since)
    elif processing_since is None:
      flow.ClearField("processing_since")
    if isinstance(processing_deadline, rdfvalue.RDFDatetime):
      flow.processing_deadline = int(processing_deadline)
    elif processing_deadline is None:
      flow.ClearField("processing_deadline")
    flow.last_update_time = int(rdfvalue.RDFDatetime.Now())

    self.flows[(ClientID(client_id), FlowID(flow_id))] = flow

  @utils.Synchronized
  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
  ) -> None:
    """Writes a list of flow requests to the database."""
    flow_processing_requests = []

    for request in requests:
      if (request.client_id, request.flow_id) not in self.flows:
        raise db.AtLeastOneUnknownFlowError(
            [(request.client_id, request.flow_id)]
        )

    for request in requests:
      key = (ClientID(request.client_id), FlowID(request.flow_id))
      request_dict = self.flow_requests.setdefault(key, {})
      clone = flows_pb2.FlowRequest()
      clone.CopyFrom(request)
      request_dict[request.request_id] = clone
      request_dict[request.request_id].timestamp = int(
          rdfvalue.RDFDatetime.Now()
      )

      if request.needs_processing:
        flow = self.flows[(request.client_id, request.flow_id)]
        if (
            flow.next_request_to_process == request.request_id
            or request.start_time
        ):
          processing_request = flows_pb2.FlowProcessingRequest(
              client_id=request.client_id, flow_id=request.flow_id
          )
          if request.start_time:
            processing_request.delivery_time = request.start_time
          flow_processing_requests.append(processing_request)

    if flow_processing_requests:
      self.WriteFlowProcessingRequests(flow_processing_requests)

  @utils.Synchronized
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
  ) -> None:
    """Updates incremental flow requests."""
    if (client_id, flow_id) not in self.flows:
      raise db.UnknownFlowError(client_id, flow_id)

    request_dict = self.flow_requests[(client_id, flow_id)]
    for request_id, next_response_id in next_response_id_updates.items():
      request_dict[request_id].next_response_id = next_response_id
      request_dict[request_id].timestamp = int(rdfvalue.RDFDatetime.Now())

  @utils.Synchronized
  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
  ) -> None:
    """Deletes a list of flow requests from the database."""
    for request in requests:
      if (request.client_id, request.flow_id) not in self.flows:
        raise db.UnknownFlowError(request.client_id, request.flow_id)

    for request in requests:
      key = (request.client_id, request.flow_id)
      request_dict = self.flow_requests.get(key, {})
      try:
        del request_dict[request.request_id]
      except KeyError as e:
        raise db.UnknownFlowRequestError(
            request.client_id, request.flow_id, request.request_id
        ) from e

      response_dict = self.flow_responses.get(key, {})
      try:
        del response_dict[request.request_id]
      except KeyError:
        pass

  @utils.Synchronized
  def WriteFlowResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> None:
    """Writes Flow responses and updates corresponding requests."""
    status_available = {}
    requests_updated = set()

    for response in responses:
      flow_key = (response.client_id, response.flow_id)
      if flow_key not in self.flows:
        logging.error(
            "Received response for unknown flow %s, %s.",
            response.client_id,
            response.flow_id,
        )
        continue

      request_dict = self.flow_requests.get(flow_key, {})
      if response.request_id not in request_dict:
        logging.error(
            "Received response for unknown request %s, %s, %d.",
            response.client_id,
            response.flow_id,
            response.request_id,
        )
        continue

      req_response_dict = self.flow_responses.setdefault(flow_key, {})
      clone = flows_pb2.FlowResponse()
      if isinstance(response, flows_pb2.FlowIterator):
        clone = flows_pb2.FlowIterator()
      elif isinstance(response, flows_pb2.FlowStatus):
        clone = flows_pb2.FlowStatus()

      clone.CopyFrom(response)
      clone.timestamp = int(rdfvalue.RDFDatetime.Now())

      response_dict = req_response_dict.setdefault(response.request_id, {})
      response_dict[response.response_id] = clone

      if isinstance(response, flows_pb2.FlowStatus):
        status_available[(
            response.client_id,
            response.flow_id,
            response.request_id,
            response.response_id,
        )] = response

      request_key = (response.client_id, response.flow_id, response.request_id)
      requests_updated.add(request_key)

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
        req_response_dict = self.flow_responses.setdefault(flow_key, {})
        response_dict = req_response_dict.get(request_id, {})

        if len(response_dict) == request.nr_responses_expected:
          request.needs_processing = True

          if flow.next_request_to_process == request_id:
            added_for_processing = True
            flow_processing_request = flows_pb2.FlowProcessingRequest(
                client_id=client_id,
                flow_id=flow_id,
            )
            if request.start_time:
              flow_processing_request.delivery_time = request.start_time
            needs_processing.append(flow_processing_request)

      if (
          request.callback_state
          and flow.next_request_to_process == request_id
          and not added_for_processing
      ):

        needs_processing.append(
            flows_pb2.FlowProcessingRequest(
                client_id=client_id, flow_id=flow_id
            )
        )
    if needs_processing:
      self.WriteFlowProcessingRequests(needs_processing)

  @utils.Synchronized
  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> Iterable[
      tuple[
          flows_pb2.FlowRequest,
          dict[
              int,
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ]
  ]:
    """Reads all requests and responses for a given flow from the database."""
    flow_key = (client_id, flow_id)
    try:
      self.flows[flow_key]
    except KeyError:
      return []

    request_dict: dict[int, flows_pb2.FlowRequest] = self.flow_requests.get(
        flow_key, {}
    )
    req_response_dict: dict[int, dict[int, flows_pb2.FlowResponse]] = (
        self.flow_responses.get(flow_key, {})
    )

    res = []
    for request_id in sorted(request_dict):
      res.append(
          (request_dict[request_id], req_response_dict.get(request_id, {}))
      )

    return res

  @utils.Synchronized
  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> None:
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
  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
  ) -> dict[
      int,
      tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    """Reads all requests for a flow that can be processed by the worker."""
    request_dict: dict[int, flows_pb2.FlowRequest] = self.flow_requests.get(
        (client_id, flow_id), {}
    )
    req_response_dict: dict[int, dict[int, flows_pb2.FlowResponse]] = (
        self.flow_responses.get((client_id, flow_id), {})
    )

    # Do a pass for completed requests.
    res = {}
    for request_id in sorted(request_dict):
      request = request_dict[request_id]
      responses = sorted(
          req_response_dict.get(request_id, {}).values(),
          key=lambda response: response.response_id,
      )

      # Serialize/deserialize responses to better simulate the
      # real DB behavior (where serialization/deserialization is almost
      # guaranteed to be done).
      # TODO(user): change mem-db implementation to do
      # serialization/deserialization everywhere in a generic way.
      reserialized_responses = []
      for r in responses:
        response = r.__class__()
        response.ParseFromString(r.SerializeToString())
        reserialized_responses.append(response)
      responses = reserialized_responses

      res[request_id] = (request, responses)

    return res

  @utils.Synchronized
  def ReleaseProcessedFlow(self, flow_obj: flows_pb2.Flow) -> bool:
    """Releases a flow that the worker was processing to the database."""
    key = (flow_obj.client_id, flow_obj.flow_id)
    next_id_to_process = flow_obj.next_request_to_process
    request_dict = self.flow_requests.get(key, {})
    if (
        next_id_to_process in request_dict
        and request_dict[next_id_to_process].needs_processing
    ):
      start_time = request_dict[next_id_to_process].start_time
      if not start_time or start_time < int(rdfvalue.RDFDatetime.Now()):
        return False

    self.UpdateFlow(
        flow_obj.client_id,
        flow_obj.flow_id,
        flow_obj=flow_obj,
        processing_on=None,
        processing_since=None,
        processing_deadline=None,
    )
    return True

  def _InlineProcessingOK(
      self, requests: Sequence[flows_pb2.FlowProcessingRequest]
  ) -> bool:
    """Returns whether inline processing is OK for a list of requests."""
    for r in requests:
      if r.delivery_time:
        return False

      # If the corresponding flow is already being processed, inline processing
      # won't work.
      flow = self.flows[r.client_id, r.flow_id]
      if flow.HasField("processing_since"):
        return False
    return True

  @utils.Synchronized
  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Writes a list of flow processing requests to the database."""
    # If we don't have a handler thread running, we might be able to process the
    # requests inline. If we are not, we start the handler thread for real and
    # queue the requests normally.
    if not self.flow_handler_thread and self.flow_handler_target:
      if self._InlineProcessingOK(requests):
        for r in requests:
          r.creation_time = int(rdfvalue.RDFDatetime.Now())
          self.flow_handler_target(r)
        return
      else:
        self._RegisterFlowProcessingHandler(self.flow_handler_target)
        self.flow_handler_target = None

    for r in requests:
      cloned_request = flows_pb2.FlowProcessingRequest()
      cloned_request.CopyFrom(r)
      key = (r.client_id, r.flow_id)
      cloned_request.creation_time = int(rdfvalue.RDFDatetime.Now())
      self.flow_processing_requests[key] = cloned_request

  @utils.Synchronized
  def ReadFlowProcessingRequests(
      self,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    """Reads all flow processing requests from the database."""
    return list(self.flow_processing_requests.values())

  @utils.Synchronized
  def AckFlowProcessingRequests(
      self, requests: Iterable[flows_pb2.FlowProcessingRequest]
  ) -> None:
    """Deletes a list of flow processing requests from the database."""
    for r in requests:
      key = (r.client_id, r.flow_id)
      if key in self.flow_processing_requests:
        del self.flow_processing_requests[key]

  @utils.Synchronized
  def DeleteAllFlowProcessingRequests(self) -> None:
    self.flow_processing_requests = {}

  def RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    """Registers a message handler to receive flow processing messages."""
    self.UnregisterFlowProcessingHandler()

    # For the in memory db, we just call the handler straight away if there is
    # no delay in starting times so we don't run the thread here.
    self.flow_handler_target = handler

    for request in self._GetFlowRequestsReadyForProcessing():
      handler(request)
      with self.lock:
        self.flow_processing_requests.pop(
            (request.client_id, request.flow_id), None
        )

  def _RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    """Registers a handler to receive flow processing messages."""
    self.flow_handler_stop = False
    self.flow_handler_thread = threading.Thread(
        name="flow_processing_handler",
        target=self._HandleFlowProcessingRequestLoop,
        args=(handler,),
    )
    self.flow_handler_thread.daemon = True
    self.flow_handler_thread.start()

  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered flow processing handler."""
    self.flow_handler_target = None

    if self.flow_handler_thread:
      self.flow_handler_stop = True
      if timeout:
        self.flow_handler_thread.join(timeout.ToInt(timeunit=rdfvalue.SECONDS))
      else:
        self.flow_handler_thread.join()
      if self.flow_handler_thread.is_alive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_handler_thread = None

  @utils.Synchronized
  def _GetFlowRequestsReadyForProcessing(
      self,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    now = rdfvalue.RDFDatetime.Now()
    todo = []
    for r in list(self.flow_processing_requests.values()):
      if not r.delivery_time or r.delivery_time <= now:
        todo.append(r)

    return todo

  def WaitUntilNoFlowsToProcess(
      self,
      timeout: Optional[rdfvalue.Duration] = None,
  ):
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
        if not t.is_alive() or (
            not self._GetFlowRequestsReadyForProcessing()
            and not self.flow_handler_num_being_processed
        ):
          return

      time.sleep(0.2)

      if timeout and time.time() - start_time > timeout.ToInt(
          timeunit=rdfvalue.SECONDS
      ):
        raise TimeOutWhileWaitingForFlowsToBeProcessedError(
            "Flow processing didn't finish in time."
        )

  def _HandleFlowProcessingRequestLoop(self, handler):
    """Handler thread for the FlowProcessingRequest queue."""
    while not self.flow_handler_stop:
      with self.lock:
        todo = self._GetFlowRequestsReadyForProcessing()
        for request in todo:
          self.flow_handler_num_being_processed += 1
          del self.flow_processing_requests[
              (request.client_id, request.flow_id)
          ]

      for request in todo:
        handler(request)
        with self.lock:
          self.flow_handler_num_being_processed -= 1

      time.sleep(0.2)

  @utils.Synchronized
  def _WriteFlowResultsOrErrors(
      self, container: dict[tuple[str, str], T], items: Sequence[T]
  ) -> None:
    for i in items:
      dest = container.setdefault((i.client_id, i.flow_id), [])
      to_write = i.__class__()
      to_write.CopyFrom(i)
      to_write.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
      dest.append(to_write)

  def WriteFlowResults(self, results: Sequence[flows_pb2.FlowResult]) -> None:
    """Writes flow results for a given flow."""
    self._WriteFlowResultsOrErrors(self.flow_results, results)

  @utils.Synchronized
  def _ReadFlowResultsOrErrors(
      self,
      container: dict[tuple[str, str], T],
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
  ) -> Sequence[T]:
    """Reads flow results/errors of a given flow using given query options."""
    container_copy = []
    for x in container.get((client_id, flow_id), []):
      x_copy = x.__class__()
      x_copy.CopyFrom(x)
      container_copy.append(x)
    results = sorted(container_copy, key=lambda r: r.timestamp)

    if with_tag is not None:
      results = [i for i in results if i.tag == with_tag]

    if with_proto_type_url is not None:
      results = [
          i for i in results if i.payload.type_url == with_proto_type_url
      ]
    elif with_type is not None:
      results = [
          i
          for i in results
          if db_utils.TypeURLToRDFTypeName(i.payload.type_url) == with_type
      ]

    if with_substring is not None:
      encoded_substring = with_substring.encode("utf8")
      results = [
          i
          for i in results
          if encoded_substring in i.payload.SerializeToString()
      ]

    return results[offset : offset + count]

  def ReadFlowResults(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads flow results of a given flow using given query options."""
    return self._ReadFlowResultsOrErrors(
        self.flow_results,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_proto_type_url=with_proto_type_url,
        with_substring=with_substring,
    )

  @utils.Synchronized
  def CountFlowResults(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow results of a given flow using given query options."""
    return len(
        self.ReadFlowResults(
            client_id,
            flow_id,
            0,
            sys.maxsize,
            with_tag=with_tag,
            with_type=with_type,
        )
    )

  @utils.Synchronized
  def CountFlowResultsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by result type."""
    result = collections.Counter()
    for hr in self.ReadFlowResults(client_id, flow_id, 0, sys.maxsize):
      key = db_utils.TypeURLToRDFTypeName(hr.payload.type_url)
      result[key] += 1

    return result

  @utils.Synchronized
  def CountFlowResultsByProtoTypeUrl(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by proto result type."""
    result = collections.Counter()
    for hr in self.ReadFlowResults(client_id, flow_id, 0, sys.maxsize):
      key = hr.payload.type_url
      result[key] += 1

    return result

  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    """Writes flow errors for a given flow."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    self._WriteFlowResultsOrErrors(self.flow_errors, errors)

  def ReadFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowError]:
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
        with_type=with_type,
    )

  @utils.Synchronized
  def CountFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow errors of a given flow using given query options."""
    return len(
        self.ReadFlowErrors(
            client_id,
            flow_id,
            0,
            sys.maxsize,
            with_tag=with_tag,
            with_type=with_type,
        )
    )

  @utils.Synchronized
  def CountFlowErrorsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow errors grouped by error type."""
    result = collections.Counter()
    for hr in self.ReadFlowErrors(client_id, flow_id, 0, sys.maxsize):
      key = db_utils.TypeURLToRDFTypeName(hr.payload.type_url)
      result[key] += 1

    return result

  @utils.Synchronized
  def WriteFlowLogEntry(self, entry: flows_pb2.FlowLogEntry) -> None:
    """Writes a single flow log entry to the database."""
    key = (entry.client_id, entry.flow_id)

    if key not in self.flows:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id)

    log_entry = flows_pb2.FlowLogEntry()
    log_entry.CopyFrom(entry)
    log_entry.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    self.flow_log_entries.setdefault(key, []).append(log_entry)

  @utils.Synchronized
  def ReadFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads flow log entries of a given flow using given query options."""
    entries = sorted(
        self.flow_log_entries.get((client_id, flow_id), []),
        key=lambda e: e.timestamp,
    )

    if with_substring is not None:
      entries = [i for i in entries if with_substring in i.message]

    return entries[offset : offset + count]

  @utils.Synchronized
  def CountFlowLogEntries(self, client_id: str, flow_id: str) -> int:
    """Returns number of flow log entries of a given flow."""
    return len(self.ReadFlowLogEntries(client_id, flow_id, 0, sys.maxsize))

  @utils.Synchronized
  def WriteFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      request_id: int,
      logs: Mapping[int, rrg_pb2.Log],
  ) -> None:
    """Writes new log entries for a particular action request."""
    if (client_id, flow_id) not in self.flows:
      raise db.UnknownFlowError(client_id, flow_id)

    for response_id, log in logs.items():
      log_copy = rrg_pb2.Log()
      log_copy.CopyFrom(log)

      flow_logs = self.rrg_logs.setdefault((client_id, flow_id), {})
      flow_logs[(request_id, response_id)] = log_copy

  @utils.Synchronized
  def ReadFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
  ) -> Sequence[rrg_pb2.Log]:
    """Reads log entries logged by actions issued by a particular flow."""
    results = []

    flow_logs = self.rrg_logs.get((client_id, flow_id), {})

    for request_id, response_id in sorted(flow_logs):
      log_copy = rrg_pb2.Log()
      log_copy.CopyFrom(flow_logs[(request_id, response_id)])

      results.append(log_copy)

    return results[offset : offset + count]

  @utils.Synchronized
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: flows_pb2.FlowOutputPluginLogEntry,
  ) -> None:
    """Writes a single output plugin log entry to the database."""
    self.WriteMultipleFlowOutputPluginLogEntries([entry])

  @utils.Synchronized
  def WriteMultipleFlowOutputPluginLogEntries(
      self,
      entries: Sequence[flows_pb2.FlowOutputPluginLogEntry],
  ) -> None:
    """Writes multiple output plugin log entries to the database."""
    if not entries:
      return

    for entry in entries:
      now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
      key = (entry.client_id, entry.flow_id)

      if key not in self.flows:
        raise db.AtLeastOneUnknownFlowError([(entry.client_id, entry.flow_id)])

      log_entry = flows_pb2.FlowOutputPluginLogEntry()
      log_entry.CopyFrom(entry)
      log_entry.timestamp = now

      self.flow_output_plugin_log_entries.setdefault(key, []).append(log_entry)

  @utils.Synchronized
  def ReadFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries."""
    entries = sorted(
        self.flow_output_plugin_log_entries.get((client_id, flow_id), []),
        key=lambda e: e.timestamp,
    )

    entries = [e for e in entries if e.output_plugin_id == output_plugin_id]

    if with_type is not None:
      entries = [e for e in entries if e.log_entry_type == with_type]

    return entries[offset : offset + count]

  @utils.Synchronized
  def ReadAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries for all plugins of a given flow."""
    entries = sorted(
        self.flow_output_plugin_log_entries.get((client_id, flow_id), []),
        key=lambda e: e.timestamp,
    )

    if with_type is not None:
      entries = [e for e in entries if e.log_entry_type == with_type]

    return entries[offset : offset + count]

  @utils.Synchronized
  def CountFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ):
    """Returns number of flow output plugin log entries of a given flow."""

    return len(
        self.ReadFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            0,
            sys.maxsize,
            with_type=with_type,
        )
    )

  @utils.Synchronized
  def CountAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
  ):
    """Returns number of flow output plugin log entries of a given flow."""

    entries = self.flow_output_plugin_log_entries.get((client_id, flow_id), [])

    if with_type is not None:
      entries = [e for e in entries if e.log_entry_type == with_type]

    return len(entries)

  @utils.Synchronized
  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
  ) -> None:
    """See base class."""
    if scheduled_flow.client_id not in self.metadatas:
      raise db.UnknownClientError(scheduled_flow.client_id)

    if scheduled_flow.creator not in self.users:
      raise db.UnknownGRRUserError(scheduled_flow.creator)

    full_id = (
        ClientID(scheduled_flow.client_id),
        Username(scheduled_flow.creator),
        FlowID(scheduled_flow.scheduled_flow_id),
    )
    self.scheduled_flows[full_id] = flows_pb2.ScheduledFlow()
    self.scheduled_flows[full_id].CopyFrom(scheduled_flow)

  @utils.Synchronized
  def DeleteScheduledFlow(
      self,
      client_id: str,
      creator: str,
      scheduled_flow_id: str,
  ) -> None:
    """See base class."""
    key = (
        ClientID(client_id),
        Username(creator),
        FlowID(scheduled_flow_id),
    )
    try:
      self.scheduled_flows.pop(key)
    except KeyError:
      raise db.UnknownScheduledFlowError(
          client_id=client_id,
          creator=creator,
          scheduled_flow_id=scheduled_flow_id,
      )

  @utils.Synchronized
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    """See base class."""
    results = []

    for flow in self.scheduled_flows.values():
      if flow.client_id == client_id and flow.creator == creator:
        flow_copy = flows_pb2.ScheduledFlow()
        flow_copy.CopyFrom(flow)

        results.append(flow_copy)

    return results
