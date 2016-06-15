#!/usr/bin/env python
"""Test for client."""


import array
import pdb
import StringIO
import time
import urllib2


from M2Crypto import X509

import logging

from grr.client import actions
from grr.client import comms
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import ca_enroller
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows

# pylint: mode=test


class ServerCommunicatorFake(flow.ServerCommunicator):
  """A fake communicator to initialize the ServerCommunicator."""

  # For tests we bypass loading of the server certificate.

  def _LoadOurCertificate(self):
    return communicator.Communicator._LoadOurCertificate(self)


class ClientCommsTest(test_lib.GRRBaseTest):
  """Test the communicator."""

  def setUp(self):
    """Set up communicator tests."""
    super(ClientCommsTest, self).setUp()

    # These tests change the config so we preserve state.
    self.config_stubber = test_lib.PreserveConfig()
    self.config_stubber.Start()

    self.client_private_key = config_lib.CONFIG["Client.private_key"]

    self.server_serial_number = 0
    self.server_certificate = config_lib.CONFIG["Frontend.certificate"]
    self.server_private_key = config_lib.CONFIG["PrivateKeys.server_key"]
    self.client_communicator = comms.ClientCommunicator(
        private_key=self.client_private_key)

    self.client_communicator.LoadServerCertificate(
        server_certificate=self.server_certificate,
        ca_certificate=config_lib.CONFIG["CA.certificate"])

    self.server_communicator = ServerCommunicatorFake(
        certificate=self.server_certificate,
        private_key=self.server_private_key,
        token=self.token)

    self.last_urlmock_error = None

  def tearDown(self):
    super(ClientCommsTest, self).tearDown()
    self.config_stubber.Stop()

  def ClientServerCommunicate(self, timestamp=None):
    """Tests the end to end encrypted communicators."""
    message_list = rdf_flows.MessageList()
    for i in range(1, 11):
      message_list.job.Append(session_id=rdfvalue.SessionID(base="aff4:/flows",
                                                            queue=queues.FLOWS,
                                                            flow_name=i),
                              name="OMG it's a string")

    result = rdf_flows.ClientCommunication()
    timestamp = self.client_communicator.EncodeMessages(message_list,
                                                        result,
                                                        timestamp=timestamp)
    self.cipher_text = result.SerializeToString()

    (decoded_messages, source, client_timestamp) = (
        self.server_communicator.DecryptMessage(self.cipher_text))

    self.assertEqual(source, self.client_communicator.common_name)
    self.assertEqual(client_timestamp, timestamp)
    self.assertEqual(len(decoded_messages), 10)
    for i in range(1, 11):
      self.assertEqual(decoded_messages[i - 1].session_id,
                       rdfvalue.SessionID(base="aff4:/flows",
                                          queue=queues.FLOWS,
                                          flow_name=i))

    return decoded_messages

  def testCommunications(self):
    """Test that messages from unknown clients are tagged unauthenticated."""
    decoded_messages = self.ClientServerCommunicate()
    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED)

  def MakeClientAFF4Record(self):
    """Make a client in the data store."""
    cert = self.ClientCertFromPrivateKey(self.client_private_key)
    client_cert = rdf_crypto.RDFX509Cert(cert.as_pem())
    new_client = aff4.FACTORY.Create(client_cert.common_name,
                                     aff4_grr.VFSGRRClient,
                                     token=self.token)
    new_client.Set(new_client.Schema.CERT, client_cert)
    new_client.Close()
    return new_client

  def testKnownClient(self):
    """Test that messages from known clients are authenticated."""
    self.MakeClientAFF4Record()

    # Now the server should know about it
    decoded_messages = self.ClientServerCommunicate()

    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

  def testClientPingAndClockIsUpdated(self):
    """Check PING and CLOCK are updated, simulate bad client clock."""
    new_client = self.MakeClientAFF4Record()
    now = rdfvalue.RDFDatetime().Now()
    client_now = now - 20
    with test_lib.FakeTime(now):
      self.ClientServerCommunicate(timestamp=client_now)

      client_obj = aff4.FACTORY.Open(new_client.urn,
                                     ignore_cache=True,
                                     token=self.token)
      self.assertEqual(
          now.AsSecondsFromEpoch(),
          client_obj.Get(client_obj.Schema.PING).AsSecondsFromEpoch())
      self.assertEqual(
          client_now.AsSecondsFromEpoch(),
          client_obj.Get(client_obj.Schema.CLOCK).AsSecondsFromEpoch())

    now += 60
    client_now += 40
    with test_lib.FakeTime(now):
      self.ClientServerCommunicate(timestamp=client_now)

      client_obj = aff4.FACTORY.Open(new_client.urn,
                                     ignore_cache=True,
                                     token=self.token)
      self.assertEqual(
          now.AsSecondsFromEpoch(),
          client_obj.Get(client_obj.Schema.PING).AsSecondsFromEpoch())
      self.assertEqual(
          client_now.AsSecondsFromEpoch(),
          client_obj.Get(client_obj.Schema.CLOCK).AsSecondsFromEpoch())

  def testServerReplayAttack(self):
    """Test that replaying encrypted messages to the server invalidates them."""
    self.MakeClientAFF4Record()

    # First send some messages to the server
    decoded_messages = self.ClientServerCommunicate(timestamp=1000000)

    encrypted_messages = self.cipher_text

    self.assertEqual(decoded_messages[0].auth_state,
                     rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    # Immediate replay is accepted by the server since some proxies do this.
    (decoded_messages, _,
     _) = self.server_communicator.DecryptMessage(encrypted_messages)

    self.assertEqual(decoded_messages[0].auth_state,
                     rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    # Move the client time more than 1h forward.
    self.ClientServerCommunicate(timestamp=1000000 + 3700 * 1000000)

    # And replay the old messages again.
    (decoded_messages, _,
     _) = self.server_communicator.DecryptMessage(encrypted_messages)

    # Messages should now be tagged as desynced
    self.assertEqual(decoded_messages[0].auth_state,
                     rdf_flows.GrrMessage.AuthorizationState.DESYNCHRONIZED)

  def testCompression(self):
    """Tests that the compression works."""
    with test_lib.ConfigOverrider({"Network.compression": "UNCOMPRESSED"}):
      self.testCommunications()
      uncompressed_len = len(self.cipher_text)

    # If the client compresses, the server should still be able to
    # parse it:
    with test_lib.ConfigOverrider({"Network.compression": "ZCOMPRESS"}):
      self.testCommunications()
      compressed_len = len(self.cipher_text)

      self.assertLess(compressed_len, uncompressed_len)

    # If we chose a crazy compression scheme, the client should not
    # compress.
    with test_lib.ConfigOverrider({
        "Network.compression": "SOMECRAZYCOMPRESSION"
    }):
      self.testCommunications()
      compressed_len = len(self.cipher_text)

      self.assertEqual(compressed_len, uncompressed_len)

  def testX509Verify(self):
    """X509 Verify can have several failure paths."""

    # This is a successful verify.
    with utils.Stubber(X509.X509, "verify", lambda self, pkey=None: 1):
      self.client_communicator.LoadServerCertificate(
          self.server_certificate, config_lib.CONFIG["CA.certificate"])

      # Mock the verify function to simulate certificate failures.
      X509.X509.verify = lambda self, pkey=None: 0
      self.assertRaises(IOError, self.client_communicator.LoadServerCertificate,
                        self.server_certificate,
                        config_lib.CONFIG["CA.certificate"])

      # Verification can also fail with a -1 error.
      X509.X509.verify = lambda self, pkey=None: -1
      self.assertRaises(IOError, self.client_communicator.LoadServerCertificate,
                        self.server_certificate,
                        config_lib.CONFIG["CA.certificate"])

  def testErrorDetection(self):
    """Tests the end to end encrypted communicators."""
    # Install the client - now we can verify its signed messages
    self.MakeClientAFF4Record()

    # Make something to send
    message_list = rdf_flows.MessageList()
    for i in range(0, 10):
      message_list.job.Append(session_id=str(i))

    result = rdf_flows.ClientCommunication()
    self.client_communicator.EncodeMessages(message_list, result)
    cipher_text = result.SerializeToString()

    # Depending on this modification several things may happen:
    # 1) The padding may not match which will cause a decryption exception.
    # 2) The protobuf may fail to decode causing a decoding exception.
    # 3) The modification may affect the signature resulting in UNAUTHENTICATED
    #    messages.
    # 4) The modification may have no effect on the data at all.
    for x in range(0, len(cipher_text), 50):
      # Futz with the cipher text (Make sure it's really changed)
      mod_cipher_text = (cipher_text[:x] + chr((ord(cipher_text[x]) % 250) + 1)
                         + cipher_text[x + 1:])

      try:
        decoded, client_id, _ = self.server_communicator.DecryptMessage(
            mod_cipher_text)

        for i, message in enumerate(decoded):
          # If the message is actually authenticated it must not be changed!
          if message.auth_state == message.AuthorizationState.AUTHENTICATED:
            self.assertEqual(message.source, client_id)

            # These fields are set by the decoder and are not present in the
            # original message - so we clear them before comparison.
            message.auth_state = None
            message.source = None
            self.assertRDFValuesEqual(message, message_list.job[i])
          else:
            logging.debug("Message %s: Authstate: %s", i, message.auth_state)

      except communicator.DecodingError as e:
        logging.debug("Detected alteration at %s: %s", x, e)

  def testEnrollingCommunicator(self):
    """Test that the ClientCommunicator generates good keys."""
    self.client_communicator = comms.ClientCommunicator(certificate="")

    self.client_communicator.LoadServerCertificate(
        self.server_certificate, config_lib.CONFIG["CA.certificate"])

    req = X509.load_request_string(self.client_communicator.GetCSR())

    # Verify that the CN is of the correct form
    public_key = req.get_pubkey().get_rsa().pub()[1]
    cn = rdf_client.ClientURN.FromPublicKey(public_key)

    self.assertEqual(cn, req.get_subject().CN)


class HTTPClientTests(test_lib.GRRBaseTest):
  """Test the http communicator."""

  def setUp(self):
    """Set up communicator tests."""
    super(HTTPClientTests, self).setUp()

    # These tests change the config so we preserve state.
    self.config_stubber = test_lib.PreserveConfig()
    self.config_stubber.Start()

    self.certificate = self.ClientCertFromPrivateKey(config_lib.CONFIG[
        "Client.private_key"]).as_pem()
    self.server_serial_number = 0

    self.server_private_key = config_lib.CONFIG["PrivateKeys.server_key"]
    self.server_certificate = config_lib.CONFIG["Frontend.certificate"]

    self.client_cn = rdf_crypto.RDFX509Cert(self.certificate).common_name

    # Make a new client
    self.CreateNewClientObject()

    # The housekeeper threads of the time based caches also call time.time and
    # interfere with some tests so we disable them here.
    utils.InterruptableThread.exit = True
    # The same also applies to the StatsCollector thread.
    stats.StatsCollector.exit = True

    # Make a client mock
    self.client = aff4.FACTORY.Create(self.client_cn,
                                      aff4_grr.VFSGRRClient,
                                      mode="rw",
                                      token=self.token)
    self.client.Set(self.client.Schema.CERT(self.certificate))
    self.client.Flush()

    # Stop the client from actually processing anything
    self.out_queue_overrider = test_lib.ConfigOverrider({
        "Client.max_out_queue": 0
    })
    self.out_queue_overrider.Start()

    # And cache it in the server
    self.CreateNewServerCommunicator()

    self.urlopen_stubber = utils.Stubber(urllib2, "urlopen", self.UrlMock)
    self.urlopen_stubber.Start()
    self.sleep_stubber = utils.Stubber(time, "sleep", lambda x: None)
    self.sleep_stubber.Start()

    self.messages = []

    ca_enroller.enrolment_cache.Flush()

    # Response to send back to clients.
    self.server_response = dict(session_id="aff4:/W:session",
                                name="Echo",
                                response_id=2)

  def CreateNewServerCommunicator(self):
    self.server_communicator = ServerCommunicatorFake(
        certificate=self.server_certificate,
        private_key=self.server_private_key,
        token=self.token)

    self.server_communicator.client_cache.Put(self.client_cn, self.client)

  def tearDown(self):
    self.urlopen_stubber.Stop()
    self.out_queue_overrider.Stop()
    self.config_stubber.Stop()
    self.sleep_stubber.Stop()
    super(HTTPClientTests, self).tearDown()

  def CreateNewClientObject(self):
    self.client_communicator = comms.GRRHTTPClient(
        ca_cert=config_lib.CONFIG["CA.certificate"],
        worker=comms.GRRClientWorker)

    # Disable stats collection for tests.
    self.client_communicator.client_worker.last_stats_sent_time = (
        time.time() + 3600)

    # Build a client context with preloaded server certificates
    self.client_communicator.communicator.LoadServerCertificate(
        self.server_certificate, config_lib.CONFIG["CA.certificate"])

    self.client_communicator.http_manager.retry_error_limit = 5

  def UrlMock(self, req, num_messages=10, **kwargs):
    """A mock for url handler processing from the server's POV."""
    if "server.pem" in req.get_full_url():
      return StringIO.StringIO(config_lib.CONFIG["Frontend.certificate"])

    _ = kwargs
    try:
      self.client_communication = rdf_flows.ClientCommunication(req.data)

      # Decrypt incoming messages
      self.messages, source, ts = self.server_communicator.DecodeMessages(
          self.client_communication)

      # Make sure the messages are correct
      self.assertEqual(source, self.client_cn)
      for i, message in enumerate(self.messages):
        # Do not check any status messages.
        if message.request_id:
          self.assertEqual(message.response_id, i)
          self.assertEqual(message.request_id, 1)
          self.assertEqual(message.session_id, "aff4:/W:session")

      # Now prepare a response
      response_comms = rdf_flows.ClientCommunication()
      message_list = rdf_flows.MessageList()
      for i in range(0, num_messages):
        message_list.job.Append(request_id=i, **self.server_response)

      # Preserve the timestamp as a nonce
      self.server_communicator.EncodeMessages(
          message_list,
          response_comms,
          destination=source,
          timestamp=ts,
          api_version=self.client_communication.api_version)

      return StringIO.StringIO(response_comms.SerializeToString())
    except communicator.UnknownClientCert:
      raise urllib2.HTTPError(url=None, code=406, msg=None, hdrs=None, fp=None)
    except Exception as e:
      logging.info("Exception in mock urllib2.Open: %s.", e)
      self.last_urlmock_error = e

      if flags.FLAGS.debug:
        pdb.post_mortem()

      raise urllib2.HTTPError(url=None, code=500, msg=None, hdrs=None, fp=None)

  def CheckClientQueue(self):
    """Checks that the client context received all server messages."""
    # Check the incoming messages

    self.assertEqual(self.client_communicator.client_worker.InQueueSize(), 10)

    for i, message in enumerate(
        self.client_communicator.client_worker._in_queue):
      # This is the common name embedded in the certificate.
      self.assertEqual(message.source, "aff4:/GRR Test Server")
      self.assertEqual(message.response_id, 2)
      self.assertEqual(message.request_id, i)
      self.assertEqual(message.session_id, "aff4:/W:session")
      self.assertEqual(message.auth_state,
                       rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    # Clear the queue
    self.client_communicator.client_worker._in_queue = []

  def SendToServer(self):
    """Schedule some packets from client to server."""
    # Generate some client traffic
    for i in range(0, 10):
      self.client_communicator.client_worker.SendReply(
          rdf_flows.GrrStatus(),
          session_id=rdfvalue.SessionID("W:session"),
          response_id=i,
          request_id=1)

  def testInitialEnrollment(self):
    """If the client has no certificate initially it should enroll."""

    # Clear the certificate so we can generate a new one.
    with test_lib.ConfigOverrider({
        "Client.private_key": "",
        "Client.retry_error_limit": 5
    }):
      self.CreateNewClientObject()

      # Client should get a new Common Name.
      self.assertNotEqual(self.client_cn,
                          self.client_communicator.communicator.common_name)

      self.client_cn = self.client_communicator.communicator.common_name

      # The client will sleep and re-attempt to connect multiple times.
      status = self.client_communicator.RunOnce()

      self.assertEqual(status.code, 406)

      # The client should now send an enrollment request.
      status = self.client_communicator.RunOnce()

      # Client should generate enrollment message by itself.
      self.assertEqual(len(self.messages), 1)
      self.assertEqual(self.messages[0].session_id,
                       ca_enroller.Enroler.well_known_session_id)

  def testEnrollment(self):
    """Test the http response to unknown clients."""
    # We start off with the server not knowing about the client at all.
    self.server_communicator.client_cache.Flush()

    # Assume we do not know the client yet by clearing its certificate.
    self.client = aff4.FACTORY.Create(self.client_cn,
                                      aff4_grr.VFSGRRClient,
                                      mode="rw",
                                      token=self.token)
    self.client.DeleteAttribute(self.client.Schema.CERT)
    self.client.Flush()

    # Now communicate with the server.
    self.SendToServer()
    status = self.client_communicator.RunOnce()

    # We expect to receive a 406 and all client messages will be tagged as
    # UNAUTHENTICATED.
    self.assertEqual(status.code, 406)
    self.assertEqual(len(self.messages), 10)
    self.assertEqual(self.messages[0].auth_state,
                     rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED)

    # The next request should be an enrolling request.
    status = self.client_communicator.RunOnce()

    self.assertEqual(len(self.messages), 11)
    self.assertEqual(self.messages[-1].session_id,
                     ca_enroller.Enroler.well_known_session_id)

    # Now we manually run the enroll well known flow with the enrollment
    # request. This will start a new flow for enrolling the client, sign the
    # cert and add it to the data store.
    flow_obj = ca_enroller.Enroler(ca_enroller.Enroler.well_known_session_id,
                                   mode="rw",
                                   token=self.token)
    flow_obj.ProcessMessage(self.messages[-1])

    # The next client communication should be enrolled now.
    status = self.client_communicator.RunOnce()

    self.assertEqual(status.code, 200)

    # There should be a cert for the client right now.
    self.client = aff4.FACTORY.Create(self.client_cn,
                                      aff4_grr.VFSGRRClient,
                                      mode="rw",
                                      token=self.token)
    self.assertTrue(self.client.Get(self.client.Schema.CERT))

    # Now communicate with the server once again.
    self.SendToServer()
    status = self.client_communicator.RunOnce()

    self.assertEqual(status.code, 200)

  def testReboots(self):
    """Test the http communication with reboots."""
    # Now we add the new client record to the server cache
    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

    # Simulate the client rebooted
    self.CreateNewClientObject()

    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

    # Simulate the server rebooting
    self.CreateNewServerCommunicator()
    self.server_communicator.client_cache.Put(self.client_cn, self.client)

    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

  def _CheckFastPoll(self, require_fastpoll, expected_sleeptime):
    self.server_response = dict(session_id="aff4:/W:session",
                                name="Echo",
                                response_id=2,
                                priority="LOW_PRIORITY",
                                require_fastpoll=require_fastpoll)

    # Make sure we don't have any output messages that might override the
    # fastpoll setting from the input messages we send
    self.assertEqual(self.client_communicator.client_worker.OutQueueSize(), 0)

    self.client_communicator.RunOnce()
    # Make sure the timer is set to the correct value.
    self.assertEqual(self.client_communicator.timer.sleep_time,
                     expected_sleeptime)
    self.CheckClientQueue()

  def testNoFastPoll(self):
    """Test that the fast poll False is respected on input messages.

    Also make sure we wait the correct amount of time before next poll.
    """
    self._CheckFastPoll(False, config_lib.CONFIG["Client.poll_max"])

  def testFastPoll(self):
    """Test the the fast poll True is respected on input messages.

    Also make sure we wait the correct amount of time before next poll.
    """
    self._CheckFastPoll(True, config_lib.CONFIG["Client.poll_min"])

  def testCachedRSAOperations(self):
    """Make sure that expensive RSA operations are cached."""
    # First time fill the cache.
    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

    metric_value = stats.STATS.GetMetricValue("grr_rsa_operations")
    self.assertGreater(metric_value, 0)

    for _ in range(100):
      self.SendToServer()
      self.client_communicator.RunOnce()
      self.CheckClientQueue()

    # There should not have been any expensive operations any more
    self.assertEqual(
        stats.STATS.GetMetricValue("grr_rsa_operations"), metric_value)

  def testCorruption(self):
    """Simulate corruption of the http payload."""

    self.corruptor_field = None

    def Corruptor(req, **_):
      """Futz with some of the fields."""
      self.client_communication = rdf_flows.ClientCommunication(req.data)

      if self.corruptor_field and "server.pem" not in req.get_full_url():
        field_data = getattr(self.client_communication, self.corruptor_field)
        modified_data = array.array("c", field_data)
        offset = len(field_data) / 2
        modified_data[offset] = chr((ord(field_data[offset]) % 250) + 1)
        setattr(self.client_communication, self.corruptor_field,
                str(modified_data))

        # Make sure we actually changed the data.
        self.assertNotEqual(field_data, modified_data)

      req.data = self.client_communication.SerializeToString()
      return self.UrlMock(req)

    with utils.Stubber(urllib2, "urlopen", Corruptor):
      self.SendToServer()
      status = self.client_communicator.RunOnce()
      self.assertEqual(status.code, 200)

      for field in ["packet_iv", "encrypted"]:
        # Corrupting each field should result in HMAC verification errors.
        self.corruptor_field = field

        self.SendToServer()
        status = self.client_communicator.RunOnce()

        self.assertEqual(status.code, 500)
        self.assertTrue(
            "HMAC verification failed" in str(self.last_urlmock_error))

      # Corruption of these fields will likely result in RSA errors, since we do
      # the RSA operations before the HMAC verification (in order to recover the
      # hmac key):
      for field in ["encrypted_cipher", "encrypted_cipher_metadata"]:
        # Corrupting each field should result in HMAC verification errors.
        self.corruptor_field = field

        self.SendToServer()
        status = self.client_communicator.RunOnce()

        self.assertEqual(status.code, 500)

  def testClientRetransmission(self):
    """Test that client retransmits failed messages."""
    fail = True
    num_messages = 10

    def FlakyServer(req, timeout=None):  # pylint: disable=unused-argument
      if not fail or "server.pem" in req.get_full_url():
        return self.UrlMock(req, num_messages=num_messages)

      raise urllib2.HTTPError(url=None, code=500, msg=None, hdrs=None, fp=None)

    with utils.Stubber(urllib2, "urlopen", FlakyServer):
      self.SendToServer()
      status = self.client_communicator.RunOnce()
      self.assertEqual(status.code, 500)

      # Server should not receive anything.
      self.assertEqual(len(self.messages), 0)

      # Try to send these messages again.
      fail = False

      self.assertEqual(self.client_communicator.client_worker.InQueueSize(), 0)

      status = self.client_communicator.RunOnce()

      self.assertEqual(status.code, 200)

      # We have received 10 client messages.
      self.assertEqual(self.client_communicator.client_worker.InQueueSize(), 10)
      self.CheckClientQueue()

      # Server should have received 10 messages this time.
      self.assertEqual(len(self.messages), 10)

  def testClientStatsCollection(self):
    """Tests that the client stats are collected automatically."""
    now = 1000000
    # Pretend we have already sent stats.
    self.client_communicator.client_worker.last_stats_sent_time = (
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(now))

    with test_lib.FakeTime(now):
      self.client_communicator.client_worker.CheckStats()

    runs = []
    action_cls = actions.ActionPlugin.classes.get("GetClientStatsAuto")
    with utils.Stubber(action_cls, "Run", lambda cls, _: runs.append(1)):

      # No stats collection after 10 minutes.
      with test_lib.FakeTime(now + 600):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 0)

      # Let one hour pass.
      with test_lib.FakeTime(now + 3600):
        self.client_communicator.client_worker.CheckStats()
        # This time the client should collect stats.
        self.assertEqual(len(runs), 1)

      # Let one hour and ten minutes pass.
      with test_lib.FakeTime(now + 3600 + 600):
        self.client_communicator.client_worker.CheckStats()
        # Again, there should be no stats collection, as last collection
        # happened less than an hour ago.
        self.assertEqual(len(runs), 1)

  def testClientStatsCollectionHappensEveryMinuteWhenClientIsBusy(self):
    """Tests that client stats are collected more often when client is busy."""
    now = 1000000
    # Pretend we have already sent stats.
    self.client_communicator.client_worker.last_stats_sent_time = (
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(now))
    self.client_communicator.client_worker._is_active = True

    with test_lib.FakeTime(now):
      self.client_communicator.client_worker.CheckStats()

    runs = []
    action_cls = actions.ActionPlugin.classes.get("GetClientStatsAuto")
    with utils.Stubber(action_cls, "Run", lambda cls, _: runs.append(1)):

      # No stats collection after 30 seconds.
      with test_lib.FakeTime(now + 30):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 0)

      # Let 61 seconds pass.
      with test_lib.FakeTime(now + 61):
        self.client_communicator.client_worker.CheckStats()
        # This time the client should collect stats.
        self.assertEqual(len(runs), 1)

      # No stats collection within one minute from the last time.
      with test_lib.FakeTime(now + 61 + 59):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 1)

      # Stats collection happens as more than one minute has passed since the
      # last one.
      with test_lib.FakeTime(now + 61 + 61):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 2)

  def testClientStatsCollectionAlwaysHappensAfterHandleMessage(self):
    """Tests that client stats are collected more often when client is busy."""
    now = 1000000
    # Pretend we have already sent stats.
    self.client_communicator.client_worker.last_stats_sent_time = (
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(now))

    with test_lib.FakeTime(now):
      self.client_communicator.client_worker.CheckStats()

    runs = []
    action_cls = actions.ActionPlugin.classes.get("GetClientStatsAuto")
    with utils.Stubber(action_cls, "Run", lambda cls, _: runs.append(1)):

      # No stats collection after 30 seconds.
      with test_lib.FakeTime(now + 30):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 0)

      self.client_communicator.client_worker.HandleMessage(rdf_flows.GrrMessage(
          name="HashFile"))

      # HandleMessage was called, but one minute hasn't passed, so
      # stats should not be sent.
      with test_lib.FakeTime(now + 59):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 0)

      # HandleMessage was called more than one minute ago, so stats
      # should be sent.
      with test_lib.FakeTime(now + 61):
        self.client_communicator.client_worker.CheckStats()
        self.assertEqual(len(runs), 1)

  def RaiseError(self, request, timeout=0):
    raise urllib2.URLError("Not a real connection.")

  def testClientConnectionErrors(self):
    client_obj = comms.GRRHTTPClient()
    # Make the connection unavailable and skip the retry interval.
    with utils.MultiStubber((urllib2, "urlopen", self.RaiseError),
                            (time, "sleep", lambda s: None)):

      with test_lib.ConfigOverrider({"Client.connection_error_limit": 8}):
        # Simulate a client run. The client will retry the connection limit by
        # itself. The Run() method will quit when connection_error_limit is
        # reached. This will make the real client quit.
        client_obj.Run()

        self.assertEqual(client_obj.http_manager.consecutive_connection_errors,
                         config_lib.CONFIG["Client.connection_error_limit"] + 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
