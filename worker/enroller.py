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

"""A special worker responsible for initial enrollment of clients."""


import re
import sys


from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf
from grr.client import conf as flags

from grr.client import client_config
# pylint: disable=W0611
from grr.lib import data_store
# pylint: enable=W0611
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import key_utils

from grr.lib import registry

# pylint: disable=W0611
# Make sure we load the enroller module
from grr.lib.flows import general
from grr.lib.flows.caenroll import ca_enroller
# pylint: enable=W0611

flags.DEFINE_string("ca_queue_name", "CA",
                    "The name of the queue for this worker.")

FLAGS = flags.FLAGS


def main(unused_argv):
  """Main."""
  # Try to load the CA key.
  ca_pem = key_utils.GetCert(FLAGS.ca)
  registry.CA_KEY = RSA.load_key_string(ca_pem)
  registry.CA_CERT = X509.load_cert_string(ca_pem)

  # Initialise everything
  registry.Init()

  # Start a worker
  token = data_store.ACLToken("GRREnroller", "Implied.")
  worker = flow.GRRWorker(queue_name=FLAGS.ca_queue_name, token=token)
  worker.Run()

if __name__ == "__main__":
  conf.StartMain(main)
