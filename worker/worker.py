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

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import registry


config_lib.DEFINE_string("Worker.queue_name", "W",
                         "The name of the queue for this worker.")


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.SetEnv("Environment.component", "Worker")

  # Initialise flows
  registry.Init()

  # Make the worker section override all others.
  config_lib.CONFIG.ExecuteSection("Worker")

  # Start a worker
  token = access_control.ACLToken("GRRWorker", "Implied.")
  worker = flow.GRRWorker(
      queue_name=config_lib.CONFIG["Worker.queue_name"], token=token)

  worker.Run()

if __name__ == "__main__":
  conf.StartMain(main)
