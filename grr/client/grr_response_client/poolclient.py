#!/usr/bin/env python
"""This is the GRR client for thread pools."""

import base64
import logging
import threading
import time

from absl import app
from absl import flags

# pylint: disable=unused-import
# Make sure we load the client plugins
from grr_response_client import client_plugins
# pylint: enable=unused-import

from grr_response_client import client_startup
from grr_response_client import comms
from grr_response_client import vfs
from grr_response_client.vfs_handlers import files as vfs_files
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths

_NRCLIENTS = flags.DEFINE_integer("nrclients", 1, "Number of clients to start")

_CERT_FILE = flags.DEFINE_string(
    "cert_file", "", "Path to a file that stores all certificates for"
    "the client pool.")

_ENROLL_ONLY = flags.DEFINE_bool(
    "enroll_only", False,
    "If specified, the script will enroll all clients and exit.")

_FAST_POLL = flags.DEFINE_bool(
    "fast_poll", False,
    "If specified, every client in the pool will work in the "
    "fast poll mode. This is useful for benchmarks, as in fast "
    "poll mode the timeouts are predictable and benchmarks "
    "results are more stable.")

_SEND_FOREMAN_REQUEST = flags.DEFINE_bool(
    "send_foreman_request", False,
    "If specified, every client will send a foreman poll request "
    "right after startup. Useful for testing hunts.")


class PoolGRRClient(threading.Thread):
  """A GRR client for running in pool mode."""

  def __init__(self,
               ca_cert=None,
               private_key=None,
               fast_poll=False,
               send_foreman_request=False):
    """Constructor."""
    super().__init__()
    self.private_key = private_key
    self.daemon = True

    self.client = comms.GRRHTTPClient(ca_cert=ca_cert, private_key=private_key)
    if fast_poll:
      self.client.timer.FastPoll()

    if send_foreman_request:
      self.client.SendForemanRequest()

    self.stop = False
    # Is this client already enrolled?
    self.enrolled = False

  def Run(self):
    while not self.stop:
      status = self.client.RunOnce()
      if status.code == 200:
        self.enrolled = True
      self.client.timer.Wait()

  def Stop(self):
    self.stop = True

  def run(self):
    self.Run()


def CreateClientPool(n):
  """Create n clients to run in a pool."""
  clients = []

  # Load previously stored clients.
  try:
    certificates = []
    with open(_CERT_FILE.value, "rb") as fd:
      # Certificates are base64-encoded, so that we can use new-lines as
      # separators.
      for l in fd:
        cert = rdf_crypto.RSAPrivateKey(initializer=base64.b64decode(l))
        certificates.append(cert)

    for certificate in certificates[:n]:
      clients.append(
          PoolGRRClient(
              private_key=certificate,
              ca_cert=config.CONFIG["CA.certificate"],
              fast_poll=_FAST_POLL.value,
              send_foreman_request=_SEND_FOREMAN_REQUEST.value,
          ))

    clients_loaded = True
  except (IOError, EOFError):
    clients_loaded = False

  if clients_loaded and len(clients) < n:
    raise RuntimeError(
        "Loaded %d clients, but expected %d." % (len(clients), n))

  while len(clients) < n:
    # Generate a new RSA key pair for each client.
    bits = config.CONFIG["Client.rsa_key_length"]
    key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=bits)
    clients.append(
        PoolGRRClient(private_key=key, ca_cert=config.CONFIG["CA.certificate"]))

  # Start all the clients now.
  for c in clients:
    c.start()

  start_time = rdfvalue.RDFDatetime.Now()
  try:
    if _ENROLL_ONLY.value:
      while True:
        time.sleep(1)
        enrolled = len([x for x in clients if x.enrolled])

        if enrolled == n:
          logging.info("All clients enrolled, exiting.")
          break

        else:
          logging.info("%s: Enrolled %d/%d clients.", int(time.time()),
                       enrolled, n)
    else:
      try:
        while True:
          time.sleep(100)
      except KeyboardInterrupt:
        pass

  finally:
    # Stop all pool clients.
    for cl in clients:
      cl.Stop()

  # Note: code below is going to be executed after SIGTERM is sent to this
  # process.
  duration = rdfvalue.RDFDatetime.Now() - start_time
  logging.info("Pool done in %s seconds.",
               duration.ToFractional(rdfvalue.SECONDS))

  # The way benchmarking is supposed to work is that we execute poolclient with
  # --enroll_only flag, it dumps the certificates to the flags.FLAGS.cert_file.
  # Then, all further poolclient invocations just read private keys back
  # from that file. Therefore if private keys were loaded from
  # flags.FLAGS.cert_file, then there's no need to rewrite it again with the
  # same data.
  if not clients_loaded:
    logging.info("Saving certificates.")
    with open(_CERT_FILE.value, "wb") as fd:
      # We're base64-encoding ceritificates so that we can use new-lines
      # as separators.
      b64_certs = [
          base64.b64encode(x.private_key.SerializeToBytes()) for x in clients
      ]
      fd.write("\n".join(b64_certs))


def CheckLocation():
  """Checks that the poolclient is not accidentally ran against production."""
  for url in (config.CONFIG["Client.server_urls"] +
              config.CONFIG["Client.control_urls"]):
    if "staging" in url or "localhost" in url:
      # This is ok.
      return
  logging.error("Poolclient should only be run against test or staging.")
  exit()


class _UseOSForTSKFile(vfs_files.File):
  """OS-file handler to be used for TSK files, since TSK is not threadsafe."""
  supported_pathtype = rdf_paths.PathSpec.PathType.TSK


def main(argv):
  del argv  # Unused.
  config.CONFIG.AddContext(contexts.POOL_CLIENT_CONTEXT,
                           "Context applied when we run the pool client.")

  client_startup.ClientInit()

  config.CONFIG.SetWriteBack("/dev/null")

  CheckLocation()

  # Let the OS handler also handle sleuthkit requests since sleuthkit is not
  # thread safe.
  vfs.VFS_HANDLERS[_UseOSForTSKFile.supported_pathtype] = _UseOSForTSKFile

  CreateClientPool(_NRCLIENTS.value)


if __name__ == "__main__":
  app.run(main)
