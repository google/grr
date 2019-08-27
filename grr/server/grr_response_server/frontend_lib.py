#!/usr/bin/env python
"""The GRR frontend server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import operator
import time

from future import builtins as future_builtins
from future.utils import iteritems

from grr_response_core.lib import communicator
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import random
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import message_handlers
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


CLIENT_PINGS_BY_LABEL = metrics.Counter(
    "client_pings_by_label", fields=[("label", future_builtins.str)])
FRONTEND_ACTIVE_COUNT = metrics.Gauge(
    "frontend_active_count", int, fields=[("source", future_builtins.str)])
FRONTEND_MAX_ACTIVE_COUNT = metrics.Gauge("frontend_max_active_count", int)
FRONTEND_HTTP_REQUESTS = metrics.Counter(
    "frontend_http_requests",
    fields=[("action", future_builtins.str), ("protocol", future_builtins.str)])
FRONTEND_IN_BYTES = metrics.Counter(
    "frontend_in_bytes", fields=[("source", future_builtins.str)])
FRONTEND_OUT_BYTES = metrics.Counter(
    "frontend_out_bytes", fields=[("source", future_builtins.str)])
FRONTEND_REQUEST_COUNT = metrics.Counter(
    "frontend_request_count", fields=[("source", future_builtins.str)])
FRONTEND_INACTIVE_REQUEST_COUNT = metrics.Counter(
    "frontend_inactive_request_count", fields=[("source", future_builtins.str)])
FRONTEND_REQUEST_LATENCY = metrics.Event(
    "frontend_request_latency", fields=[("source", future_builtins.str)])
GRR_FRONTENDSERVER_HANDLE_TIME = metrics.Event("grr_frontendserver_handle_time")
GRR_FRONTENDSERVER_HANDLE_NUM = metrics.Counter("grr_frontendserver_handle_num")
GRR_MESSAGES_SENT = metrics.Counter("grr_messages_sent")
GRR_PUB_KEY_CACHE = metrics.Counter(
    "grr_pub_key_cache", fields=[("type", future_builtins.str)])
GRR_UNIQUE_CLIENTS = metrics.Counter("grr_unique_clients")


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using the relational db."""

  def __init__(self, certificate, private_key):
    super(ServerCommunicator, self).__init__(
        certificate=certificate, private_key=private_key)
    self.pub_key_cache = utils.FastStore(max_size=50000)
    self.common_name = self.certificate.GetCN()

  def _GetRemotePublicKey(self, common_name):
    remote_client_id = common_name.Basename()
    try:
      # See if we have this client already cached.
      remote_key = self.pub_key_cache.Get(remote_client_id)
      GRR_PUB_KEY_CACHE.Increment(fields=["hits"])
      return remote_key
    except KeyError:
      GRR_PUB_KEY_CACHE.Increment(fields=["misses"])

    try:
      md = data_store.REL_DB.ReadClientMetadata(remote_client_id)
    except db.UnknownClientError:
      GRR_UNIQUE_CLIENTS.Increment()
      raise communicator.UnknownClientCertError("Cert not found")

    cert = md.certificate
    if cert is None:
      raise communicator.UnknownClientCertError("Cert not found")

    if rdfvalue.RDFURN(cert.GetCN()) != rdfvalue.RDFURN(common_name):
      logging.error("Stored cert mismatch for %s", common_name)
      raise communicator.UnknownClientCertError("Stored cert mismatch")

    pub_key = cert.GetPublicKey()
    self.pub_key_cache.Put(common_name, pub_key)
    return pub_key

  def VerifyMessageSignature(self, response_comms, packed_message_list, cipher,
                             cipher_verified, api_version, remote_public_key):
    """Verifies the message list signature.

    In the server we check that the timestamp is later than the ping timestamp
    stored with the client. This ensures that client responses can not be
    replayed.

    Args:
      response_comms: The raw response_comms rdfvalue.
      packed_message_list: The PackedMessageList rdfvalue from the server.
      cipher: The cipher object that should be used to verify the message.
      cipher_verified: If True, the cipher's signature is not verified again.
      api_version: The api version we should use.
      remote_public_key: The public key of the source.

    Returns:
      An rdf_flows.GrrMessage.AuthorizationState.
    """
    if (not cipher_verified and
        not cipher.VerifyCipherSignature(remote_public_key)):
      communicator.GRR_UNAUTHENTICATED_MESSAGES.Increment()
      return rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    try:
      client_id = cipher.cipher_metadata.source.Basename()
      metadata = data_store.REL_DB.ReadClientMetadata(client_id)
      client_time = packed_message_list.timestamp or rdfvalue.RDFDatetime(0)
      update_metadata = True

      # This used to be a strict check here so absolutely no out of
      # order messages would be accepted ever. Turns out that some
      # proxies can send your request with some delay even if the
      # client has already timed out (and sent another request in
      # the meantime, making the first one out of order). In that
      # case we would just kill the whole flow as a
      # precaution. Given the behavior of those proxies, this seems
      # now excessive and we have changed the replay protection to
      # only trigger on messages that are more than one hour old.
      if metadata and metadata.clock:
        stored_client_time = metadata.clock

        if client_time < stored_client_time - rdfvalue.Duration.From(
            1, rdfvalue.HOURS):
          logging.warning("Message desynchronized for %s: %s >= %s", client_id,
                          stored_client_time, client_time)
          # This is likely an old message
          return rdf_flows.GrrMessage.AuthorizationState.DESYNCHRONIZED

        # Update the client and server timestamps only if the client time moves
        # forward.
        if client_time < stored_client_time:
          logging.warning("Out of order message for %s: %s > %s", client_id,
                          stored_client_time, client_time)
          update_metadata = False

      communicator.GRR_AUTHENTICATED_MESSAGES.Increment()

      for label in data_store.REL_DB.ReadClientLabels(client_id):
        CLIENT_PINGS_BY_LABEL.Increment(fields=[label.name])

      if not update_metadata:
        return rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

      source_ip = response_comms.orig_request.source_ip
      if source_ip:
        last_ip = rdf_client_network.NetworkAddress(
            human_readable_address=response_comms.orig_request.source_ip)
      else:
        last_ip = None

      data_store.REL_DB.WriteClientMetadata(
          client_id,
          last_ip=last_ip,
          last_clock=client_time,
          last_ping=rdfvalue.RDFDatetime.Now(),
          fleetspeak_enabled=False)

    except communicator.UnknownClientCertError:
      pass

    return rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED


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

  def __init__(self,
               certificate,
               private_key,
               max_queue_size=50,
               message_expiry_time=120,
               max_retransmission_time=10):
    # Identify ourselves as the server.
    self.token = access_control.ACLToken(
        username="GRRFrontEnd", reason="Implied.")
    self.token.supervisor = True

    self._communicator = ServerCommunicator(
        certificate=certificate, private_key=private_key)

    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size

    # There is only a single session id that we accept unauthenticated
    # messages for, the one to enroll new clients.
    self.unauth_allowed_session_id = rdfvalue.SessionID(
        queue=queues.ENROLLMENT, flow_name="Enrol")

  @GRR_FRONTENDSERVER_HANDLE_NUM.Counted()
  @GRR_FRONTENDSERVER_HANDLE_TIME.Timed()
  def HandleMessageBundles(self, request_comms, response_comms):
    """Processes a queue of messages as passed from the client.

    We basically dispatch all the GrrMessages in the queue to the task scheduler
    for backend processing. We then retrieve from the TS the messages destined
    for this client.

    Args:
       request_comms: A ClientCommunication rdfvalue with messages sent by the
         client. source should be set to the client CN.
       response_comms: A ClientCommunication rdfvalue of jobs destined to this
         client.

    Returns:
       tuple of (source, message_count) where message_count is the number of
       messages received from the client with common name source.
    """
    messages, source, timestamp = self._communicator.DecodeMessages(
        request_comms)

    now = time.time()
    if messages:
      # Receive messages in line.
      self.ReceiveMessages(source, messages)

    # We send the client a maximum of self.max_queue_size messages
    required_count = max(0, self.max_queue_size - request_comms.queue_size)

    message_list = rdf_flows.MessageList()
    # Only give the client messages if we are able to receive them in a
    # reasonable time.
    if time.time() - now < 10:
      client_id = source.Basename()
      message_list.job = self.DrainTaskSchedulerQueueForClient(
          client_id, required_count)

    # Encode the message_list in the response_comms using the same API version
    # the client used.
    self._communicator.EncodeMessages(
        message_list,
        response_comms,
        destination=source,
        timestamp=timestamp,
        api_version=request_comms.api_version)

    return source, len(messages)

  def DrainTaskSchedulerQueueForClient(self, client, max_count=None):
    """Drains the client's Task Scheduler queue.

    Args:
       client: The client id specifying this client.
       max_count: The maximum number of messages we will issue for the client.
         If not given, uses self.max_queue_size .

    Returns:
       The tasks respresenting the messages returned. If we can not send them,
       we can reschedule them for later.
    """
    if max_count is None:
      max_count = self.max_queue_size

    if max_count <= 0:
      return []

    start_time = time.time()
    # Drain the queue for this client
    action_requests = data_store.REL_DB.LeaseClientActionRequests(
        client,
        lease_time=rdfvalue.Duration.From(self.message_expiry_time,
                                          rdfvalue.SECONDS),
        limit=max_count)
    result = [
        rdf_flow_objects.GRRMessageFromClientActionRequest(r)
        for r in action_requests
    ]

    GRR_MESSAGES_SENT.Increment(len(result))
    if result:
      logging.debug("Drained %d messages for %s in %s seconds.", len(result),
                    client,
                    time.time() - start_time)

    return result

  def EnrolFleetspeakClient(self, client_id):
    """Enrols a Fleetspeak-enabled client for use with GRR.

    Args:
      client_id: GRR client-id for the client.

    Returns:
      True if the client is new, and actually got enrolled. This method
      is a no-op if the client already exists (in which case False is returned).
    """
    client_urn = rdf_client.ClientURN(client_id)
    # If already enrolled, return.
    try:
      data_store.REL_DB.ReadClientMetadata(client_id)
      return False
    except db.UnknownClientError:
      pass

    logging.info("Enrolling a new Fleetspeak client: %r", client_id)

    now = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteClientMetadata(
        client_id, first_seen=now, fleetspeak_enabled=True, last_ping=now)

    # Publish the client enrollment message.
    events.Events.PublishEvent("ClientEnrollment", client_urn, token=self.token)
    return True

  legacy_well_known_session_ids = set([
      str(rdfvalue.SessionID(flow_name="Foreman", queue=rdfvalue.RDFURN("W"))),
      str(rdfvalue.SessionID(flow_name="Stats", queue=rdfvalue.RDFURN("W")))
  ])

  # Message handler requests addressed to these handlers will be processed
  # directly on the frontend and not written to the worker queue.
  # Currently we only do this for BlobHandler, since it's important
  # to write blobs to the datastore as fast as possible. GetFile/MultiGetFile
  # logic depends on blobs being in the blob store to do file hashing.
  _SHORTCUT_HANDLERS = frozenset([transfer.BlobHandler.handler_name])

  def ReceiveMessages(self, client_id, messages):
    """Receives and processes the messages.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      client_id: The client which sent the messages.
      messages: A list of GrrMessage RDFValues.
    """
    now = time.time()
    unprocessed_msgs = []
    worker_message_handler_requests = []
    frontend_message_handler_requests = []
    dropped_count = 0
    for session_id, msgs in iteritems(
        collection.Group(messages, operator.attrgetter("session_id"))):

      for msg in msgs:
        if (msg.auth_state != msg.AuthorizationState.AUTHENTICATED and
            msg.session_id != self.unauth_allowed_session_id):
          dropped_count += 1
          continue

        session_id_str = str(session_id)
        if session_id_str in message_handlers.session_id_map:
          request = rdf_objects.MessageHandlerRequest(
              client_id=msg.source.Basename(),
              handler_name=message_handlers.session_id_map[session_id],
              request_id=msg.response_id or random.UInt32(),
              request=msg.payload)
          if request.handler_name in self._SHORTCUT_HANDLERS:
            frontend_message_handler_requests.append(request)
          else:
            worker_message_handler_requests.append(request)
        elif session_id_str in self.legacy_well_known_session_ids:
          logging.debug("Dropping message for legacy well known session id %s",
                        session_id)
        else:
          unprocessed_msgs.append(msg)

    if dropped_count:
      logging.info("Dropped %d unauthenticated messages for %s", dropped_count,
                   client_id)

    if unprocessed_msgs:
      flow_responses = []
      for message in unprocessed_msgs:
        try:
          flow_responses.append(
              rdf_flow_objects.FlowResponseForLegacyResponse(message))
        except ValueError as e:
          logging.warning("Failed to parse legacy FlowResponse:\n%s\n%s", e,
                          message)

      data_store.REL_DB.WriteFlowResponses(flow_responses)

      for msg in unprocessed_msgs:
        if msg.type == rdf_flows.GrrMessage.Type.STATUS:
          stat = rdf_flows.GrrStatus(msg.payload)
          if stat.status == rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
            # A client crashed while performing an action, fire an event.
            crash_details = rdf_client.ClientCrash(
                client_id=client_id,
                session_id=msg.session_id,
                backtrace=stat.backtrace,
                crash_message=stat.error_message,
                nanny_status=stat.nanny_status,
                timestamp=rdfvalue.RDFDatetime.Now())
            events.Events.PublishEvent(
                "ClientCrash", crash_details, token=self.token)

    if worker_message_handler_requests:
      data_store.REL_DB.WriteMessageHandlerRequests(
          worker_message_handler_requests)

    if frontend_message_handler_requests:
      worker_lib.ProcessMessageHandlerRequests(
          frontend_message_handler_requests)

    logging.debug("Received %s messages from %s in %s sec", len(messages),
                  client_id,
                  time.time() - now)
