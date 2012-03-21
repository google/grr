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


import multiprocessing
import platform
import time


from grr.client import conf
from grr.client import conf as flags
import logging

# Make sure we load the client plugins
from grr.client import client_actions

from grr.client import client_config
from grr.client import comms
from grr.client import conf
from grr.lib import registry


flags.DEFINE_float("poll_min", 0.2,
                   "Minimum time between polls in seconds")

flags.DEFINE_float("poll_max", 600,
                   "Maximum time between polls in seconds")

flags.DEFINE_float("poll_slew", 1.15,
                   "Slew of poll time in seconds")

flags.DEFINE_bool("process_separate", False,
                  "Use process separation for stability "
                  "[Default:%default]")

flags.DEFINE_string("camode", client_config.CAMODE,
                    "The mode to run in, test,production,staging. This "
                    "affects the CA certificate we trust.")

flags.DEFINE_integer("server_serial_number", 0,
                     "Minimal serial number we accept for server cert.")

flags.DEFINE_string("certificate", "",
                    "A PEM encoded certificate file (combined private "
                    "and X509 key in PEM format)")

if platform.system() == "Windows":
  flags.DEFINE_string("regpath", client_config.REGISTRY_KEY,
                      "A registry path for storing GRR configuration.")
else:
  flags.DEFINE_string("config", "/etc/grr.ini",
                      "Comma separated list of grr configuration files.")

FLAGS = flags.FLAGS


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
    for status in self.context.Run():
      # If we communicated this time we want to continue aggressively
      if status.high_priority_sent > 0 or status.received_count > 0:
        self.sleep_time = 0

      cn = self.context.communicator.common_name
      logging.debug("%s: Sending %s(%s), Received %s messages. Sleeping for %s",
                    cn, status.sent_count, status.sent_len,
                    status.received_count,
                    self.sleep_time)

      time.sleep(self.sleep_time)

      if self.stop:
        logging.debug("Client stopped by main thread.")
        break

      # Back off slowly at first and fast if no answer.
      self.sleep_time = min(
          FLAGS.poll_max,
          max(FLAGS.poll_min, self.sleep_time) * FLAGS.poll_slew)


def main(unused_args):
  # Ensure multiprocesses can run when packaged on windows.
  multiprocessing.freeze_support()

  conf.PARSER.parse_args()

  log_level = logging.INFO
  if FLAGS.verbose:
    log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
                        format="[%(levelname)s "
                               "%(module)s:%(lineno)s] %(message)s")
  registry.Init()
  client = GRRClient()
  client.Run()


if __name__ == "__main__":
  conf.StartMain(main)
