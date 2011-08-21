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


"""This is the GRR client."""


import logging
import multiprocessing
import os
import time

# Make sure we load the client plugins
from grr.client import client_actions

from grr.client import client_config
from grr.client import client_utils
from grr.client import comms
from grr.client import conf
from grr.client import vfs

FLAGS = conf.PARSER.flags

conf.PARSER.add_option("", "--poll_min",
                       default=1, type="int",
                       help="Minimum time between polls in seconds")

conf.PARSER.add_option("", "--poll_max",
                       default=600, type="int",
                       help="Maximum time between polls in seconds")

conf.PARSER.add_option("", "--poll_slew",
                       default=0.5, type="int",
                       help="Slew of poll time in seconds")

conf.PARSER.add_option("-p", "--process_separate",
                       default=False, action="store_true",
                       help="Use process separation for stability "
                       "[Default:%default]")

conf.PARSER.add_option("", "--camode",
                       default="PRODUCTION", type="string",
                       help="The mode to run in, test,production,staging. This "
                       "affects the CA certificate we trust.")

conf.PARSER.add_option("", "--server_serial_number",
                       default=0, type="int",
                       help="Minimal serial number we accept for server cert.")

conf.PARSER.add_option("-c", "--certificate",
                       default="", type="string",
                       help="A PEM encoded certificate file (combined private "
                       "and X509 key in PEM format)")

FLAGS = conf.PARSER.flags


class GRRClient(object):
  """A stand alone GRR client."""

  stop = False

  def __init__(self):
    """Constructor."""

    ca_cert = client_config.CACERTS.get(FLAGS.camode.upper())
    if not ca_cert:
      raise RuntimeError("Invalid camode specified.")

    if FLAGS.process_separate:
      self.context = comms.ProcessSeparatedContext(ca_cert=ca_cert)
    else:
      self.context = comms.GRRHTTPContext(ca_cert=ca_cert)

    self.context.LoadCertificates()

    # Start off with a maximum poling interval
    self.sleep_time = FLAGS.poll_max

  def Run(self):
    """The client main loop - never exits."""
    # Set up proxies:
    proxies = client_utils.FindProxies()
    if proxies:
      os.environ["http_proxy"] = proxies[0]

    for status in self.context.Run():
      # If we communicated this time we want to continue aggressively
      if status.sent_count > 0 or status.received_count > 0:
        self.sleep_time = FLAGS.poll_min

      logging.debug("Sending %s(%s), Received %s messages. Sleeping for %s",
                    status.sent_count, status.sent_len,
                    status.received_count,
                    self.sleep_time)

      time.sleep(self.sleep_time)

      if self.stop:
        logging.debug("Client stopped by main thread.")
        break

      # Back off slowly
      self.sleep_time = min(FLAGS.poll_max, self.sleep_time + FLAGS.poll_slew)

if __name__ == "__main__":
  # Ensure multiprocesses can run when packaged on windows.
  multiprocessing.freeze_support()

  conf.PARSER.parse_args()

  log_level = logging.INFO
  if FLAGS.verbose:
    log_level = logging.DEBUG
  logging.basicConfig(level=log_level,
                      format="%(levelname)s %(module)s:%(lineno)s] %(message)s")

  vfs.VFSInit()
  client = GRRClient()
  client.Run()
