#!/usr/bin/env python
"""Test for client."""


import pdb
import StringIO
import time
import urllib2


from M2Crypto import X509
import mox

import logging

from grr.client import actions
from grr.client import comms
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
# pylint: disable=unused-import
from grr.lib import server_plugins
# pylint: enable=unused-import
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils


from grr.lib.flows.caenroll import ca_enroller


class ServerCommunicatorFake(flow.ServerCommunicator):
  """A fake communicator to initialize the ServerCommunicator."""

  # For tests we bypass loading of the server certificate.
  def _LoadOurCertificate(self):
    return communicator.Communicator._LoadOurCertificate(self)


class ClientCommsTest(test_lib.GRRBaseTest):
  """Test the communicator."""

  def setUp(self):
    """Set up communicator tests."""
    test_lib.GRRBaseTest.setUp(self)

    self.client_certificate = config_lib.CONFIG["Client.certificate"]
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

  def ClientServerCommunicate(self, timestamp=None):
    """Tests the end to end encrypted communicators."""
    message_list = rdfvalue.MessageList()
    for i in range(0, 10):
      message_list.job.Append(
          session_id=rdfvalue.SessionID("aff4:/flows/W:%d" % i),
          name="OMG it's a string")

    result = rdfvalue.ClientCommunication()
    timestamp = self.client_communicator.EncodeMessages(message_list, result,
                                                        timestamp=timestamp)
    self.cipher_text = result.SerializeToString()

    (decoded_messages, source, client_timestamp) = (
        self.server_communicator.DecryptMessage(self.cipher_text))

    self.assertEqual(source, self.client_communicator.common_name)
    self.assertEqual(client_timestamp, timestamp)
    self.assertEqual(len(decoded_messages), 10)
    for i in range(0, 10):
      self.assertEqual(decoded_messages[i].session_id,
                       rdfvalue.SessionID("aff4:/flows/W:%d" % i))

    return decoded_messages

  def testCommunications(self):
    """Test that messages from unknown clients are tagged unauthenticated."""
    decoded_messages = self.ClientServerCommunicate()
    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       rdfvalue.GrrMessage.AuthorizationState.UNAUTHENTICATED)

  def MakeClientAFF4Record(self):
    """Make a client in the data store."""
    client_cert = rdfvalue.RDFX509Cert(self.client_certificate)
    new_client = aff4.FACTORY.Create(client_cert.common_name, "VFSGRRClient",
                                     token=self.token)
    new_client.Set(new_client.Schema.CERT, client_cert)
    new_client.Close()

  def testKnownClient(self):
    """Test that messages from known clients are authenticated."""
    self.MakeClientAFF4Record()

    # Now the server should know about it
    decoded_messages = self.ClientServerCommunicate()

    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

  def testServerReplayAttack(self):
    """Test that replaying encrypted messages to the server invalidates them."""
    self.MakeClientAFF4Record()

    # First send some messages to the server
    decoded_messages = self.ClientServerCommunicate()

    self.assertEqual(decoded_messages[0].auth_state,
                     rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

    # Now replay the last message to the server
    (decoded_messages, _, _) = self.server_communicator.DecryptMessage(
        self.cipher_text)

    # Messages should now be tagged as desynced
    self.assertEqual(decoded_messages[0].auth_state,
                     rdfvalue.GrrMessage.AuthorizationState.DESYNCHRONIZED)

  def testCompression(self):
    """Tests that the compression works."""
    config_lib.CONFIG.Set("Network.compression", "UNCOMPRESSED")
    self.testCommunications()
    uncompressed_len = len(self.cipher_text)

    # If the client compresses, the server should still be able to
    # parse it:
    config_lib.CONFIG.Set("Network.compression", "ZCOMPRESS")
    self.testCommunications()
    compressed_len = len(self.cipher_text)

    self.assert_(compressed_len < uncompressed_len)

    # If we chose a crazy compression scheme, the client should not
    # compress.
    config_lib.CONFIG.Set("Network.compression", "SOMECRAZYCOMPRESSION")
    self.testCommunications()
    compressed_len = len(self.cipher_text)

    self.assertEqual(compressed_len, uncompressed_len)

  def testX509Verify(self):
    """X509 Verify can have several failure paths."""
    x509_verify = X509.X509.verify

    try:
      # This is a successful verify.
      X509.X509.verify = lambda self, pkey=None: 1
      self.client_communicator.LoadServerCertificate(
          self.server_certificate, config_lib.CONFIG["CA.certificate"])

      # Mock the verify function to simulate certificate failures.
      X509.X509.verify = lambda self, pkey=None: 0
      self.assertRaises(
          IOError, self.client_communicator.LoadServerCertificate,
          self.server_certificate, config_lib.CONFIG["CA.certificate"])

      # Verification can also fail with a -1 error.
      X509.X509.verify = lambda self, pkey=None: -1
      self.assertRaises(
          IOError, self.client_communicator.LoadServerCertificate,
          self.server_certificate, config_lib.CONFIG["CA.certificate"])

    finally:
      X509.X509.verify = x509_verify

  def testErrorDetection(self):
    """Tests the end to end encrypted communicators."""
    # Install the client - now we can verify its signed messages
    self.MakeClientAFF4Record()

    # Make something to send
    message_list = rdfvalue.MessageList()
    for i in range(0, 10):
      message_list.job.Append(session_id=str(i))

    result = rdfvalue.ClientCommunication()
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
      mod_cipher_text = (cipher_text[:x] +
                         chr((ord(cipher_text[x]) % 250)+1) +
                         cipher_text[x+1:])

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
            self.assertProtoEqual(message, message_list.job[i])
          else:
            logging.debug("Message %s: Authstate: %s", i, message.auth_state)

      except communicator.DecodingError as e:
        logging.debug("Detected alteration at %s: %s", x, e)

  def testEnrollingCommunicator(self):
    """Test that the ClientCommunicator generates good keys."""
    self.client_communicator = comms.ClientCommunicator(
        certificate="")

    self.client_communicator.LoadServerCertificate(
        self.server_certificate, config_lib.CONFIG["CA.certificate"])

    req = X509.load_request_string(self.client_communicator.GetCSR())

    # Verify that the CN is of the correct form
    public_key = req.get_pubkey().get_rsa().pub()[1]
    cn = rdfvalue.ClientURN.FromPublicKey(public_key)

    self.assertEqual(cn, req.get_subject().CN)


class HTTPClientTests(test_lib.GRRBaseTest):
  """Test the http communicator."""

  def setUp(self):
    """Set up communicator tests."""
    super(HTTPClientTests, self).setUp()

    self.certificate = config_lib.CONFIG["Client.certificate"]
    self.server_serial_number = 0

    self.server_private_key = config_lib.CONFIG["PrivateKeys.server_key"]
    self.server_certificate = config_lib.CONFIG["Frontend.certificate"]

    self.client_cn = rdfvalue.RDFX509Cert(self.certificate).common_name

    # Make a new client
    self.CreateNewClientObject()

    # The housekeeper threads of the time based caches also call time.time and
    # interfere with some tests so we disable them here.
    utils.InterruptableThread.exit = True
    # The same also applies to the StatsCollector thread.
    stats.StatsCollector.exit = True

    # Make a client mock
    self.client = aff4.FACTORY.Create(self.client_cn, "VFSGRRClient", mode="rw",
                                      token=self.token)
    self.client.Set(self.client.Schema.CERT(self.certificate))
    self.client.Flush()

    # Stop the client from actually processing anything
    config_lib.CONFIG.Set("Client.max_out_queue", 0)

    # And cache it in the server
    self.CreateNewServerCommunicator()

    self.urlopen = urllib2.urlopen
    urllib2.urlopen = self.UrlMock
    self.messages = []

    ca_enroller.enrolment_cache.Flush()

  def CreateNewServerCommunicator(self):
    self.server_communicator = ServerCommunicatorFake(
        certificate=self.server_certificate,
        private_key=self.server_private_key,
        token=self.token)

    self.server_communicator.client_cache.Put(
        self.client_cn, self.client)

  def tearDown(self):
    urllib2.urlopen = self.urlopen
    super(HTTPClientTests, self).tearDown()

  def CreateNewClientObject(self):
    self.client_communicator = comms.GRRHTTPClient(
        self.certificate, worker=comms.GRRClientWorker)

    # Disable stats collection for tests.
    self.client_communicator.client_worker.last_stats_sent_time = (
        time.time() + 3600)

    # Build a client context with preloaded server certificates
    self.client_communicator.communicator.LoadServerCertificate(
        self.server_certificate, config_lib.CONFIG["CA.certificate"])

  def UrlMock(self, req, **kwargs):
    """A mock for url handler processing from the server's POV."""
    _ = kwargs
    try:
      self.client_communication = rdfvalue.ClientCommunication(req.data)

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
      response_comms = rdfvalue.ClientCommunication()
      message_list = rdfvalue.MessageList()
      for i in range(0, 10):
        message_list.job.Append(session_id="aff4:/W:session", name="Echo",
                                response_id=2, request_id=i)

      # Preserve the timestamp as a nonce
      self.server_communicator.EncodeMessages(
          message_list, response_comms, destination=source,
          timestamp=ts, api_version=self.client_communication.api_version)

      return StringIO.StringIO(response_comms.SerializeToString())
    except communicator.RekeyError:
      raise urllib2.HTTPError(url=None, code=400, msg=None, hdrs=None, fp=None)
    except communicator.UnknownClientCert:
      raise urllib2.HTTPError(url=None, code=406, msg=None, hdrs=None, fp=None)
    except Exception as e:
      logging.info("Exception in mock urllib2.Open: %s.", e)
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
      self.assertEqual(message.GetWireFormat("source"), "GRR Test Server")
      self.assertEqual(message.response_id, 2)
      self.assertEqual(message.request_id, i)
      self.assertEqual(message.session_id, "aff4:/W:session")
      self.assertEqual(message.auth_state,
                       rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

    # Clear the queue
    self.client_communicator.client_worker._in_queue = []

  def SendToServer(self):
    """Schedule some packets from client to server."""
    # Generate some client traffic
    for i in range(0, 10):
      self.client_communicator.client_worker.SendReply(
          rdfvalue.GrrStatus(),
          session_id=rdfvalue.SessionID("W:session"),
          response_id=i, request_id=1)

  def testInitialEnrollment(self):
    """If the client has no certificate initially it should enroll."""

    # Clear the certificate so we can generate a new one.
    config_lib.CONFIG.Set("Client.private_key", None)
    self.CreateNewClientObject()

    # Client should get a new Common Name.
    self.assertNotEqual(self.client_cn,
                        self.client_communicator.communicator.common_name)

    self.client_cn = self.client_communicator.communicator.common_name

    # Now communicate with the server.
    status = self.client_communicator.RunOnce()

    self.assertEqual(status.code, 406)

    # The client should now send an enrollment request.
    status = self.client_communicator.RunOnce()

    # Client should generate enrollment message by itself.
    self.assertEqual(len(self.messages), 1)
    self.assertEqual(self.messages[0].session_id,
                     rdfvalue.SessionID("aff4:/flows/CA:Enrol"))

  def testEnrollment(self):
    """Test the http response to unknown clients."""
    # We start off with the server not knowing about the client at all.
    self.server_communicator.client_cache.Flush()

    # Assume we do not know the client yet by clearing its certificate.
    self.client = aff4.FACTORY.Create(self.client_cn, "VFSGRRClient", mode="rw",
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
                     rdfvalue.GrrMessage.AuthorizationState.UNAUTHENTICATED)

    # The next request should be an enrolling request.
    status = self.client_communicator.RunOnce()

    self.assertEqual(len(self.messages), 11)
    self.assertEqual(self.messages[-1].session_id,
                     rdfvalue.SessionID("aff4:/flows/CA:Enrol"))

    # Now we manually run the enroll well known flow with the enrollment request
    # - in reality this will be run on the Enroller.
    # This will start a new flow for enrolling the client, sign the cert and
    # add it to the data store.
    flow_obj = aff4.Enroler(aff4.Enroler.well_known_session_id, mode="rw",
                            token=self.token)
    flow_obj.ProcessMessage(self.messages[-1])

    # The next client communication should be enrolled now.
    status = self.client_communicator.RunOnce()

    self.assertEqual(status.code, 200)

    # There should be a cert for the client right now.
    self.client = aff4.FACTORY.Create(self.client_cn, "VFSGRRClient", mode="rw",
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
    self.server_communicator.client_cache.Put(
        self.client_cn, self.client)

    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

  def testCachedRSAOperations(self):
    """Make sure that expensive RSA operations are cached."""
    # First time fill the cache.
    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

    metric_value = stats.STATS.GetMetricValue("grr_rsa_operations")
    self.assert_(metric_value > 0)

    for _ in range(100):
      self.SendToServer()
      self.client_communicator.RunOnce()
      self.CheckClientQueue()

    # There should not have been any expensive operations any more
    self.assertEqual(stats.STATS.GetMetricValue("grr_rsa_operations"),
                     metric_value)

  def testCorruption(self):
    """Simulate corruption of the http payload."""

    def Corruptor(req):
      """Futz with some of the fields."""
      self.client_communication = rdfvalue.ClientCommunication()
      self.client_communication.ParseFromString(req.data)

      cipher_text = self.client_communication.encrypted_cipher
      cipher_text = (cipher_text[:10] +
                     chr((ord(cipher_text[10]) % 250)+1) +
                     cipher_text[11:])

      self.client_communication.encrypted_cipher = cipher_text
      req.data = self.client_communication.SerializeToString()
      return self.UrlMock(req)

    old_urlopen = urllib2.urlopen
    try:
      urllib2.urlopen = Corruptor

      self.SendToServer()
      status = self.client_communicator.RunOnce()
      self.assertEqual(status.code, 500)
    finally:
      urllib2.urlopen = old_urlopen

  def testClientRetransmission(self):
    """Test that client retransmits failed messages."""

    fail = True

    def FlakyServer(req):
      if not fail:
        return self.UrlMock(req)
      raise urllib2.HTTPError(url=None, code=500, msg=None, hdrs=None, fp=None)

    urllib2.urlopen = FlakyServer

    self.SendToServer()
    status = self.client_communicator.RunOnce()
    self.assertEqual(status.code, 500)

    # Server should not receive anything.
    self.assertEqual(len(self.messages), 0)

    # Try to send these messages again.
    fail = False

    status = self.client_communicator.RunOnce()

    self.assertEqual(status.code, 200)
    self.CheckClientQueue()

    # Server should have received 10 messages this time.
    self.assertEqual(len(self.messages), 10)

  def testClientStatsCollection(self):
    """Tests that the client stats are collected automatically."""

    now = 1000000
    # Pretend we have already sent stats.
    self.client_communicator.client_worker.last_stats_sent_time = now

    self.mox = mox.Mox()
    self.mox.StubOutWithMock(logging, "info")
    self.mox.StubOutWithMock(time, "time")

    try:
      # No calls to logging here.
      time.time().AndReturn(now)
      self.mox.ReplayAll()
      self.client_communicator.client_worker.CheckStats()

    finally:
      self.mox.UnsetStubs()
      self.mox.VerifyAll()

    # Creating responses calls time.time() so we mock the action out.
    action_cls = actions.ActionPlugin.classes.get("GetClientStatsAuto")
    old_run = action_cls.Run
    action_cls.Run = lambda cls, _: True
    self.mox.StubOutWithMock(logging, "info")
    self.mox.StubOutWithMock(time, "time")

    try:
      # No stats collection after 10 minutes.
      time.time().AndReturn(now + 600)
      # Let one hour pass.
      time.time().AndReturn(now + 3600)
      # This time the client should collect stats.
      logging.info("Sending back client statistics to the server.")
      # For setting the last time we need to replay another time() call.
      time.time().AndReturn(now + 3600)

      # The last call will be shortly after.
      time.time().AndReturn(now + 3600 + 600)
      # Again, there should be no stats collection and, thus, no logging either.

      self.mox.ReplayAll()

      self.client_communicator.client_worker.CheckStats()
      self.client_communicator.client_worker.CheckStats()
      self.client_communicator.client_worker.CheckStats()

    finally:
      self.mox.UnsetStubs()
      self.mox.VerifyAll()
      action_cls.Run = old_run

    # Disable stats collection again.
    self.client_communicator.client_worker.last_stats_sent_time = (
        time.time() + 3600)


class BackwardsCompatibleClientCommsTest(ClientCommsTest):
  """Test that we can talk using the old protocol still (version 2)."""

  def setUp(self):
    self.current_api = config_lib.CONFIG["Network.api"]
    config_lib.CONFIG.Set("Network.api", 2)
    super(BackwardsCompatibleClientCommsTest, self).setUp()


class BackwardsCompatibleHTTPClientTests(HTTPClientTests):
  """Test that we can talk using the old protocol still (version 2)."""

  def setUp(self):
    super(BackwardsCompatibleHTTPClientTests, self).setUp()
    config_lib.CONFIG.Set("Network.api", 2)

  def testCachedRSAOperations(self):
    """With the old protocol there should be many RSA operations."""
    # First time fill the cache.
    self.SendToServer()
    self.client_communicator.RunOnce()
    self.CheckClientQueue()

    metric_value = stats.STATS.GetMetricValue("grr_rsa_operations")
    self.assert_(metric_value > 0)

    for _ in range(5):
      self.SendToServer()
      self.client_communicator.RunOnce()
      self.CheckClientQueue()

    # There should be about 2 operations per loop iteration using the old
    # protocol (client and server must sign the message_list). Note that clients
    # actually running the old version will do 4 operations per loop since we
    # used to generate a new cipher protobuf for each packet as well. However,
    # currently, when running in compatibility mode we cache the same ciphers on
    # each end. The result is that the new code is still faster even when
    # running the old api.
    self.assertEqual(stats.STATS.GetMetricValue("grr_rsa_operations"),
                     metric_value + 10)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
