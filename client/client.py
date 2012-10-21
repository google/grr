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


from grr.client import conf
from grr.client import conf as flags

# pylint: disable=W0611
# Make sure we load the client plugins
from grr.client import client_actions
# pylint: enable=W0611

from grr.client import client_config
from grr.client import client_log
from grr.client import comms
from grr.client import conf
from grr.lib import registry


flags.DEFINE_string("camode", client_config.CAMODE,
                    "The mode to run in, test,production,staging. This "
                    "affects the CA certificate we trust.")

flags.DEFINE_integer("server_serial_number", 0,
                     "Minimal serial number we accept for server cert.")

FLAGS = flags.FLAGS


class GRRClient(object):
  """A stand alone GRR client, which uses the HTTP mechanism."""

  stop = False

  def __init__(self, certificate=None):
    """Constructor."""
    super(GRRClient, self).__init__()
    ca_cert = client_config.CACERTS.get(FLAGS.camode.upper())
    if not ca_cert:
      raise RuntimeError("Invalid camode specified.")

    self.client = comms.GRRHTTPClient(ca_cert=ca_cert, certificate=certificate)

  def Run(self):
    """The client main loop - never exits."""
    # Generate the client forever.
    for _ in self.client.Run():
      pass


def main(unused_args):
  # Ensure multiprocesses can run when packaged on windows.
  multiprocessing.freeze_support()

  conf.PARSER.parse_args()

  client_log.SetUpClientLogging()

  registry.Init()
  client = GRRClient()
  client.Run()


if __name__ == "__main__":
  conf.StartMain(main)
