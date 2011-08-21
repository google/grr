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

"""This class handles the GRR Client Communication."""


import hashlib
import logging
import multiprocessing
import pdb
import posixpath
import sys
import time
import urllib
import urllib2

from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509

from grr.client import actions
from grr.client import client_config
from grr.client import conf
from grr.lib import communicator
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2

FLAGS = conf.PARSER.flags

conf.PARSER.add_option("-l", "--location",
                       default="http://grr-server/control.py",
                       help="URL of the controlling server.")

conf.PARSER.add_option("-m", "--max_post_size", default=800000, type="int",
                       help="Maximum size of the post.")

conf.PARSER.add_option("", "--max_out_queue", default=1024000, type="int",
                       help="Maximum size of the output queue.")

conf.DEFINE_integer("foreman_check_frequency", default=3600,
                    help="The minimum number of seconds before checking with "
                    "the foreman for new work.")

# Counters used here
stats.STATS.grr_client_sent_messages = 0
stats.STATS.grr_client_received_messages = 0
stats.STATS.grr_client_slave_restarts = 0


class Status(object):
  """An abstraction to encapsulates results of the HTTP Post."""
  # Number of messages received
  received_count = 0

  # Number of messages sent to server.
  sent_count = 0
  sent_len = 0

  # Server status code (200 is OK)
  code = 200

  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)


class GRRContext(object):
  """The main GRR Context.

  This provides access to the GRR framework to plugins and other code.
  """

  def __init__(self):
    """Create a new GRRContext."""
    # Queue of messages from the server to be processed.
    self._in_queue = []

    # Queue of messages to be sent to the server.
    self._out_queue = []

    # A tally of the total byte count of messages
    self._out_queue_size = 0

    self.certs_loaded = False

  def Drain(self, max_size=1024):
    """Return a GrrQueue message list from the queue, draining it.

    This is used to get the messages going _TO_ the server when the
    client connects.

    Args:
       max_size: The size of the returned protobuf will be at most one
       message length over this size.

    Returns:
       A MessageList protobuf
    """
    queue = jobs_pb2.MessageList()

    length = 0
    # Use implicit True/False evaluation instead of len (WTF)
    while self._out_queue and length < max_size:
      message = self._out_queue.pop(0)
      new_job = queue.job.add()
      new_job.MergeFromString(message)
      stats.STATS.grr_client_sent_messages += 1

      # Maintain the output queue tally
      length += len(message)
      self._out_queue_size -= len(message)

    return queue

  def SendReply(self, protobuf=None, request_id=None, response_id=None,
                session_id="W:0", message_type=None, jump_queue=False):
    """Send the protobuf to the server."""
    message = jobs_pb2.GrrMessage()
    if protobuf:
      message.args = protobuf.SerializeToString()

    message.session_id = session_id

    if response_id is not None:
      message.response_id = response_id

    if request_id is not None:
      message.request_id = request_id

    if message_type is None:
      message_type = jobs_pb2.GrrMessage.MESSAGE

    message.type = message_type

    serialized_message = message.SerializeToString()
    self.QueueResponse(serialized_message, jump_queue=jump_queue)

  def QueueResponse(self, serialized_message, jump_queue=False):
    """Push the Serialized Message on the output queue."""
    # Maintain the tally of the output queue size
    if jump_queue:
      self._out_queue.insert(0, serialized_message)
    else:
      self._out_queue.append(serialized_message)
    self._out_queue_size += len(serialized_message)

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.
    """
    # Only process if we're enrolled or this is an enrolment request.
    if self.certs_loaded or message.name == "SaveCert":
      action_cls = actions.ActionPlugin.classes.get(
          message.name, actions.ActionPlugin)
      action = action_cls(message=message, grr_context=self)
      action.Execute(message)
    else:
      logging.error("Cannot handle message %s, we're not enrolled yet.",
                    message.name)

  def QueueMessages(self, messages):
    """Queue a message from the server for processing.

    We maintain all the incoming messages in a queue. These messages
    are consumed until the outgoing queue fills to the allowable
    level. This mechanism allows us to throttle the server messages
    and limit the size of the outgoing queue on the client.

    Note that we can only limit processing of single request messages
    so if a single request message generates huge amounts of response
    messages we will still overflow the output queue. Therefore
    actions must be written in such a way that each request generates
    a limited and known maximum number and size of responses. (e.g. do
    not write a single client action to fetch the entire disk).

    Args:
      messages: List of parsed protobuf arriving from the server.
    """
    # Push all the messages to our input queue
    for message in messages:
      self._in_queue.append(message)
      stats.STATS.grr_client_received_messages += 1

    # As long as our output queue has some room we can process some
    # input messages:
    while self._in_queue and (
        self._out_queue_size < FLAGS.max_out_queue):
      message = self._in_queue.pop(0)

      try:
        self.HandleMessage(message)
        # Catch any errors and keep going here
      except Exception, e:
        logging.error("%s", e)
        self.SendReply(
            jobs_pb2.GrrStatus(
                status=jobs_pb2.GrrStatus.GENERIC_ERROR,
                error_message=str(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            message_type=jobs_pb2.GrrMessage.STATUS)
        if FLAGS.debug:
          pdb.post_mortem()

  def InQueueSize(self):
    """Returns the number of protobufs ready to be sent in the queue."""
    return len(self._in_queue)


class GRRHTTPContext(GRRContext):
  """A class which abstracts away HTTP communications.

  To create a new GRR HTTP client, intantiate this class and generate
  its Run() method.
  """

  def __init__(self, ca_cert=None):
    """Constructor.

    Args:
      ca_cert: String representation of a CA certificate to use for checking
          server certificate.

    """
    self.ca_cert = ca_cert
    self.communicator = None

    # The time we last checked with the foreman.
    self.last_foreman_check = 0
    GRRContext.__init__(self)

  def GetServerCert(self):
    """Obtain the server certificate and initialize the client."""
    cert_url = "/".join((posixpath.dirname(FLAGS.location), "server.pem"))
    try:
      handle = urllib2.urlopen(cert_url)
      data = handle.read()

      self.communicator.LoadServerCertificate(
          server_certificate=data, ca_certificate=self.ca_cert)
      return

    # This has to succeed or we can not go on
    except Exception, e:
      logging.error("Unable to verify server certificate at %s: %s",
                    cert_url, e)
      # Try again in a short time
      time.sleep(60)

  def MakeRequest(self, data, status):
    """Make a HTTP Post request and return the raw results."""
    request = dict(data=data.encode("base64"),
                   api=client_config.NETWORK_API)

    status.sent_len = len(request["data"])
    start = time.time()
    try:
      ## Now send the request using POST
      url = urllib.urlencode(request)
      handle = urllib2.urlopen(FLAGS.location, url)
      data = handle.read()
      logging.debug("Request took %s Seconds", time.time() - start)

      return data
    except urllib2.HTTPError, e:
      status.code = e.code
      # Server can not talk with us - re-enroll.
      if e.code == 406:
        self.InitiateEnrolment()

    except urllib2.URLError, e:
      status.code = 500

    # Error path:
    status.sent_count = 0
    return ""

  def RunOnce(self):
    """Makes a single request to the GRR server.

    Returns:
      A Status() object indicating how the last POST went.
    """
    try:
      # Grab some messages to send
      message_list = self.Drain(max_size=FLAGS.max_post_size)

      status = Status(sent_count=len(message_list.job))

      # Make new encrypted ClientCommunication protobuf
      payload = jobs_pb2.ClientCommunication()

      # Let the server know how many messages are currently queued in
      # the input queue
      payload.queue_size = self.InQueueSize()

      nonce = self.communicator.EncodeMessages(
          message_list, payload)

      response = self.MakeRequest(payload.SerializeToString(), status)

      if status.code != 200:
        logging.info("Could not connect to server at %s, status %s.",
                     FLAGS.location, status.code)
        return status

      if not response:
        if self.certs_loaded:     # Normal error if enrolling.
          logging.info("No data returned from server at %s", FLAGS.location)
        return status

      try:
        tmp = self.communicator.DecryptMessage(response)
        (messages, source, server_nonce) = tmp

        if server_nonce != nonce:
          logging.info("Nonce not matched.")
          status.code = 500
          return status

      except jobs_pb2.message.DecodeError:
        logging.info("Protobuf decode error. Bad URL or auth.")
        status.code = 500
        return status

      if source != self.communicator.server_name:
        logging.info("Received a message not from the server "
                     "%s, expected %s.", source,
                     self.communicator.server_name)
        status.code = 500
        return status

      status.received_count = len(messages)

      # Process all messages. Messages can be processed by clients in
      # any order since clients do not have state.
      self.QueueMessages(messages)

    except Exception, e:
      # Catch everything, yes, this is terrible but necessary
      logging.error("Uncaught exception caught. %s: %s",
                    sys.exc_info()[0], e)
      status.code = 500
      if FLAGS.debug:
        pdb.post_mortem()

    return status

  def Run(self):
    """A Generator which makes a single request to the GRR server.

    Callers should generate this when they wish to make a connection
    to the server. It is up to the caller to sleep between calls in
    order to enforce the required network and CPU utilization
    policies.

    Yields:
      A Status() object indicating how the last POST went.
    """
    while True:
      while self.communicator.server_name is None:
        self.GetServerCert()
        yield Status()

      now = time.time()
      # Check with the foreman if we need to
      if now > self.last_foreman_check + FLAGS.foreman_check_frequency:
        self.SendReply(jobs_pb2.DataBlob(), session_id="W:Foreman")
        self.last_foreman_check = now

      status = self.RunOnce()
      yield status

  def LoadCertificates(self):
    """Reload our certificates and reset our client name."""
    # Find out our client name
    try:
      self.communicator = ClientCommunicator(certificate=FLAGS.certificate)
      self.certs_loaded = True
      logging.info("Starting client %s", self.communicator.common_name)
    except (IOError, RSA.RSAError, X509.X509Error), err:
      if FLAGS.certificate:
        logging.warn("Cert exists but loading failed. Re-enrolling: %s", err)
      else:
        logging.info("Starting Enrolment")

      self.InitiateEnrolment()
      logging.info("Client pending enrolment %s", self.communicator.common_name)

  def InitiateEnrolment(self):
    """Initiate the enrolment.

    After this function we will have valid keys which we can use.
    """
    if not isinstance(self.communicator, EnrollingCommunicator):
      # Choose our enrolling communicator which will make new keys:
      self.communicator = EnrollingCommunicator(
          certificate=FLAGS.certificate,
          )

      # Send registration request:
      self.SendReply(
          jobs_pb2.Certificate(
              type=jobs_pb2.Certificate.CSR,
              pem=self.communicator.GetCSR()
              ),
          session_id="CA:Enrol")

  def StoreCert(self, cert):
    """Append the certificate received from the server to the cert store."""
    FLAGS.certificate += cert
    conf.PARSER.UpdateConfig(["certificate"])


class PoolGRRHTTPContext(GRRHTTPContext):
  """A class which abstracts away HTTP communications.

  The pool version uses the pool enroller to support multiple clients
  on a machine at the same time.
  """

  def __init__(self, cert_storage, storage_id, ca_cert=None):
    """Constructor.

    Args:
      cert_storage: A list that stores all client certificates.
      storage_id: The index in cert_storage reserved for this client.
      ca_cert: String representation of a CA certificate to use for checking
          server certificate.

    """
    self.cert_storage = cert_storage
    self.storage_id = storage_id

    GRRHTTPContext.__init__(self, ca_cert)

  def LoadCertificates(self):
    """Reload our certificates and reset our client name."""
    # Find out our client name
    try:
      self.communicator = ClientCommunicator(self.cert_storage[self.storage_id])
      self.certs_loaded = True
      logging.info("Starting client %s", self.communicator.common_name)
    except (IOError, RSA.RSAError, X509.X509Error), err:
      if self.cert_storage[self.storage_id]:
        logging.warn("Cert exists but loading failed. Re-enrolling: %s", err)
      else:
        logging.info("Starting Enrolment")

      self.InitiateEnrolment()
      logging.info("Client pending enrolment %s", self.communicator.common_name)

  def InitiateEnrolment(self):
    """Initiate the enrolment.

    After this function we will have valid keys which we can use.
    """
    if not isinstance(self.communicator, PoolEnrollingCommunicator):
      # Choose our enrolling communicator which will make new keys:
      self.communicator = PoolEnrollingCommunicator(self.cert_storage,
                                                    self.storage_id)

      # Send registration request:
      self.SendReply(
          jobs_pb2.Certificate(
              type=jobs_pb2.Certificate.CSR,
              pem=self.communicator.GetCSR()
              ),
          session_id="CA:Enrol")

  def StoreCert(self, cert):
    """Append the certificate received from the server to the cert store."""
    self.cert_storage[self.storage_id] += cert


# The following GRRContext implementations implement process separation -
# Communications are done by the master process and a slave process is spawned
# to actually satisfy requests. The advantage of this scheme is reliability - if
# the slave crashes we simply send back an error and restart the
# slave.

# TODO(user): Implement process memory limits to combat potential memory
# leaks in the slave.


class SlaveContext(GRRContext, multiprocessing.Process):
  """All work is actually done in this worker."""

  def __init__(self, pipe):
    self.pipe = pipe
    GRRContext.__init__(self)
    multiprocessing.Process.__init__(self)

  def run(self):
    """Start processing."""
    while True:
      try:
        incoming = self.pipe.recv()
        message = jobs_pb2.GrrMessage()
        message.ParseFromString(incoming)

        # Run the request
        self.HandleMessage(message)
      except Exception, e:
        logging.error("Uncaught exception caught in slave. %s: %s",
                      sys.exc_info()[0], e)
        raise

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.
    """
    action_cls = actions.ActionPlugin.classes[message.name]
    action = action_cls(message=message, grr_context=self)
    action.Execute(message)

  def QueueResponse(self, serialized_message, jump_queue=False):
    """Push the response to the our out queue."""
    self.pipe.send(serialized_message)


class ProcessSeparatedContext(GRRHTTPContext):
  """A special GRR Context which runs the worker in a separate process."""

  PARENT_ONLY_MESSAGES = ["Kill", "Uninstall", "SaveCert"]

  def __init__(self, ca_cert=None):
    """Constructor.

    Args:
      ca_cert: String representation of a CA certificate to use for checking
          server certificate.
    """
    GRRHTTPContext.__init__(self, ca_cert=ca_cert)
    logging.info("Initiating process separation.")
    self.MakeSlave()

  def MakeSlave(self):
    """Create a new slave to execute requests in."""
    # Bidirectional pipe
    self.pipe, slave_pipe = multiprocessing.Pipe()
    self.slave = SlaveContext(slave_pipe)
    self.slave.start()

  def HandleMessageInParent(self, message):
    """Handle a message in the parent context."""
    logging.info("Handling %s message in the parent context.", message.name)
    GRRContext.HandleMessage(self, message)

  def HandleMessage(self, message):
    """Pass the message to the slave and wait for responses."""
    # If the slave has died restart it.
    if not self.slave.is_alive():
      logging.error("Slave died - restarting")
      self.MakeSlave()

    # Handle special messages that cannot be sent to the child.
    if message.name in self.PARENT_ONLY_MESSAGES:
      self.HandleMessageInParent(message)
      return

    self.pipe.send(message.SerializeToString())

    # We block here until the slave has _some_ responses. The actual responses
    # are drained with Drain(). We may not retrieve all the responses here as we
    # unblock as soon as some responses are available. In practice this is not a
    # problem as the next call to Drain() will occur when we are ready to make
    # another POST - i.e. a fairly long time after issuing the requests.
    while not self.pipe.poll():
      if not self.slave.is_alive():
        # Oops - whatever we did here caused the slave to crash
        stats.STATS.grr_client_slave_restarts += 1
        self.slave.SendReply(
            jobs_pb2.GrrStatus(
                status=jobs_pb2.GrrStatus.GENERIC_ERROR,
                error_message="Slave crashed"),
            request_id=message.request_id,
            session_id=message.session_id,
            message_type=jobs_pb2.GrrMessage.STATUS)
      else:
        time.sleep(0.5)

  def Drain(self, max_size=1024):
    """Drain the input queue from messages."""

    # Drain from the primary queue running in the parent context.
    queue = GRRHTTPContext.Drain(self, max_size)

    # Now we drain all the messages we can from our slave.
    length = 0
    while self.pipe.poll() and length < max_size:
      serialized_message = self.pipe.recv()
      new_response = queue.job.add()
      new_response.MergeFromString(serialized_message)

      length += len(serialized_message)
      self._out_queue_size -= len(serialized_message)

    return queue

  def Terminate(self):
    """Kill the slave gently."""
    # Push a kill request to the slave
    message = jobs_pb2.GrrMessage(
        name="KillSlave",
        auth_state=jobs_pb2.GrrMessage.AUTHENTICATED,
        request_id=1)

    # Wait for it to die
    self.pipe.send(message.SerializeToString())
    self.slave.join()


class ClientCommunicator(communicator.Communicator):
  """A communicator implementation for clients.

    This extends the generic communicator to include verification of
    server side certificates.
  """

  def LoadServerCertificate(self, server_certificate=None,
                            ca_certificate=None):
    """Loads and verifies the server certificate."""
    try:
      server_cert = X509.load_cert_string(server_certificate)
      ca_cert = X509.load_cert_string(ca_certificate)

      # Check that the server certificate verifies
      if server_cert.verify(ca_cert.get_pubkey()) == 0:
        self.server_name = None
        raise IOError("Server cert is invalid.")

      # Make sure that the serial number is higher.
      server_cert_serial = server_cert.get_serial_number()
      if server_cert_serial < FLAGS.server_serial_number:
        # We can not accept this serial number...
        raise IOError("Server cert is too old.")
      elif server_cert_serial > FLAGS.server_serial_number:
        logging.info("Server serial number updated to %s", server_cert_serial)
        FLAGS.server_serial_number = server_cert_serial
        try:
          conf.PARSER.UpdateConfig(["server_serial_number"])
        except IOError: pass

    except X509.X509Error:
      raise IOError("Server cert is invalid.")

    self.server_name = self._GetCNFromCert(server_cert)

    # We need to store the serialised verion of the public key due
    # to M2Crypto memory referencing bugs
    pub_key = server_cert.get_pubkey().get_rsa()
    bio = BIO.MemoryBuffer()
    pub_key.save_pub_key_bio(bio)

    self.pub_key_cache.Put(self.server_name, bio.read_all())


class EnrollingCommunicator(ClientCommunicator):
  """A communicator created when no new certs exist.

  This communicators creates new keys and can be used to enroll for a
  new certificate.

  After enrolment the certificate will be written by calling
  conf.PARSER.UpdateConfig() which will write the cert to registry/ini file.
  """
  BITS = 1024

  def _LoadOurCertificate(self, certificate):
    """Make new keys and a CSR."""
    try:
      # This is our private key - make sure it has no password set.
      rsa = RSA.load_key_string(certificate, callback=lambda x: "")
    except (X509.X509Error, RSA.RSAError):
      # 65537 is the standard value for e
      rsa = RSA.gen_key(self.BITS, 65537, lambda: None)

    # Make new keys
    pk = EVP.PKey()
    csr = X509.Request()

    pk.assign_rsa(rsa)

    csr.set_pubkey(pk)
    name = csr.get_subject()

    # Our CN will be the first 64 bits of the hash of the public key.
    public_key = rsa.pub()[1]
    self.common_name = "C.%s" % (
        hashlib.sha256(public_key).digest()[:8].encode("hex"))

    name.CN = self.common_name

    # Save the keys
    self.SavePrivateKey(pk)
    self.csr = csr.as_pem()

  def GetCSR(self):
    """Return our CSR in pem format."""
    return self.csr

  def SavePrivateKey(self, pkey):
    """Store the new private key on disk."""
    bio = BIO.MemoryBuffer()
    pkey.save_key_bio(bio, cipher=None)

    self.private_key = bio.read_all()

    FLAGS.certificate = self.private_key
    conf.PARSER.UpdateConfig(["certificate"])


class PoolEnrollingCommunicator(EnrollingCommunicator):
  """A enrolling communicator that saves the keys in a separate file."""

  def __init__(self, cert_storage, storage_id):
    """Creates a communicator."""
    self.pub_key_cache = utils.FastStore(100)
    self.cert_storage = cert_storage
    self.storage_id = storage_id
    self._LoadOurCertificate(self.cert_storage[self.storage_id])

  def SavePrivateKey(self, pkey):
    """Store the new private key in the cert storage."""
    bio = BIO.MemoryBuffer()
    pkey.save_key_bio(bio, cipher=None)

    self.private_key = bio.read_all()

    self.cert_storage[self.storage_id] = self.private_key
