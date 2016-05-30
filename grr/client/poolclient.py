#!/usr/bin/env python
"""This is the GRR client for thread pools."""


import pickle
import threading
import time


import logging

# pylint: disable=unused-import
# Make sure we load the client plugins
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.client import comms
from grr.client import vfs
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths

flags.DEFINE_integer("nrclients", 1, "Number of clients to start")

flags.DEFINE_string("cert_file", "",
                    "Path to a file that stores all certificates for"
                    "the client pool.")

flags.DEFINE_bool("enroll_only", False,
                  "If specified, the script will enroll all clients and exit.")


class PoolGRRClient(threading.Thread):
  """A GRR client for running in pool mode."""

  def __init__(self, ca_cert=None, private_key=None):
    """Constructor."""
    super(PoolGRRClient, self).__init__()
    self.private_key = private_key
    self.daemon = True

    self.client = comms.GRRHTTPClient(ca_cert=ca_cert, private_key=private_key)
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
    fd = open(flags.FLAGS.cert_file, "rb")
    certificates = pickle.load(fd)
    fd.close()

    for certificate in certificates:
      clients.append(PoolGRRClient(private_key=certificate,
                                   ca_cert=config_lib.CONFIG["CA.certificate"]))

    clients_loaded = True
  except (IOError, EOFError):
    clients_loaded = False

  if clients_loaded and len(clients) < n:
    raise RuntimeError("Loaded %d clients, but expected %d." %
                       (len(clients), n))

  while len(clients) < n:
    # Generate a new RSA key pair for each client.
    bits = config_lib.CONFIG["Client.rsa_key_length"]
    key = rdf_crypto.PEMPrivateKey.GenKey(bits=bits)
    clients.append(PoolGRRClient(private_key=key,
                                 ca_cert=config_lib.CONFIG["CA.certificate"]))

  # Start all the clients now.
  for c in clients:
    c.start()

  start_time = time.time()
  try:
    if flags.FLAGS.enroll_only:
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
  logging.info("Pool done in %s seconds.", time.time() - start_time)

  # The way benchmarking is supposed to work is that we execute poolclient with
  # --enroll_only flag, it dumps the certificates to the flags.FLAGS.cert_file.
  # Then, all further poolclient invocations just read private keys back
  # from that file. Therefore if private keys were loaded from
  # flags.FLAGS.cert_file, then there's no need to rewrite it again with the
  # same data.
  if not clients_loaded:
    logging.info("Saving certificates.")
    with open(flags.FLAGS.cert_file, "wb") as fd:
      pickle.dump([x.private_key for x in clients], fd)


def CheckLocation():
  """Checks that the poolclient is not accidentally ran against production."""
  for url in (config_lib.CONFIG["Client.server_urls"] +
              config_lib.CONFIG["Client.control_urls"]):
    if "staging" in url or "localhost" in url:
      # This is ok.
      return
  logging.error("Poolclient should only be run against test or staging.")
  exit()


def main(unused_argv):
  config_lib.CONFIG.AddContext("PoolClient Context",
                               "Context applied when we run the pool client.")

  startup.ClientInit()

  config_lib.CONFIG.SetWriteBack("/dev/null")

  CheckLocation()

  # Let the OS handler also handle sleuthkit requests since sleuthkit is not
  # thread safe.
  tsk = rdf_paths.PathSpec.PathType.TSK
  os = rdf_paths.PathSpec.PathType.OS
  vfs.VFS_HANDLERS[tsk] = vfs.VFS_HANDLERS[os]

  CreateClientPool(flags.FLAGS.nrclients)


if __name__ == "__main__":
  flags.StartMain(main)
