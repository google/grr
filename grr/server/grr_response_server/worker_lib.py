#!/usr/bin/env python
"""Module with GRRWorker implementation."""

import logging
import time
from typing import Sequence

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import collection
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import handler_registry
# pylint: disable=unused-import
from grr_response_server import server_stubs
# pylint: enable=unused-import
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_objects


WELL_KNOWN_FLOW_REQUESTS = metrics.Counter(
    "well_known_flow_requests", fields=[("flow", str)]
)


class Error(Exception):
  """Base error class."""


class FlowHasNothingToProcessError(Error):
  """Raised when a flow is expected to have work to do, but doesn't."""


def ProcessMessageHandlerRequests(
    requests: Sequence[objects_pb2.MessageHandlerRequest],
) -> None:
  """Processes message handler requests."""
  logging.info(
      "Leased message handler request ids: %s",
      ",".join(str(r.request_id) for r in requests),
  )
  grouped_requests = collection.Group(requests, lambda r: r.handler_name)
  for handler_name, requests_for_handler in grouped_requests.items():
    requests_for_handler = [
        mig_objects.ToRDFMessageHandlerRequest(r) for r in requests_for_handler
    ]
    handler_cls = handler_registry.handler_name_map.get(handler_name)
    if not handler_cls:
      logging.error("Unknown message handler: %s", handler_name)
      continue

    num_requests = len(requests_for_handler)
    WELL_KNOWN_FLOW_REQUESTS.Increment(
        fields=[handler_name], delta=num_requests
    )

    try:
      logging.debug(
          "Running %d messages for handler %s", num_requests, handler_name
      )
      handler_cls().ProcessMessages(requests_for_handler)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(
          "Exception while processing message handler %s: %s", handler_name, e
      )

  logging.info(
      "Deleting message handler request ids: %s",
      ",".join(str(r.request_id) for r in requests),
  )
  data_store.REL_DB.DeleteMessageHandlerRequests(requests)


class GRRWorker(object):
  """A GRR worker."""

  message_handler_lease_time = rdfvalue.Duration.From(600, rdfvalue.SECONDS)

  def __init__(self):
    """Constructor."""
    logging.info("Started GRR worker.")

  def Shutdown(self) -> None:
    data_store.REL_DB.UnregisterMessageHandler()
    data_store.REL_DB.UnregisterFlowProcessingHandler()

  def Run(self) -> None:
    """Event loop."""
    data_store.REL_DB.RegisterMessageHandler(
        ProcessMessageHandlerRequests,
        self.message_handler_lease_time,
        limit=100,
    )
    data_store.REL_DB.RegisterFlowProcessingHandler(self.ProcessFlow)

    try:
      # The main thread just keeps sleeping and listens to keyboard interrupt
      # events in case the server is running from a console.
      while True:
        time.sleep(3600)
    except KeyboardInterrupt:
      logging.info("Caught interrupt, exiting.")
      self.Shutdown()

  def _ReleaseProcessedFlow(self, flow_obj: rdf_flow_objects.Flow) -> bool:
    """Release a processed flow if the processing deadline is not exceeded."""
    rdf_flow = flow_obj.rdf_flow
    if rdf_flow.processing_deadline < rdfvalue.RDFDatetime.Now():
      raise flow_base.FlowError(
          "Lease expired for flow %s on %s (%s)."
          % (
              rdf_flow.flow_id,
              rdf_flow.client_id,
              rdf_flow.processing_deadline,
          ),
      )
    flow_obj.FlushQueuedMessages()

    proto_flow = mig_flow_objects.ToProtoFlow(rdf_flow)
    return data_store.REL_DB.ReleaseProcessedFlow(proto_flow)

  def ProcessFlow(
      self, flow_processing_request: flows_pb2.FlowProcessingRequest
  ) -> None:
    """The callback for the flow processing queue."""
    client_id = flow_processing_request.client_id
    flow_id = flow_processing_request.flow_id

    data_store.REL_DB.AckFlowProcessingRequests([flow_processing_request])

    try:
      flow = data_store.REL_DB.LeaseFlowForProcessing(
          client_id,
          flow_id,
          processing_time=rdfvalue.Duration.From(6, rdfvalue.HOURS),
      )
    except db.ParentHuntIsNotRunningError:
      flow_base.TerminateFlow(client_id, flow_id, "Parent hunt stopped.")
      return

    rdf_flow = mig_flow_objects.ToRDFFlow(flow)

    first_request_to_process = rdf_flow.next_request_to_process
    logging.info(
        "Processing Flow %s/%s/%d (%s).",
        client_id,
        flow_id,
        first_request_to_process,
        rdf_flow.flow_class_name,
    )

    flow_cls = registry.FlowRegistry.FlowClassByName(rdf_flow.flow_class_name)
    flow_obj = flow_cls(rdf_flow)

    if not flow_obj.IsRunning():
      logging.info(
          "Received a request to process flow %s on client %s that is not "
          "running.",
          flow_id,
          client_id,
      )
      return

    processed, incrementally_processed = flow_obj.ProcessAllReadyRequests()
    if processed == 0 and incrementally_processed == 0:
      raise FlowHasNothingToProcessError(
          "Unable to process any requests for flow %s on client %s."
          % (flow_id, client_id)
      )

    while not self._ReleaseProcessedFlow(flow_obj):
      processed, incrementally_processed = flow_obj.ProcessAllReadyRequests()
      if processed == 0 and incrementally_processed == 0:
        raise FlowHasNothingToProcessError(
            "%s/%s: ReleaseProcessedFlow returned false but no "
            "request could be processed (next req: %d)."
            % (client_id, flow_id, flow_obj.rdf_flow.next_request_to_process)
        )

    if flow_obj.IsRunning():
      logging.info(
          "Processing Flow %s/%s/%d (%s) done, next request to process: %d.",
          client_id,
          flow_id,
          first_request_to_process,
          rdf_flow.flow_class_name,
          rdf_flow.next_request_to_process,
      )
    else:
      logging.info(
          "Processing Flow %s/%s/%d (%s) done, flow is done.",
          client_id,
          flow_id,
          first_request_to_process,
          rdf_flow.flow_class_name,
      )
