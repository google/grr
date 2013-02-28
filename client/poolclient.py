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


import pickle
import threading
import time


from grr.client import conf
from grr.client import conf as flags
import logging

from grr.client import client

# pylint: disable=W0611
# Make sure we load the client plugins
from grr.client import client_actions
# pylint: enable=W0611

from grr.client import conf
from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import registry

flags.DEFINE_integer("nrclients", 1,
                     "Number of clients to start")

flags.DEFINE_string("cert_file", "",
                    "Path to a file that stores all certificates for"
                    "the client pool.")

flags.DEFINE_bool("enroll_only", False,
                  "If specified, the script will enroll all clients and exit.")


class PoolGRRClient(client.GRRClient, threading.Thread):
  """A GRR client for running in pool mode."""

  def __init__(self):
    """Constructor."""
    super(PoolGRRClient, self).__init__()
    self.daemon = True
    self.stop = False

    # Is this client already enrolled?
    self.enrolled = False

    self.common_name = self.client.communicator.common_name
    self.private_key = self.client.communicator.private_key

  def Run(self):
    for status in self.client.Run():
      # if the status is 200 we assume we have successfully enrolled.
      if status.code == 200:
        self.enrolled = True

      # Thread should stop now.
      if self.stop:
        break

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
      clients.append(PoolGRRClient(certificate=certificate))

  except (IOError, EOFError):
    pass

  while len(clients) < n:
    # Force the client to regenerate the RSA key pair each time.
    clients.append(PoolGRRClient("Invalid"))

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

  logging.info("Pool done in %s seconds, saving certs.",
               time.time() - start_time)
  try:
    fd = open(flags.FLAGS.cert_file, "wb")
    pickle.dump([x.private_key for x in clients], fd)
    fd.close()
  except IOError:
    pass


def main(unused_argv):
  conf.PARSER.parse_args()

  # Make sure that we do not update the config file when we create new clients.
  flags.FLAGS.client_config = "/dev/null"

  if ("staging" not in flags.FLAGS.location and
      "localhost" not in flags.FLAGS.location):
    logging.error("Poolclient should only be run against test or staging.")
    exit()

  registry.Init()

  # Let the OS handler also handle sleuthkit requests since sleuthkit is not
  # thread safe.
  tsk = rdfvalue.RDFPathSpec.Enum("TSK")
  os = rdfvalue.RDFPathSpec.Enum("OS")
  vfs.VFS_HANDLERS[tsk] = vfs.VFS_HANDLERS[os]

  CreateClientPool(flags.FLAGS.nrclients)

if __name__ == "__main__":
  conf.StartMain(main)
