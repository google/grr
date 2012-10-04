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

"""This is a backend analysis worker which will be deployed on the server.

We basically pull a new task from the task master, and run the plugin
it specifies.
"""


import re
import sys

from grr.client import conf
from grr.client import conf as flags

from grr.client import client_config
from grr import artifacts

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import registry

# Make sure we load the enroller module
from grr.lib.flows import console
from grr.lib.flows import general

flags.DEFINE_string("worker_queue_name", "W",
                    "The name of the queue for this worker.")

FLAGS = flags.FLAGS


def main(unused_argv):
  """Main."""
  # Initialise flows
  registry.Init()

  # Start a worker
  token = data_store.ACLToken("GRRWorker", "Implied.")
  worker = flow.GRRWorker(queue_name=FLAGS.worker_queue_name, token=token)
  worker.Run()

if __name__ == "__main__":
  conf.StartMain(main)
