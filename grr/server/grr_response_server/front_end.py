#!/usr/bin/env python
"""The GRR frontend server."""

import logging
import operator
import time

from grr import config
from grr.lib import communicator
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import client_index
from grr.server.grr_response_server import data_migration
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import db
from grr.server.grr_response_server import events
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import queue_manager
from grr.server.grr_response_server import rekall_profile_server
from grr.server.grr_response_server import threadpool
from grr.server.grr_response_server.aff4_objects import aff4_grr


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using AFF4."""

  def __init__(self, certificate, private_key, token=None):
    self.client_cache = utils.FastStore(1000)
    self.token = token
    super(ServerCommunicator, self).__init__(
        certificate=certificate, private_key=private_key)
    self.pub_key_cache = utils.FastStore(max_size=50000)
    # Our common name as an RDFURN.
    self.common_name = rdfvalue.RDFURN(self.certificate.GetCN())

  def _GetRemotePublicKey(self, common_name):
    try:
      # See if we have this client already cached.
      remote_key = self.pub_key_cache.Get(str(common_name))
      stats.STATS.IncrementCounter("grr_pub_key_cache", fields=["hits"])
      return remote_key
    except KeyError:
      stats.STATS.IncrementCounter("grr_pub_key_cache", fields=["misses"])

    # Fetch the client's cert and extract the key.
    client = aff4.FACTORY.Create(
        common_name,
        aff4.AFF4Object.classes["VFSGRRClient"],
        mode="rw",
        token=self.token)
    cert = client.Get(client.Schema.CERT)
    if not cert:
      stats.STATS.IncrementCounter("grr_unique_clients")
      raise communicator.UnknownClientCert("Cert not found")

    if rdfvalue.RDFURN(cert.GetCN()) != rdfvalue.RDFURN(common_name):
      logging.error("Stored cert mismatch for %s", common_name)
      raise communicator.UnknownClientCert("Stored cert mismatch")

    self.client_cache.Put(common_name, client)
    stats.STATS.SetGaugeValue("grr_frontendserver_client_cache_size",
                              len(self.client_cache))

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
      stats.STATS.IncrementCounter("grr_unauthenticated_messages")
      return rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    try:
      client_id = cipher.cipher_metadata.source
      try:
        client = self.client_cache.Get(client_id)
      except KeyError:
        client = aff4.FACTORY.Create(
            client_id,
            aff4.AFF4Object.classes["VFSGRRClient"],
            mode="rw",
            token=self.token)
        self.client_cache.Put(client_id, client)
        stats.STATS.SetGaugeValue("grr_frontendserver_client_cache_size",
                                  len(self.client_cache))

      ip = response_comms.orig_request.source_ip
      client.Set(client.Schema.CLIENT_IP(ip))

      # The very first packet we see from the client we do not have its clock
      remote_time = client.Get(client.Schema.CLOCK) or rdfvalue.RDFDatetime(0)
      client_time = packed_message_list.timestamp or rdfvalue.RDFDatetime(0)

      # This used to be a strict check here so absolutely no out of
      # order messages would be accepted ever. Turns out that some
      # proxies can send your request with some delay even if the
      # client has already timed out (and sent another request in
      # the meantime, making the first one out of order). In that
      # case we would just kill the whole flow as a
      # precaution. Given the behavior of those proxies, this seems
      # now excessive and we have changed the replay protection to
      # only trigger on messages that are more than one hour old.

      if client_time < long(remote_time - rdfvalue.Duration("1h")):
        logging.warning("Message desynchronized for %s: %s >= %s", client_id,
                        long(remote_time), int(client_time))
        # This is likely an old message
        return rdf_flows.GrrMessage.AuthorizationState.DESYNCHRONIZED

      stats.STATS.IncrementCounter("grr_authenticated_messages")

      # Update the client and server timestamps only if the client
      # time moves forward.
      if client_time > long(remote_time):
        client.Set(client.Schema.CLOCK, rdfvalue.RDFDatetime(client_time))
        client.Set(client.Schema.PING, rdfvalue.RDFDatetime.Now())

        clock = client_time
        ping = rdfvalue.RDFDatetime.Now()

        for label in client.Get(client.Schema.LABELS, []):
          stats.STATS.IncrementCounter(
              "client_pings_by_label", fields=[label.name])
      else:
        clock = None
        ping = None
        logging.warning("Out of order message for %s: %s >= %s", client_id,
                        long(remote_time), int(client_time))

      client.Flush()
      if data_store.RelationalDBWriteEnabled():
        source_ip = response_comms.orig_request.source_ip
        if source_ip:
          last_ip = rdf_client.NetworkAddress(
              human_readable_address=response_comms.orig_request.source_ip)
        else:
          last_ip = None

        if ping or clock or last_ip:
          try:
            data_store.REL_DB.WriteClientMetadata(
                client_id.Basename(),
                last_ip=last_ip,
                last_clock=clock,
                last_ping=ping,
                fleetspeak_enabled=False)
          except db.UnknownClientError:
            pass

    except communicator.UnknownClientCert:
      pass

    return rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED


class RelationalServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using the relational db."""

  def __init__(self, certificate, private_key):
    super(RelationalServerCommunicator, self).__init__(
        certificate=certificate, private_key=private_key)
    self.pub_key_cache = utils.FastStore(max_size=50000)
    self.common_name = self.certificate.GetCN()

  def _GetRemotePublicKey(self, common_name):
    remote_client_id = common_name.Basename()
    try:
      # See if we have this client already cached.
      remote_key = self.pub_key_cache.Get(remote_client_id)
      stats.STATS.IncrementCounter("grr_pub_key_cache", fields=["hits"])
      return remote_key
    except KeyError:
      stats.STATS.IncrementCounter("grr_pub_key_cache", fields=["misses"])

    md = data_store.REL_DB.ReadClientMetadata(remote_client_id)
    if not md:
      stats.STATS.IncrementCounter("grr_unique_clients")
      raise communicator.UnknownClientCert("Cert not found")

    cert = md.certificate
    if rdfvalue.RDFURN(cert.GetCN()) != rdfvalue.RDFURN(common_name):
      logging.error("Stored cert mismatch for %s", common_name)
      raise communicator.UnknownClientCert("Stored cert mismatch")

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
      stats.STATS.IncrementCounter("grr_unauthenticated_messages")
      return rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    try:
      client_id = cipher.cipher_metadata.source.Basename()
      metadata = data_store.REL_DB.ReadClientMetadata(client_id)
      client_time = packed_message_list.timestamp or rdfvalue.RDFDatetime(0)

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

        if client_time < stored_client_time - rdfvalue.Duration("1h"):
          logging.warning("Message desynchronized for %s: %s >= %s", client_id,
                          long(stored_client_time), long(client_time))
          # This is likely an old message
          return rdf_flows.GrrMessage.AuthorizationState.DESYNCHRONIZED

        stats.STATS.IncrementCounter("grr_authenticated_messages")

        # Update the client and server timestamps only if the client
        # time moves forward.
        if client_time <= stored_client_time:
          logging.warning("Out of order message for %s: %s >= %s", client_id,
                          long(stored_client_time), long(client_time))
          return rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

      stats.STATS.IncrementCounter("grr_authenticated_messages")

      for label in data_store.REL_DB.ReadClientLabels(client_id):
        stats.STATS.IncrementCounter(
            "client_pings_by_label", fields=[label.name])

      source_ip = response_comms.orig_request.source_ip
      if source_ip:
        last_ip = rdf_client.NetworkAddress(
            human_readable_address=response_comms.orig_request.source_ip)
      else:
        last_ip = None

      data_store.REL_DB.WriteClientMetadata(
          client_id,
          last_ip=last_ip,
          last_clock=client_time,
          last_ping=rdfvalue.RDFDatetime.Now(),
          fleetspeak_enabled=False)

    except communicator.UnknownClientCert:
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
               max_retransmission_time=10,
               threadpool_prefix="grr_threadpool"):
    # Identify ourselves as the server.
    self.token = access_control.ACLToken(
        username="GRRFrontEnd", reason="Implied.")
    self.token.supervisor = True

    if data_store.RelationalDBReadEnabled():
      self._communicator = RelationalServerCommunicator(
          certificate=certificate, private_key=private_key)
    else:
      self._communicator = ServerCommunicator(
          certificate=certificate, private_key=private_key, token=self.token)

    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size
    self.thread_pool = threadpool.ThreadPool.Factory(
        threadpool_prefix,
        min_threads=2,
        max_threads=config.CONFIG["Threadpool.size"])
    self.thread_pool.Start()

    # There is only a single session id that we accept unauthenticated
    # messages for, the one to enroll new clients.
    self.unauth_allowed_session_id = rdfvalue.SessionID(
        queue=queues.ENROLLMENT, flow_name="Enrol")

    # Some well known flows are run on the front end.
    available_wkfs = flow.WellKnownFlow.GetAllWellKnownFlows(token=self.token)
    whitelist = set(config.CONFIG["Frontend.well_known_flows"])

    available_wkf_set = set(available_wkfs)
    unknown_flows = whitelist - available_wkf_set
    if unknown_flows:
      raise ValueError("Unknown flows in Frontend.well_known_flows: %s" %
                       ",".join(unknown_flows))

    self.well_known_flows = {
        flow_name: available_wkfs[flow_name]
        for flow_name in whitelist & available_wkf_set
    }

  @stats.Counted("grr_frontendserver_handle_num")
  @stats.Timed("grr_frontendserver_handle_time")
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
    tasks = []

    message_list = rdf_flows.MessageList()
    # Only give the client messages if we are able to receive them in a
    # reasonable time.
    if time.time() - now < 10:
      tasks = self.DrainTaskSchedulerQueueForClient(source, required_count)
      message_list.job = tasks

    # Encode the message_list in the response_comms using the same API version
    # the client used.
    try:
      self._communicator.EncodeMessages(
          message_list,
          response_comms,
          destination=source,
          timestamp=timestamp,
          api_version=request_comms.api_version)
    except communicator.UnknownClientCert:
      # We can not encode messages to the client yet because we do not have the
      # client certificate - return them to the queue so we can try again later.
      with data_store.DB.GetMutationPool() as pool:
        queue_manager.QueueManager(token=self.token).Schedule(tasks, pool)
      raise

    return source, len(messages)

  def DrainTaskSchedulerQueueForClient(self, client, max_count=None):
    """Drains the client's Task Scheduler queue.

    1) Get all messages in the client queue.
    2) Sort these into a set of session_ids.
    3) Use data_store.DB.ResolvePrefix() to query all requests.
    4) Delete all responses for retransmitted messages (if needed).

    Args:
       client: The ClientURN object specifying this client.

       max_count: The maximum number of messages we will issue for the
                  client.
                  If not given, uses self.max_queue_size .

    Returns:
       The tasks respresenting the messages returned. If we can not send them,
       we can reschedule them for later.
    """
    if max_count is None:
      max_count = self.max_queue_size

    if max_count <= 0:
      return []

    client = rdf_client.ClientURN(client)

    start_time = time.time()
    # Drain the queue for this client
    new_tasks = queue_manager.QueueManager(token=self.token).QueryAndOwn(
        queue=client.Queue(),
        limit=max_count,
        lease_seconds=self.message_expiry_time)

    initial_ttl = rdf_flows.GrrMessage().task_ttl
    check_before_sending = []
    result = []
    for task in new_tasks:
      if task.task_ttl < initial_ttl - 1:
        # This message has been leased before.
        check_before_sending.append(task)
      else:
        result.append(task)

    if check_before_sending:
      with queue_manager.QueueManager(token=self.token) as manager:
        status_found = manager.MultiCheckStatus(check_before_sending)

        # All messages that don't have a status yet should be sent again.
        for task in check_before_sending:
          if task not in status_found:
            result.append(task)
          else:
            manager.DeQueueClientRequest(client, task.task_id)

    stats.STATS.IncrementCounter("grr_messages_sent", len(result))
    if result:
      logging.debug("Drained %d messages for %s in %s seconds.", len(result),
                    client,
                    time.time() - start_time)

    return result

  def EnrolFleetspeakClient(self, client_id):
    """Enrols a Fleetspeak-enabled client for use with GRR."""
    client_urn = rdf_client.ClientURN(client_id)

    # If already enrolled, return.
    if data_store.RelationalDBReadEnabled():
      if data_store.REL_DB.ReadClientMetadata(client_id):
        return
    else:
      if aff4.FACTORY.ExistsWithType(
          client_urn, aff4_type=aff4_grr.VFSGRRClient, token=self.token):
        return

    logging.info("Enrolling a new Fleetspeak client: %r", client_id)

    if data_store.RelationalDBWriteEnabled():
      data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    # TODO(fleetspeak-team,grr-team): If aff4 isn't reliable enough, we can
    # catch exceptions from it and forward them to Fleetspeak by failing its
    # gRPC call. Fleetspeak will then retry with a random, perhaps healthier,
    # instance of the GRR frontend.
    with aff4.FACTORY.Create(
        client_urn,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token) as client:

      client.Set(client.Schema.FLEETSPEAK_ENABLED, rdfvalue.RDFBool(True))

      index = client_index.CreateClientIndex(token=self.token)
      index.AddClient(client)
      if data_store.RelationalDBWriteEnabled():
        index = client_index.ClientIndex()
        index.AddClient(data_migration.ConvertVFSGRRClient(client))

    # Publish the client enrollment message.
    events.Events.PublishEvent("ClientEnrollment", client_urn, token=self.token)

  def RecordFleetspeakClientPing(self, client_id):
    """Records the last client contact in the datastore."""
    ping = rdfvalue.RDFDatetime.Now()
    with aff4.FACTORY.Create(
        rdf_client.ClientURN(client_id),
        aff4_type=aff4_grr.VFSGRRClient,
        mode="w",
        token=self.token,
        force_new_version=False) as client:
      client.Set(client.Schema.PING, ping)

    if data_store.RelationalDBWriteEnabled():
      data_store.REL_DB.WriteClientMetadata(client_id, last_ping=ping)

  def ReceiveMessages(self, client_id, messages):
    """Receives and processes the messages from the source.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      client_id: The client which sent the messages.
      messages: A list of GrrMessage RDFValues.
    """
    now = time.time()
    with queue_manager.QueueManager(token=self.token) as manager:
      for session_id, msgs in utils.GroupBy(
          messages, operator.attrgetter("session_id")).iteritems():

        # Remove and handle messages to WellKnownFlows
        leftover_msgs = self.HandleWellKnownFlows(msgs)

        unprocessed_msgs = []
        for msg in leftover_msgs:
          if (msg.auth_state == msg.AuthorizationState.AUTHENTICATED or
              msg.session_id == self.unauth_allowed_session_id):
            unprocessed_msgs.append(msg)

        if len(unprocessed_msgs) < len(leftover_msgs):
          logging.info("Dropped %d unauthenticated messages for %s",
                       len(leftover_msgs) - len(unprocessed_msgs), client_id)

        if not unprocessed_msgs:
          continue

        for msg in unprocessed_msgs:
          manager.QueueResponse(msg)

        for msg in unprocessed_msgs:
          # Messages for well known flows should notify even though they don't
          # have a status.
          if msg.request_id == 0:
            manager.QueueNotification(
                session_id=msg.session_id, priority=msg.priority)
            # Those messages are all the same, one notification is enough.
            break
          elif msg.type == rdf_flows.GrrMessage.Type.STATUS:
            # If we receive a status message from the client it means the client
            # has finished processing this request. We therefore can de-queue it
            # from the client queue. msg.task_id will raise if the task id is
            # not set (message originated at the client, there was no request on
            # the server), so we have to check .HasTaskID() first.
            if msg.HasTaskID():
              manager.DeQueueClientRequest(client_id, msg.task_id)

            manager.QueueNotification(
                session_id=msg.session_id,
                priority=msg.priority,
                last_status=msg.request_id)

            stat = rdf_flows.GrrStatus(msg.payload)
            if stat.status == rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
              # A client crashed while performing an action, fire an event.
              crash_details = rdf_client.ClientCrash(
                  client_id=client_id,
                  session_id=session_id,
                  backtrace=stat.backtrace,
                  crash_message=stat.error_message,
                  nanny_status=stat.nanny_status,
                  timestamp=rdfvalue.RDFDatetime.Now())
              events.Events.PublishEvent(
                  "ClientCrash", crash_details, token=self.token)

    logging.debug("Received %s messages from %s in %s sec", len(messages),
                  client_id,
                  time.time() - now)

  def HandleWellKnownFlows(self, messages):
    """Hands off messages to well known flows."""
    msgs_by_wkf = {}
    result = []
    for msg in messages:
      # Regular message - queue it.
      if msg.response_id != 0:
        result.append(msg)
        continue

      # Well known flows:
      flow_name = msg.session_id.FlowName()

      if flow_name in self.well_known_flows:
        # This message should be processed directly on the front end.
        msgs_by_wkf.setdefault(flow_name, []).append(msg)

        # TODO(user): Deprecate in favor of 'well_known_flow_requests'
        # metric.
        stats.STATS.IncrementCounter("grr_well_known_flow_requests")

        stats.STATS.IncrementCounter(
            "well_known_flow_requests", fields=[str(msg.session_id)])
      else:
        # Message should be queued to be processed in the backend.

        # Well known flows have a response_id==0, but if we queue up the state
        # as that it will overwrite some other message that is queued. So we
        # change it to a random number here.
        msg.response_id = utils.PRNG.GetUInt32()

        # Queue the message in the data store.
        result.append(msg)

    for flow_name, msg_list in msgs_by_wkf.iteritems():
      wkf = self.well_known_flows[flow_name]
      wkf.ProcessMessages(msg_list)

    return result

  def _GetClientPublicKey(self, client_id):
    client_obj = aff4.FACTORY.Open(client_id, token=aff4.FACTORY.root_token)
    return client_obj.Get(client_obj.Schema.CERT).GetPublicKey()

  def _GetRekallProfileServer(self):
    try:
      return self._rekall_profile_server
    except AttributeError:
      server_type = config.CONFIG["Rekall.profile_server"]
      self._rekall_profile_server = rekall_profile_server.ProfileServer.classes[
          server_type]()
      return self._rekall_profile_server

  def GetRekallProfile(self, name, version="v1.0"):
    server = self._GetRekallProfileServer()

    logging.debug("Serving Rekall profile %s/%s", version, name)
    try:
      return server.GetProfileByName(name, version)
    # TODO(amoser): We raise too many different exceptions in profile server.
    except Exception as e:  # pylint: disable=broad-except
      logging.debug("Unable to serve profile %s/%s: %s", version, name, e)
      return None


class FrontendInit(registry.InitHook):

  def RunOnce(self):
    # Frontend metrics. These metrics should be used by the code that
    # feeds requests into the frontend.
    stats.STATS.RegisterCounterMetric(
        "client_pings_by_label", fields=[("label", str)])
    stats.STATS.RegisterGaugeMetric(
        "frontend_active_count", int, fields=[("source", str)])
    stats.STATS.RegisterGaugeMetric("frontend_max_active_count", int)
    stats.STATS.RegisterCounterMetric(
        "frontend_http_requests", fields=[("action", str), ("protocol", str)])
    stats.STATS.RegisterCounterMetric(
        "frontend_in_bytes", fields=[("source", str)])
    stats.STATS.RegisterCounterMetric(
        "frontend_out_bytes", fields=[("source", str)])
    stats.STATS.RegisterCounterMetric(
        "frontend_request_count", fields=[("source", str)])
    # Client requests sent to an inactive datacenter. This indicates a
    # misconfiguration.
    stats.STATS.RegisterCounterMetric(
        "frontend_inactive_request_count", fields=[("source", str)])
    stats.STATS.RegisterEventMetric(
        "frontend_request_latency", fields=[("source", str)])

    stats.STATS.RegisterEventMetric("grr_frontendserver_handle_time")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_num")
    stats.STATS.RegisterGaugeMetric("grr_frontendserver_client_cache_size", int)
    stats.STATS.RegisterCounterMetric("grr_messages_sent")

    stats.STATS.RegisterCounterMetric(
        "grr_pub_key_cache", fields=[("type", str)])
