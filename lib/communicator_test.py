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

"""Test for client."""


from hashlib import sha256
import os


from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf
from grr.client import conf as flags

from grr.client import client_config
from grr.client import comms
from grr.client import conf
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import flow
from grr.lib import test_lib
from grr.proto import jobs_pb2

FLAGS = flags.FLAGS


class ServerCommunicatorFake(flow.ServerCommunicator):
  """A fake communicator to initialize the ServerCommunicator."""

  # For tests we bypass the keystore.
  def _LoadOurCertificate(self, certificate):
    return communicator.Communicator._LoadOurCertificate(
        self, certificate)


class ClientCommsTest(test_lib.GRRBaseTest):
  """Test the communicator."""

  def setUp(self):
    """Set up communicator tests."""
    test_lib.GRRBaseTest.setUp(self)

    self.options = conf.PARSER.flags
    self.options.certificate = open(os.path.join(self.key_path,
                                                 "cert.pem")).read()
    self.options.server_serial_number = 0
    self.options.config = os.path.join(FLAGS.test_tmpdir, "testconf")
    self.server_certificate = open(
        os.path.join(self.key_path, "server-priv.pem")).read()

    self.client_communicator = comms.ClientCommunicator(
        self.options.certificate)

    self.client_communicator.LoadServerCertificate(
        self.server_certificate,
        client_config.CACERTS["TEST"])

    self.server_communicator = ServerCommunicatorFake(
        self.server_certificate)

  def ClientServerCommunicate(self, timestamp=None):
    """Tests the end to end encrypted communicators."""
    message_list = jobs_pb2.MessageList()
    for i in range(0, 10):
      message_list.job.add(session_id=str(i), name="OMG it's a string")

    result = jobs_pb2.ClientCommunication()
    timestamp = self.client_communicator.EncodeMessages(message_list, result,
                                                        timestamp=timestamp)
    self.cipher_text = result.SerializeToString()

    # Line too long:
    _ = self.server_communicator.DecryptMessage(self.cipher_text)
    (decoded_messages, source, client_timestamp) = _

    self.assertEqual(source, self.client_communicator.common_name)
    self.assertEqual(client_timestamp, timestamp)
    self.assertEqual(len(decoded_messages), 10)
    for i in range(0, 10):
      self.assertEqual(decoded_messages[i].session_id, str(i))

    return decoded_messages

  def testCommunications(self):
    """Test that messages from unknown clients are tagged unauthenticated."""
    decoded_messages = self.ClientServerCommunicate()
    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       jobs_pb2.GrrMessage.UNAUTHENTICATED)

  def MakeClientAFF4Record(self):
    """Make a client in the data store."""
    client_cert = aff4.FACTORY.RDFValue("RDFX509Cert")(
        self.options.certificate)
    client = aff4.FACTORY.Create(client_cert.common_name, "VFSGRRClient")
    client.Set(client.Schema.CERT, client_cert)
    client.Close()

  def testKnownClient(self):
    """Test that messages from known clients are authenticated."""
    self.MakeClientAFF4Record()
    # Now the server should know about it
    decoded_messages = self.ClientServerCommunicate()

    for i in range(len(decoded_messages)):
      self.assertEqual(decoded_messages[i].auth_state,
                       jobs_pb2.GrrMessage.AUTHENTICATED)

  def testServerReplayAttack(self):
    """Test that replaying encrypted messages to the server invalidates them."""
    self.MakeClientAFF4Record()

    # First send some messages to the server
    decoded_messages = self.ClientServerCommunicate()

    self.assertEqual(decoded_messages[0].auth_state,
                     jobs_pb2.GrrMessage.AUTHENTICATED)

    # Now replay the last message to the server
    (decoded_messages, _, _) = self.server_communicator.DecryptMessage(
        self.cipher_text)

    # Messages should now be tagged as desynced
    self.assertEqual(decoded_messages[0].auth_state,
                     jobs_pb2.GrrMessage.DESYNCHRONIZED)

  def testCompression(self):
    """Tests that the compression works."""
    FLAGS.compression = "UNCOMPRESSED"
    self.testCommunications()
    uncompressed_len = len(self.cipher_text)

    # If the client compresses, the server should still be able to
    # parse it:
    FLAGS.compression = "ZCOMPRESS"
    self.testCommunications()
    compressed_len = len(self.cipher_text)

    self.assert_(compressed_len < uncompressed_len)

    # If we chose a crazy compression scheme, the client should not
    # compress.
    FLAGS.compression = "SOMECRAZYCOMPRESSION"
    self.testCommunications()
    compressed_len = len(self.cipher_text)

    self.assertEqual(compressed_len, uncompressed_len)

  def testErrorDetection(self):
    """Tests the end to end encrypted communicators."""
    # Install the client - now we can verify its signed messages
    self.MakeClientAFF4Record()

    # Make something to send
    message_list = jobs_pb2.MessageList()
    for i in range(0, 10):
      message_list.job.add(session_id=str(i))

    result = jobs_pb2.ClientCommunication()
    self.client_communicator.EncodeMessages(message_list, result)
    cipher_text = result.SerializeToString()

    # Futz with the cipher text (Make sure it's really changed)
    cipher_text = (cipher_text[:100] +
                   chr((ord(cipher_text[100]) % 250)+1) +
                   cipher_text[101:])

    # This signature should not match
    self.assertRaises(
        RSA.RSAError,
        self.server_communicator.DecryptMessage,
        cipher_text)

  def testEnrollingCommunicatorWorks(self):
    """Test that the EnrollingCommunicator still works."""
    self.client_communicator = comms.EnrollingCommunicator(
        certificate="")

    self.client_communicator.LoadServerCertificate(
        self.server_certificate,
        client_config.CACERTS["TEST"])

    self.testCommunications()

  def testEnrollingCommunicator(self):
    """Test that the EnrollingCommunicator generates good keys."""
    self.client_communicator = comms.EnrollingCommunicator(
        certificate="")

    self.client_communicator.LoadServerCertificate(
        self.server_certificate,
        client_config.CACERTS["TEST"])

    req = X509.load_request_string(self.client_communicator.GetCSR())

    # Verify that the CN is of the correct form
    public_key = req.get_pubkey().get_rsa().pub()[1]
    cn = "C.%s" % (
        sha256(public_key).digest()[:8].encode("hex"))
    self.assertEqual(cn, req.get_subject().CN)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
