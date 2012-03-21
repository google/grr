#!/usr/bin/env python

# Copyright 2011 Google Inc.
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


"""This is the GRR client for thread pools."""


import logging
import multiprocessing
import pickle
import threading
import time


from grr.client import conf
from grr.client import conf as flags

from grr.client import client

# Make sure we load the client plugins
from grr.client import client_actions

from grr.client import client_config
from grr.client import comms
from grr.client import conf
from grr.lib import registry

flags.DEFINE_integer("nrclients", 1,
                     "Number of clients to start")

flags.DEFINE_string("cert_file", "",
                    "Path to a file that stores all certificates for"
                    "the client pool.")

flags.DEFINE_bool("enroll_only", False,
                  "If specified, the script will enroll all clients and exit.")

FLAGS = flags.FLAGS


class PoolGRRClient(client.GRRClient, threading.Thread):
  """A GRR client for running in pool mode."""

  def __init__(self, cert_storage, storage_id):
    """Constructor."""
    threading.Thread.__init__(self)
    self.daemon = True

    ca_cert = client_config.CACERTS.get(FLAGS.camode.upper())
    if not ca_cert:
      raise RuntimeError("Invalid camode specified.")

    self.context = comms.PoolGRRHTTPContext(cert_storage, storage_id, ca_cert)

    self.context.LoadCertificates()

    # Start off with a maximum poling interval
    self.sleep_time = FLAGS.poll_max

  def Stop(self):
    self.stop = True

  def run(self):
    self.Run()


def CreateClientPool(n):
  """Create n clients to run in a pool."""
  cert_storage = []
  clients = []

  try:
    fd = open(FLAGS.cert_file, "rb")
    cert_storage = pickle.load(fd)
    fd.close()
  except (IOError, EOFError):
    pass

  if len(cert_storage) < n:
    cert_storage.extend([None] * (n - len(cert_storage)))

  for i in range(n):
    cl = PoolGRRClient(cert_storage, i)
    clients.append(cl)
    cl.start()

  if FLAGS.enroll_only:
    last_time = 0
    while True:
      time.sleep(1)
      enrolled = 0
      for certificate in cert_storage[:n]:
        if "----BEGIN CERTIFICATE----" in certificate:
          enrolled += 1

      if enrolled == n:
        logging.info("All clients enrolled, exiting.")
        break
      else:
        if enrolled != last_time:
          last_time = enrolled
          logging.info("Enrolled %d/%d clients.", enrolled, n)
  else:
    try:
      while True:
        time.sleep(100)
    except KeyboardInterrupt:
      pass

  for cl in clients:
    cl.Stop()

  logging.debug("Pool done, saving certs.")
  try:
    fd = open(FLAGS.cert_file, "wb")
    pickle.dump(cert_storage, fd)
    fd.close()
  except IOError:
    pass


def main(unused_argv):
  # Ensure multiprocesses can run when packaged on windows.
  multiprocessing.freeze_support()

  if FLAGS.camode.upper() == "PRODUCTION":
    logging.error("Poolclient should not be run against production.")
    exit()

  conf.PARSER.parse_args()

  log_level = logging.INFO
  if FLAGS.verbose:
    log_level = logging.DEBUG
  logging.basicConfig(level=log_level,
                      format="%(levelname)s %(module)s:%(lineno)s] %(message)s")

  registry.Init()

  CreateClientPool(FLAGS.nrclients)

if __name__ == "__main__":
  conf.StartMain(main)
